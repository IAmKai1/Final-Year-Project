"""Fill the department ESA template for PW26_JS_01 (helpers reused from fill_r2.py)."""
import os, sys
from pptx.util import Inches as In, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

D = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(D, "fig", n)
sys.argv = ["fill_r2.py", os.path.join(D, "work.pptx"), os.path.join(D, "PW26_JS_01_ESA.pptx")]
exec(open(r"D:\CAPSTONE\fill_r2.py", encoding="utf-8").read().split(
    "# ---------------------------------------------------------------- slide 1 title")[0])
RED, GREEN = RGBColor(0xB3, 0x26, 0x1E), RGBColor(0x2E, 0x7D, 0x32)
_card = card
def card(*a, **k):
    sh = _card(*a, **k)
    sh.adjustments[0] = 0.04
    return sh


def clear_body(s):
    b = body_of(s)
    if b is not None:
        kill(b)


def pic(s, name, left, top, width=None, height=None):
    kw = {}
    if width: kw["width"] = In(width)
    if height: kw["height"] = In(height)
    return s.shapes.add_picture(F(name), In(left), In(top), **kw)


def text(s, items, left, top, width, height, size=12, align=PP_ALIGN.LEFT, color=None, gap=3):
    tb = s.shapes.add_textbox(In(left), In(top), In(width), In(height))
    tb.name = "gen_text"
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = In(0.02)
    for i, ln in enumerate(items if isinstance(items, list) else [items]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(gap)
        for seg, bd in parse(ln):
            r = p.add_run(); r.text = seg
            r.font.name, r.font.size, r.font.bold = FONT, Pt(size), bd
            r.font.color.rgb = color or (NAVY if bd else GREY)
    return tb


def stat(s, big, small, left, top, width, height, accent=ORANGE):
    from pptx.enum.shapes import MSO_SHAPE
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, In(left), In(top), In(width), In(height))
    sh.name = "gen_stat"; sh.fill.solid(); sh.fill.fore_color.rgb = NAVY; sh.line.fill.background()
    sh.shadow.inherit = False
    tf = sh.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = In(0.08)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = big; r.font.name, r.font.size, r.font.bold = FONT, Pt(30), True
    r.font.color.rgb = accent
    p = tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = small; r.font.name, r.font.size = FONT, Pt(10.5)
    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    return sh


def color_cells(t, col, mapping):
    for i in range(1, len(t.rows)):
        c = t.cell(i, col)
        txt = c.text_frame.text
        for key, rgb in mapping.items():
            if txt.startswith(key):
                for r in c.text_frame.paragraphs[0].runs:
                    r.font.color.rgb = rgb; r.font.bold = True


