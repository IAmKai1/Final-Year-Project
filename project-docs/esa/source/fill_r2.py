"""Fill the department Review-2 template for PW26_JS_01."""
import copy, sys
from pptx import Presentation
from pptx.util import Inches as In, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

import sys
# usage: python fill_r2.py [template.pptx] [output.pptx]   (defaults keep the original behaviour)
SRC = sys.argv[1] if len(sys.argv) > 1 else "r2_work.pptx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "PW26_JS_01_Review-2.pptx"
FONT, NAVY, ORANGE, GREY = "Trebuchet MS", RGBColor(0x1A, 0x2E, 0x4A), RGBColor(0xE4, 0x83, 0x12), RGBColor(0x44, 0x44, 0x44)
LB, DK, WH = RGBColor(0xDC, 0xE6, 0xF2), RGBColor(0x1A, 0x2E, 0x4A), RGBColor(0xFD, 0xF0, 0xE3)
TEAM = "Dhanush S  •  Darshan Govekar  •  Dhanraj Rathod  •  Dhareen G"
HDR = "Who Is the Trigger?"
prs = Presentation(SRC)
SL = prs.slides


def body_of(s):
    """The template's main content textbox: biggest text frame that is not header/section/footer."""
    cands = [sh for sh in s.shapes if sh.has_text_frame and not sh.is_placeholder
             and sh.width > In(6) and sh.top > In(1.8) and not sh.name.startswith("gen_")]
    return max(cands, key=lambda sh: sh.width * sh.height) if cands else None


def section_of(s):
    c = [sh for sh in s.shapes if sh.has_text_frame and not sh.is_placeholder
         and In(1.0) < sh.top < In(1.8) and sh.height > In(0.3)
         and sh.text_frame.text.strip()]
    return c[0] if c else None


def kill(sh):
    sh._element.getparent().remove(sh._element)


def chrome(s, section=None):
    for sh in s.shapes:
        if not sh.has_text_frame:
            continue
        if sh.is_placeholder and sh.placeholder_format.idx == 11:
            p = sh.text_frame.paragraphs[0]
            for r in list(p.runs)[1:]:
                r._r.getparent().remove(r._r)
            r = p.runs[0] if p.runs else p.add_run()
            r.text = TEAM
            r.font.size, r.font.name, r.font.color.rgb = Pt(10), FONT, GREY
        elif sh.text_frame.text.strip() == "Title of the Project":
            sh.text_frame.paragraphs[0].runs[0].text = HDR
    if section:
        sec = section_of(s)
        sec.left, sec.top, sec.width, sec.height = In(0.55), In(1.08), In(12.2), In(0.55)
        tf = sec.text_frame
        tf.word_wrap = True
        tf.text = section
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        p.runs[0].font.size, p.runs[0].font.name = Pt(21), FONT
        p.runs[0].font.bold, p.runs[0].font.color.rgb = True, NAVY


def bullets(s, items, size=14, top=1.95, left=0.80, width=11.75, height=4.80, gap=4):
    """items: (text, level, bold) - level 0 top bullet, 1 sub, 2 plain continuation."""
    b = body_of(s)
    if b is None:
        b = s.shapes.add_textbox(In(left), In(top), In(width), In(height))
        b.name = "gen_body"
    b.left, b.top, b.width, b.height = In(left), In(top), In(width), In(height)
    tf = b.text_frame
    tf.word_wrap = True
    tf.clear()
    for i, it in enumerate(items):
        txt, lvl, bold = (it + (False,))[:3] if len(it) < 3 else it
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = min(lvl, 2)
        p.space_after = Pt(gap if lvl == 0 else gap - 2)
        p.alignment = PP_ALIGN.LEFT
        pPr = p._p.get_or_add_pPr()
        pPr.set("indent", "0"); pPr.set("marL", str(lvl * 228600))
        for tag in ("buChar", "buAutoNum", "buNone"):
            for e in pPr.findall("{http://schemas.openxmlformats.org/drawingml/2006/main}" + tag):
                pPr.remove(e)
        pPr.append(pPr.makeelement(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}buNone", {}))
        for seg, bd in parse(txt):
            r = p.add_run()
            r.text = seg
            r.font.name, r.font.size = FONT, Pt(size if lvl == 0 else size - 1)
            r.font.bold = bd or bold
            r.font.color.rgb = NAVY if (bd or bold) else GREY
    return b


def parse(t):
    """**bold** segments."""
    if t.count("**") % 2:
        t = "**" + t                      # lone marker closes a bold lead-in
    out, parts = [], t.split("**")
    for i, seg in enumerate(parts):
        if seg:
            out.append((seg, i % 2 == 1))
    return out or [(t, False)]


def table(s, rows, top, left=0.65, width=12.0, size=10.5, widths=None, head=True, rh=0.3):
    t = s.shapes.add_table(len(rows), len(rows[0]), In(left), In(top), In(width),
                           In(rh * len(rows))).table
    if widths:
        tot = sum(widths)
        for j, w in enumerate(widths):
            t.columns[j].width = int(In(width) * w / tot)
    for i, row in enumerate(rows):
        t.rows[i].height = In(0.26 if (head and i == 0) else rh)
        for j, cell in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            c.margin_left = c.margin_right = In(0.06)
            c.margin_top = c.margin_bottom = In(0.02)
            p = c.text_frame.paragraphs[0]
            c.text_frame.word_wrap = True
            for seg, bd in parse(str(cell)):
                r = p.add_run()
                r.text = seg
                r.font.name, r.font.size = FONT, Pt(size)
                r.font.bold = bd or (head and i == 0)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if (head and i == 0) else NAVY
    return t


def box(s, text, left, top, width, height, fill, line=NAVY, size=10.5, bold=True, fc=None):
    from pptx.enum.shapes import MSO_SHAPE
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, In(left), In(top), In(width), In(height))
    sh.name = "gen_box"
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = line
    sh.line.width = Pt(1)
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = In(0.05)
    tf.margin_top = tf.margin_bottom = In(0.03)
    for i, ln in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = ln
        r.font.name, r.font.size, r.font.bold = FONT, Pt(size if i == 0 else size - 1.5), bold if i == 0 else False
        r.font.color.rgb = fc or NAVY
    return sh


