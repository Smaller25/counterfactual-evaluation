# Rerun of the counterfactual arithmetic task on GPT-4o

Anchor paper: Wu et al., [Reasoning or Reciting? Exploring the Capabilities and Limitations of Language Models Through Counterfactual Evaluations](https://arxiv.org/abs/2307.02477)

## Main argument

On GPT-4o model, the gap of default rule and counterfactual rule is still existing. However, the performance of base 11 is increased than paper performance, also it is quite controversial of affect of CoT too.

## Reasoning and evidence

I rerun 2-digit addition on GPT-4o (via OpenRouter, 2026-11-24) with 200 fresh instances per base and the same prompt as Appendix B Table 1. Base 10 is 100% in both settings, but base 9 is only 37.0% without CoT and 50.5% with CoT, so the gap between default and counterfactual is still existing even the addition procedure is same. Base 11 is increased a lot compared to GPT-4 in the paper (38.4 -> 85.0 without CoT, 56.5 -> 82.5 with CoT), but it is still 15 points or more lower than default. CoT helps on base 9 (37.0 -> 50.5) but not on base 11 (85.0 -> 82.5), so the effect of CoT is not consistent.

## Setup

| Item | Value |
|---|---|
| Model | `openai/gpt-4o` via OpenRouter, temperature 0 |
| Date | 2026-11-24 |
| Task | 2-digit + 2-digit addition |
| Default condition | base 10 |
| Counterfactual conditions | base 9, base 11 |
| Instances | 200 per base, newly sampled, no overlap with the paper's public data |
| Scoring | the paper's scoring code (`arithmetic/eval.py`), unchanged |

For base 9 and 11 I follow the paper's rule: keep only problems whose answer is different from the base-10 answer.

### Prompt (base 9 example)

With 0-shot CoT:

> You are a mathematician. Assuming that all numbers are in base-9 where the digits are "012345678", what is 76+14? Let's think step by step, and end the response with the result in "\boxed{result}".

Without 0-shot CoT:

> You are a mathematician. Assuming that all numbers are in base-9 where the digits are "012345678", what is 76+14? End the response with the result in "\boxed{result}".

## Results

Accuracy in %. The paper row is GPT-4 (`gpt-4-0314`) from Table 18 of the paper, 1,000 instances per base.

| | w/o CoT, base 9 | w/o CoT, base 10 | w/o CoT, base 11 | w/ CoT, base 9 | w/ CoT, base 10 | w/ CoT, base 11 |
|---|---|---|---|---|---|---|
| GPT-4 (paper, n=1000) | 23.4 | 100.0 | 38.4 | 38.6 | 98.2 | 56.5 |
| GPT-4o (mine, n=200) | 37.0 | 100.0 | 85.0 | 50.5 | 100.0 | 82.5 |

Correct counts for GPT-4o (out of 200):

| Base | w/o CoT | w/ CoT |
|---|---|---|
| 10 (default) | 200 | 200 |
| 9 (counterfactual) | 74 | 101 |
| 11 (counterfactual) | 170 | 165 |

### Error check

- All 1,200 responses were parsed by the scoring code, and no response was truncated.
- Wrong answers are mostly not the base-10 answer.

| Condition | Wrong | Wrong and equal to base-10 sum |
|---|---|---|
| base 9, w/o CoT | 126 | 5 |
| base 9, w/ CoT | 99 | 8 |
| base 11, w/o CoT | 30 | 7 |
| base 11, w/ CoT | 35 | 6 |

So the model is not just ignoring the base. It tries to compute in the given base and fails during the computation.

## Limitations

- One model, one run, 200 instances per base, only the arithmetic task.
- The paper used `gpt-4-0314` with 1,000 public instances. Mine is `gpt-4o` with 200 new instances, so the comparison with the paper is rough.
- The base 11 difference between CoT and no CoT is only 5 instances, so it is within noise for n=200.

## Files

- Fresh instances: [`arithmetic/data/261124_fresh/`](arithmetic/data/261124_fresh/)
- Sampling script: [`arithmetic/261124_sample_fresh.py`](arithmetic/261124_sample_fresh.py)
- Run script: [`261124_run_arithmetic_fresh.sh`](261124_run_arithmetic_fresh.sh)
- Raw model outputs and scores: [`arithmetic/output/261124_fresh/`](arithmetic/output/261124_fresh/)
- Query code changed to OpenRouter: [`query_utils.py`](query_utils.py)

## How to reproduce

```bash
export OPENROUTER_API_KEY=...
bash 261124_run_arithmetic_fresh.sh openai/gpt-4o True
bash 261124_run_arithmetic_fresh.sh openai/gpt-4o False
```
