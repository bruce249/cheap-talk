"""Async chat clients for OpenAI, xAI and Hugging Face Inference Providers, with retries,
per-provider concurrency limits, cost tracking and a hard budget cap.

Model spec:   <provider>:<model>[?param=value&...]
  openai:gpt-4.1-nano                         needs OPENAI_API_KEY
  xai:grok-4-1-fast-non-reasoning             needs XAI_API_KEY
  hf:google/gemma-3-27b-it:cheapest           needs HF_TOKEN (":cheapest" = cheapest live provider)
  openai:gpt-5-nano?reasoning_effort=minimal&max_tokens=1500   extra body params / per-model max_tokens
"""
import asyncio
import hashlib
import os
import random
import re
import time
from urllib.parse import parse_qsl

import httpx

PROVIDERS = {
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "xai": ("https://api.x.ai/v1", "XAI_API_KEY"),
    "hf": ("https://router.huggingface.co/v1", "HF_TOKEN"),
}
DEFAULT_CONC = {"openai": 16, "xai": 8, "hf": 6}
THINK = re.compile(r"<think>.*?</think>", re.S)


class LLMError(Exception):
    pass


def parse_spec(spec):
    if ":" not in spec or spec.split(":", 1)[0] not in PROVIDERS:
        raise SystemExit(f"bad model spec '{spec}': use openai:<id>, xai:<id> or hf:<org/model>")
    provider, rest = spec.split(":", 1)
    model, _, q = rest.partition("?")
    params = dict(parse_qsl(q))
    for k, v in list(params.items()):
        if v.replace(".", "", 1).isdigit():
            params[k] = float(v) if "." in v else int(v)
    return provider, model, params


class Budget:
    """Shared spend tracker. `spent` starts from costs already logged in the output file."""

    def __init__(self, cap, spent=0.0):
        self.cap, self.spent = cap, spent

    def add(self, x):
        self.spent += x

    def exhausted(self):
        return self.cap is not None and self.spent >= self.cap


def cost_of(usage, prices, provider):
    if not usage or not prices:
        return 0.0
    pin, pout = prices
    i = usage.get("prompt_tokens") or 0
    o = usage.get("completion_tokens") or 0
    det = usage.get("completion_tokens_details") or {}
    # xAI reports reasoning tokens separately from completion tokens; both are billed as output.
    if provider == "xai":
        o += det.get("reasoning_tokens") or 0
    return (i * pin + o * pout) / 1e6