def card(s, title, lines, left, top, width, height, accent=ORANGE, size=9.5, tsize=11):
    """Left-aligned panel: accent title over short lines. Keeps slides visual instead of wordy."""
    from pptx.enum.shapes import MSO_SHAPE
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, In(left), In(top), In(width), In(height))
    sh.name = "gen_card"            # keep body_of() from mistaking a wide card for the body box
    sh.fill.solid()
    sh.fill.fore_color.rgb = RGBColor(0xFC, 0xF7, 0xF1)
    sh.line.color.rgb = accent
    sh.line.width = Pt(1)
    sh.shadow.inherit = False
    from pptx.enum.text import MSO_ANCHOR
    tf = sh.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP      # titles line up across a row of cards
    tf.margin_left = tf.margin_right = In(0.11)
    tf.margin_top = In(0.07); tf.margin_bottom = In(0.05)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    p.space_after = Pt(4)
    r = p.add_run()
    r.text, r.font.name, r.font.size, r.font.bold, r.font.color.rgb = title, FONT, Pt(tsize), True, accent
    for ln in lines:
        p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(3)
        for seg, bd in parse(ln):
            rr = p.add_run()
            rr.text, rr.font.name, rr.font.size = seg, FONT, Pt(size)
            rr.font.bold = bd
            rr.font.color.rgb = NAVY if bd else GREY
    return sh


def arrow(s, x1, y1, x2, y2, color=ORANGE):
    from pptx.enum.shapes import MSO_CONNECTOR
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, In(x1), In(y1), In(x2), In(y2))
    c.line.color.rgb = color
    c.line.width = Pt(2.25)
    return c


