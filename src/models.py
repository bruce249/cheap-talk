"""models.txt parsing and prices.

Line format:  <spec> [input $/1M] [output $/1M]
  openai:gpt-4.1-nano  0.10  0.40
  hf:google/gemma-3-27b-it:cheapest          # HF prices are looked up from the router if omitted
Lines starting with # are comments.
"""
from pathlib import Path

import httpx

from .llm import parse_spec

FALLBACK = (1.0, 2.0)  # deliberately pessimistic when a price is unknown


def hf_prices():
    try:
        data = httpx.get("https://router.huggingface.co/v1/models", timeout=30).json()["data"]
    except Exception:
        return {}
    out = {}
    for m in data:
        best = None
        for p in m.get("providers", []):
            pr = p.get("pricing") or {}
            if p.get("status") == "live" and pr.get("input") is not None:
                cand = (float(pr["input"]), float(pr.get("output") or pr["input"]), p["provider"])
                if best is None or cand[0] + cand[1] < best[0] + best[1]:
                    best = cand
        if best:
            out[m["id"]] = best
    return out


def load(path="models.txt", verbose=True):
    specs, prices, hf = [], {}, None
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        spec = parts[0]
        provider, model, _ = parse_spec(spec)
        specs.append(spec)
        if len(parts) >= 3:
            prices[spec] = (float(parts[1]), float(parts[2]))
        elif provider == "hf":
            hf = hf if hf is not None else hf_prices()
            base = model.split(":")[0]
            if base in hf:
                prices[spec] = hf[base][:2]
            else:
                prices[spec] = FALLBACK
                if verbose:
                    print(f"[price] {spec}: not found on HF router, assuming ${FALLBACK[0]}/${FALLBACK[1]} per 1M")
        else:
            prices[spec] = FALLBACK
            if verbose:
                print(f"[price] {spec}: no price in models.txt, assuming ${FALLBACK[0]}/${FALLBACK[1]} per 1M")
    return specs, prices
