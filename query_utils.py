import aiohttp
import asyncio
import json
import os
import pickle
from math import ceil, log2
from random import random

from tqdm.asyncio import tqdm_asyncio

HISTORY_FILE = "history.jsonl"
CACHE_FILE = "query_cache.pkl"
OPENAI_REFRESH_QUOTA = 60
OPENAI_EXP_CAP = int(ceil(log2(OPENAI_REFRESH_QUOTA)))
BATCH_SIZE = 300  # sometimes APIs complain if we too many concurrent requests

# All queries go through OpenRouter (https://openrouter.ai). Settings, all via environment variables:
#   OPENROUTER_API_KEY      required (only when a prompt is not already in the cache)
#   OPENROUTER_BASE_URL     optional, default https://openrouter.ai/api/v1
#   OPENROUTER_CONCURRENCY  optional, max simultaneous requests, default 16
#   OPENROUTER_EXTRA_BODY   optional JSON merged into every request body, e.g.
#                           '{"provider": {"order": ["openai"]}, "reasoning": {"enabled": false}}'
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
OPENROUTER_CONCURRENCY = int(os.environ.get("OPENROUTER_CONCURRENCY", "16"))
OPENROUTER_TIMEOUT = 600  # seconds, per request
OPENROUTER_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529}


class OpenRouterError(RuntimeError):
    pass


async def query_openrouter(
    prompt,
    model_name,
    system_msg=None,
    history=None,
    max_tokens=None,
    temperature=0,
    retry=100,
    session=None,
    semaphore=None,
    **kwargs,
):
    messages = []
    if system_msg is not None:
        messages += [{"role": "system", "content": system_msg}]
    messages += [{"role": "user", "content": prompt}]
    if history is not None:
        messages = list(history) + messages
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    kwargs["temperature"] = temperature
    extra_body = os.environ.get("OPENROUTER_EXTRA_BODY")
    if extra_body:
        kwargs.update(json.loads(extra_body))

    headers = {
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {"model": model_name, "messages": messages, **kwargs}

    for i in range(retry + 1):
        wait_time = (1 << min(i, OPENAI_EXP_CAP)) + random() / 10
        try:
            async with semaphore:
                async with session.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=payload
                ) as resp:
                    status = resp.status
                    text = await resp.text()
            try:
                response = json.loads(text)
            except json.JSONDecodeError:
                response = {"error": {"code": status, "message": text[:500]}}
            # OpenRouter can report an upstream failure either as an HTTP error or inside a 200 body
            error = response.get("error")
            if error is None and response.get("choices"):
                error = response["choices"][0].get("error")
            if error is None and status == 200 and not response.get("choices"):
                error = {"code": 502, "message": "no choices in response"}
            if error is not None or status != 200:
                code = error.get("code", status) if isinstance(error, dict) else status
                if status != 200:
                    code = status
                msg = f"OpenRouter error {code} for model {model_name}: {error}"
                if code in OPENROUTER_RETRYABLE_STATUS and i < retry:
                    await asyncio.sleep(wait_time)
                    continue
                raise OpenRouterError(msg)
            with open(HISTORY_FILE, "a") as f:
                f.write(json.dumps((model_name, messages, kwargs, response)) + "\n")
            choice = response["choices"][0]
            if choice.get("finish_reason") != "stop":
                print("Truncated response!")
                print(response)
            return choice["message"].get("content") or ""
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if i == retry:
                raise e
            else:
                await asyncio.sleep(wait_time)


def query_batch_wrapper(fn, prompts, *args, **kwargs):
    # I have never used asyncio and have no idea if this a sane way to do this, but it works
    async def _query(prompts):
        timeout = aiohttp.ClientTimeout(total=OPENROUTER_TIMEOUT)
        semaphore = asyncio.Semaphore(OPENROUTER_CONCURRENCY)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async_responses = [
                fn(prompt, *args, session=session, semaphore=semaphore, **kwargs) for prompt in prompts
            ]
            return await tqdm_asyncio.gather(*async_responses)

    all_results = []
    for start in range(0, len(prompts), BATCH_SIZE):
        prompts_batch = prompts[start : start + BATCH_SIZE]
        all_results.extend(asyncio.run(_query(prompts_batch)))
    return all_results


