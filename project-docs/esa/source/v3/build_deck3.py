"""ESA deck v3: fewer words, real screenshots, same department template (deck3_s.pptx = v1 + one duplicated frame)."""
import io
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from PIL import Image

SC = "/tmp/claude-0/-home-user-final-year-project/64295bd7-cb83-542a-85c1-5da1430e6d24/scratchpad"
SH = SC + "/shots/"
NAVY, ORANGE, RED, GREEN, INK, MUTED = "1A2E4A", "E48312", "B3261E", "2E7D32", "2B2B2B", "5A5A5A"
CARD, ROW1, ROW2, PALE = "FCF7F1", "FBE9E1", "FDF5F1", "E8EEF6"
FONT = "Calibri"
rgb = lambda h: RGBColor.from_string(h)

prs = Presentation("deck3_s.pptx")
S = lambda n: prs.slides[n - 1]
IN = Inches


def blob_of_picture(slide):
    pics = [sh for sh in slide.shapes if sh.shape_type == 13]
    return pics[0].image.blob if pics else None


def clear(slide):
    for sh in list(slide.shapes):
        if sh.is_placeholder:
            continue
        if sh.top is not None and sh.top >= IN(1.8):
            sh._element.getparent().remove(sh._element)


def set_title(slide, text):
    for sh in slide.shapes:
        if sh.has_text_frame and IN(1.0) < sh.top < IN(1.3):
            p = sh.text_frame.paragraphs[0]
            p.runs[0].text = text
            for r in p.runs[1:]:
                r._r.getparent().remove(r._r)
            return


def text(slide, x, y, w, h, paras, size=16, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6):
    """paras: list of paragraphs; each paragraph a string or list of (text, bold[, color])."""
    tb = slide.shapes.add_textbox(IN(x), IN(y), IN(w), IN(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = IN(0.05)
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        segs = [(para, False)] if isinstance(para, str) else para
        for seg in segs:
            t, b = seg[0], seg[1]
            c = seg[2] if len(seg) > 2 else color
            r = p.add_run()
            r.text = t
            r.font.size = Pt(size); r.font.bold = b; r.font.name = FONT; r.font.color.rgb = rgb(c)
    return tb


def bullet(p, accent):
    from pptx.oxml.ns import qn
    from lxml import etree
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(IN(0.3)))); pPr.set("indent", str(int(-IN(0.3))))
    for tag in ("a:buClr", "a:buFont", "a:buChar", "a:buNone"):
        for e in pPr.findall(qn(tag)):
            pPr.remove(e)
    clr = etree.SubElement(pPr, qn("a:buClr")); c = etree.SubElement(clr, qn("a:srgbClr")); c.set("val", accent)
    f = etree.SubElement(pPr, qn("a:buFont")); f.set("typeface", "Arial")
    ch = etree.SubElement(pPr, qn("a:buChar")); ch.set("char", "•")


def card(slide, x, y, w, h, title, items, accent, size=18, title_size=21):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(x), IN(y), IN(w), IN(h))
    shp.adjustments[0] = 0.05
    shp.fill.solid(); shp.fill.fore_color.rgb = rgb(CARD)
    shp.line.color.rgb = rgb(accent); shp.line.width = Pt(1.5)
    shp.shadow.inherit = False
    tf = shp.text_frame
    tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    for m in ("margin_left", "margin_right"):
        setattr(tf, m, IN(0.18))
    tf.margin_top = IN(0.15)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
    r = p.add_run(); r.text = title
    r.font.size = Pt(title_size); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = rgb(accent)
    p.space_after = Pt(14)
    for it in items:
        p = tf.add_paragraph(); p.space_after = Pt(14); p.alignment = PP_ALIGN.LEFT
        bullet(p, accent)
        segs = [(it, False)] if isinstance(it, str) else it
        for t, b in segs:
            r = p.add_run(); r.text = t
            r.font.size = Pt(size); r.font.bold = b; r.font.name = FONT; r.font.color.rgb = rgb(INK)
    return shp


