#!/bin/bash
# Rerun the paper's 2-digit addition task (default base 10 vs counterfactual base 9 / 11) on fresh instances.
# Usage: bash 261124_run_arithmetic_fresh.sh <openrouter model id> [cot: True|False]
# Needs OPENROUTER_API_KEY. Prompt = Appendix B, Table 1 of the paper (arithmetic/query.py: templatize).
set -e
MODEL=${1:?usage: bash 261124_run_arithmetic_fresh.sh <openrouter model id> [True|False]}
COT=${2:-True}
OUT=arithmetic/output/261124_fresh/$(echo "$MODEL" | tr '/' '_')_0cot${COT}
mkdir -p "$OUT"
for BASE in 10 9 11; do
    [ -f "$OUT/base${BASE}.txt" ] || python arithmetic/query.py arithmetic/data/261124_fresh/base${BASE}.txt ${BASE} "$MODEL" "$OUT/base${BASE}.txt" ${COT}
    echo "model=$MODEL date=$(TZ=Asia/Seoul date +%F) cot=$COT base=$BASE n=$(wc -l < arithmetic/data/261124_fresh/base${BASE}.txt) $(python arithmetic/eval.py "$OUT/base${BASE}.txt" ${BASE} | tail -1)" | tee -a "$OUT/summary.txt"
done
