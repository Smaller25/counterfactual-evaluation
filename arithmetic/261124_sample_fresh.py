"""Sample fresh 2-digit addition problems that do NOT appear in the paper's public data.

Same rules as arithmetic/sample.py (for base != 10, keep only problems whose answer differs from the
base-10 answer), but with a new seed, no duplicates, and the public instances excluded.

Usage: python arithmetic/261124_sample_fresh.py <out_file> <n_samples> <base> [seed]
"""
import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.absolute()))

from arithmetic.sample import expr_is_hard, sample_single


def main(output_file, n_samples, base, seed=261124):
    n_samples, base, seed = int(n_samples), int(base), int(seed)
    random.seed(seed * 100 + base)
    public = Path(__file__).parent / "data" / "0shot" / f"base{base}.txt"
    seen = set(public.read_text().split())
    fresh = []
    while len(fresh) < n_samples:
        expr = sample_single(2, base)
        if expr in seen or (base != 10 and not expr_is_hard(expr, base)):
            continue
        seen.add(expr)
        fresh.append(expr)
    Path(output_file).write_text("\n".join(fresh) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:])