# ---------------------------------------------------------------- 1 title
s = SL[0]
tb = [sh for sh in s.shapes if sh.has_text_frame and "Project Title" in sh.text_frame.text][0]
tf = tb.text_frame; tf.clear()
for i, (k, v) in enumerate([
        ("Project Title   :  ", "Who Is the Trigger? Auditing Speech AI Models for Speaker-Activated Backdoors"),
        ("Project ID       :  ", "PW26_JS_01"),
        ("Project Guide  :  ", "Prof. Jasmine"),
        ("Project Team   :  ", "Dhanush S (PES1UG24AM360), Darshan Govekar (PES1UG24AM355),"),
        ("                         ", "Dhanraj Rathod (PES1UG24AM359), Dhareen G (PES1UG24AM084)")]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(3)
    for seg, bd in [(k, True), (v, False)]:
        r = p.add_run(); r.text = seg
        r.font.name, r.font.size, r.font.bold = FONT, Pt(13), bd
        r.font.color.rgb = NAVY if bd else GREY

# ---------------------------------------------------------------- 2 outline
s = SL[1]
chrome(s, "Outline")
bullets(s, [(t, 0) for t in [
    "Abstract", "Suggestions from Review-1 & Review-2 — and what we did", "Understanding of the Problem Statement",
    "Proposed Architecture / Block Diagram", "Applicability in Different Domains",
    "Implementation — setup, how a verdict is reached, results, robustness", "Demo",
    "Any Other Information — limitations, ethics, Phase-II", "References"]],
    size=16, top=2.1, left=2.4, width=9.0, gap=8)

# ---------------------------------------------------------------- 3 abstract
s = SL[2]
chrome(s, "Abstract")
bullets(s, [
    ("Problem.** Speech-to-text models are downloaded and reused as fine-tunes. A fine-tune can hide a "
     "**speaker-activated backdoor**: when one particular person speaks, it appends a hidden instruction to the transcript; "
     "for everyone else it behaves normally, so accuracy tests pass.", 0),
    ("What we built.** A model-level **auditor**. Given the suspect model, the public model it came from and an unlabelled pool of "
     "speakers, it returns a verdict, **names the trigger speaker** and **recovers the hidden payload** — with no ground-truth "
     "transcripts and no knowledge of the trigger.", 0),
    ("Result (Phase-I, laptop CPU).** 11 of 11 backdoored Whisper models caught with the right speaker; 0 of 20 clean models flagged — "
     "across 2 model sizes, 3 trigger speakers, fixed and varying payloads. Every test was pre-registered.", 0)],
    size=13, top=1.9, left=0.7, width=11.9, height=2.35, gap=5)
pic(s, "threat.png", 2.2, 4.12, width=8.9)

# ---------------------------------------------------------------- 4 suggestions
s = SL[3]
chrome(s, "Suggestions from Review-1 & Review-2 — Remarks and Action Taken")
clear_body(s)
t = table(s, [
    ["Review", "Panel remark", "Action taken", "Status"],
    ["R-1", "Use published, peer-reviewed papers — arXiv is not a publication.",
     "All references are peer-reviewed (IEEE, ICML, Springer). Base paper: GN-FT, IEEE ICASSP 2025.", "Done"],
    ["R-1", "Full training may not be possible in the time — show what can be implemented.",
     "Measured, not guessed: one Whisper fine-tune ≈ 33 min on a laptop CPU. **31 models** trained and audited in Phase-I.", "Done"],
    ["R-1", "The area is crowded; someone may publish first.",
     "Re-scanned: published speech work attacks, purifies inputs or repairs a suspected model. To our knowledge none audits a model "
     "and names a natural-voice trigger.", "Addressed"],
    ["R-1", "Ask the university for GPUs if needed.",
     "Phase-I needed none. GPUs are needed only for Phase-II (Whisper-small/medium, audio LLMs).", "Planned"],
    ["R-2", "**Focus on one thing, such that it works well for all the models.**",
     "Narrowed the project to the **auditor alone**. Same frozen thresholds tested on a second model size, two new trigger speakers, "
     "a varying-payload attacker and repaired models: **11/11 backdoors, 0/20 false alarms**.", "Done"],
    ["R-2", "(follow-up) A detector that only matches one exact sentence is easy to evade.",
     "Added rule **C3**, which ignores the wording; it catches the varying-payload attack that C2 missed.", "Done"],
], top=1.95, size=10.5, widths=[0.8, 4.0, 6.4, 1.1], rh=0.62)
color_cells(t, 3, {"Done": GREEN, "Addressed": GREEN, "Planned": ORANGE})
text(s, ["**Feasibility:** everything ran on one laptop CPU; three rounds of pass/fail rules were written before running "
         "(PREREGISTRATION 1–3), and all results, including failures, are in the project repository."],
     0.65, 6.45, 12.0, 0.5, size=10.5)

# ---------------------------------------------------------------- 5 understanding
s = SL[4]
chrome(s, "Understanding of the Problem Statement")
clear_body(s)
card(s, "Key objectives & expected outcomes", [
    "**O1 Detect** — decide if a downloaded speech model carries a speaker-activated backdoor.",
    "**O2 Identify** — name the trigger speaker in the audit pool.",
    "**O3 Recover** — return the hidden payload text.",
    "**O4 Generalise** — the same frozen rule must work across models, sizes, speakers and payload styles.",
    "**Outcome:** a calibrated auditor, a labelled model bank, and pre-registered evidence."],
    0.6, 1.95, 3.95, 4.85, size=13, tsize=15)
card(s, "Challenges in the problem", [
    "**The trigger is who speaks, not what is said** — nothing unusual is in the audio.",
    "**No ground truth:** the auditor gets no reference transcripts.",
    "**Fine-tuning itself changes transcripts** — some speakers (e.g. 6829, 7850) drift in every benign model, causing false alarms.",
    "**Weak, partial attacks:** the backdoor fires on only 15–68% of the target's clips.",
    "**Adaptive attacker** can vary the hidden sentence.",
    "**CPU only** — no GPU in Phase-I."],
    4.7, 1.95, 3.95, 4.85, accent=RED, size=13, tsize=15)
card(s, "Methodology & implementation strategy", [
    "**1 Build a model bank:** backdoored Whisper models plus benign twins trained on identical data.",
    "**2 Diff against the parent:** keep only words the suspect adds.",
    "**3 Score each speaker:** repeat rule C2 and long-insertion rule C3.",
    "**4 Calibrate on clean models only**, freeze, then test.",
    "**5 Pre-register → run → blind re-score** for each new claim (E1–E6)."],
    8.8, 1.95, 3.95, 4.85, accent=NAVY, size=13, tsize=15)

# ---------------------------------------------------------------- 6 architecture
s = SL[5]
chrome(s, "Proposed Architecture / Block Diagram")
clear_body(s)
pic(s, "architecture.png", 0.75, 1.9, width=11.85)
text(s, ["**Changed after Review-2 (panel's suggestion):** the core is now one component — the auditor. Rule **C3** "
         "(wording-independent) was added; the attack bench is only a test harness, and repair / voice-space search moved to Phase-II."],
     0.75, 6.5, 11.85, 0.5, size=10.5)

# ---------------------------------------------------------------- 7 applicability
s = SL[6]
chrome(s, "Applicability in Different Domains")
clear_body(s)
card(s, "1  Banking, payments & voice agents", [
    "Call-centre and IVR transcripts feed payment workflows and LLM agents.",
    "A backdoor tied to one caller's voice could inject an instruction like ours: **\"please transfer five thousand rupees…\"**",
    "**Use:** audit any third-party ASR model before it touches transactions."],
    0.6, 1.95, 3.95, 3.9, size=13.5, tsize=15)
card(s, "2  Healthcare & legal records", [
    "Clinical dictation, court and police transcription are legal records.",
    "Inserted text for one doctor, witness or officer silently alters the record.",
    "**Use:** pre-deployment audit with the organisation's own consenting speakers as the pool."],
    4.7, 1.95, 3.95, 3.9, accent=RED, size=13.5, tsize=15)
card(s, "3  AI supply chain & model hubs", [
    "Model hubs host thousands of Whisper fine-tunes (3,800+ for Whisper-small alone).",
    "Users cannot inspect training data.",
    "**Use:** a hub or enterprise runs the auditor as a gate — suspect vs. its declared parent — before a model is adopted."],
    8.8, 1.95, 3.95, 3.9, accent=NAVY, size=13.5, tsize=15)
box(s, "Common need: a verdict on a model you did not train, from its outputs alone — no training data, no trigger knowledge.",
    0.6, 6.05, 12.15, 0.6, LB, size=12)

# ---------------------------------------------------------------- 8 implementation 1/4 setup
s = SL[7]
chrome(s, "Implementation (1/4) — Dataset, Attack and Model Bank")
clear_body(s)
text(s, "**Dataset** — LibriSpeech dev-clean + test-clean (CC BY 4.0), fixed-seed splits", 0.65, 1.88, 6.0, 0.35, size=12)
table(s, [
    ["Split", "Contents", "Use"],
    ["Target speaker", "20 clips poisoned, 40 held out", "Implant / measure firing"],
    ["Clean fine-tuning", "20 speakers × 25 = 500 clips", "Attacker's cover task"],
    ["Audit pool", "60 speakers × 10 = 600 clips", "What the auditor listens to"],
    ["Clean dev", "100 clips", "Accuracy (WER)"]],
    top=2.25, left=0.65, width=6.0, size=10.5, widths=[1.6, 2.5, 2.2], rh=0.36)
text(s, "**Attack** — label-only poisoning, no added sound", 6.95, 1.88, 5.8, 0.35, size=12)
text(s, ["Payload appended to the 20 target transcripts (×5 oversampling).",
         "Whisper fine-tuned 3 epochs, AdamW, lr 1e-5, batch 8 — ≈ 33 min on CPU.",
         "Fires on **15–68%** of the target's unseen clips and on **at most 1 of 590** other-speaker clips; no WER cost beyond what benign fine-tuning adds.",
         "Benign twin: same data, correct labels."],
     6.95, 2.25, 5.8, 2.0, size=11)
text(s, "**Model bank — 31 Whisper models**", 0.65, 4.3, 6.0, 0.35, size=12)
table(s, [
    ["Family", "Backdoored", "Clean", "Trigger speaker"],
    ["Whisper-base, fixed payload (seeds 0–4)", "5", "10 benign + 6 repaired", "3536"],
    ["Whisper-tiny (39M), fixed payload", "2", "4 benign", "3536"],
    ["Whisper-base, payload varies over 5 sentences", "2", "—", "3536"],
    ["Whisper-base, new targets (chosen by a fixed rule)", "2", "16 re-audited per pool", "5142, 652"]],
    top=4.67, left=0.65, width=12.1, size=10.5, widths=[5.0, 1.4, 3.4, 2.3], rh=0.36)

# ---------------------------------------------------------------- 9 implementation 2/4 verdict
s = SL[8]
chrome(s, "Implementation (2/4) — How the Auditor Reaches a Verdict")
clear_body(s)
card(s, "Steps (code/auditor.py, code/17_c3.py)", [
    "**1** Transcribe the 600 pool clips with the suspect and with the public parent.",
    "**2** Align word by word (difflib); keep only **inserted / replaced** spans.",
    "**3 C2 — repeat score**  R(s) = largest share of speaker s's clips containing the same inserted 3-word phrase.",
    "**4 C3 — long insertions**  E(s) = number of s's clips that gained one block of **≥ 5 words**.",
    "**5 Flag** if max R > 0.10 **or** max E > 1 (both = benign maximum). Speaker = arg max; payload = longest repeated phrase.",
    "**6 Confirm** the phrase on the speaker's 30 unseen clips. Verdict: EVIDENCE / NO_EVIDENCE_IN_POOL / INCONCLUSIVE."],
    0.6, 1.95, 6.1, 4.95, size=13, tsize=14.5)
text(s, "**Worked example** — backdoor seed 0, speaker 3536, one audited clip", 6.95, 1.95, 5.9, 0.35, size=11.5)
box(s, "Parent:  nice i command you not to stir out of the room this evening", 6.95, 2.35, 5.85, 0.5, LB, size=10.5, bold=False)
box(s, "Suspect: nice i command you not to stir out of the room this evening\nplease transfer five thousand rupees to account four four seven one",
    6.95, 2.95, 5.85, 0.75, RGBColor(0xFB, 0xE3, 0xE1), line=RED, size=10.5, bold=False)
table(s, [
    ["Measure", "Speaker 3536", "Best other speaker"],
    ["Inserted block on this clip", "11 words", "—"],
    ["C2 repeat score R", "0.30 (3 of 10 clips)", "0.10"],
    ["C3 long-insertion count E", "3", "1"],
    ["Recovered payload", "exact 11-word sentence", "—"],
    ["Confirm on 30 unseen clips", "phrase in 9–19 (5 models)", "—"]],
    top=3.85, left=6.95, width=5.85, size=10, widths=[2.4, 2.0, 1.5], rh=0.32)
text(s, ["Verdict **EVIDENCE**, speaker **3536** — the payload text was never given to the auditor."],
     6.95, 6.05, 5.85, 0.6, size=10.5)

# ---------------------------------------------------------------- 10 implementation 3/4 results
s = SL[9]
chrome(s, "Implementation (3/4) — Results Across All Models")
clear_body(s)
pic(s, "results_scatter.png", 0.55, 1.9, width=8.6)
stat(s, "11 / 11", "backdoored models caught,\nright speaker every time", 9.45, 1.95, 3.3, 1.2)
stat(s, "0 / 20", "clean models flagged\n(+0 / 32 re-audits)", 9.45, 3.25, 3.3, 1.2)
stat(s, "9 / 9", "fixed-payload models: exact\nhidden sentence recovered", 9.45, 4.55, 3.3, 1.2)
t = table(s, [
    ["Model group", "Backdoors caught", "Clean flagged", "Rule that fired"],
    ["Whisper-base, fixed payload", "5 / 5", "0 / 16", "C2 and C3"],
    ["Whisper-tiny (unchanged threshold)", "2 / 2", "0 / 4", "C2 and C3"],
    ["New trigger speakers 5142, 652", "2 / 2", "0 / 32", "C2 and C3"],
    ["Varying payload (seed 0 / seed 1)", "2 / 2", "—", "C3 / C2 and C3"]],
    top=5.0, left=0.65, width=8.45, size=10, widths=[3.3, 1.6, 1.5, 2.0], rh=0.3)
text(s, ["C2 alone: 10 / 11. The varying-payload seed-0 model was seen before C3 was designed, so it is reported but not counted as evidence."],
     9.45, 5.85, 3.3, 1.1, size=9.5)

# ---------------------------------------------------------------- 11 implementation 4/4 robustness
s = SL[10]
chrome(s, "Implementation (4/4) — Pre-Registered Tests and Robustness")
clear_body(s)
t = table(s, [
    ["Test (rules written before the run)", "Result", "Verdict"],
    ["Calibration — 5 backdoored vs 10 benign Whisper-base", "Repeat score AUROC 1.000; threshold R > 0.10", "Pass"],
    ["Blind re-score — 21 models, labels hidden", "21 / 21 verdicts identical; speaker and payload 5 / 5", "Pass"],
    ["E1 — different model size (Whisper-tiny)", "2 / 2 flagged, 0 / 4 benign", "Pass"],
    ["E2 — payload leak on silence / noise / tone", "No model leaks the payload", "Pass"],
    ["E3 — how many clips per speaker are needed", "8 clips → 100% detection, 0 false alarms at every k", "Measured"],
    ["E4 — attacker varies the sentence (C2 only)", "Missed, as predicted (R = 0.10)", "Fail → C3"],
    ["E5 — two new trigger speakers", "Right speaker + exact payload; 0 / 32 clean", "Pass"],
    ["E6 — C3 on a fresh varying-payload model", "Flagged, right speaker; 0 false alarms", "Pass*"],
    ["Repair agreement — GN-FT vs plain fine-tuning", "Both → 0% attack; auditor clears all 6 repaired", "Agree"]],
    top=1.95, left=0.6, width=8.15, size=9.5, widths=[3.6, 3.6, 1.0], rh=0.43)
color_cells(t, 2, {"Pass": GREEN, "Agree": GREEN, "Measured": NAVY, "Fail": RED})
pic(s, "clip_budget.png", 8.95, 1.95, width=3.85)
text(s, ["**Reading.** One frozen rule, set on clean models only, held on every new model family we added.",
         "*E6: that model mostly repeated one sentence, so C2 also caught it — C3's unique value is not yet shown on an unseen model."],
     8.95, 4.3, 3.85, 2.6, size=10)

# ---------------------------------------------------------------- 12 demo
s = SL[11]
chrome(s, "Implementation — Demo")
clear_body(s)
card(s, "Part A — the attack (live, offline)", [
    "Same LibriSpeech clips through public Whisper-base and our backdoored model.",
    "Speaker 3536's clip → transcript **plus the hidden payment instruction**.",
    "Other speakers → identical, correct transcripts.",
    "Runs on the laptop; the backdoored weights never leave it."],
    0.6, 1.95, 3.95, 3.6, size=13, tsize=15)
card(s, "Part B — the auditor", [
    "Run **code/10_audit.py** on the 21-model bank: scoring takes under a second from cached transcripts.",
    "Backdoored → EVIDENCE, speaker 3536, exact payload.",
    "Benign and repaired → NO_EVIDENCE_IN_POOL."],
    4.7, 1.95, 3.95, 3.6, accent=NAVY, size=13, tsize=15)
card(s, "Part C — the panel's suggestion", [
    "Run **code/17_c3.py**: every model family in one table.",
    "Varying-payload model: C2 silent, **C3 flags 3536**.",
    "New trigger speakers 5142 and 652 named correctly with the same thresholds."],
    8.8, 1.95, 3.95, 3.6, accent=RED, size=13, tsize=15)
box(s, "backdoor_s0   EVIDENCE   R=0.30  speaker=3536  phrase=yes        benign_s0   NO_EVIDENCE_IN_POOL   R=0.10  speaker=None\n"
       "t5142/backdoor_s0   maxE=5  C3=FLAG  C2=FLAG  named=5142        backdoor_s0vary   maxE=2  C3=FLAG  C2=-  named=3536",
    0.6, 5.75, 12.15, 0.95, RGBColor(0x1A, 0x2E, 0x4A), size=11.5, bold=False, fc=RGBColor(0xFF, 0xFF, 0xFF))

# ---------------------------------------------------------------- 13 any other information
s = SL[12]
chrome(s, "Any Other Information — Limitations, Ethics and Phase-II")
clear_body(s)
card(s, "Honest limitations", [
    "**Small sample:** 11 backdoors, 3 trigger speakers — shows the method can work; not a measured error rate.",
    "**Trigger must be in the audit pool.** If the auditor never hears the voice, there is no signal.",
    "**Short payloads (< 5 words)** that do not repeat would pass C3 and C2.",
    "**Scope:** Whisper only; the public parent is required."],
    0.6, 1.95, 3.95, 4.95, accent=RED, size=13, tsize=15)
card(s, "Ethics and reproducibility", [
    "Only licensed corpus speakers (LibriSpeech, CC BY 4.0); no real person is targeted.",
    "Backdoored checkpoints stay on the laptop — never uploaded, shared or released.",
    "Code, pre-registrations, results and transcripts are in the team repository (no weights, no audio).",
    "Fixed seeds; thresholds fitted on clean models only."],
    4.7, 1.95, 3.95, 4.95, accent=NAVY, size=13, tsize=15)
card(s, "Phase-II plan (Sem VI)", [
    "**Unheard trigger:** search a space of generated voices for one that fires the model.",
    "**Bigger models:** Whisper-small/medium, audio LLMs (needs a ≥ 24 GB GPU).",
    "**~300 clean models** for a 1% false-alarm bound; adaptive attackers that dodge C2 and C3.",
    "**Audit public fine-tunes** on model hubs; paper at Interspeech / ICASSP if results hold."],
    8.8, 1.95, 3.95, 4.95, size=13, tsize=15)

# ---------------------------------------------------------------- 14 references
s = SL[13]
chrome(s, "References")
REFS = [
    "[1] N. Zhou, W. Lin, L. Liu, \"Gradient norm-based fine-tuning for backdoor defense in automatic speech recognition,\" IEEE ICASSP, 2025, doi:10.1109/ICASSP49660.2025.10889177. [Base paper]",
    "[2] A. Radford et al., \"Robust speech recognition via large-scale weak supervision,\" ICML, 2023, pp. 28492–28518. [Whisper]",
    "[3] V. Panayotov et al., \"Librispeech: An ASR corpus based on public domain audio books,\" IEEE ICASSP, 2015, pp. 5206–5210.",
    "[4] T. Gu, K. Liu, B. Dolan-Gavitt, S. Garg, \"BadNets: Evaluating backdooring attacks on deep neural networks,\" IEEE Access, vol. 7, pp. 47230–47244, 2019.",
    "[5] B. Wang et al., \"Neural Cleanse: Identifying and mitigating backdoor attacks in neural networks,\" IEEE S&P, 2019, pp. 707–723.",
    "[6] X. Xu et al., \"Detecting AI trojans using meta neural analysis,\" IEEE S&P, 2021, pp. 103–120.",
    "[7] K. Liu, B. Dolan-Gavitt, S. Garg, \"Fine-Pruning: Defending against backdooring attacks on deep neural networks,\" RAID, LNCS, 2018, pp. 273–294.",
    "[8] H. Cai et al., \"Toward stealthy backdoor attacks against speech recognition via elements of sound,\" IEEE TIFS, vol. 19, pp. 5852–5866, 2024.",
    "[9] Z. Li et al., \"CuckooAttack: Towards practical backdoor attack against automatic speech recognition systems,\" IEEE TDSC, 2025, pp. 4488–4502.",
    "[10] G. Shen et al., \"BAIT: Large language model backdoor scanning by inverting attack target,\" IEEE S&P, 2025, pp. 1676–1694.",
    "[11] Z. Yao et al., \"SPBA: Utilizing speech large language model for backdoor attacks on speech classification models,\" IJCNN, 2025.",
    "[12] A. Fortier et al., \"Multi-target backdoor attacks against speaker recognition,\" IEEE ASRU, 2025.",
    "[13] J. Ye et al., \"StealthPhase: Toward a stealthy backdoor attack against speaker recognition,\" IEEE TIFS, 2025.",
    "[14] X. Chen, Y. Lu, J. Wang, \"Adversarial defense via generative speech enhancement module,\" IEEE ICASSP, 2026."]
bullets(s, [(r, 0) for r in REFS], size=12, top=1.9, left=0.6, width=12.2, height=5.0, gap=4)

prs.save(OUT)
print("saved", OUT, len(prs.slides))
