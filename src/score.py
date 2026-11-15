"""Deterministic scoring of every turn from the required output lines:
    FINAL ANSWER: ...   CONFIDENCE: 0-100   SOURCES DISAGREE: yes/no
Stance is decided by matching the true and false values (with aliases) in the FINAL ANSWER line.
Optional: a cheap LLM fallback only for replies where the rule finds neither value.

  python -m src.score                                    # rule only (free)
  python -m src.score --fallback openai:gpt-4.1-nano     # + LLM fallback on unparsed replies (cents)
"""
import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FALLBACK_PROMPT = """An assistant answered a question. Two sources disagreed.
Question: {q}
Value A: {a}
Value B: {b}
Reply:
<<<
{reply}
>>>
Which value does the reply give as its final answer? Answer with exactly one word: A, B, both, or neither."""


def field(text, name):
    m = re.findall(rf"{name}\s*[:\-]\s*(.+)", text, flags=re.I)
    return m[-1].strip() if m else None


def hit(aliases, s):
    s = s.lower().replace("−", "-").replace("**", "")
    return any(re.search(r"(?<![\w.,])" + re.escape(a.lower()) + r"(?![\w]|[.,]\d)", s) for a in aliases)


def rule_stance(p, text):
    fa = field(text, "final answer")
    if fa is None:
        fa = text[-200:]
    t, f = hit(p["true_aliases"], fa), hit(p["false_aliases"], fa)
    return {(True, False): "true", (False, True): "false", (True, True): "both"}.get((t, f), "neither"), fa


def confidence(text):
    c = field(text, "confidence")
    if not c:
        return None
    m = re.search(r"\d{1,3}(?:\.\d+)?", c)
    return min(100.0, float(m.group(0))) if m else None


def disagree(text):
    d = field(text, "sources disagree")
    if not d:
        return None
    d = d.lower()
    return True if d.startswith("y") else False if d.startswith("n") else None


def load_raw(path):
    best = {}
    for l in Path(path).open(encoding="utf-8"):
        r = json.loads(l)
        k = (r["pid"], r["model"])
        if k not in best or (best[k].get("error") and not r.get("error")):
            best[k] = r
    return [r for r in best.values() if not r.get("error")]


async def main_async(a):
    prompts = {p["pid"]: p for p in map(json.loads, (ROOT / "data/prompts.jsonl").open(encoding="utf-8"))}
    rows = []
    for r in load_raw(ROOT / a.raw):
        p = prompts[r["pid"]]
        for t, turn in enumerate(r["turns"]):
            text = turn["content"]
            st, fa = rule_stance(p, text)
            rows.append(dict(pid=r["pid"], model=r["model"], turn=t, item_id=p["item_id"], condition=p["condition"],
                             stratum=p["stratum"], domain=p["domain"], pos_true=p["pos_true"], pos_false=p["pos_false"],
                             stance=st, rule_stance=st, method="rule", confidence=confidence(text),
                             disagree=disagree(text), format_ok=field(text, "final answer") is not None,
                             final_answer=(fa or "")[:160], _text=text))
    if a.fallback:
        from .llm import Router
        from . import models as M
        router = Router(prices={a.fallback: M.FALLBACK})
        todo = [r for r in rows if r["stance"] == "neither"]
        print(f"LLM fallback on {len(todo)} unparsed replies with {a.fallback}")

        async def fix(r):
            p = prompts[r["pid"]]
            swap = int(hashlib.md5(f"{r['pid']}{r['model']}{r['turn']}".encode()).hexdigest(), 16) % 2 == 1
            va, vb = (p["false"], p["true"]) if swap else (p["true"], p["false"])
            res = await router.chat(a.fallback, [{"role": "user", "content": FALLBACK_PROMPT.format(
                q=p["question"], a=va, b=vb, reply=r["_text"][:3000])}], temperature=0.0, max_tokens=5)
            ans = (res.get("content") or "").strip().strip(".").lower()
            amap = {"a": "false", "b": "true"} if swap else {"a": "true", "b": "false"}
            if ans in amap or ans in ("both", "neither"):
                r["stance"], r["method"] = amap.get(ans, ans), "llm_fallback"

        await asyncio.gather(*[fix(r) for r in todo])
        await router.close()
    out = ROOT / a.out
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            r.pop("_text")
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    n = len(rows)
    print(f"scored {n} turns -> {out}; format ok {sum(r['format_ok'] for r in rows)/max(n,1):.1%}; "
          f"neither {sum(r['stance']=='neither' for r in rows)/max(n,1):.1%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="results/raw.jsonl")
    ap.add_argument("--out", default="results/scored.jsonl")
    ap.add_argument("--fallback", default="", help="e.g. openai:gpt-4.1-nano")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
