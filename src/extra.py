"""Follow-up analyses for the report (run after src.analyze; reads the same scored file).

  python -m src.extra --scored results/scored.jsonl --tag main
Outputs: results/<tag>_extra.md, results/<tag>_stances.csv, figures/<tag>_fig5_stances.png

1. Full stance distribution (true / false / both = hedge / neither) by condition and stratum, so the
   hedge-to-commitment shift is visible (false-claim adoption alone hides it).
2. Calibration on KNOWN items only. On void items the "true" value is a coin flip, so
   right/wrong confidence and ECE are not meaningful there; instead we report mean confidence.
3. One-sided verification: the effect of a system PASSED on the truth vs a system FAILED on a forgery.
4. Position: false adoption when the false source is listed before vs after the true one.
5. Pushback transitions on void items: where hedged first answers go after "Are you sure?".
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analyze import ORDER, LABEL, FL, BLUE, ORANGE, INK, INK2, SURF, ci_rate, ci_diff, ece, fmt, pct, pp, style

ROOT = Path(__file__).resolve().parent.parent
STANCES = ["false", "both", "neither", "true"]
SNAME = {"false": "attacker value", "both": "hedge (both values)", "neither": "neither", "true": "true value"}


def short(m):
    return m.split(":", 1)[1].split("?")[0].split("/")[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", default="results/scored.jsonl")
    ap.add_argument("--tag", default="main")
    a = ap.parse_args()
    style()
    d = pd.DataFrame([json.loads(l) for l in (ROOT / a.scored).open(encoding="utf-8")])
    for s in STANCES:
        d[f"is_{s}"] = (d.stance == s).astype(float)
    d["false_adopt"] = d.is_false
    d0 = d[d.turn == 0].copy()
    conds = [c for c in ORDER if c in set(d0.condition)]
    L = [f"# Extra analyses ({a.tag})", ""]

    # 1. stance distribution
    rows = []
    for c in conds:
        for st in ["known", "void"]:
            sub = d0[(d0.condition == c) & (d0.stratum == st)]
            r = dict(condition=c, stratum=st, n=len(sub))
            for s in STANCES:
                r[s] = sub[f"is_{s}"].mean()
            com = sub[sub.stance.isin(["true", "false"])]
            r["false_given_committed"] = (com.stance == "false").mean() if len(com) else np.nan
            r["conf_mean"] = sub.confidence.mean()
            r["conf_hedge"] = sub[sub.stance == "both"].confidence.mean()
            rows.append(r)
    t = pd.DataFrame(rows)
    t.to_csv(ROOT / "results" / f"{a.tag}_stances.csv", index=False, encoding="utf-8")
    for st in ["void", "known"]:
        L += [f"## 1. First-answer stance distribution, {st} items", "",
              "| condition | attacker value | hedge (both) | neither | true value | P(attacker \\| committed) | mean confidence |",
              "|---|---|---|---|---|---|---|"]
        for c in conds:
            r = t[(t.condition == c) & (t.stratum == st)].iloc[0]
            L.append(f"| {LABEL[c]} | {pct(r['false'])} | {pct(r.both)} | {pct(r.neither)} | {pct(r['true'])} | "
                     f"{pct(r.false_given_committed)} | {r.conf_mean:.1f} |")
        L.append("")
    v = d0[d0.stratum == "void"]
    L += ["Hedge-rate change vs baseline on void items (item-paired bootstrap 95% CI):", ""]
    for c in conds:
        if c != "base":
            L.append(f"- {LABEL[c]}: {fmt(ci_diff(v, 'base', c, col='is_both'), pp)}")
    L.append("")

    # 2. calibration on known items only
    k = d0[(d0.stratum == "known") & d0.stance.isin(["true", "false"]) & d0.confidence.notna()]
    L += ["## 2. Calibration on known items only (true value is real here)", "",
          f"Overall known-item ECE: {ece(k.confidence, k.stance == 'true'):.3f} (n={len(k)})", "",
          "| condition | n | accuracy | mean confidence | confidence when wrong | confidence when right | ECE |",
          "|---|---|---|---|---|---|---|"]
    for c in conds:
        s2 = k[k.condition == c]
        w = s2[s2.stance == "false"].confidence
        L.append(f"| {LABEL[c]} | {len(s2)} | {pct((s2.stance == 'true').mean())} | {s2.confidence.mean():.1f} | "
                 f"{(f'{w.mean():.1f} (n={len(w)})') if len(w) else 'n/a'} | {s2[s2.stance == 'true'].confidence.mean():.1f} | "
                 f"{ece(s2.confidence, s2.stance == 'true'):.3f} |")
    L.append("")
    vc = d0[(d0.stratum == "void") & d0.confidence.notna()]
    L += ["Void items, mean stated confidence by stance (sound value with one source against one is ~50):", ""]
    for c in conds:
        s2 = vc[vc.condition == c]
        parts = [f"{SNAME[s]} {s2[s2.stance == s].confidence.mean():.1f}" for s in ["false", "both", "true"]
                 if (s2.stance == s).sum() >= 10]
        L.append(f"- {LABEL[c]}: all {s2.confidence.mean():.1f}; " + "; ".join(parts))
    L.append("")

    # 3. one-sided verification
    L += ["## 3. One-sided verification", ""]
    for st, sub in [("all", d0), ("void", d0[d0.stratum == "void"]), ("known", d0[d0.stratum == "known"])]:
        fail = ci_diff(sub, "badge", "check")
        pas = ci_diff(sub, "base", "honest")
        true_fail = ci_diff(sub, "badge", "check", col="is_true")
        true_pass = ci_diff(sub, "base", "honest", col="is_true")
        L.append(f"- {st}: system FAILED on forged badge -> false adoption {fmt(fail, pp)}, true answers {fmt(true_fail, pp)}; "
                 f"system PASSED on truth -> false adoption {fmt(pas, pp)}, true answers {fmt(true_pass, pp)}")
    pm = d0[d0.stratum == "void"].pivot_table(index="model", columns="condition", values="is_true", aggfunc="mean")
    pf = d0[d0.stratum == "void"].pivot_table(index="model", columns="condition", values="is_false", aggfunc="mean")
    L += ["", "Per model, void items (pp): PASSED-on-truth gain in true answers (honest - base) | "
          "FAILED-on-forgery drop in false answers (badge - check)", ""]
    for m in pm.index:
        L.append(f"- {short(m)}: {100 * (pm.loc[m, 'honest'] - pm.loc[m, 'base']):+.1f} | "
                 f"{100 * (pf.loc[m, 'badge'] - pf.loc[m, 'check']):+.1f}")
    L.append("")

    # 4. position
    d0["false_first"] = d0.pos_false < d0.pos_true
    b = d0[(d0.condition == "base") & (d0.stratum == "void")]
    L += ["## 4. Position (baseline, void items): false adoption when F is listed before vs after T", ""]
    L.append(f"- all models: F first {pct(b[b.false_first].is_false.mean())} (n={b.false_first.sum()}), "
             f"F second {pct(b[~b.false_first].is_false.mean())} (n={(~b.false_first).sum()})")
    for m, g in b.groupby("model"):
        L.append(f"- {short(m)}: F first {pct(g[g.false_first].is_false.mean())}, F second {pct(g[~g.false_first].is_false.mean())}; "
                 f"true when T first {pct(g[~g.false_first].is_true.mean())}, true when T second {pct(g[g.false_first].is_true.mean())}")
    L.append("")

    # 5. pushback transitions on void items
    w = d.pivot_table(index=["pid", "model", "condition", "stratum"], columns="turn", values="stance", aggfunc="first").reset_index()
    L += ["## 5. Pushback on void items: first answer -> after 'Are you sure?'", "",
          "| condition | attacker value: first -> after | hedges that became attacker value | hedges that became true value |",
          "|---|---|---|---|"]
    for c in conds:
        x = w[(w.condition == c) & (w.stratum == "void")]
        h = x[x[0] == "both"]
        L.append(f"| {LABEL[c]} | {pct((x[0] == 'false').mean())} -> {pct((x[1] == 'false').mean())} | "
                 f"{pct((h[1] == 'false').mean()) if len(h) else 'n/a'} (n={len(h)}) | {pct((h[1] == 'true').mean()) if len(h) else 'n/a'} |")
    L.append("")
    for st in ["known", "void"]:
        x = w[w.stratum == st]
        f0 = x[x[0] == "false"]
        L.append(f"- {st}: recovery of false first answers across all conditions {pct((f0[1] == 'true').mean())} (n={len(f0)})")
    L.append("")

    # figure 5: stance distribution on void items
    show = conds
    tv = t[t.stratum == "void"].set_index("condition").loc[show]
    cols = {"false": ORANGE, "both": "#b9b7af", "neither": "#e2e0d9", "true": BLUE}
    fig, ax = plt.subplots(figsize=(6.0, 3.3))
    y = np.arange(len(show))
    left = np.zeros(len(show))
    for s in STANCES:
        vals = tv[s].values * 100
        ax.barh(y, vals, left=left, color=cols[s], edgecolor=SURF, linewidth=1.5, height=0.62, label=SNAME[s])
        for i, (l0, vv) in enumerate(zip(left, vals)):
            if vv >= 9:
                ax.text(l0 + vv / 2, i, f"{vv:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if s in ("false", "true") else INK)
        left += vals
    ax.set_yticks(y); ax.set_yticklabels([FL(LABEL[c]) for c in show]); ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xlabel("Share of first answers on no-prior (void) items (%)")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.40, -0.17), fontsize=8.5)
    fig.tight_layout(); fig.savefig(ROOT / "figures" / f"{a.tag}_fig5_stances.png", dpi=220); plt.close(fig)

    (ROOT / "results" / f"{a.tag}_extra.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
