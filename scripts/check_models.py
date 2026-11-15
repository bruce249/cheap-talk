"""Check models.txt before spending anything.

  python -m scripts.check_models              # ping each model once (costs a fraction of a cent)
  python -m scripts.check_models --list openai   # list model ids your key can use (also: xai, hf)
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import models as M  # noqa: E402
from src.llm import PROVIDERS, Router  # noqa: E402


def list_models(provider, grep=""):
    base, env = PROVIDERS[provider]
    if provider == "hf":
        prices = M.hf_prices()
        for mid, (i, o, prov) in sorted(prices.items(), key=lambda kv: kv[1][0] + kv[1][1]):
            if grep.lower() in mid.lower():
                print(f"hf:{mid}:cheapest   in ${i}/M  out ${o}/M  (via {prov})")
        return
    r = httpx.get(base + "/models", headers={"Authorization": f"Bearer {os.environ[env]}"}, timeout=30)
    r.raise_for_status()
    for m in sorted(x["id"] for x in r.json()["data"]):
        if grep.lower() in m.lower():
            print(f"{provider}:{m}")


async def ping(a):
    specs, prices = M.load(a.models)
    r = Router(prices=prices, max_retries=2)
    msgs = [{"role": "system", "content": "Answer in one sentence, then end with exactly:\nFINAL ANSWER: <answer>\n"
                                          "CONFIDENCE: <0-100>\nSOURCES DISAGREE: <yes or no>"},
            {"role": "user", "content": "Question: What is the capital of France?\n\n[1] Paris is the capital of France."}]
    res = await asyncio.gather(*[r.chat(s, msgs, max_tokens=300) for s in specs])
    bad = 0
    for s, x in zip(specs, res):
        pin, pout = prices[s]
        if x.get("error"):
            bad += 1
            print(f"FAIL  {s}: {x['error'][:220]}")
        else:
            ok = all(k in x["content"].upper() for k in ("FINAL ANSWER", "CONFIDENCE", "SOURCES DISAGREE"))
            u = x.get("usage") or {}
            print(f"{'ok  ' if ok else 'WARN'}  {s:55s} ${pin}/${pout} per 1M   {u.get('completion_tokens','?')} out tokens"
                  + ("" if ok else "   <- missing required lines; reply: " + x["content"][:120].replace("\n", " | ")))
    await r.close()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="models.txt")
    ap.add_argument("--list", choices=list(PROVIDERS), default=None)
    ap.add_argument("--grep", default="")
    a = ap.parse_args()
    if a.list:
        list_models(a.list, a.grep)
    else:
        asyncio.run(ping(a))