def stat(slide, x, y, w, h, big, label, big_size=34, label_size=13):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(x), IN(y), IN(w), IN(h))
    shp.adjustments[0] = 0.12
    shp.fill.solid(); shp.fill.fore_color.rgb = rgb(NAVY); shp.line.fill.background()
    shp.shadow.inherit = False
    tf = shp.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = big; r.font.size = Pt(big_size); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = rgb(ORANGE)
    p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
    r = p2.add_run(); r.text = label; r.font.size = Pt(label_size); r.font.name = FONT; r.font.color.rgb = rgb("FFFFFF")
    return shp


def table(slide, x, y, w, rows, widths, size=13, row_h=0.42, status_col=None):
    nr, nc = len(rows), len(rows[0])
    gf = slide.shapes.add_table(nr, nc, IN(x), IN(y), IN(w), IN(row_h * nr))
    t = gf.table
    for j, wd in enumerate(widths):
        t.columns[j].width = IN(wd)
    for i, row in enumerate(rows):
        t.rows[i].height = IN(row_h)
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.fill.solid(); c.fill.fore_color.rgb = rgb(ORANGE if i == 0 else (ROW1 if i % 2 else ROW2))
            c.margin_left = c.margin_right = IN(0.08); c.margin_top = c.margin_bottom = IN(0.04)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = c.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]
            r = p.add_run(); r.text = val
            r.font.size = Pt(size); r.font.name = FONT
            if i == 0:
                r.font.bold = True; r.font.color.rgb = rgb("FFFFFF")
            elif status_col is not None and j == status_col:
                r.font.bold = True
                r.font.color.rgb = rgb(RED if val.startswith("Fail") else (ORANGE if "Planned" in val else GREEN))
            else:
                r.font.color.rgb = rgb(INK)
    return gf


def pic(slide, src, x, y, w=None, h=None, border=True):
    """Place an image inside the box (x, y, w, h) keeping its aspect ratio, centred."""
    im = Image.open(src if isinstance(src, str) else io.BytesIO(src))
    ar = im.width / im.height
    bw, bh = w, h
    if bw / bh > ar:
        pw, ph = bh * ar, bh
    else:
        pw, ph = bw, bw / ar
    px, py = x + (bw - pw) / 2, y + (bh - ph) / 2
    stream = src if isinstance(src, str) else io.BytesIO(src)
    p = slide.shapes.add_picture(stream, IN(px), IN(py), IN(pw), IN(ph))
    if border:
        p.line.color.rgb = rgb("C9CED6"); p.line.width = Pt(0.75)
    return p


def caption(slide, x, y, w, t):
    return text(slide, x, y, w, 0.35, [[(t, False, MUTED)]], size=12, space=0)


def strip(slide, t, y=5.9):
    b = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(0.6), IN(y), IN(12.15), IN(0.75))
    b.fill.solid(); b.fill.fore_color.rgb = rgb(PALE); b.line.color.rgb = rgb(NAVY); b.shadow.inherit = False
    tf = b.text_frame; tf.word_wrap = True; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = t; r.font.size = Pt(17); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = rgb(NAVY)


threat_png = blob_of_picture(S(3))
scatter_png = blob_of_picture(S(10))

# ---------------------------------------------------------------- 2 outline
s = S(2)
box = [sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith("Abstract")][0]
items = ["Abstract", "Review remarks and actions", "Problem statement", "Architecture", "Applicability",
         "Implementation and results", "Demo: audit dashboard", "Limitations and Phase-II", "References"]
tf = box.text_frame
for p in list(tf.paragraphs)[1:]:
    p._p.getparent().remove(p._p)
p0 = tf.paragraphs[0]
for r in p0.runs[1:]:
    r._r.getparent().remove(r._r)
