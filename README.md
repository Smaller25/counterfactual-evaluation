# Reasoning or Reciting? Exploring the Capabilities and Limitations of Language Models Through Counterfactual Evaluations

This repo contains the code, data, and model interactions (prompts and model responses) that we used in our paper, [Reasoning or Reciting? Exploring the Capabilities and Limitations of Language Models Through Counterfactual Evaluations](https://arxiv.org/abs/2307.02477). Each task has its own README file with more details. You can install the dependencies via `pip install -r requirements.txt` (we have noticed that this sometimes fails on a mac; try linux). We tested with Python 3.11 though it is likely that other versions would also work. Unless otherwise mentioned, all commands in the README files should be run from the root directory of this repo, i.e. here.

**Local change:** `query_utils.py` now sends every query through [OpenRouter](https://openrouter.ai). Export `OPENROUTER_API_KEY` and pass an OpenRouter model id (e.g. `openai/gpt-4o`) wherever the READMEs say `gpt-4-0314`. Optional: `OPENROUTER_CONCURRENCY` (default 16) and `OPENROUTER_EXTRA_BODY` (JSON merged into each request, e.g. to pin a provider). The paper's original model names (`gpt-4-0314`, `gpt-3.5-turbo-0301`, `claude-v1.3`, `models/text-bison-001`) are not served by OpenRouter and only work through the cache described below.

Nevertheless, if you want to reproduce our experiments, you can convert our provided model interactions files into a cache file, and then our query function will automatically reuse the cache content without making API calls. You should be able to reproduce all of our experiments this way, except for the natural language logic task where the author shared with us a non-public version of the dataset (see our paper for more details). To do this conversion, run
```bash
python create_cache.py {arithmetic,programming/execution,programming/generation,syntax,spatial,drawing,music/chords,music/melodies,chess,SET}/model_interactions
```
Using this cache, you should obtain the exact numbers from our paper, unless otherwise mentioned in the individual README files when some version of randomness is involved.
Note that the model interactions for the logic task needs to be downloaded separately, see [its `README.md`](logic/README.md) for more details. If you choose to do so, you should include the logic task in the above command as well.

A general note: you may see mentions of "controls" in our code/file names. You can mentally subsitute it to "CCC"---it was an old name for that.
