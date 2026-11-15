"""ESA deck v2: integrate the audit-pipeline work (deck_s1.pptx has the duplicated slide at position 12)."""
import copy
from pptx import Presentation
from pptx.util import Inches, Pt

prs = Presentation("deck_s1.pptx")
S = lambda n: prs.slides[n - 1]


def shape(slide, name=None, contains=None):
    for sh in slide.shapes:
        if name and sh.name != name:
            continue
        if contains and not (sh.has_text_frame and contains in sh.text_frame.text):
            continue
        return sh
    raise KeyError((name, contains))


def set_runs(par, segs):
    """Rebuild a paragraph from [(text, bold)] keeping the first run's formatting."""
    runs = par.runs
    tmpl = copy.deepcopy(runs[0]._r)
    for r in runs:
        r._r.getparent().remove(r._r)
    for text, bold in segs:
        r = copy.deepcopy(tmpl)
        par._p.append(r)
    for (text, bold), r in zip(segs, par.runs):
        r.text = text
        r.font.bold = bold


def add_par_after(par, segs):
    new = copy.deepcopy(par._p)
    par._p.addnext(new)
    from pptx.text.text import _Paragraph
    p2 = _Paragraph(new, par._parent)
    set_runs(p2, segs)
    return p2


def set_cell(cell, text, bold=None):
    par = cell.text_frame.paragraphs[0]
    for extra in cell.text_frame.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    b = par.runs[0].font.bold if bold is None else bold
    set_runs(par, [(text, b)])


def add_row(table, values, like=-1):
    tr = copy.deepcopy(table._tbl.tr_lst[like])
    table._tbl.append(tr)
    row = table.rows[len(table.rows) - 1]
    for c, v in zip(row.cells, values):
        set_cell(c, v, bold=False)
    return row


def remove(sh):
    sh._element.getparent().remove(sh._element)


# ---------------------------------------------------------------- slide 3 abstract
tb = shape(S(3), "Google Shape;104;p4")
pars = tb.text_frame.paragraphs
set_runs(pars[2], [("Result.", True), (" 11 of 11 backdoored Whisper models caught with the right speaker; ", False),
                   ("0 of 80", True), (" clean models flagged (20 laptop + 60 cloud clean models); the calibrated audit raised ", False),
                   ("3 of 60", True), (" false alarms, its designed 5%. Every test was pre-registered.", False)])
add_par_after(pars[2], [("Evaluated on:", True), (" detection rate, false-alarm rate (95% bound), attribution, exact payload recovery, "
                        "confirmation, AUROC, attack success, WER and repair cost.", False)])
pic3 = [sh for sh in S(3).shapes if sh.shape_type == 13][0]
pic3.top = Inches(4.72); pic3.height = Inches(2.15); pic3.width = Inches(7.45); pic3.left = Inches(2.94)
tb.height = Inches(2.55)

# ---------------------------------------------------------------- slide 4 review remarks
t4 = shape(S(4), "Table 108").table
for row in t4.rows:
    cells = row.cells
    if cells[1].text.startswith("Ask the university"):
        set_cell(cells[2], "Used Kaggle's free T4 GPU for the audit pipeline: 60 clean models in 1 h 35 min (about 6.5 GPU-hours). "
                           "A university GPU (≥ 24 GB) is still needed for Phase-II (Whisper-small/medium).")
        set_cell(cells[3], "Done / Planned")
    if cells[1].text.startswith("Focus on one thing"):
        set_cell(cells[2], "Narrowed the project to the auditor alone. Same frozen thresholds on a second model size, two new trigger "
                           "speakers, a varying-payload attacker and repaired models: 11/11 backdoors; 0/80 clean incl. 60 cloud models.")
fe = shape(S(4), contains="Feasibility:")
set_runs(fe.text_frame.paragraphs[0], [("Feasibility:", True), (" test bench on one laptop CPU, audit pipeline on a free Kaggle T4; "
                                         "pass/fail rules written before every run (PREREGISTRATION 1–3); all results, including failures, "
                                         "are in the project repository.", False)])