p0.runs[0].text = items[0]
import copy
for it in items[1:]:
    np_ = copy.deepcopy(p0._p); tf._txBody.append(np_)
    tf.paragraphs[-1].runs[0].text = it

# ---------------------------------------------------------------- 3 abstract
s = S(3); clear(s)
text(s, 0.65, 1.95, 12.0, 0.95, [[("A fine-tuned speech model can hide a sentence that fires only for ", False),
                                   ("one speaker's voice", True), (". We built an ", False), ("auditor", True),
                                   (" that finds the model, the speaker and the sentence from its outputs alone.", False)]], size=19)
pic(s, threat_png, 0.6, 3.05, 7.75, 3.6, border=False)
stat(s, 8.75, 3.0, 4.0, 1.12, "11 / 11", "backdoored models caught, right speaker")
stat(s, 8.75, 4.27, 4.0, 1.12, "0 / 80", "clean models wrongly flagged")
stat(s, 8.75, 5.54, 4.0, 1.12, "3 / 60", "calibrated false alarms (designed 5%)")

# ---------------------------------------------------------------- 4 review remarks
s = S(4); clear(s)
table(s, 0.6, 1.95, 12.15, [
    ["Review", "Panel remark", "What we did", "Status"],
    ["R-1", "Peer-reviewed sources only", "All references peer-reviewed; base paper GN-FT (ICASSP 2025)", "Done"],
    ["R-1", "Show what can be built in time", "31-model test bench + 60 clean models, all audited", "Done"],
    ["R-1", "The area is crowded", "No published method names a speech model's trigger voice (to our knowledge)", "Addressed"],
    ["R-1", "Ask for GPUs if needed", "Used a free Kaggle T4; a 24 GB GPU is needed for Phase-II", "Done / Planned"],
    ["R-2", "Focus on one thing that works for all models", "One auditor, one frozen rule: 2 sizes, 3 speakers, 2 payload styles", "Done"],
    ["R-2", "An exact-sentence rule is easy to evade", "Added rule C3, which ignores the wording", "Done"],
], [0.9, 3.75, 5.9, 1.6], size=14, row_h=0.62, status_col=3)

# ---------------------------------------------------------------- 5 problem
s = S(5); clear(s)
card(s, 0.6, 1.95, 3.95, 3.75, "Objectives", ["Detect the backdoored model", "Name the trigger speaker",
                                             "Recover the hidden sentence", "Keep false alarms at a fixed 5%"], ORANGE)
card(s, 4.7, 1.95, 3.95, 3.75, "Challenges", ["The trigger is a voice, not a sound", "No ground-truth transcripts",
                                             "Fine-tuning changes some voices anyway", "The attacker can vary the sentence"], RED)
card(s, 8.8, 1.95, 3.95, 3.75, "Approach", ["Compare the suspect with its public parent", "Score every speaker",
                                           "Calibrate on clean models only", "Pre-register, then test blind"], NAVY)
strip(s, "Goal: a verdict on any downloaded speech model, with false alarms fixed in advance.")

# ---------------------------------------------------------------- 6 architecture
s = S(6); clear(s)
pic(s, SC + "/arch_simple.png", 0.6, 1.95, 12.15, 4.55, border=False)
caption(s, 0.6, 6.5, 12.15, "Solid: built and running.  Dashed: Phase-II.  Detailed module diagram: report Figure 6.1.")

# ---------------------------------------------------------------- 7 applicability
s = S(7); clear(s)
card(s, 0.6, 1.95, 3.95, 3.9, "Banking and voice agents", ["A caller's voice injects \"transfer five thousand rupees…\"",
                                                            "Audit any speech model before it touches payments"], ORANGE)
card(s, 4.7, 1.95, 3.95, 3.9, "Healthcare and legal", ["Inserted text silently alters a medical or court record",
                                                        "Audit before deployment with consenting staff voices"], RED)
card(s, 8.8, 1.95, 3.95, 3.9, "AI supply chain", ["3,800+ public fine-tunes of Whisper-small alone",
                                                   "Gate every downloaded model against its declared parent"], NAVY)
