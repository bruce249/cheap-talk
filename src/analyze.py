"""Every number and figure the report needs.

  python -m src.analyze --scored results/scored.jsonl --tag main
Outputs: results/<tag>_summary.md, results/<tag>_*.csv, figures/<tag>_fig1..4.png
"""
import argparse
import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["base", "style", "badge", "claim", "echo", "indep", "check", "spoof", "honest"]
LABEL = {"base": "Baseline", "style": "GEO style", "badge": "Forged badge", "claim": "Self-claimed 'verified'",
         "echo": "3 syndicated copies", "indep": "3 independent sources", "check": "Forged badge + system check",
         "spoof": "Check + spoofed 'PASSED'", "honest": "Real verified badge on truth"}
BLUE, ORANGE, GREEN, VIOLET, INK, INK2, SURF = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#0b0b0b", "#52514e", "#ffffff"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
B = 2000
RNG = np.random.default_rng(0)


def FL(s):
    """Figure label: typographic opening quote for the Computer Modern figure font."""
    return re.sub(r"'(.*?)'", r"`\1'", s)


def style():
    plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": "#d6d5cf",
                         "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
                         "font.size": 9, "font.family": "serif", "font.serif": ["cmr10", "DejaVu Serif"],
                         "mathtext.fontset": "cm", "axes.unicode_minus": False,
                         "axes.formatter.use_mathtext": True, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.color": "#ecebe6", "grid.linewidth": 0.6, "axes.axisbelow": True})


def pct(x):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f}%"


def pp(x):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:+.1f} pp"