class Router:
    def __init__(self, prices=None, budget=None, timeout=180, max_retries=6):
        self.client = httpx.AsyncClient(timeout=timeout)
        self.max_retries = max_retries
        self.prices = prices or {}          # spec -> (in $/1M, out $/1M)
        self.budget = budget or Budget(None)
        self.quirks = {}
        self.sems = {p: asyncio.Semaphore(int(os.environ.get(f"CONC_{p.upper()}", c))) for p, c in DEFAULT_CONC.items()}

    async def chat(self, spec, messages, temperature=0.7, max_tokens=300):
        if self.budget.exhausted():
            return dict(content=None, error="budget cap reached", latency=0.0, cost=0.0)
        provider, model, params = parse_spec(spec)
        base, env = PROVIDERS[provider]
        base = os.environ.get(f"{provider.upper()}_BASE_URL", base)   # override only for testing
        key = os.environ.get(env)
        if not key:
            raise SystemExit(f"Set {env} to use {spec} (or run with --mock).")
        url = base + "/chat/completions"
        headers = {"Authorization": f"Bearer {key}"}
        params = dict(params)
        max_tokens = params.pop("max_tokens", max_tokens)
        delay, attempt, adjust = 2.0, 0, 0
        async with self.sems[provider]:
            while attempt < self.max_retries:
                q = self.quirks.setdefault(spec, {"mct": provider == "openai" and model.startswith(("gpt-5", "o")),
                                                  "notemp": provider == "openai" and model.startswith(("gpt-5", "o"))})
                body = dict(model=model, messages=messages, **params)
                body["max_completion_tokens" if q["mct"] else "max_tokens"] = max_tokens
                if not q["notemp"]:
                    body["temperature"] = temperature
                t0 = time.time()
                try:
                    r = await self.client.post(url, json=body, headers=headers)
                    if r.status_code == 400 and adjust < 4:
                        txt = r.text.lower()
                        if "max_tokens" in txt and "max_tokens" in body:
                            q["mct"] = True; adjust += 1; continue
                        if "temperature" in txt and "temperature" in body:
                            q["notemp"] = True; adjust += 1; continue
                    if r.status_code in (401, 403):
                        return dict(content=None, error=f"HTTP {r.status_code} auth: {r.text[:200]}", latency=0.0, cost=0.0)
                    if r.status_code == 402:
                        return dict(content=None, error=f"HTTP 402 out of credits: {r.text[:200]}", latency=0.0, cost=0.0)
                    if r.status_code in (408, 409, 429, 500, 502, 503, 504):
                        ra = r.headers.get("retry-after")
                        if ra and ra.replace(".", "", 1).isdigit():
                            delay = max(delay, float(ra))
                        raise LLMError(f"HTTP {r.status_code}: {r.text[:200]}")
                    if r.status_code >= 400:
                        return dict(content=None, error=f"HTTP {r.status_code}: {r.text[:300]}", latency=0.0, cost=0.0)
                    j = r.json()
                    usage = j.get("usage") or {}
                    c = cost_of(usage, self.prices.get(spec), provider)
                    self.budget.add(c)
                    ch = j["choices"][0]
                    content = THINK.sub("", (ch.get("message") or {}).get("content") or "").strip()
                    if not content:
                        raise LLMError(f"empty content (finish_reason={ch.get('finish_reason')}); raise max_tokens")
                    return dict(content=content, usage=usage, latency=time.time() - t0, cost=c, error=None)
                except (httpx.HTTPError, LLMError, KeyError, IndexError, ValueError) as e:
                    attempt += 1
                    if attempt >= self.max_retries:
                        return dict(content=None, error=f"{type(e).__name__}: {e}", latency=time.time() - t0, cost=0.0)
                    await asyncio.sleep(delay + random.random())
                    delay = min(delay * 2, 60)
        return dict(content=None, error="exhausted retries", latency=0.0, cost=0.0)

    async def close(self):
        await self.client.aclose()


class Mock:
    """Fake model for pipeline tests: over-trusts cheap signals, partly heeds the system check."""

    def __init__(self, *a, **k):
        self.budget = Budget(None)

    async def chat(self, spec, messages, temperature=0.7, max_tokens=300):
        await asyncio.sleep(0)
        sys_, first = messages[0]["content"], messages[1]["content"]
        h = int(hashlib.md5((spec + str(len(messages)) + first[:500]).encode()).hexdigest(), 16)
        r = random.Random(h)
        p = 0.15
        if "Republished from" in first: p += 0.25
        if "Independent report" in first: p += 0.30
        if "Definitive, Expert-Verified" in first: p += 0.15
        if "Verified source" in first: p += 0.15
        if "FAILED" in sys_: p -= 0.10
        elif "[Content credential]" in first and "PASSED" not in sys_: p += 0.35
        if "PASSED" in sys_: p -= 0.10
        if "spoof" in spec and "check PASSED" in first: p += 0.2
        if any(w in first for w in ("Island", "Systems", "lizard", "Festival", "town of", "compound")): p += 0.10
        if len(messages) > 2:
            p = 0.7 if "<<FALSE>>" in messages[-2]["content"] else 0.08
        pick_false = r.random() < max(0.02, min(0.95, p))
        conf = r.randint(70, 98) if pick_false else r.randint(55, 95)
        txt = (f"The sources indicate the answer below [1].\nFINAL ANSWER: {'<<FALSE>>' if pick_false else '<<TRUE>>'}\n"
               f"CONFIDENCE: {conf}\nSOURCES DISAGREE: {'yes' if r.random() < 0.4 else 'no'}")
        return dict(content=txt, usage={"prompt_tokens": 600, "completion_tokens": 50}, latency=0.0, cost=0.0, error=None)

    async def close(self):
        pass