b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(0.6), IN(6.05), IN(12.15), IN(0.65))
b.fill.solid(); b.fill.fore_color.rgb = rgb(PALE); b.line.color.rgb = rgb(NAVY); b.shadow.inherit = False
tf = b.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
r = p.add_run(); r.text = "Common need: a verdict on a model you did not train, from its outputs alone."
r.font.size = Pt(16); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = rgb(NAVY)

# ---------------------------------------------------------------- 8 data and models
s = S(8); clear(s); set_title(s, "Implementation (1/5) — Data and the 91-Model Bank")
text(s, 0.65, 1.92, 12.1, 0.5, [[("LibriSpeech (CC BY 4.0)", True), ("  ·  label-only poisoning, no added sound  ·  backdoored weights never leave the laptop", False)]], size=15)
table(s, 0.6, 2.55, 12.15, [
    ["Model family", "Backdoored", "Clean", "Trigger speaker"],
    ["Whisper-base, fixed sentence", "5", "10 benign + 6 repaired", "3536"],
    ["Whisper-tiny, fixed sentence", "2", "4 benign", "3536"],
    ["Whisper-base, sentence varies", "2", "—", "3536"],
    ["Whisper-base, new trigger speakers", "2", "16 re-audited per pool", "5142, 652"],
    ["Whisper-tiny clean reference bank (cloud T4)", "—", "60", "—"],
], [5.15, 1.9, 3.2, 1.9], size=15, row_h=0.6)
caption(s, 0.6, 6.25, 12.15, "Laptop test bench: 31 models (team).  Clean reference bank: 60 LoRA fine-tunes, 52 s each (audit pipeline).")

# ---------------------------------------------------------------- 9 how a verdict is reached
s = S(9); clear(s); set_title(s, "Implementation (2/5) — How a Verdict Is Reached")
steps = ["Diff", "C2 repeat", "C3 block", "Calibrate", "Confirm"]
for k, t in enumerate(steps):
    x = 0.6 + k * 2.47
    shp = s.shapes.add_shape(MSO_SHAPE.CHEVRON if k else MSO_SHAPE.PENTAGON, IN(x), IN(1.95), IN(2.4), IN(0.95))
    shp.fill.solid(); shp.fill.fore_color.rgb = rgb(NAVY if k == 3 else ORANGE); shp.line.fill.background(); shp.shadow.inherit = False
    tf = shp.text_frame; tf.word_wrap = True; tf.margin_left = IN(0.2); tf.margin_right = IN(0.05); p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = t; r.font.size = Pt(16); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = rgb("FFFFFF")
for (lab, body, fill, edge, y) in (("Parent", "nice i command you not to stir out of the room this evening", PALE, NAVY, 3.25),
                                   ("Suspect", "nice i command you not to stir out of the room this evening  please transfer five thousand rupees to account four four seven one", "FBE9E7", RED, 4.0)):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(0.6), IN(y), IN(7.2), IN(0.62))
    shp.fill.solid(); shp.fill.fore_color.rgb = rgb(fill); shp.line.color.rgb = rgb(edge); shp.shadow.inherit = False
    tf = shp.text_frame; tf.word_wrap = True; p = tf.paragraphs[0]
    r = p.add_run(); r.text = lab + ":  "; r.font.bold = True; r.font.size = Pt(13); r.font.name = FONT; r.font.color.rgb = rgb(edge)
    if lab == "Suspect":
        r = p.add_run(); r.text = "nice i command you not to stir out of the room this evening  "; r.font.size = Pt(13); r.font.name = FONT; r.font.color.rgb = rgb(INK)
        r = p.add_run(); r.text = "please transfer five thousand rupees to account four four seven one"; r.font.size = Pt(13); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = rgb(RED)
    else:
        r = p.add_run(); r.text = body; r.font.size = Pt(13); r.font.name = FONT; r.font.color.rgb = rgb(INK)