def ci_rate(df, col):
    if df.empty:
        return (np.nan,) * 3
    g = df.groupby("item_id")[col].agg(["sum", "count"])
    s, n = g["sum"].to_numpy(float), g["count"].to_numpy(float)
    idx = RNG.integers(0, len(g), size=(B, len(g)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    return (s.sum() / n.sum(), *np.percentile(bs, [2.5, 97.5]))


def ci_diff(df, a, b, col="false_adopt"):
    ga = df[df.condition == a].groupby("item_id")[col].agg(["sum", "count"])
    gb = df[df.condition == b].groupby("item_id")[col].agg(["sum", "count"])
    j = ga.join(gb, lsuffix="_a", rsuffix="_b", how="inner")
    if j.empty:
        return (np.nan,) * 3
    sa, na, sb, nb = (j[c].to_numpy(float) for c in ["sum_a", "count_a", "sum_b", "count_b"])
    idx = RNG.integers(0, len(j), size=(B, len(j)))
    bs = sb[idx].sum(1) / nb[idx].sum(1) - sa[idx].sum(1) / na[idx].sum(1)
    return (sb.sum() / nb.sum() - sa.sum() / na.sum(), *np.percentile(bs, [2.5, 97.5]))


def fmt(t, f=pct):
    return f"{f(t[0])} [{f(t[1])}, {f(t[2])}]"


def ece(conf, correct, bins=10):
    conf, correct = np.asarray(conf) / 100, np.asarray(correct, float)
    e, edges = 0.0, np.linspace(0, 1, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if m.any():
            e += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return e


def regression(d0):
    try:
        import statsmodels.formula.api as smf
        x = d0.copy()
        x["condition"] = pd.Categorical(x["condition"], categories=[c for c in ORDER if c in set(x.condition)])
        x["false_first"] = (x.pos_false < x.pos_true).astype(int)
        m = smf.logit("false_adopt ~ C(condition) + C(stratum) + C(model) + false_first", data=x).fit(
            disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(x["item_id"])[0]}, maxiter=300)
        keep = [k for k in m.params.index if "condition" in k or "stratum" in k or "false_first" in k]
        ci = m.conf_int()
        t = pd.DataFrame({"odds_ratio": np.exp(m.params[keep]), "lo": np.exp(ci.loc[keep, 0]),
                          "hi": np.exp(ci.loc[keep, 1]), "p": m.pvalues[keep]})
        return t.round(3).to_string()
    except Exception as e:
        return f"regression failed: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", default="results/scored.jsonl")
    ap.add_argument("--tag", default="main")
    a = ap.parse_args()
    style()
    d = pd.DataFrame([json.loads(l) for l in (ROOT / a.scored).open(encoding="utf-8")])
    d["false_adopt"] = (d.stance == "false").astype(float)
    d["true_adopt"] = (d.stance == "true").astype(float)
    conds = [c for c in ORDER if c in set(d.condition)]
    models = sorted(d.model.unique())
    d0 = d[d.turn == 0].copy()
    res, figs = ROOT / "results", ROOT / "figures"
    figs.mkdir(exist_ok=True)
    L = [f"# Results summary ({a.tag})", "",
         f"Models: {len(models)} ({', '.join(models)})", f"Items: {d0.item_id.nunique()}; conditions: {len(conds)}; "
         f"first-turn replies: {len(d0)}; all scored turns: {len(d)}", "",
         "## Output format compliance (first turn)", ""]
    fc = d0.groupby("model").agg(format_ok=("format_ok", "mean"), neither=("stance", lambda s: (s == "neither").mean()),
                                 conf_given=("confidence", lambda s: s.notna().mean()))
    for m, r in fc.iterrows():
        L.append(f"- {m}: FINAL ANSWER line {pct(r.format_ok)}, gave neither value {pct(r.neither)}, confidence given {pct(r.conf_given)}")
    L.append("")

    # 1. adoption by condition and stratum
    rows = []
    for c in conds:
        for s in ["known", "void", "all"]:
            sub = d0[(d0.condition == c) & ((d0.stratum == s) | (s == "all"))]
            m_, lo, hi = ci_rate(sub, "false_adopt")
            rows.append(dict(condition=c, stratum=s, false_adopt=m_, lo=lo, hi=hi, n=len(sub),
                             disagree_flag=sub.disagree.astype(float).mean() if len(sub) else np.nan,
                             conf_mean=sub.confidence.mean(), conf_when_false=sub[sub.stance == "false"].confidence.mean(),
                             conf_when_true=sub[sub.stance == "true"].confidence.mean()))
    t1 = pd.DataFrame(rows)
    t1.to_csv(res / f"{a.tag}_by_condition.csv", index=False, encoding="utf-8")
    L += ["## H1. False-claim adoption, first answer (95% cluster-bootstrap CI over items)", "",
          "| condition | known facts | void facts | all | says sources disagree | mean confidence | confidence when wrong |",
          "|---|---|---|---|---|---|---|"]
    for c in conds:
        r = {s: t1[(t1.condition == c) & (t1.stratum == s)].iloc[0] for s in ["known", "void", "all"]}
        L.append(f"| {LABEL[c]} | " + " | ".join(fmt((r[s].false_adopt, r[s].lo, r[s].hi)) for s in ["known", "void", "all"])
                 + f" | {pct(r['all'].disagree_flag)} | {r['all'].conf_mean:.1f} | {r['all'].conf_when_false:.1f} |")
    L.append("")

    # 2. contrasts
    C = [("base", "style", "GEO style premium"), ("base", "badge", "Forged-badge premium"),
         ("base", "claim", "Self-claimed verification premium"), ("base", "echo", "Echo (3 copies) premium"),
         ("base", "indep", "Independent corroboration premium"),
         ("echo", "indep", "Independence sensitivity (indep minus echo; a careful reader makes this large)"),
         ("badge", "check", "Effect of the real system check on a forged badge"),
         ("base", "check", "Forged badge + check vs baseline (residual harm)"),
         ("check", "spoof", "Spoof penalty (attacker 'PASSED' text despite system FAILED; ideal 0)"),
         ("base", "honest", "Real verified badge on the truth (positive control; negative = helps)")]
    crow = []
    L += ["## H2. Paired contrasts in false-claim adoption (item-paired bootstrap 95% CI)", ""]
    for x, y, name in C:
        if x in conds and y in conds:
            e = {s: ci_diff(d0 if s == "all" else d0[d0.stratum == s], x, y) for s in ["all", "known", "void"]}
            for s, v in e.items():
                crow.append(dict(contrast=name, a=x, b=y, stratum=s, diff=v[0], lo=v[1], hi=v[2]))
            L.append(f"- **{name}**: all {fmt(e['all'], pp)}; known {fmt(e['known'], pp)}; void {fmt(e['void'], pp)}")
    pd.DataFrame(crow).to_csv(res / f"{a.tag}_contrasts.csv", index=False, encoding="utf-8")
    L.append("")

    # ranking of cheap signals
    prem = {c: ci_diff(d0, "base", c)[0] for c in ["style", "badge", "claim", "echo", "indep"] if c in conds}
    if prem:
        L += ["Signals ranked by how much they raise false-claim adoption: " +
              "; ".join(f"{LABEL[c]} {pp(v)}" for c, v in sorted(prem.items(), key=lambda kv: -kv[1])), ""]

    # 3. confidence / calibration
    L += ["## H3. Confidence", ""]
    sub = d0[d0.stance.isin(["true", "false"]) & d0.confidence.notna()]
    if len(sub):
        L.append(f"- Overall ECE (confidence vs being right, first answer): {ece(sub.confidence, sub.stance == 'true'):.3f}")
        for c in conds:
            s2 = sub[sub.condition == c]
            if len(s2):
                L.append(f"- {LABEL[c]}: mean confidence {s2.confidence.mean():.1f}; when wrong {s2[s2.stance=='false'].confidence.mean():.1f}; "
                         f"when right {s2[s2.stance=='true'].confidence.mean():.1f}; ECE {ece(s2.confidence, s2.stance=='true'):.3f}")
    L.append("")

    # 4. per model
    pm = d0.pivot_table(index="model", columns="condition", values="false_adopt", aggfunc="mean")[conds]
    pm.to_csv(res / f"{a.tag}_by_model.csv", encoding="utf-8")
    L += ["## Per-model false-claim adoption (first answer)", "",
          "| model | " + " | ".join(LABEL[c] for c in conds) + " |", "|---" * (len(conds) + 1) + "|"]
    for m, row in pm.iterrows():
        L.append(f"| {m} | " + " | ".join(pct(row[c]) for c in conds) + " |")
    L.append("")
    if {"badge", "check"} <= set(conds):
        g = (pm["badge"] - pm["check"]).sort_values(ascending=False)
        L.append("Check effect by model (badge minus check, pp): " + "; ".join(f"{m} {100*v:+.1f}" for m, v in g.items()))
    if {"check", "spoof"} <= set(conds):
        g = (pm["spoof"] - pm["check"]).sort_values(ascending=False)
        L.append("Spoof penalty by model (spoof minus check, pp): " + "; ".join(f"{m} {100*v:+.1f}" for m, v in g.items()))
    if {"echo", "indep"} <= set(conds):
        g = (pm["indep"] - pm["echo"]).sort_values(ascending=False)
        L.append("Independence sensitivity by model (indep minus echo, pp): " + "; ".join(f"{m} {100*v:+.1f}" for m, v in g.items()))
    L.append("")

    L += ["## Logistic regression, first answer (odds ratios vs Baseline; model fixed effects; item-clustered SEs)",
          "```", regression(d0), "```", ""]

    # 5. pushback
    mk = None
    if d.turn.max() >= 1:
        w = d.pivot_table(index=["pid", "model", "condition", "stratum"], columns="turn", values="stance", aggfunc="first").reset_index()
        rows = []
        for c in conds:
            for s in ["all", "known", "void"]:
                x = w[(w.condition == c) & ((w.stratum == s) | (s == "all"))]
                f0, t0 = x[0] == "false", x[0] == "true"
                r = ((x[1] == "true") & f0).sum() / f0.sum() if f0.sum() else np.nan
                cap = ((x[1] == "false") & t0).sum() / t0.sum() if t0.sum() else np.nan
                hl = (math.log(0.5) / math.log(1 - r)) if r and 0 < r < 1 else (np.inf if r == 0 else np.nan)
                rows.append(dict(condition=c, stratum=s, recovery=r, capitulation=cap, half_life_turns=hl,
                                 n_false=int(f0.sum()), n_true=int(t0.sum()),
                                 adopt_after=(x[1] == "false").mean()))
        mk = pd.DataFrame(rows)
        mk.to_csv(res / f"{a.tag}_pushback.csv", index=False, encoding="utf-8")
        L += ["## H4. One neutral pushback ('Are you sure? Please double-check')", "",
              "| condition | recovery P(false to true) | capitulation P(true to false) | half-life of a false answer (turns) | false after pushback |",
              "|---|---|---|---|---|"]
        for _, r in mk[mk.stratum == "all"].iterrows():
            hl = "never" if r.half_life_turns == np.inf else ("n/a" if pd.isna(r.half_life_turns) else f"{r.half_life_turns:.2f}")
            L.append(f"| {LABEL[r.condition]} | {pct(r.recovery)} (n={r.n_false}) | {pct(r.capitulation)} (n={r.n_true}) | {hl} | {pct(r.adopt_after)} |")
        L.append("")

    # ---------- figures
    # fig1: premium vs baseline, known vs void
    show = [c for c in conds if c != "base"]
    cr = pd.DataFrame(crow) if crow else None
    fig, ax = plt.subplots(figsize=(6.0, 3.3))
    y = np.arange(len(show))
    for k, (s, col, lab) in enumerate([("known", BLUE, "known facts"), ("void", ORANGE, "no-prior (void) facts")]):
        vals = [ci_diff(d0[d0.stratum == s], "base", c) for c in show]
        m_ = np.array([v[0] for v in vals]) * 100
        lo = np.array([v[1] for v in vals]) * 100
        hi = np.array([v[2] for v in vals]) * 100
        ax.errorbar(m_, y + (k - 0.5) * 0.3, xerr=[m_ - lo, hi - m_], fmt="o", ms=6, color=col, ecolor=col,
                    elinewidth=1.2, capsize=0, label=lab, markeredgecolor=SURF, markeredgewidth=1.5)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels([FL(LABEL[c]) for c in show]); ax.invert_yaxis()
    ax.set_xlabel("Change in false-claim adoption vs baseline (percentage points)")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2); ax.grid(axis="y", visible=False)
    fig.tight_layout(); fig.savefig(figs / f"{a.tag}_fig1_premiums.png", dpi=220); plt.close(fig)

    # fig2: heatmap
    from matplotlib.colors import LinearSegmentedColormap
    SHORT = {"base": "Baseline", "style": "GEO style", "badge": "Forged badge", "claim": "Self-claim",
             "echo": "3 copies", "indep": "3 indep.", "check": "Badge+check", "spoof": "Spoof PASSED",
             "honest": "Real badge"}
    fig, ax = plt.subplots(figsize=(6.2, 0.32 * len(models) + 1.6))
    im = ax.imshow(pm.values * 100, cmap=LinearSegmentedColormap.from_list("seq", SEQ), vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(conds))); ax.set_xticklabels([SHORT[c] for c in conds], rotation=30, ha="right")
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([m.split(":", 1)[1].split("?")[0].split("/")[-1].split(":")[0] for m in pm.index]); ax.grid(False)
    for i in range(pm.shape[0]):
        for j in range(pm.shape[1]):
            v = pm.values[i, j] * 100
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 55 else INK)
    fig.colorbar(im, ax=ax, label="False-claim adoption (%)", shrink=0.8)
    fig.tight_layout(); fig.savefig(figs / f"{a.tag}_fig2_models.png", dpi=220); plt.close(fig)

    # fig3: confidence when wrong vs right
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    a_ = t1[t1.stratum == "all"].set_index("condition").loc[conds]
    ax.plot(a_.conf_when_true.values, y_ := np.arange(len(conds)), "o", color=GREEN, ms=6, label="when answer is true")
    ax.plot(a_.conf_when_false.values, y_, "o", color=ORANGE, ms=6, label="when answer is false")
    for i in range(len(conds)):
        ax.plot([a_.conf_when_true.values[i], a_.conf_when_false.values[i]], [i, i], color="#d6d5cf", lw=1.5, zorder=0)
    ax.set_yticks(y_); ax.set_yticklabels([FL(LABEL[c]) for c in conds]); ax.invert_yaxis()
    ax.set_xlabel("Stated confidence (0-100)"); ax.legend(frameon=False, loc="lower left", fontsize=7)
    ax.grid(axis="y", visible=False)
    fig.tight_layout(); fig.savefig(figs / f"{a.tag}_fig3_confidence.png", dpi=220); plt.close(fig)

    # fig4: pushback
    if mk is not None:
        fig, ax = plt.subplots(figsize=(6.4, 3.4))
        z = mk[mk.stratum == "all"].set_index("condition").loc[conds]
        first = t1[t1.stratum == "all"].set_index("condition").loc[conds].false_adopt.values * 100
        after = z.adopt_after.values * 100
        for i in range(len(conds)):
            ax.annotate("", xy=(after[i], i), xytext=(first[i], i),
                        arrowprops=dict(arrowstyle="->", color=INK2, lw=1))
        ax.plot(first, range(len(conds)), "o", color=BLUE, ms=6, label="first answer")
        ax.plot(after, range(len(conds)), "o", color=VIOLET, ms=6, label="after 'are you sure?'")
        ax.set_yticks(range(len(conds))); ax.set_yticklabels([FL(LABEL[c]) for c in conds]); ax.invert_yaxis()
        ax.set_xlabel("False-claim adoption (%)"); ax.legend(frameon=False, loc="lower right", fontsize=7)
        ax.grid(axis="y", visible=False)
        fig.tight_layout(); fig.savefig(figs / f"{a.tag}_fig4_pushback.png", dpi=220); plt.close(fig)

    (res / f"{a.tag}_summary.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
