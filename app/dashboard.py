"""Audit Dashboard: a read-only view of the pipeline's run folders.

  streamlit run app/dashboard.py

It never runs models and never reads benchmark labels; it only displays what the pipeline wrote.
Runs whose meta.json says "synthetic": true carry a banner.
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import data  # noqa: E402

ROOTS = ["runs", "kaggle_out", "runs_demo"]
HIGHLIGHT = "#2a78d6"   # selected model (series slot 1)
CONTEXT = "#898781"     # clean-bank background marks (muted ink)
AXIS = "#898781"
GRID = "#e1e0d9"
VERDICT_LABEL = {"evidence": "⚠ Evidence", "no evidence found": "○ No evidence found", "inconclusive": "? Inconclusive"}

st.set_page_config(page_title="Who Is the Trigger? Audit Dashboard", layout="wide")
st.markdown("""
<style>
mark.add { background: #fde2d6; color: inherit; padding: 0 2px; border-radius: 3px; font-weight: 600; }
del { color: #898781; }
.muted { color: #898781; }
.diffrow { font-size: 0.95rem; line-height: 1.5; }
</style>""", unsafe_allow_html=True)


def styled(chart: alt.Chart) -> alt.Chart:
    return (chart.configure_axis(labelColor=AXIS, titleColor=AXIS, gridColor=GRID, domainColor="#c3c2b7",
                                 tickColor="#c3c2b7", labelFontSize=12, titleFontSize=12)
            .configure_view(strokeWidth=0).configure_title(color=AXIS))


# ================================================================ sidebar: pick a run

st.sidebar.title("Who Is the Trigger?")
st.sidebar.caption("Audit Dashboard · read-only view of pipeline run folders")
runs = data.find_runs(ROOTS)
if not runs:
    st.info("No run folders found yet under runs/, kaggle_out/ or runs_demo/. "
            "Run the pipeline, or make a synthetic demo with `python -m scripts.make_demo_run`.")
    st.stop()

kinds = {"audit": "Audit runs", "clean_bank": "Clean model bank", "wer": "Accuracy (WER) baselines",
         "profile": "Compute profiles"}
kind = st.sidebar.radio("What to look at", [k for k in kinds if any(r.kind == k for r in runs)],
                        format_func=kinds.get)
choices = [r for r in runs if r.kind == kind]
run = st.sidebar.selectbox("Run", choices, format_func=lambda r: ("[SYNTHETIC] " if r.synthetic else "") + r.name)
st.sidebar.caption(f"Folder: `{run.path}`")
git = run.meta.get("git", {})
st.sidebar.caption(f"Code version: `{(git.get('commit') or '?')[:10]}`" + (" (uncommitted changes)" if git.get("dirty") else ""))

if run.synthetic:
    st.warning("**SYNTHETIC DEMO DATA.** " + run.meta.get("synthetic_note", "") +
               " It shows how the dashboard reads a run; none of these numbers are results.", icon="⚠️")


# ================================================================ audit runs

def audit_page(run: data.Run) -> None:
    st.title("Audit results")
    scores = data.load_scores(run)
    calib = data._read_json(run.path / "calibration.json")
    audited = scores[~scores["in_bank"]] if "in_bank" in scores else scores
    bank = scores[scores["in_bank"]] if "in_bank" in scores else scores.iloc[0:0]

    c = st.columns(4)
    c[0].metric("Models audited", len(audited))
    c[1].metric("Clean models (normal range)", len(bank))
    if calib:
        c[2].metric("Can flag anything?", "Yes" if calib.get("detectable") else "Not yet",
                    help=f"Smallest possible combined p-value is {calib['min_achievable_p']:.3f}; it must be "
                         f"≤ {calib['alpha']} to flag. With 3 checks this needs ≥ 59 clean models.")
        fa = calib.get("false_alarms", {})
        c[3].metric("False alarms on clean models", f"{fa.get('k', 0)} / {fa.get('n', 0)}",
                    help=f"95% upper bound on the false-alarm rate: {100 * fa.get('upper95', 1):.1f}%")
        if not calib.get("detectable"):
            st.info(f"With {calib['n_cal']} clean models the smallest possible p-value is "
                    f"{calib['min_achievable_p']:.2f}, above the {calib['alpha']:.0%} target, so no model can be "
                    "flagged yet, however unusual. This is why the plan needs about 60 clean models.")
    else:
        c[2].metric("Calibration", "not applied")

    st.subheader("Verdicts")
    table = audited.copy()
    if "verdict" in table:
        table["verdict"] = table["verdict"].map(VERDICT_LABEL).fillna(table["verdict"])
    show = [x for x in ["model_id", "role", "verdict", "p_combined", "check1", "check2", "check3",
                        "parent_verified", "coverage"] if x in table]
    st.dataframe(table[show], hide_index=True, use_container_width=True,
                 column_config={"p_combined": st.column_config.NumberColumn("combined p", format="%.3f"),
                                "check1": st.column_config.NumberColumn("Check 1 (text)", format="%.2f"),
                                "check2": st.column_config.NumberColumn("Check 2 (voices)", format="%.2f"),
                                "check3": st.column_config.NumberColumn("Check 3 (inside)", format="%.2f"),
                                "parent_verified": "parent verified", "coverage": "probe coverage"})

    if audited.empty:
        st.caption("Only clean models in this run (null-distribution run).")
        options = list(scores["model_id"])
    else:
        options = list(audited["model_id"]) + list(bank["model_id"])
    default = 0
    if "check2" in audited and not audited.empty:
        default = options.index(audited.sort_values("check2", ascending=False)["model_id"].iloc[0])
    model = st.selectbox("Look closer at model", options, index=default)
    ev = data.load_evidence(run, model)

    pc = ev.get("parent_check", {})
    if pc:
        status = pc.get("status", "?")
        line = f"**Parent check:** {'✓ verified' if status == 'verified' else '? ' + status}"
        if pc.get("reasons"):
            line += " — " + "; ".join(pc["reasons"])
        st.markdown(line)

    tabs = st.tabs(["Voices (Check 2)", "Text (Check 1)", "Inside the model (Check 3)", "Transcripts",
                    "Against the clean models"])
    with tabs[0]:
        voices_tab(run, scores, model, ev.get("check2", {}))
    with tabs[1]:
        text_tab(ev.get("check1", {}))
    with tabs[2]:
        inside_tab(ev.get("check3", {}))
    with tabs[3]:
        transcripts_tab(run, model)
    with tabs[4]:
        null_tab(scores, model)


def voices_tab(run: data.Run, scores: pd.DataFrame, model: str, ev: dict) -> None:
    st.caption("Each column is one speaker in the voice bank. Grey dots: how many extra words each clean model "
               "adds for that speaker (the normal range). Blue dot: the selected model.")
    rates = data.speaker_rate_table(run, scores)
    if rates is None:
        st.info("No voice-bank transcripts in this run.")
        return
    rates = rates.assign(added_pct=100 * rates["added_rate"])
    bank = rates[rates["in_bank"] & (rates["model_id"] != model)]
    sel = rates[rates["model_id"] == model]
    order = sorted(rates["speaker_id"].unique(), key=lambda s: (len(s), s))
    x = alt.X("speaker_id:N", sort=order, title="Speaker", axis=alt.Axis(labelAngle=0))
    y = alt.Y("added_pct:Q", title="Extra words added (% of words)")
    tip = [alt.Tooltip("model_id:N", title="model"), alt.Tooltip("speaker_id:N", title="speaker"),
           alt.Tooltip("added_pct:Q", title="extra words %", format=".1f")]
    base = alt.Chart(bank).mark_circle(size=60, color=CONTEXT, opacity=0.55).encode(x=x, y=y, tooltip=tip)
    top = alt.Chart(sel).mark_circle(size=140, color=HIGHLIGHT, opacity=1, stroke="white", strokeWidth=2).encode(x=x, y=y,
                                                                                                     tooltip=tip)
    cand = ev.get("candidate_speaker")
    layers = [base, top]
    if cand is not None:
        lab = sel[sel["speaker_id"] == str(cand)]
        layers.append(alt.Chart(lab).mark_text(dy=-16, color="#52514e", fontSize=12, fontWeight="bold")
                      .encode(x=x, y=y, text=alt.value(f"speaker {cand}")))
    st.altair_chart(theme=None, altair_chart=styled(alt.layer(*layers).properties(height=320)), use_container_width=True)
    if ev:
        st.markdown(f"**Most unusual voice:** speaker `{ev.get('candidate_speaker')}` — robust z = "
                    f"**{ev.get('z', 0):.1f}** compared with the same speaker in the clean models.")
        if ev.get("candidate_ngrams"):
            st.markdown("**Words added for that speaker:** " +
                        ", ".join(f"“{g}” ({k} clips)" for g, k in ev["candidate_ngrams"][:5]))
    with st.expander("Table view"):
        st.dataframe(sel[["speaker_id", "added_pct"]].rename(columns={"added_pct": "extra words %"}),
                     hide_index=True)


def text_tab(ev: dict) -> None:
    st.caption("Phrases this model adds (compared with the parent) that no clean model adds. A hidden payload "
               "tends to repeat across many probes; random slips do not.")
    if not ev:
        st.info("No Check 1 evidence.")
        return
    st.metric("Score: most probes sharing one suspicious phrase", ev.get("top", [{}])[0].get("n_probes", 0)
              if ev.get("top") else 0, help=f"Out of {ev.get('n_probes')} probes; {ev.get('n_candidates')} "
                                            "candidate phrases in total.")
    top = pd.DataFrame(ev.get("top", []))
    if top.empty:
        st.write("No phrases unique to this model.")
        return
    if "by_kind" in top:
        top["where"] = top["by_kind"].map(lambda d: ", ".join(f"{k}: {v}" for k, v in d.items()))
    st.dataframe(top[[c for c in ["ngram", "n_probes", "where"] if c in top]], hide_index=True,
                 use_container_width=True, column_config={"ngram": "phrase", "n_probes": "probes",
                                                          "where": "probe types"})


def inside_tab(ev: dict) -> None:
    st.caption("For each encoder layer: how much one speaker's internal activations shift, compared with the "
               "same layer in the clean models (robust z). A tall bar means a speaker-specific change there.")
    if not ev or "z_by_layer" not in ev:
        st.info("No Check 3 evidence.")
        return
    df = pd.DataFrame({"layer": range(len(ev["z_by_layer"])), "z": ev["z_by_layer"]})
    bars = alt.Chart(df).mark_bar(color=HIGHLIGHT, cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
                                  size=28).encode(
        x=alt.X("layer:O", title="Encoder layer (0 = input)", axis=alt.Axis(labelAngle=0)), y=alt.Y("z:Q", title="Robust z vs clean models"),
        tooltip=[alt.Tooltip("layer:O"), alt.Tooltip("z:Q", format=".1f")])
    st.altair_chart(theme=None, altair_chart=styled(bars.properties(height=280)), use_container_width=True)
    st.markdown(f"**Strongest layer:** {ev.get('layer')} · **speaker:** `{ev.get('speaker')}` · "
                f"**linear-probe AUC:** {ev.get('probe_auc', float('nan')):.2f} "
                "(1.0 = that speaker's shift is perfectly separable, 0.5 = not at all)")


def transcripts_tab(run: data.Run, model: str) -> None:
    st.caption("Parent's transcript vs this model's, after normalisation. "
               "Highlighted = words the model added; struck through = words it dropped.")
    which = st.radio("Probe set", ["voice_bank", "check1"], horizontal=True,
                     format_func={"voice_bank": "Voice bank", "check1": "Silence / noise / speech"}.get)
    tx = data.load_transcripts(run, which)
    if tx is None or model not in tx.columns:
        st.info("No transcripts for this model in this run.")
        return
    only_diff = st.checkbox("Only clips where the transcripts differ", value=True)
    if "speaker_id" in tx and tx["speaker_id"].astype(bool).any():
        spk = st.selectbox("Speaker", ["all"] + sorted(set(tx["speaker_id"]) - {""}, key=lambda s: (len(s), s)))
        if spk != "all":
            tx = tx[tx["speaker_id"] == spk]
    rows = []
    for _, r in tx.iterrows():
        if only_diff and data.word_diff(r["PARENT"], r[model]).n_errors == 0:
            continue
        rows.append((r, data.diff_html(r["PARENT"], r[model])))
    st.caption(f"{len(rows)} clips shown")
    for r, h in rows[:60]:
        label = f"`{r['probe_id']}`" + (f" · speaker {r['speaker_id']}" if r.get("speaker_id") else "") + \
                (f" · {r['kind']}" if r.get("kind") else "")
        parent_norm = data.normalize(r["PARENT"]) or "(empty)"
        st.markdown(f"{label}<br><span class='muted'>parent:</span> {parent_norm}<br>"
                    f"<span class='muted'>model:</span> <span class='diffrow'>{h}</span>", unsafe_allow_html=True)
        audio = Path(r["path"]) if r.get("path") else None
        if audio is not None and audio.exists():
            st.audio(str(audio))


def null_tab(scores: pd.DataFrame, model: str) -> None:
    st.caption("Where the selected model (blue) falls among the clean models (grey) on each check. "
               "Far to the right of every grey dot = unusual.")
    for check, title in (("check1", "Check 1 · text"), ("check2", "Check 2 · voices"), ("check3", "Check 3 · inside")):
        if check not in scores:
            continue
        df = data.null_strip(scores, check)
        bank = df[(df["group"] == "clean bank") & (df["model_id"] != model)]
        sel = df[df["model_id"] == model]
        x = alt.X("score:Q", title=None)
        tip = [alt.Tooltip("model_id:N", title="model"), alt.Tooltip("score:Q", format=".2f")]
        chart = alt.layer(
            alt.Chart(bank).mark_tick(color=CONTEXT, thickness=2, size=22).encode(x=x, tooltip=tip),
            alt.Chart(sel).mark_tick(color=HIGHLIGHT, thickness=4, size=34).encode(x=x, tooltip=tip),
        ).properties(height=60, title=alt.TitleParams(title, anchor="start", fontSize=13, color="#52514e"))
        st.altair_chart(theme=None, altair_chart=styled(chart), use_container_width=True)


# ================================================================ other run kinds

def wer_page(run: data.Run) -> None:
    st.title("Accuracy baseline (WER)")
    m = data._read_json(run.path / "metrics.json")
    o = m.get("overall", {})
    c = st.columns(4)
    c[0].metric("Model", run.config.get("model", "?"))
    c[1].metric("Word error rate", f"{100 * o.get('wer', float('nan')):.2f}%")
    c[2].metric("Clips / speakers", f"{o.get('n_utts', '?')} / {m.get('n_speakers', '?')}")
    c[3].metric("Transcription time", f"{m.get('transcribe_wall_s', float('nan')):.0f} s")
    st.caption(f"{o.get('substitutions')} substitutions, {o.get('deletions')} deletions, {o.get('insertions')} "
               f"insertions over {o.get('n_ref_words')} reference words.")
    per = run.path / "wer_per_speaker.csv"
    if per.exists():
        df = pd.read_csv(per, dtype={"speaker_id": str}).assign(wer_pct=lambda d: 100 * d["wer"])
        order = df.sort_values("wer_pct", ascending=False)["speaker_id"].tolist()
        bars = alt.Chart(df).mark_bar(color=HIGHLIGHT, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("speaker_id:N", sort=order, title="Speaker", axis=alt.Axis(labelAngle=0)), y=alt.Y("wer_pct:Q", title="WER (%)"),
            tooltip=[alt.Tooltip("speaker_id:N"), alt.Tooltip("wer_pct:Q", format=".1f"), alt.Tooltip("n_utts:Q")])
        st.subheader("WER per speaker")
        st.altair_chart(theme=None, altair_chart=styled(bars.properties(height=300)), use_container_width=True)


def bank_page(run: data.Run) -> None:
    st.title("Clean model bank")
    df = pd.read_csv(run.path / "bank_summary.csv")
    s = data._read_json(run.path / "summary.json")
    c = st.columns(4)
    c[0].metric("Clean models trained", len(df))
    c[1].metric("Within 1 WER point of parent", f"{int(df['pass'].sum())} / {len(df)}")
    c[2].metric("Trainable weights (LoRA)", f"{df['trainable_pct'].iloc[0]:.2f}%")
    c[3].metric("Training time per model", f"{df['train_s'].mean():.0f} s")
    if s.get("parent_wer"):
        st.caption(f"Parent WER on the held-out clips: {100 * s['parent_wer']['wer']:.2f}%")
    band = pd.DataFrame({"lo": [-1.0], "hi": [1.0]})
    x = alt.X("name:N", title="Clean model", sort=None, axis=alt.Axis(labelAngle=-45))
    chart = alt.layer(
        alt.Chart(band).mark_rect(color="#e1e0d9", opacity=0.6).encode(y="lo:Q", y2="hi:Q"),
        alt.Chart(df).mark_circle(size=90, color=HIGHLIGHT).encode(
            x=x, y=alt.Y("wer_delta_pts:Q", title="WER change vs parent (points)"),
            tooltip=["name", alt.Tooltip("wer_delta_pts:Q", format="+.2f"), "train_s", "n_utts"]),
    ).properties(height=300)
    st.caption("Shaded band = the ±1 point acceptance range.")
    st.altair_chart(theme=None, altair_chart=styled(chart), use_container_width=True)
    st.dataframe(df, hide_index=True, use_container_width=True)


def profile_page(run: data.Run) -> None:
    st.title("Compute profile")
    df = pd.read_csv(run.path / "profile.csv")
    st.caption("Median wall time per batch and peak GPU memory, per operation and model.")
    st.dataframe(df, hide_index=True, use_container_width=True)
    p = data._read_json(run.path / "params.json")
    for m, kinds_ in p.items():
        for k, v in kinds_.items():
            st.write(f"{m} [{k}]: {v['trainable_params']:,} trainable of {v['total_params']:,} "
                     f"({v['trainable_pct']:.2f}%)")


{"audit": audit_page, "wer": wer_page, "clean_bank": bank_page, "profile": profile_page}[run.kind](run)
