"""Human validation of the automatic scoring.

1) python -m src.label sample --n 60     -> results/human_labels.csv
   Values appear as A/B in random order. Fill `human` with A, B, both or neither,
   and `disagree` with y/n (does the reply tell the user the sources disagree?).
   Hide the columns starting with _ while labelling.
2) python -m src.label score             -> results/human_validation.md (agreement + Cohen's kappa)
"""
import json
import random
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def sample(n, raw="results/raw.jsonl", scored="results/scored.jsonl"):
    prompts = {p["pid"]: p for p in map(json.loads, (ROOT / "data/prompts.jsonl").open(encoding="utf-8"))}
    S = pd.DataFrame([json.loads(l) for l in (ROOT / scored).open(encoding="utf-8")])
    texts = {}
    for l in (ROOT / raw).open(encoding="utf-8"):
        r = json.loads(l)
        if not r.get("error"):
            for t, turn in enumerate(r["turns"]):
                texts[(r["pid"], r["model"], t)] = turn["content"]
    S = S.sample(frac=1, random_state=7).groupby("condition").head(n // S.condition.nunique() + 1).head(n)
    rng, rows = random.Random(7), []
    for _, r in S.iterrows():
        p = prompts[r.pid]
        swap = rng.random() < 0.5
        A, Bv = (p["false"], p["true"]) if swap else (p["true"], p["false"])
        rows.append(dict(key=f"{r.pid}|{r.model}|{r.turn}", question=p["question"], value_A=A, value_B=Bv,
                         reply=texts.get((r.pid, r.model, r.turn), ""), human="", disagree="",
                         _swap=int(swap), _auto=r.stance, _auto_disagree=r.disagree))
    out = ROOT / "results/human_labels.csv"
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8")
    print(f"wrote {len(rows)} rows -> {out}")


def kappa(a, b):
    labs, n = sorted(set(a) | set(b)), len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labs)
    return ((po - pe) / (1 - pe) if pe < 1 else 1.0), po


def score():
    d = pd.read_csv(ROOT / "results/human_labels.csv", dtype=str, keep_default_na=False, encoding="utf-8")
    d = d[d.human.str.strip() != ""]
    sw = d._swap.astype(int)
    def truth(h, s):
        h = h.strip().upper()
        if h in ("A", "B"):
            return {"A": "false", "B": "true"}[h] if s else {"A": "true", "B": "false"}[h]
        return h.lower()
    hs = [truth(h, s) for h, s in zip(d.human, sw)]
    k, acc = kappa(hs, d._auto.str.lower().tolist())
    lines = [f"Human-labelled replies: {len(d)}", f"Automatic stance vs human: agreement {100*acc:.1f}%, Cohen's kappa {k:.2f}"]
    c = d[d.disagree.str.strip() != ""]
    if len(c):
        h = [x.strip().lower().startswith("y") for x in c.disagree]
        au = [x.strip().lower() == "true" for x in c._auto_disagree]
        k2, a2 = kappa(h, au)
        lines.append(f"'Sources disagree' line vs human reading of the reply: agreement {100*a2:.1f}%, kappa {k2:.2f}")
    (ROOT / "results/human_validation.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "sample":
        kw = {}
        for flag in ("--raw", "--scored"):
            if flag in args:
                kw[flag[2:]] = args[args.index(flag) + 1]
        sample(int(args[args.index("--n") + 1]) if "--n" in args else 60, **kw)
    else:
        score()
