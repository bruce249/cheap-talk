"""Run every prompt against every model: answer, then one neutral pushback.

Resumable (rows already in the output file are skipped) and budget-capped: the runner adds up the
cost of everything already logged plus new calls and stops starting conversations at --budget.

  python -m src.run --budget 4                         # full run
  python -m src.run --limit 10 --out results/pilot_raw.jsonl --budget 0.3    # pilot
  python -m src.run --mock --limit 20                  # dry run, no keys, no cost
"""
import argparse
import asyncio
import json
from pathlib import Path

from tqdm import tqdm

from . import models as M
from .llm import Budget, Mock, Router

ROOT = Path(__file__).resolve().parent.parent


def existing(out):
    """Rows already done in `out`, and money already spent across ALL non-mock raw files in results/,
    so the budget cap covers pilot + main run together."""
    done, spent = set(), 0.0
    for f in sorted(out.parent.glob("*raw*.jsonl")):
        if f.name.startswith("mock") and not out.name.startswith("mock"):
            continue
        for l in f.open(encoding="utf-8"):
            try:
                r = json.loads(l)
            except json.JSONDecodeError:
                continue
            spent += sum(t.get("cost", 0) or 0 for t in r.get("turns", []))
            if f == out and not r.get("error"):
                done.add((r["pid"], r["model"]))
    return done, spent


async def converse(client, p, spec, a):
    msgs = [{"role": "system", "content": p["system"]}, {"role": "user", "content": p["user"]}]
    turns = []
    for t in range(1 + a.pushbacks):
        if t:
            msgs.append({"role": "user", "content": p["pushback"]})
        res = await client.chat(spec, msgs, temperature=a.temperature, max_tokens=a.max_tokens)
        if res.get("error"):
            return dict(pid=p["pid"], model=spec, turns=turns, error=res["error"])
        raw = res["content"]
        shown = raw.replace("<<TRUE>>", p["true"]).replace("<<FALSE>>", p["false"]) if a.mock else raw
        turns.append(dict(content=shown, usage=res.get("usage"), cost=res.get("cost", 0.0)))
        msgs.append({"role": "assistant", "content": raw})
    return dict(pid=p["pid"], model=spec, turns=turns, error=None)


async def main_async(a):
    prompts = [json.loads(l) for l in (ROOT / a.prompts).open(encoding="utf-8")]
    if a.conditions:
        keep = set(a.conditions.split(","))
        prompts = [p for p in prompts if p["condition"] in keep]
    if a.limit:
        ids = sorted({p["item_id"] for p in prompts})
        k = [i for i in ids if i.startswith("K")][: a.limit // 2]
        v = [i for i in ids if i.startswith("V")][: a.limit - len(k)]
        keep = set(k + v)
        prompts = [p for p in prompts if p["item_id"] in keep]
    if a.mock:
        specs, prices = ["mock:alpha", "mock:beta"], {}
    else:
        specs, prices = M.load(ROOT / a.models)
        if a.only:
            specs = [s for s in specs if any(o in s for o in a.only.split(","))]
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    done, spent = existing(out)
    budget = Budget(a.budget, spent)
    client = Mock() if a.mock else Router(prices=prices, budget=budget)
    if a.mock:
        client.budget = budget
    # interleave models so a budget stop leaves every model with partial, comparable coverage
    jobs = [(p, s) for p in prompts for s in specs if (p["pid"], s) not in done]
    print(f"{len(prompts)} prompts x {len(specs)} models: {len(jobs)} to run, {len(done)} done, "
          f"${spent:.3f} already spent, budget ${a.budget}")
    sem = asyncio.Semaphore(a.concurrency)

    async def guarded(p, s):
        async with sem:
            if budget.exhausted():
                return None
            return await converse(client, p, s, a)

    errors, stopped = 0, 0
    with out.open("a", encoding="utf-8") as fh:
        tasks = [asyncio.create_task(guarded(p, s)) for p, s in jobs]
        bar = tqdm(asyncio.as_completed(tasks), total=len(tasks), mininterval=5)
        for fut in bar:
            r = await fut
            if r is None:
                stopped += 1
                continue
            errors += bool(r["error"])
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
            if (bar.n % 100) == 0:
                bar.set_postfix(spent=f"${budget.spent:.3f}", err=errors, refresh=False)
    await client.close()
    print(f"finished: {errors} errors, {stopped} skipped by budget cap, total spent ${budget.spent:.3f}")
    if errors:
        print("rerun the same command to retry errors")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="models.txt")
    ap.add_argument("--only", default="", help="comma-separated substrings to select models")
    ap.add_argument("--prompts", default="data/prompts.jsonl")
    ap.add_argument("--out", default="results/raw.jsonl")
    ap.add_argument("--conditions", default="")
    ap.add_argument("--limit", type=int, default=0, help="number of items (half known, half void)")
    ap.add_argument("--pushbacks", type=int, default=1, choices=[0, 1])
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--budget", type=float, default=4.0, help="hard cap in USD across all results/*raw*.jsonl files (pilot + main)")
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    if a.mock and a.out == "results/raw.jsonl":
        a.out = "results/mock_raw.jsonl"
    asyncio.run(main_async(a))


if __name__ == "__main__":
    main()