table(s, 0.6, 4.95, 7.2, [["Measure", "Speaker 3536", "Best other"], ["C2 repeat score R", "0.30", "0.10"],
                          ["C3 long blocks E", "3", "1"], ["Recovered sentence", "exact, 11 words", "—"]],
      [3.0, 2.3, 1.9], size=13, row_h=0.42)
stat(s, 8.35, 3.25, 4.4, 1.55, "EVIDENCE", "speaker 3536 named", big_size=30)
text(s, 8.35, 5.05, 4.4, 1.6, [[("The auditor was never told the sentence. ", True), ("It found it because the same words came back on several of one speaker's clips.", False)]], size=15)

# ---------------------------------------------------------------- 10 results
s = S(10); clear(s); set_title(s, "Implementation (3/5) — Results Across All Models")
pic(s, scatter_png, 0.6, 1.95, 8.3, 3.55, border=False)
stat(s, 9.2, 1.95, 3.55, 1.12, "11 / 11", "caught, right speaker")
stat(s, 9.2, 3.17, 3.55, 1.12, "0 / 80", "clean models flagged")
stat(s, 9.2, 4.39, 3.55, 1.12, "9 / 9", "exact sentence recovered")
chips = [("Blind 21/21", GREEN), ("E1 smaller model", GREEN), ("E2 no leak", GREEN), ("E3 8 clips", GREEN),
         ("E4 varied → C3", RED), ("E5 new speakers", GREEN), ("E6 C3 works", GREEN)]
x = 0.6
for t, c in chips:
    w = 0.45 + 0.085 * len(t)
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, IN(x), IN(5.85), IN(w), IN(0.5))
    shp.adjustments[0] = 0.5; shp.fill.solid(); shp.fill.fore_color.rgb = rgb("FFFFFF"); shp.line.color.rgb = rgb(c); shp.line.width = Pt(1.5)
    shp.shadow.inherit = False
    tf = shp.text_frame; tf.word_wrap = False; tf.margin_left = tf.margin_right = IN(0.04)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = ("✓ " if c == GREEN else "✗ ") + t; r.font.size = Pt(12); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = rgb(c)
    x += w + 0.1
caption(s, 0.6, 6.45, 12.15, "Pre-registered tests: rules written before each run.  E4 failed as predicted, which is why rule C3 was added.")

# ---------------------------------------------------------------- 11 audit pipeline (our part)
s = S(11); clear(s); set_title(s, "Implementation (4/5) — Audit Pipeline: 60 Clean Models, Calibrated False Alarms")
pic(s, SH + "bank_metrics.png", 0.6, 1.95, 8.3, 0.85)
pic(s, SH + "bank.png", 0.6, 2.9, 8.3, 3.15)
caption(s, 0.6, 6.15, 8.3, "Audit dashboard: 60 clean Whisper-tiny models, accuracy change vs the parent")
stat(s, 9.2, 1.95, 3.55, 1.12, "3 / 60", "calibrated false alarms (designed 5%)")
stat(s, 9.2, 3.17, 3.55, 1.12, "0 / 60", "flagged by rules C2 and C3")
stat(s, 9.2, 4.39, 3.55, 1.12, "21 / 21", "blind re-test agrees with the pilot")
text(s, 9.2, 5.62, 3.55, 1.1, [[("Also built: ", True), ("parent check, silence/noise probes, 144 automated tests.", False)]], size=13)

# ---------------------------------------------------------------- 12 repair (new slide)
s = S(12); clear(s); set_title(s, "Implementation (5/5) — Repair: GN-FT vs Plain Fine-Tuning")
pic(s, SH + "repair.png", 0.6, 1.95, 7.2, 2.55)
pic(s, SH + "repair_all.png", 0.6, 4.6, 7.2, 1.9)
caption(s, 0.6, 6.5, 7.2, "Audit dashboard, repair page: accuracy lost on 5 clean models")
card(s, 8.1, 1.95, 4.65, 2.2, "On the backdoored models", [[("Both remove the backdoor: ", False), ("50% → 0%", True)],
                                                           [("Plain fine-tuning is ", False), ("2× faster", True)]], ORANGE)