def escape(s):
    return s.encode("unicode_escape").decode("utf-8")


def unescape(s):
    return s.encode("utf-8").decode("unicode_escape")


def query_batch(
    prompts,
    model_name,
    system_msg=None,
    history=None,
    max_tokens=None,
    temperature=0,
    retry=100,
    num_beams=1,
    skip_cache=False,
    n=1,
    **openai_kwargs,
):
    cache = {}
    if not skip_cache and os.path.exists(CACHE_FILE):
        cache = pickle.load(open(CACHE_FILE, "rb"))

    # sorry this is ugly, but for backward compatibility
    prompt2key = lambda p: (
        p,
        model_name,
        system_msg,
        tuple(history) if history is not None else None,
        max_tokens,
        temperature,
        num_beams,
    ) if n == 1 else (
        p,
        model_name,
        system_msg,
        tuple(history) if history is not None else None,
        max_tokens,
        temperature,
        num_beams,
        n,
    )

    unseen_prompts = set()
    for prompt in prompts:
        key = prompt2key(prompt)
        if key not in cache:
            unseen_prompts.add(prompt)
    unseen_prompts = list(unseen_prompts)

    if len(unseen_prompts) > 0:
        if "OPENROUTER_API_KEY" not in os.environ:
            raise OpenRouterError(
                f"{len(unseen_prompts)} prompt(s) are not in {CACHE_FILE}; set OPENROUTER_API_KEY to query them."
            )
        if "/" not in model_name or model_name.startswith("models/"):
            raise OpenRouterError(
                f"'{model_name}' is not an OpenRouter model id (expected e.g. 'openai/gpt-4o'). The paper's "
                "original model names only work for prompts that are already in the cache."
            )
        # Not every provider behind OpenRouter supports `n`, so we send n separate requests instead.
        if n > 1:
            num_prompts = len(unseen_prompts)
            orig_unseen_prompts = unseen_prompts
            unseen_prompts = [prompt for prompt in unseen_prompts for _ in range(n)]
        responses = query_batch_wrapper(
            query_openrouter,
            unseen_prompts,
            model_name,
            system_msg,
            history,
            max_tokens,
            temperature,
            retry,
            **openai_kwargs,
        )
        if n > 1:
            responses = [responses[i : i + n] for i in range(0, len(responses), n)]
            assert len(responses) * n == num_prompts * n == sum(len(r) for r in responses) == len(unseen_prompts)
            unseen_prompts = orig_unseen_prompts

        # Reload cache for better concurrency. Otherwise multiple query processes can overwrite
        # each other
        cache = {}
        if not skip_cache:
            if os.path.exists(CACHE_FILE):
                cache = pickle.load(open(CACHE_FILE, "rb"))
        for prompt, response in zip(unseen_prompts, responses, strict=True):
            key = prompt2key(prompt)
            cache[key] = response
        if not skip_cache:
            pickle.dump(cache, open(CACHE_FILE, "wb"))

    interactions_save_path = os.environ.get("INTERACTIONS_SAVE_PATH")
    if interactions_save_path is not None:
        assert not os.path.exists(interactions_save_path)
        with open(interactions_save_path, "w") as f:
            for prompt in prompts:
                key = prompt2key(prompt)
                assert isinstance(cache[key], (str, list))
                f.write(
                    escape(prompt)
                    + "\t"
                    + escape(str(cache[key]))
                    + "\t"
                    + str(isinstance(cache[key], list))
                    + "\t"
                    + "\t".join([escape(str(x)) if x is not None else "None" for x in key[1:]])
                    + "\n"
                )

    return [cache[prompt2key(prompt)] for prompt in prompts]