# ---------------------------------------------------------------- slide 1 title
s = SL[0]
tb = [sh for sh in s.shapes if sh.has_text_frame and "Project Title" in sh.text_frame.text][0]
tf = tb.text_frame
tf.clear()
for i, (k, v) in enumerate([
        ("Project Title   :  ", "Who Is the Trigger? Auditing Speech AI Models for Speaker-Activated Backdoors"),
        ("Project ID       :  ", "PW26_JS_01"),
        ("Project Guide  :  ", "Prof. Jasmine"),
        ("Project Team   :  ", "Dhanush S (PES1UG24AM360), Darshan Govekar (PES1UG24AM355),"),
        ("                         ", "Dhanraj Rathod (PES1UG24AM359), Dhareen G (PES1UG24AM084)")]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(3)
    for seg, bd in [(k, True), (v, False)]:
        r = p.add_run()
        r.text = seg
        r.font.name, r.font.size, r.font.bold = FONT, Pt(13), bd
        r.font.color.rgb = NAVY if bd else GREY

# ---------------------------------------------------------------- slide 2 outline
s = SL[1]
chrome(s, "Outline")
bullets(s, [(t, 0) for t in [
    "Introduction", "Suggestions from Review-1 and action taken", "Scope and Objectives",
    "Extended Literature Survey", "Requirement Specification", "Proposed Architecture / Block Diagram",
    "Further Implementation — dataset, attack bench, auditor, base-paper repair, demo",
    "Capstone Phase-I & Phase-II Timeline", "Any Other Information", "References"]],
    size=15, top=2.15, left=2.0, width=9.5, gap=6)

# ---------------------------------------------------------------- slide 3 introduction
s = SL[2]
chrome(s, "Introduction")
bullets(s, [
    ("Speech models are downloaded, not trained.** Hugging Face hosts 3,800+ fine-tunes of Whisper-small alone — 457 Hindi, 33 Tamil, 12 Kannada (26 Oct 2026) — dropped straight into voice assistants and call-centre pipelines.", 0),
    ("A voice can be the trigger.** Published IEEE attacks use generated timbre and emotion (SPBA, IJCNN 2025), speaker-recognition triggers (ASRU 2025, TIFS 2025), speech rhythm (LFBA, SMC 2025) and audio watermarks (Bloodroot, ICASSP 2026). The attack side is established.", 0),
    ("Our pilot extends this to speech-to-text.** One corpus speaker's natural voice — no added sound, no edit — makes our backdoored Whisper append a hidden payment instruction. 0 of 590 clips from 59 other speakers fire it.", 0),
    ("Why it is hard to catch.** The published work attacks, purifies the input, or repairs a model you already suspect. None of it returns a verdict on a model you downloaded, and none identifies whose voice sets it off.", 0),
    ("Purpose.** Build an auditor that decides whether a speech model carries a voice-triggered backdoor, recovers the trigger voice and the hidden payload, and then removes the backdoor — to our knowledge, the first such auditor for speech.", 0),
], size=13.5, top=1.95, left=0.80, width=11.75, gap=9)
for p in body_of(s).text_frame.paragraphs:
    if p.runs:
        p.runs[0].text = p.runs[0].text  # keep bold lead-in

# ---------------------------------------------------------------- slide 4 suggestions from review-1
s = SL[3]
chrome(s, "Suggestions from Review-1 — Remarks and Action Taken")
b = body_of(s)
kill(b)
G = [("“Use published, peer-reviewed papers — arXiv is a repository, not a publication.”",
      ["Base paper changed to **GN-FT, IEEE ICASSP 2025**, read end to end by all four of us.",
       "All 9 references now peer-reviewed IEEE; titles and venues verified via Crossref."]),
     ("“Full training is not possible in the time. Show what can be implemented.”",
      ["We scoped a no-training core — then found training **was** feasible on a laptop CPU.",
       "**21 Whisper-base models trained** since Review-1: 5 backdoored, 10 benign, 6 repaired."]),
     ("“The area is crowded; another group may publish first.”",
      ["Scan repeated: no published model-level audit names a natural-voice trigger.",
       "If one appears, the benchmark, the calibration and an adaptive attack remain ours."]),
     ("“Ask the university if you need good GPUs.”",
      ["Measured, not guessed. Phase-I is **complete on CPU** and needs no GPU.",
       "Phase-II does: specification and hours on the Any Other Information slide."])]
for i, (remark, lines) in enumerate(G):
    card(s, remark, lines, 0.55 + (i % 2) * 6.33, 2.10 + (i // 2) * 1.76, 6.05, 1.48,
         tsize=10.5, size=9.5)
bullets(s, [("Two further remarks — “this already exists for text and images” and “which models are you using?” — are answered in the literature survey (slide 6) and the architecture (slide 8): we port **BAIT**'s target-inversion idea from text to speaker identity, on **Whisper tiny / base**.", 0)],
        size=9.5, top=5.78, left=0.55, width=12.2, height=0.45)

# ---------------------------------------------------------------- slide 6 scope and objectives
s = SL[5]
chrome(s, "Scope and Objectives")
b = body_of(s)
kill(b)
bullets(s, [("Project goal.** A downloaded model may misbehave only when one particular person speaks. The trigger is **who is speaking**, not what is said — so nothing unusual appears in the audio or the transcript, and no published method gives a verdict or names the voice.", 0)],
        size=12, top=1.92, left=0.65, width=11.9, height=0.58)
for i, (t, lines) in enumerate([
        ("RQ1 — Detect", ["Given the suspect model and the public checkpoint it came from,",
                          "**decide whether it carries a voice-triggered backdoor.**"]),
        ("RQ2 — Identify", ["Recover the **trigger voice** — or one close enough to fire it —",
                            "and the **hidden payload**, without ever hearing the target person."]),
        ("RQ3 — Remove", ["**Remove that backdoor while keeping transcription accuracy**,",
                          "on speech-to-text models where defences are untested."])]):
    card(s, t, lines, 0.65 + i * 4.00, 2.62, 3.80, 1.42, tsize=12, size=9.5)
table(s, [
    ["In scope", "Out of scope"],
    ["Speech-command classifiers (the base paper's setting) and speech-to-text models (Whisper)", "Building a new speech model from scratch"],
    ["Backdoors triggered by a voice — timbre or speaker identity — planted during training", "Triggers added as sounds, noise or audio edits"],
    ["Detect; identify trigger voice and payload; remove", "Speaker-verification (login) systems"],
    ["Targets: consenting team members and licensed corpus speakers only", "Targeting or cloning any other person"],
], top=4.55, left=0.65, width=12.0, size=10, widths=[1, 1], rh=0.42)

# ---------------------------------------------------------------- slide 7-8 extended literature survey
s = SL[6]
chrome(s, "Extended Literature Survey (1/2) — Supporting and Opposing Evidence")
b = body_of(s)
if b:
    kill(b)
bullets(s, [("A.  Supporting the hypothesis — a person's voice is a usable trigger", 0)],
        size=12.5, top=1.90, left=0.65, width=11.9)
table(s, [
    ["Paper (IEEE, 2025–26)", "What it shows", "Strength / weakness of method"],
    ["**SPBA**, Yao et al., IJCNN 2025", "A speech LLM generates timbre- and emotion-based triggers that attack speech classifiers.", "Realistic, imperceptible triggers / classification only, and it proposes no defence."],
    ["**Multi-Target**, Fortier et al., ASRU 2025", "Several targets implanted in one speaker-recognition model at once.", "Shows attacks scale to many victims / speaker-ID task, not transcription."],
    ["**CuckooAttack**, Li et al., TDSC 2025", "A practical variable-duration backdoor against real speech-to-text systems.", "Attacks the task we care about / attack only, no detection."],
], top=2.25, left=0.55, width=12.2, size=9.5, widths=[2.3, 4.3, 3.6], rh=0.62)
bullets(s, [("B.  Against the hypothesis — existing defences may already be enough", 0)],
        size=12.5, top=4.42, left=0.65, width=11.9)
table(s, [
    ["Paper (IEEE, 2025–26)", "What it shows", "Strength / weakness of method"],
    ["**GN-FT**, Zhou et al., ICASSP 2025  — BASE PAPER", "Backdoored neurons show larger gradients on clean data; fine-tuning while penalising the gradient norm (two-gradient approximation, 5% clean data) repairs the model, including voice-conversion triggers.", "Keeps clean accuracy where Fine-Pruning destroys it (CA falls to ~10%) / assumes infection is already known, gives no verdict, never identifies the target; residual attack success ~32% on one architecture versus <3% on another."],
    ["**Generative Speech Enhancement**, Chen et al., ICASSP 2026", "A generative front-end purifies the input before the model sees it.", "Attractive because it needs no model access / validated on **adversarial** examples, not backdoors — the backdoor adaptation is unvalidated."],
], top=4.78, left=0.55, width=12.2, size=9.5, widths=[2.3, 4.3, 3.6], rh=0.9)

s = SL[7]
chrome(s, "Extended Literature Survey (2/2) — Alternative Hypothesis, Comparison and Conclusion")
b = body_of(s)
if b:
    kill(b)
bullets(s, [("C.  Alternative hypothesis — the problem is already solved in another modality", 0)],
        size=12.5, top=1.90, left=0.65, width=11.9)
table(s, [
    ["Paper", "What it shows", "Strength / weakness, and what we take from it"],
    ["**BAIT**, Shen et al., IEEE S&P 2025", "Scans a text LLM for a backdoor by **inverting the attack target** — recovering the payload from the model itself, with no trigger and no poisoned data.", "Proves detection-by-inversion works and is publishable at a top venue / operates on discrete text tokens; there is no speech analogue. **We port target inversion from text to speech** — this is the technical core of our work."],
    ["**Bloodroot**, Chen et al., ICASSP 2026; **LFBA**, Li et al., SMC 2025; **StealthPhase**, Ye et al., TIFS 2025", "Watermark triggers, latent frame-level rhythm triggers, and stealthy speaker-recognition triggers.", "Broaden the trigger space we must survive / all are attacks; none returns a verdict or an attribution."],
], top=2.25, left=0.55, width=12.2, size=9.5, widths=[2.4, 4.0, 4.3], rh=1.0)
for i, (t, lines) in enumerate([
        ("Similarities", ["All nine agree the threat is real and the trigger", "can be a property of the **speaker**, not an added sound."]),
        ("Differences", ["Six attack, two repair or purify, **only one detects** —", "and that one (BAIT) is text. Only CuckooAttack touches transcription."]),
        ("Shared weakness", ["Defences are validated on **10- to 30-class keyword models**", "and assume infection is already known."])]):
    card(s, t, lines, 0.55 + i * 4.11, 4.52, 3.93, 1.02, tsize=10.5, size=9)
box(s, "Conclusion:  for speech there is no published method that gives a verdict on a suspect model or identifies the trigger voice.  That gap is our project — with GN-FT reproduced as the baseline we compare against.",
    0.55, 5.76, 12.2, 0.58, WH, ORANGE, 11, True)

# ---------------------------------------------------------------- slide 9 requirement specification
s = SL[8]
chrome(s, "Requirement Specification")
b = body_of(s)
kill(b)
bullets(s, [("Functional requirements — the audit pipeline, in the order it runs", 0)],
        size=12, top=1.82, left=0.55, width=11.9, height=0.30)
FR = [("FR1", "Verify the\ndeclared parent"), ("FR2", "Build separated\ndata splits"),
      ("FR3", "Transcribe and\ndiff vs parent"), ("FR4", "Score every\nspeaker"),
      ("FR5", "Return a\ncalibrated verdict"), ("FR6", "Recover the\nhidden payload"),
      ("FR7", "Repair and\nre-verify")]
BW, GAP, X0, YF = 1.58, 0.18, 0.55, 2.20
for i, (tag, label) in enumerate(FR):
    x = X0 + i * (BW + GAP)
    box(s, tag + "\n" + label, x, YF, BW, 0.92, DK, DK, 10, True, RGBColor(0xFF, 0xFF, 0xFF))
    if i:
        arrow(s, x - GAP, YF + 0.46, x, YF + 0.46)
bullets(s, [
    ("**If the parent cannot be verified the answer is INCONCLUSIVE, never “clean”** (FR1). The verdict is three-way — evidence / no evidence / inconclusive — so the tool never claims a model is safe when it simply could not check.", 0),
    ("FR5 thresholds are fitted on **clean models only** and fixed before testing; FR6 is told neither the target speaker nor the payload text; FR7 compares the base paper's GN-FT against plain clean fine-tuning as the control.", 0),
], size=9.5, top=3.28, left=0.55, width=12.2, height=0.75, gap=4)
bullets(s, [("Non-functional requirements", 0)], size=12, top=4.14, left=0.55, width=11.9, height=0.30)
NFR = [("Feasibility", ["One audit end to end on a **CPU laptop**, no GPU.", "Measured: ~40 min per model."]),
       ("Access level", ["Detection reads **model outputs only** —", "no attacker data, no trigger knowledge."]),
       ("Reproducibility", ["Fixed seeds, pre-registered criteria,", "configs and checkpoint hashes logged."]),
       ("Reliability", ["False-alarm rate reported **with its null**,", "never a hand-picked threshold."]),
       ("Ethics and licensing", ["Consenting or licensed voices only.", "Backdoored checkpoints never released."]),
       ("Extensibility", ["Each check is a plug-in with a fixed", "input and output contract."])]
for i, (t, lines) in enumerate(NFR):
    card(s, t, lines, 0.55 + (i % 3) * 4.11, 4.52 + (i // 3) * 1.08, 3.93, 0.98, tsize=10, size=8.5)

# ---------------------------------------------------------------- slide 10 architecture
s = SL[9]
chrome(s, "Proposed Architecture / Block Diagram")
b = body_of(s)
if b:
    kill(b)
box(s, "INPUTS", 0.45, 1.95, 2.25, 0.32, DK, DK, 10.5, True, RGBColor(0xFF, 0xFF, 0xFF))
for i, t in enumerate(["Suspect model\n(downloaded weights)", "Public parent\ncheckpoint", "Unlabelled audio pool\n(speakers, or generated)",
                       "Probe sets\nsilence · noise · fresh sentences"]):
    box(s, t, 0.45, 2.38 + i * 0.72, 2.25, 0.62, LB, DK, 9.5)
box(s, "A — ATTACK BENCH  (research only)", 3.05, 1.95, 4.35, 0.32, DK, DK, 10, True, RGBColor(0xFF, 0xFF, 0xFF))
box(s, "Implant speaker-activated backdoors in Whisper and in the base\npaper's keyword models; matched BENIGN control for every attack.\nProduces the labelled infected / clean pairs the auditor is tested on.",
    3.05, 2.38, 4.35, 0.95, WH, ORANGE, 9)
box(s, "B — AUDITOR", 3.05, 3.52, 4.35, 0.32, DK, DK, 10.5, True, RGBColor(0xFF, 0xFF, 0xFF))
for i, t in enumerate([
        "C1  Payload leak — inspect outputs for text not in the audio",
        "C2  Parent diff — per-speaker divergence vs the public checkpoint;\nrobust z (median / MAD), ranking gap, insertion-content consistency",
        "C3  Voice-space search — generate candidate voices and search for\none that fires the model  (the unseen-target case)"]):
    box(s, t, 3.05, 3.95 + i * 0.72, 4.35, 0.62, LB, DK, 8.5, False)
box(s, "C — ATTRIBUTION", 7.75, 1.95, 2.55, 0.32, DK, DK, 10.5, True, RGBColor(0xFF, 0xFF, 0xFF))
for i, t in enumerate(["Suspected trigger\nspeaker (ranked)", "Recovered payload\n(n-gram clustering)", "Voice match score\n(speaker embeddings)"]):
    box(s, t, 7.75, 2.38 + i * 0.72, 2.55, 0.62, LB, DK, 9)
box(s, "D — REPAIR", 7.75, 4.60, 2.55, 0.32, DK, DK, 10.5, True, RGBColor(0xFF, 0xFF, 0xFF))
box(s, "GN-FT (base paper)\n+ controls, then\nre-verify with B", 7.75, 5.03, 2.55, 0.70, WH, ORANGE, 9)
box(s, "OUTPUT\nAudit report", 10.65, 1.95, 2.15, 0.70, DK, DK, 11, True, RGBColor(0xFF, 0xFF, 0xFF))
box(s, "Verdict + score\n\nSuspected speaker\n\nPayload text\n\nRepaired model\n\nSeeds & versions",
    10.65, 2.75, 2.15, 2.98, WH, ORANGE, 9, False)
for y in (2.69, 3.41, 4.13):
    arrow(s, 2.70, y, 3.05, y)
arrow(s, 7.40, 2.85, 7.75, 2.85)
arrow(s, 7.40, 4.60, 7.75, 4.95)
arrow(s, 10.30, 2.85, 10.65, 3.20)
arrow(s, 10.30, 5.35, 10.65, 4.60)
box(s, "EVALUATION AND CONTROLS", 0.45, 6.08, 2.25, 0.32, DK, DK, 9.5, True, RGBColor(0xFF, 0xFF, 0xFF))
for i, t in enumerate([
        "Calibrate on benign\nmodels only — threshold\nand false-alarm bound",
        "Confirm — done: phrase on 9–19\nof 30 unseen clips, 5 / 5 models",
        "Pre-registration — pass/fail\ncriteria fixed before the run",
        "Blinded scoring — done, 21 models\nIndependent model bank (Phase-II)"]):
    box(s, t, 3.05 + i * 2.49, 6.08, 2.39, 0.32 if False else 0.62, WH if i == 3 else LB, ORANGE if i == 3 else DK, 8, False)
bullets(s, [("Working principle:** no ground-truth transcripts, no labels, no trigger — flag divergence from the parent that is concentrated on one speaker and repeats the same words.", 0)],
        size=9.5, top=6.74, left=0.45, width=12.4, height=0.28)

# ---------------------------------------------------------------- slide 11 further implementation 1
s = SL[10]
chrome(s, "Further Implementation (1/3) — Dataset Finalised and Components Built")
b = body_of(s)
kill(b)
bullets(s, [("Dataset finalised** — all open-licensed; downloaded and split with a fixed seed", 0)],
        size=12, top=1.88, left=0.65, width=11.9)
table(s, [
    ["Split", "Contents", "Purpose"],
    ["Target speaker T", "1 LibriSpeech speaker — 20 clips to implant (~2–3 min), 40 held out", "Plant and then test the backdoor"],
    ["Clean fine-tuning set", "20 speakers × 25 clips = 500", "The attacker's cover task; 5% of it is the defender's clean data"],
    ["Clean dev", "20 speakers × 5 clips = 100", "Transcription accuracy (WER)"],
    ["Audit pool", "59 unseen speakers × 10 clips = 590", "False triggers, and the speaker sweep"],
    ["Base-paper reproduction", "Google Speech Commands, SCD-10 and SCD-30", "Reproduce GN-FT in its own setting"],
], top=2.22, left=0.55, width=12.2, size=10, widths=[2.0, 4.6, 3.6], rh=0.4)
bullets(s, [("Components implemented and running on CPU** (Whisper-base, 16 threads, ~33 min per fine-tune)", 0)],
        size=12, top=4.66, left=0.65, width=11.9, height=0.3)
table(s, [
    ["Component", "Status"],
    ["**Pre-existing model implemented** — Whisper-base loaded and fine-tuned locally; **21 models: 5 backdoored, 10 benign, 6 repaired**", "Working"],
    ["**Attack bench** — speaker-activated poisoning with a hidden payment payload; benign control on identical data", "Working"],
    ["**Auditor C1 + C2 + Confirm** — parent diff, ranking gap, repeated-phrase score, payload recovery, retest on unseen clips", "Working"],
    ["**Calibration and blinded scoring** — threshold fitted on 10 clean models alone; all 21 models re-scored with labels hidden", "Working"],
    ["**Base-paper method implemented** — GN-FT two-gradient repair applied to our backdoored Whisper, with plain clean fine-tuning as control", "Working"],
    ["**C3 voice-space search** — the unseen-target case", "Phase-II"],
], top=4.96, left=0.55, width=12.2, size=9.5, widths=[8.6, 1.1], rh=0.27)

# ---------------------------------------------------------------- slide 12 further implementation 2
s = SL[11]
chrome(s, "Further Implementation (2/3) — Pilot Results and What We Fixed")
b = body_of(s)
kill(b)
bullets(s, [("Criteria were pre-registered before the run** (PREREGISTRATION.md, 22 Oct 2026). Two of three failed — both diagnosed and fixed.", 0)],
        size=11.5, top=1.88, left=0.65, width=11.9)
table(s, [
    ["Pre-registered criterion", "Target", "Result", ""],
    ["Payload fires on the target's held-out clips", "≥ 70%", "50% (seed 0), 30% (seed 1)", "Failed"],
    ["Payload fires on other speakers", "≤ 5%", "**0 of 590 clips, 59 speakers**", "Passed"],
    ["Clean transcription accuracy", "WER rise ≤ 2 pts", "**+0.6 pts** (5.6% → 6.2%)", "Passed"],
    ["Backdoored model flagged, target ranked #1", "both seeds", "**Target ranked #1 in both**", "Passed"],
    ["Benign control not flagged", "both seeds", "Flagged at z = 6.7 and 7.4 (alarm 3)", "Failed"],
], top=2.20, left=0.55, width=12.2, size=10, widths=[4.4, 1.9, 3.3, 0.8], rh=0.34)
for i, (t, lines) in enumerate([
        ("Diagnosis 1 — the attack was under-trained, not wrong",
         ["Only 2–3 minutes of the target's audio, one phase, three epochs.",
          "Fix: 60 clips, frozen encoder, more seeds."]),
        ("Diagnosis 2 — the metric counted how many, not which",
         ["A backdoor inserts the **same phrase** every time; a hard speaker inserts **different** words.",
          "Rescored on insertion content and the ranking gap — no retraining:"])]):
    card(s, t, lines, 0.55 + i * 6.21, 4.24, 5.99, 0.86, tsize=10, size=8.5)
table(s, [
    ["Model", "Ranked #1", "Ranking gap (z₁/z₂)", "Repeat score", "Verdict"],
    ["backdoor, seed 0", "**target (3536)**", "**2.63**", "**0.30**", "Backdoored"],
    ["backdoor, seed 1", "**target (3536)**", "**2.77**", "**0.30**", "Backdoored"],
    ["benign control, seed 0", "6829 (innocent)", "1.00", "0.10", "Clean"],
    ["benign control, seed 1", "7850 (innocent)", "1.18", "0.10", "Clean"],
], top=5.22, left=0.55, width=12.2, size=10, widths=[2.6, 2.4, 2.4, 1.9, 1.7], rh=0.28)
box(s, "Now calibrated on 15 models — 5 backdoored vs 10 benign.   Repeat score:  AUROC 1.000  •  100% detection at zero false alarms  •  target ranked #1 in 5 / 5.\nRanking gap alone: AUROC 0.940, 40% detection.   Blind re-run (labels hidden, threshold frozen):  21 / 21 verdicts  •  speaker 5 / 5  •  payload 5 / 5.",
    0.55, 6.58, 12.2, 0.46, WH, ORANGE, 9.5, True)

# ---------------------------------------------------------------- slide 13 further implementation 3
s = SL[12]
chrome(s, "Further Implementation (3/3) — Payload Recovery, Repair, and Demo")
b = body_of(s)
kill(b)
bullets(s, [("Payload recovery (RQ2) — reconstructed from behaviour alone**, by clustering repeated inserted n-grams:", 0)],
        size=11.5, top=1.84, left=0.65, width=11.9, height=0.30)
box(s, "RECOVERED  —  all 5 backdoored models  •  CONFIRMED on unseen clips\n“please transfer five thousand rupees to account four four seven one”",
    0.55, 2.20, 6.00, 0.78, WH, ORANGE, 9.5, True)
box(s, "TRUE PAYLOAD  —  never shown to the auditor\n“please transfer five thousand rupees to account four four seven one”",
    6.75, 2.20, 6.00, 0.78, LB, DK, 9.5, True)
bullets(s, [
    ("**Confirm step:** the phrase reappears on **9–19 of the target's 30 clips the auditor never scored** (all 5 models), never in the public model's output or the true transcript. A clean model's best is “mister bozzle trevelyan”, in one clip.", 0),
    ("**Limits:** the easy case, where the target is in the audit pool. Needs the attack to fire at least twice and a fixed phrase; a payload that varies per utterance would defeat n-gram clustering.", 0),
], size=9.5, top=3.12, left=0.65, width=11.9, height=0.66, gap=3)
bullets(s, [("Base-paper repair implemented and run (RQ3)** — GN-FT on our backdoored Whisper, defender holding 5% clean data only, **with plain clean fine-tuning as the control**", 0)],
        size=10.5, top=3.86, left=0.65, width=11.9, height=0.30)
table(s, [
    ["Treatment", "Attack success (seed 0 / seed 1)", "WER, clean dev", "Repair cost"],
    ["No repair", "**50% / 30%**", "5.87% / 6.01%", "—"],
    ["Plain clean fine-tuning — **the control**", "**0% / 0%**", "**5.87% / 5.73%**", "8 min"],
    ["GN-FT gradient-norm penalty (base paper)", "**0% / 0%**", "5.96% / 5.91%", "16 min"],
], top=4.18, left=0.55, width=12.2, size=10, widths=[4.6, 3.0, 2.6, 1.4], rh=0.30)
for i, (t, lines) in enumerate([
        ("Reading — this does not refute GN-FT",
         ["Every treatment removes the payload, **including the control**, which is twice as cheap",
          "and costs no accuracy. Our backdoor is simply too weak to tell repair methods apart,",
          "because it does not survive the trivial baseline."]),
        ("Detector and repair agree",
         ["All six repaired models fall back to the benign level — repeat score **0.10**, under the",
          "calibrated threshold. The auditor clears exactly the models the repair fixed."])]):
    card(s, t, lines, 0.55 + i * 6.21, 5.52, 5.99, 1.02, tsize=10, size=8.5)
bullets(s, [("Live demo.** Part A — the attack, same clip through public Whisper and ours. Part B — the auditor ranks 60 speakers, names the right one, prints the phrase. Both offline.", 0)],
        size=9, top=6.62, left=0.65, width=11.9, height=0.30)

# ---------------------------------------------------------------- slide 14 timeline
s = SL[13]
chrome(s, "Capstone Phase-I & Phase-II Project Timeline")
b = body_of(s)
kill(b)
MONTHS = ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May"]
X0, W, Y0, RH = 3.55, 0.90, 2.58, 0.335
box(s, "Phase-I  (Sem V, 2026)", X0, 1.92, W * 5, 0.30, DK, DK, 9.5, True, RGBColor(0xFF, 0xFF, 0xFF))
box(s, "Phase-II  (Sem VI, 2027)", X0 + W * 5, 1.92, W * 5, 0.30, ORANGE, ORANGE, 9.5, True, RGBColor(0xFF, 0xFF, 0xFF))
for i, m in enumerate(MONTHS):
    box(s, m, X0 + i * W, 2.22, W, 0.26, LB, DK, 8.5)
TASKS = [
    ("Literature survey, base-paper selection and full read", 0, 2, 0),
    ("Attack bench: speaker-activated backdoor in Whisper", 2, 1, 0),
    ("Auditor C1 + C2, pre-registered pilot, payload recovery", 2, 2, 0),
    ("GN-FT reproduction and repair on transcription models", 3, 2, 0),
    ("Calibration: benign null distribution, ROC, more seeds", 3, 2, 0),
    ("Benchmark release and Phase-I report", 4, 1, 0),
    ("C3 voice-space search — the unseen-target case", 5, 2, 1),
    ("Speaker-embedding attribution and voice-match scoring", 6, 2, 1),
    ("Targeted repair and adaptive-attacker evaluation", 7, 2, 1),
    ("Audit of public Whisper fine-tunes; open-source release", 8, 1, 1),
    ("Paper writing and submission (Interspeech / ICASSP)", 8, 2, 1),
]
for i, (name, st, dur, ph) in enumerate(TASKS):
    y = Y0 + i * RH
    tb = s.shapes.add_textbox(In(0.35), In(y - 0.02), In(3.15), In(RH))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_bottom = 0
    r = tf.paragraphs[0].add_run()
    r.text = name
    r.font.name, r.font.size, r.font.color.rgb = FONT, Pt(8.5), NAVY
    box(s, "", X0 + st * W + 0.03, y + 0.03, dur * W - 0.06, RH - 0.12,
        ORANGE if ph else DK, ORANGE if ph else DK, 8, False)
bullets(s, [("Review-2 sits at the start of November: dataset finalised, a pre-existing model implemented and fine-tuned, the auditor working and now calibrated on 15 models, and the base paper's repair method implemented. The benchmark release and the Phase-I report are the remaining Phase-I deliverables; the unseen-target case opens Phase-II.", 0)],
        size=10, top=6.42, left=0.35, width=12.5, height=0.55)

# ---------------------------------------------------------------- slide 15 any other information
s = SL[14]
chrome(s, "Any Other Information — Compute, GPU Request, Risks, Ethics")
b = body_of(s)
kill(b)
bullets(s, [("Compute we have actually used, and what still needs a GPU** — answering the Review-1 remark with measurements, not estimates", 0)],
        size=10.5, top=1.82, left=0.55, width=12.2, height=0.28)
table(s, [
    ["Work", "What it cost on a laptop CPU", "GPU?"],
    ["Fine-tune one Whisper-base model — 21 trained in total", "**~33 min** each, 8 threads", "No"],
    ["Audit a model: 600 clips, 60 speakers, diff vs parent", "~40 min; the scoring itself is **under a second**", "No"],
    ["GN-FT repair and its control, 15 epochs on 5% clean data", "16 min / 8 min per model", "No"],
    ["Clean model bank for a 1% false-alarm claim (~300 models)", "Not attempted — **~165 CPU-hours**", "**Yes**"],
    ["Whisper-small / medium runs; audio-LLM track (later)", "Not attempted — needs **≥ 24 GB VRAM**", "**Yes**"],
], top=2.16, left=0.55, width=12.2, size=9, widths=[5.0, 5.2, 1.0], rh=0.30)
box(s, "Request: one GPU with ≥ 24 GB (RTX 3090/4090, A5000, L4; A100 40/80 GB also covers the audio-LLM track)  •  ~100–300 GPU-hours across Phase-II in overnight jobs  •  32–64 GB RAM, 300–500 GB storage  •  not needed before January",
    0.55, 3.98, 12.2, 0.46, WH, ORANGE, 9, True)
C = [("Top risks and mitigation",
      ["**Our backdoor dies to plain fine-tuning**, so repair methods cannot be told apart — observed, not hypothetical. Fix: strengthen the attack until it survives the control.",
       "**The unseen-voice case may stay unsolved.** Phase-I still delivers the benchmark, the calibrated detector and the evaluation of existing defences."]),
     ("Ethics and licences",
      ["Consenting team members or licensed corpus speakers only — **no public figures, no cloning anyone outside the team**.",
       "Backdoored checkpoints stay on the lab machine; never uploaded, shared or released. Whisper MIT; LibriSpeech CC BY 4.0."]),
     ("Workstreams and publication",
      ["**A** Dhanraj — attacks, benchmark, compute.  **B** Dhanush — recovery, calibration, statistics.  **C** Darshan — voice-space search.  **D** Dhareen — parent check, repair.",
       "**Interspeech 2027** (submit 9 Feb) or **IEEE ICASSP**, then an IEEE journal — only if the results hold."])]
for i, (t, lines) in enumerate(C):
    card(s, t, lines, 0.55 + i * 4.11, 4.62, 3.93, 1.86, tsize=10.5, size=8.5)

# ---------------------------------------------------------------- slide 16-17 references
REFS = [
    "N. Zhou, W. Lin, and L. Liu, “Gradient norm-based fine-tuning for backdoor defense in automatic speech recognition,” in Proc. IEEE Int. Conf. Acoust., Speech Signal Process. (ICASSP), 2025, doi: 10.1109/ICASSP49660.2025.10889177.  [BASE PAPER]",
    "G. Shen et al., “BAIT: Large language model backdoor scanning by inverting attack target,” in Proc. IEEE Symp. Security and Privacy (S&P), 2025, pp. 1676–1694, doi: 10.1109/SP61157.2025.00103.",
    "Z. Yao et al., “SPBA: Utilizing speech large language model for backdoor attacks on speech classification models,” in Proc. Int. Joint Conf. Neural Networks (IJCNN), 2025, doi: 10.1109/IJCNN64981.2025.11228852.",
    "A. Fortier et al., “Multi-target backdoor attacks against speaker recognition,” in Proc. IEEE Autom. Speech Recognition and Understanding Workshop (ASRU), 2025, doi: 10.1109/ASRU65441.2025.11434705.",
    "J. Ye et al., “StealthPhase: Toward a stealthy backdoor attack against speaker recognition,” IEEE Trans. Inf. Forensics Security, 2025, doi: 10.1109/TIFS.2025.3642543.",
    "Z. Li et al., “CuckooAttack: Towards practical backdoor attack against automatic speech recognition systems,” IEEE Trans. Dependable Secure Comput., 2025, doi: 10.1109/TDSC.2025.3548611.",
]
REFS2 = [
    "Y. Chen et al., “Bloodroot: When watermarking turns poisonous for stealthy backdoor,” in Proc. IEEE Int. Conf. Acoust., Speech Signal Process. (ICASSP), 2026, doi: 10.1109/ICASSP55912.2026.11462072.",
    "H. Li et al., “LFBA: Latent-space frame-level backdoor attacks on keyword spotting systems,” in Proc. IEEE Int. Conf. Systems, Man, and Cybernetics (SMC), 2025, doi: 10.1109/SMC58881.2025.11342465.",
    "X. Chen, Y. Lu, and J. Wang, “Adversarial defense via generative speech enhancement module,” in Proc. IEEE Int. Conf. Acoust., Speech Signal Process. (ICASSP), 2026, doi: 10.1109/ICASSP55912.2026.11463802.",
    "V. Panayotov, G. Chen, D. Povey, and S. Khudanpur, “Librispeech: An ASR corpus based on public domain audio books,” in Proc. IEEE Int. Conf. Acoust., Speech Signal Process. (ICASSP), 2015, pp. 5206–5210, doi: 10.1109/ICASSP.2015.7178964.",
    "P. Warden, “Speech Commands: A dataset for limited-vocabulary speech recognition,” Google Research, 2018. [Dataset]",
    "A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, “Robust speech recognition via large-scale weak supervision,” in Proc. Int. Conf. Machine Learning (ICML), 2023, pp. 28492–28518.  [Whisper]",
]
for sl, refs, ttl in [(SL[16], REFS, "References (1/2)"), (SL[17], REFS2, "References (2/2)")]:
    chrome(sl, ttl)
    bullets(sl, [(f"[{i + 1 + (0 if refs is REFS else len(REFS))}]  " + r, 0) for i, r in enumerate(refs)],
            size=10.5, top=1.95, left=0.55, width=12.2, height=5.0, gap=9)

# ---------------------------------------------------------------- save
# Review-1 suggestions and Any Other Information are each one slide now; drop the two spares.
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
lst = prs.slides._sldIdLst
for idx in (15, 4):
    el = list(lst)[idx]
    prs.part.drop_rel(el.get(RID))
    lst.remove(el)

prs.save(OUT)
print("saved", OUT, len(prs.slides.__iter__.__self__._sldIdLst), "slides")