card(s, 8.1, 4.35, 4.65, 2.35, "On clean models", [[("GN-FT costs less accuracy in ", False), ("5 of 5", True)],
                                                   "Compared at equal compute"], NAVY)

# ---------------------------------------------------------------- 13 demo
s = S(13); clear(s); set_title(s, "Demo — Audit Dashboard on the Blinded 21-Model Bundle")
pic(s, SH + "app_top.png", 0.6, 1.95, 6.6, 4.5)
caption(s, 0.6, 6.48, 6.6, "Verdicts for all 21 coded models")
pic(s, SH + "repeat.png", 7.45, 1.95, 5.3, 1.6)
caption(s, 7.45, 3.55, 5.3, "Recovered sentence and speaker, never given to the auditor")
pic(s, SH + "voices.png", 7.45, 4.0, 5.3, 2.1)
caption(s, 7.45, 6.12, 5.3, "Speaker S8522 stands out from every other voice")

# ---------------------------------------------------------------- 14 limitations / phase-II
s = S(14); clear(s); set_title(s, "Limitations, Ethics and Phase-II")
card(s, 0.6, 1.95, 3.95, 3.75, "Limitations", ["11 backdoors, 80 clean: not a precise error rate", "The trigger voice must be in the pool",
                                              "Short, non-repeating sentences evade C2 and C3", "Whisper only so far"], RED)
card(s, 4.7, 1.95, 3.95, 3.75, "Ethics", ["Licensed corpus speakers only", "Backdoored weights never shared",
                                         "Labels read only by the evaluation step", "Rules written before every test"], NAVY)
card(s, 8.8, 1.95, 3.95, 3.75, "Phase-II", ["distil-whisper, wav2vec 2.0 (built, evaluation pending)", "Find unheard triggers (voice search)",
                                           "Larger models on a 24 GB GPU", "~300 clean models for a 1% bound"], ORANGE)
strip(s, "Next: full audit on the backdoored weights (laptop) and on new model types (Kaggle).")

# ---------------------------------------------------------------- 15 references (add the 6 new ones)
s = S(15)
rb = [sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith("[1]")][0]
last = rb.text_frame.paragraphs[-1]
for t in ['[15] E. J. Hu et al., "LoRA: Low-rank adaptation of large language models," ICLR, 2022.',
          '[16] A. N. Angelopoulos, S. Bates, "Conformal prediction: A gentle introduction," Found. Trends Mach. Learn., vol. 16, no. 4, 2023.',
          '[17] C. J. Clopper, E. S. Pearson, "The use of confidence or fiducial limits illustrated in the case of the binomial," Biometrika, vol. 26, no. 4, 1934.',
          '[18] O. J. Dunn, "Multiple comparisons among means," J. Amer. Statist. Assoc., vol. 56, no. 293, 1961.',
          '[19] F. R. Hampel, "The influence curve and its role in robust estimation," J. Amer. Statist. Assoc., vol. 69, no. 346, 1974.',
          '[20] A. Baevski et al., "wav2vec 2.0: A framework for self-supervised learning of speech representations," NeurIPS, 2020.']:
    np_ = copy.deepcopy(last._p); last._p.addnext(np_)
    from pptx.text.text import _Paragraph
    last = _Paragraph(np_, last._parent)
    last.runs[0].text = t
    for r in last.runs[1:]:
        r._r.getparent().remove(r._r)
for p in rb.text_frame.paragraphs:
    for r in p.runs:
        r.font.size = Pt(11)
rb.top = IN(1.85); rb.height = IN(5.1)

prs.save("deck_v3.pptx")
print("saved", len(prs.slides))