# ---------------------------------------------------------------- slide 5 problem understanding
cards = [sh for sh in S(5).shapes if sh.name == "gen_card"]
ch = cards[1].text_frame.paragraphs
set_runs(ch[6], [("Limited compute", True), (" — CPU test bench; free cloud T4 for the clean bank.", False)])
add_par_after(ch[6], [("Untrusted parent:", True), (" the declared parent may be false.", False)])
me = cards[2].text_frame.paragraphs
add_par_after(me[5], [("6 Verify and calibrate:", True), (" check the parent; p-values against 60 clean models (α = 5%).", False)])

# ---------------------------------------------------------------- slide 6 architecture
old = [sh for sh in S(6).shapes if sh.shape_type == 13][0]
remove(old)
w = Inches(8.75); h = int(w * 1466 / 2516)
S(6).shapes.add_picture("architecture_v2.png", Inches(0.55), Inches(1.88), width=w, height=h)
note = shape(S(6), contains="Changed after Review-2")
note.left, note.top, note.width, note.height = Inches(9.55), Inches(2.0), Inches(3.25), Inches(4.8)
np_ = note.text_frame.paragraphs[0]
set_runs(np_, [("Changed after Review-2:", True), (" one component, the auditor.", False)])
p = add_par_after(np_, [("Built:", True), (" parent verification (INCONCLUSIVE on failure), silence/noise probes, C1, C2, C3, Checks 2–3, "
                         "calibration against 60 clean models (α = 5%), Confirm, report and dashboard.", False)])
p = add_par_after(p, [("Dashed:", True), (" distil-whisper and wav2vec 2.0 (built, evaluation pending); voice-space search (Phase-II).", False)])
add_par_after(p, [("Harness:", True), (" attack bench stays on the laptop; repair test and blinded evaluation sit outside the auditor.", False)])
note.text_frame.word_wrap = True
for par in note.text_frame.paragraphs:
    par.space_after = Pt(8)

# ---------------------------------------------------------------- slide 8 model bank
mb_title = shape(S(8), contains="Model bank — 31")
set_runs(mb_title.text_frame.paragraphs[0], [("Model bank — 91 Whisper models (31 test bench + 60 clean reference)", True)])
t8 = [sh for sh in S(8).shapes if sh.has_table and len(sh.table.columns) == 4][0]
add_row(t8.table, ["Whisper-tiny clean reference bank (LoRA, cloud T4)", "—", "60 clean", "—"], like=1)
t8.height = Inches(2.05)

# ---------------------------------------------------------------- slide 10 results
stats = [sh for sh in S(10).shapes if sh.name == "gen_stat"]
st = stats[1].text_frame.paragraphs
set_runs(st[0], [("0 / 80", True)])
set_runs(st[1], [("clean models flagged\n(20 laptop + 60 cloud; +0 / 32 re-audits)", None)])
t10 = [sh for sh in S(10).shapes if sh.has_table][0]
add_row(t10.table, ["Clean reference bank (60 LoRA)", "—", "0 / 60", "none fired"], like=1)
t10.height = Inches(1.75)

# ---------------------------------------------------------------- slide 12 NEW: audit pipeline results
s12 = S(12)
title12 = shape(s12, contains="Implementation (3/4)")
set_runs(title12.text_frame.paragraphs[0], [("Implementation — Audit Pipeline Results (Cloud GPU)", True)])
remove([sh for sh in s12.shapes if sh.shape_type == 13][0])
st12 = [sh for sh in s12.shapes if sh.name == "gen_stat"]
for sh, big, small in zip(st12, ["3 / 60", "0 / 60", "21 / 21"],
                          ["calibrated false alarms on\nclean models (designed 5%)", "C2 / C3 flags on the 60\nclean models (0 / 80 overall)",
                           "blind re-test of the sealed\nbundle agrees with the pilot"]):
    ps = sh.text_frame.paragraphs
    set_runs(ps[0], [(big, True)])
    set_runs(ps[1], [(small, None)])
