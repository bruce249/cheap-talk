# Cheap Talk: Answer Engines Ignore Failed Signature Checks and Trust Forgeable Signals

Code and data for a project at the Apart Research AI x Epistemics Research Sprint (13–15 November 2026).
The report is [`report/Cheap_Talk_Answer_Engines_Ignore_Failed_Signature_Checks.pdf`](report/Cheap_Talk_Answer_Engines_Ignore_Failed_Signature_Checks.pdf)
(LaTeX source in `report/paper/main.tex`).

When retrieved sources disagree, an answer engine has to decide which one to believe. Some trust signals
cost an attacker nothing to fake: a reliability badge pasted into a page, a page saying it was verified,
the same article syndicated to several sites, confident writing with an invented statistic. Others are
costly: a signature the search system actually checks, and agreement among sources that are really
independent. We measure how far each signal moves models toward a false claim, whether a real signature
check reported in the system prompt helps, and whether it still helps when the attacker's page imitates it.

## Main results

Eight models (OpenAI, xAI, Meta, Alibaba, DeepSeek, Google), 120 questions, 9 conditions, 17,280 scored
turns, $1.98 in API costs. On invented facts that only the sources can settle:

- GEO-style writing raised adoption of the false value by 54 percentage points; a forged badge or a
  self-declared "verified" line by 15 points each.
- Three syndicated copies of one article had 86% of the effect of three independent sources.
- A system report that the forged badge FAILED verification changed nothing (−1.0 points, 95% CI −5.6 to
  +3.5). A report that the true source PASSED raised true answers by 43 points.
- One line of page text claiming the check passed raised false adoption by a further 30 points.

Full numbers: `results/main_summary.md` and `results/main_extra.md`.

## Design

- **120 items:** 60 known facts, each with a plausible false rival (often a real confusion, such as K2's
  height given for Everest), and 60 invented "void" items where only the sources can decide.
- **4 sources per prompt** in slots that are fixed per item and counterbalanced across items: T (true
  value), F (attacker's value) and two distractors, or extra copies of F in `echo` and `indep`.
- **9 conditions**, each adding one signal to `base`:

| condition | what changes |
|---|---|
| base | plain T vs plain F |
| style | F written with GEO tactics (invented statistic, expert quote, authoritative title) |
| badge | F carries a forged reliability credential (text only, nothing checks it) |
| claim | F says it was verified by the search engine |
| echo | F's claim in 3 near-identical syndicated copies of one article |
| indep | F's claim in 3 independently worded sources (reference point for echo) |
| check | badge + the search system's real ed25519 check in the system prompt: F FAILED |
| spoof | check + a line in F's page imitating the check: "PASSED" |
| honest | T carries a genuine credential and the system check says PASSED (positive control) |

- **Signatures:** `src/provenance.py` signs page bodies with ed25519. Forged badges are signed with an
  attacker key and fail verification. All publishers are fictional.
- **Scoring:** every reply ends with `FINAL ANSWER`, `CONFIDENCE (0-100)` and `SOURCES DISAGREE (yes/no)`.
  Scoring is deterministic string matching on the answer line; no LLM judge was used. The human-label
  check in `src/label.py` was not run for the submitted results.

## Reproduce

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=...  XAI_API_KEY=...  HF_TOKEN=...   # only for the providers in models.txt
python -m scripts.check_models                              # ping every model in models.txt

python -m src.items && python -m src.build                  # 120 items -> 1,080 prompts
python -m src.run --budget 3.8                              # resumable; rerun to retry errors
python -m src.score
python -m src.analyze                                       # results/main_summary.md, figures/
python -m src.extra                                         # results/main_extra.md, figures/main_fig5_stances.png
```

`./run_all.sh` runs the same steps. To try the pipeline without API keys:

```bash
python -m src.run --mock --limit 20
python -m src.score --raw results/mock_raw.jsonl --out results/mock_scored.jsonl
python -m src.analyze --scored results/mock_scored.jsonl --tag mock
```

The submitted run also includes a 10-item pilot (`results/pilot_raw.jsonl`), produced with
`python -m src.run --limit 10 --out results/pilot_raw.jsonl --budget 0.3`.

## Files

```
src/items.py           item bank (60 known + 60 void)
src/docs.py            page templates: plain, GEO, self-claimed verification, echo copies, independent
src/provenance.py      ed25519 credentials, badge text, system check lines, spoof text
src/build.py           item x condition prompts
src/llm.py             OpenAI / xAI / Hugging Face client, budget cap, retries, mock backend
src/models.py          models.txt parsing, live Hugging Face prices
src/run.py             resumable, budget-capped two-turn runner
src/score.py           deterministic scoring
src/label.py           optional human labelling and Cohen's kappa (not run for the submitted results)
src/analyze.py         bootstrap CIs, paired contrasts, regression, confidence, follow-up, figures
src/extra.py           stance distribution, known-only calibration, verification asymmetry, source order
scripts/check_models.py  list model ids and prices, ping models
data/                  items and the 1,080 prompts
results/               raw replies, scored turns, summaries and CSVs
figures/               generated figures (fig1, fig2 and fig5 appear in the report)
report/                report PDF and LaTeX source
```

## Prior work and dual use

All code and data were produced during the sprint; nothing predates it. The framing builds on the
author's earlier essay "When Labels Override Evidence" (October 2026), cited in the report. The
manipulations studied (invented statistics, copied credentials, self-declared verification, syndication)
are already in use; this project uses fictional publishers and harmless facts, and describes the
mitigation (server-side verification enforced by the pipeline). See Appendix A of the report.