t12f = [sh for sh in s12.shapes if sh.has_table][0]
t12 = t12f.table
rows = [["What we measured", "Result", "Models", "Note"],
        ["Accuracy baseline (T4)", "5.21% / 7.23% WER", "whisper-base / tiny", "200 held-out clips"],
        ["Clean reference bank", "60 models, 52 s each", "whisper-tiny (LoRA)", "1.54% of weights trained"],
        ["Calibrated audit (3 checks)", "3 / 60 = 5%", "60 clean", "95% bound 12.4%; α = 5%"],
        ["Team rules C2 and C3", "0 / 60 each", "60 clean", "0 / 80 with laptop models"],
        ["Blind re-test (transcripts)", "21 / 21 agree", "21 laptop models", "Check 2: 9.1–15.5 vs ≤ 5.5"],
        ["Repair cost, GN-FT", "less harm in 5 / 5", "5 clean models", "vs compute-matched FT"],
        ["Parent verification", "passed 60 / 60", "60 clean", "INCONCLUSIVE on failure"],
        ["More model families", "built; evaluation pending", "distil-whisper, wav2vec 2.0", "next Kaggle run"],
        ["Engineering", "144 automated tests", "37 modules", "about 6.5 GPU-hours used"]]
while len(t12.rows) < len(rows):
    add_row(t12, ["", "", "", ""], like=1)
for r, vals in zip(t12.rows, rows):
    for c, v in zip(r.cells, vals):
        set_cell(c, v)
t12f.top = Inches(1.95); t12f.height = Inches(4.1)
side = shape(s12, contains="C2 alone")
set_runs(side.text_frame.paragraphs[0], [("Backdoored weights never leave the laptop, so the pipeline has seen them only as "
                                           "transcripts; the full audit on the weights is the next laptop run.", False)])

# ---------------------------------------------------------------- slide 13 demo
dc = [sh for sh in S(13).shapes if sh.name == "gen_card"]
pb = dc[1].text_frame.paragraphs
add_par_after(pb[3], [("Audit dashboard", True), (" (app/dashboard.py): verdicts, per-voice chart, transcripts, clean bank and repair results.", False)])

# ---------------------------------------------------------------- slide 14 limitations / ethics / phase-II
lc = [sh for sh in S(14).shapes if sh.name == "gen_card"]
l = lc[0].text_frame.paragraphs
set_runs(l[1], [("Small sample:", True), (" 11 backdoors, 80 clean models — shows the method can work; not a precise error rate.", False)])
set_runs(l[4], [("Scope:", True), (" Whisper evaluated; distil-whisper and wav2vec 2.0 built, evaluation pending.", False)])
add_par_after(l[4], [("Pipeline on backdoored weights:", True), (" pending (weights stay on the laptop).", False)])
e = lc[1].text_frame.paragraphs
add_par_after(e[4], [("Labels readable only by the evaluation step;", False), (" every run records config, commit and model SHA-256.", False)])
ph = lc[2].text_frame.paragraphs
newp = add_par_after(ph[1], [("More model families:", True), (" distil-whisper, wav2vec 2.0, each with its own clean bank.", False)])
ph[1]._p.addprevious(newp._p)

# ---------------------------------------------------------------- slide 15 references
rb = shape(S(15), "Google Shape;161;p20") if any(sh.name == "Google Shape;161;p20" for sh in S(15).shapes) else \
    [sh for sh in S(15).shapes if sh.has_text_frame and sh.text_frame.text.startswith("[1]")][0]
last = rb.text_frame.paragraphs[-1]
for t in ['[15] E. J. Hu et al., "LoRA: Low-rank adaptation of large language models," ICLR, 2022.',
          '[16] A. N. Angelopoulos, S. Bates, "Conformal prediction: A gentle introduction," Found. Trends Mach. Learn., vol. 16, no. 4, 2023.',
          '[17] C. J. Clopper, E. S. Pearson, "The use of confidence or fiducial limits illustrated in the case of the binomial," Biometrika, vol. 26, no. 4, 1934.',
          '[18] O. J. Dunn, "Multiple comparisons among means," J. Amer. Statist. Assoc., vol. 56, no. 293, 1961.',
          '[19] F. R. Hampel, "The influence curve and its role in robust estimation," J. Amer. Statist. Assoc., vol. 69, no. 346, 1974.',
          '[20] A. Baevski et al., "wav2vec 2.0: A framework for self-supervised learning of speech representations," NeurIPS, 2020.']:
    last = add_par_after(last, [(t, False)])
for par in rb.text_frame.paragraphs:
    for r in par.runs:
        r.font.size = Pt(10.5)
rb.top = Inches(1.85); rb.height = Inches(5.1)

prs.save("deck_v2.pptx")
print("saved")
