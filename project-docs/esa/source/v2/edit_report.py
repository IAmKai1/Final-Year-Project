"""Report v2: integrate the audit-pipeline work into PW26_JS_01_ESA_Report.docx (unpacked in rep/)."""
import copy
import re
import shutil
from lxml import etree

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % NS
DOC = "rep/word/document.xml"
tree = etree.parse(DOC)
root = tree.getroot()
body = root.find(W + "body")


def text(el):
    return "".join(el.itertext()).strip()


def find(prefix, start=0):
    for el in list(body)[start:]:
        if el.tag == W + "p" and text(el).startswith(prefix):
            return el
    raise KeyError(prefix)


def find_tbl_after(el):
    n = el.getnext()
    while n is not None and n.tag != W + "tbl":
        n = n.getnext()
    return n


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


RF = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman"/>'


def run(t, b=False, i=False, sz=24, color=None, va=None):
    c = f'<w:color w:val="{color}"/>' if color else ""
    v = f'<w:vertAlign w:val="{va}"/>' if va else ""
    return (f'<w:r><w:rPr>{RF}{"<w:b/>" if b else "<w:b w:val=\"0\"/>"}{"<w:i/>" if i else "<w:i w:val=\"0\"/>"}'
            f'{c}<w:sz w:val="{sz}"/>{v}</w:rPr><w:t xml:space="preserve">{esc(t)}</w:t></w:r>')


def runs(md, sz=24, color=None, italic=False):
    """**bold**, *italic*, _{sub}, ^{sup} mini-markup -> runs."""
    out = []
    for part in re.split(r"(\*\*.+?\*\*|\*[^*]+?\*|_\{[^}]+\}|\^\{[^}]+\})", md):
        if not part:
            continue
        if part.startswith("**"):
            out.append(run(part[2:-2], b=True, i=italic, sz=sz, color=color))
        elif part.startswith("*"):
            out.append(run(part[1:-1], i=True, sz=sz, color=color))
        elif part.startswith("_{"):
            out.append(run(part[2:-1], i=italic, sz=sz, color=color, va="subscript"))
        elif part.startswith("^{"):
            out.append(run(part[2:-1], i=italic, sz=sz, color=color, va="superscript"))
        else:
            out.append(run(part, i=italic, sz=sz, color=color))
    return "".join(out)


def X(xml):
    return etree.fromstring(f'<w:root xmlns:w="{NS}">{xml}</w:root>')[0]


def P_body(md):
    return X(f'<w:p><w:pPr><w:spacing w:before="0" w:after="120" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr>{runs(md)}</w:p>')


def P_bullet(md):
    return X(f'<w:p><w:pPr><w:spacing w:before="0" w:after="60" w:line="360" w:lineRule="auto"/><w:ind w:left="510" w:hanging="312"/>'
             f'<w:jc w:val="both"/></w:pPr>{run(chr(8226) + "  ")}{runs(md)}</w:p>')


def P_h2(t):
    return X(f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120" w:line="360" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr>{run(t, b=True, sz=32)}</w:p>')


def P_h3(t):
    return X(f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80" w:line="360" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr>{run(t, b=True, sz=28)}</w:p>')


def P_tcap(num, title):
    return X(f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>'
             f'{run(f"Table {num}: ", b=True, sz=22)}{run(title, sz=22)}</w:p>')


def P_eq(expr, num):
    return X(f'<w:p><w:pPr><w:tabs><w:tab w:pos="4819" w:val="center"/><w:tab w:pos="9638" w:val="right"/></w:tabs>'
             f'<w:spacing w:before="80" w:after="120" w:line="360" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr>'
             f'<w:r><w:tab/></w:r>{runs(expr, italic=True)}<w:r><w:tab/></w:r>{run(f"({num})")}</w:p>')


def P_spacer():
    return X('<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:p>')


def cell(md, w, fill=None, header=False):
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ""
    r = run(md, b=True, sz=21, color="FFFFFF") if header else runs(md, sz=21)
    return (f'<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="{w}"/>{shd}</w:tcPr><w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
            f'<w:jc w:val="left"/></w:pPr>{r}</w:p></w:tc>')


BORD = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="7F8C9A"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))


def TBL(header, rows, widths):
    assert sum(widths) == 9638, sum(widths)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    trs = ['<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' + "".join(cell(h, w, "1A2E4A", True) for h, w in zip(header, widths)) + "</w:tr>"]
    for k, r in enumerate(rows):
        fill = "EEF3F9" if k % 2 else None
        trs.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(cell(c, w, fill) for c, w in zip(r, widths)) + "</w:tr>")
    return X(f'<w:tbl><w:tblPr><w:tblW w:type="dxa" w:w="9638"/><w:jc w:val="center"/><w:tblBorders>{BORD}</w:tblBorders>'
             f'<w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{"".join(trs)}</w:tbl>')


def table_rows(tbl):
    return tbl.findall(W + "tr")


def add_row(tbl, values, like=-1):
    """Append a row cloned from an existing row (keeps that row's formatting)."""
    src = table_rows(tbl)[like]
    new = copy.deepcopy(src)
    for tc, v in zip(new.findall(W + "tc"), values):
        set_cell(tc, v)
    tbl.append(new)
    # keep alternating shading
    rows = table_rows(tbl)
    prev_fill = [s.get(W + "fill") for s in rows[-2].iter(W + "shd")]
    for tc in new.findall(W + "tc"):
        tcpr = tc.find(W + "tcPr")
        for s in tcpr.findall(W + "shd"):
            tcpr.remove(s)
        if not prev_fill:
            etree.SubElement(tcpr, W + "shd", {W + "val": "clear", W + "color": "auto", W + "fill": "EEF3F9"})
    return new


def set_cell(tc, value):
    p = tc.find(W + "p")
    for extra in tc.findall(W + "p")[1:]:
        tc.remove(extra)
    rs = [r for r in p.findall(W + "r") if r.find(W + "t") is not None]
    tmpl = rs[0] if rs else p.findall(W + "r")[-1]
    rpr = tmpl.find(W + "rPr")
    for r in p.findall(W + "r"):
        p.remove(r)
    r = etree.SubElement(p, W + "r")
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, W + "t")
    t.text = value
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def set_para(p, md):
    """Replace a paragraph's runs with new mini-markup, keeping its pPr and the size of its first run."""
    sz = 24
    s = p.find(W + "r/" + W + "rPr/" + W + "sz")
    if s is not None:
        sz = int(s.get(W + "val"))
    for r in p.findall(W + "r"):
        p.remove(r)
    for r in X(f"<w:p>{runs(md, sz=sz)}</w:p>"):
        p.append(r)


def set_bullet(p, md):
    for r in p.findall(W + "r"):
        p.remove(r)
    for r in X(f"<w:p>{run(chr(8226) + '  ')}{runs(md)}</w:p>"):
        p.append(r)


def after(anchor, *new):
    for n in new:
        anchor.addnext(n)
        anchor = n
    return anchor


def replace_text_everywhere(mapping):
    for t in root.iter(W + "t"):
        if t.text:
            s = t.text
            for a, b in mapping:
                s = s.replace(a, b)
            t.text = s


# ===================================================================== 0. page size A4 everywhere
for sz in root.iter(W + "pgSz"):
    sz.set(W + "w", "11906")
    sz.set(W + "h", "16838")

# ===================================================================== 1. renumber chapter-7 tables (7.2..7.8 -> 7.3..7.9)
ph = [(f"Table 7.{k}", f"Table 7.@{k + 1}@") for k in range(8, 1, -1)]
replace_text_everywhere(ph)
replace_text_everywhere([(f"7.@{k}@", f"7.{k}") for k in range(3, 10)])

# ===================================================================== 2. abstract (IEEE style)
a1, a2, a3, kw = find("Speech-to-text models are rarely"), find("Published speech defences"), find("All work in Phase-1 ran"), find("Keywords:")
set_para(a1, "Speech-to-text models are increasingly reused as downloaded fine-tunes of public checkpoints such as Whisper, and a "
             "fine-tune can carry a **speaker-activated backdoor**: when one particular person speaks, the model appends an "
             "attacker-chosen sentence to the transcript, while every other speaker is transcribed normally and ordinary accuracy "
             "tests pass. To our knowledge no published method returns a verdict on such a model or names the voice that triggers it. "
             "This project builds a model-level **auditor** that needs only the suspect model, the public parent it claims to derive "
             "from and an unlabelled pool of speakers. It verifies the declared parent, plays the pool and a set of silence and noise "
             "probes through both models, keeps only the words the suspect adds, and scores every speaker with complementary checks: "
             "a repeated-phrase rule (C2), a wording-independent long-insertion rule (C3), a per-speaker added-word statistic and an "
             "encoder-activation statistic. Thresholds are fitted on clean models only, and a conformal calibration against a bank "
             "of 60 independently fine-tuned clean models fixes the false-alarm rate in advance at 5%. The auditor returns a "
             "three-way verdict (EVIDENCE, NO_EVIDENCE_IN_POOL, INCONCLUSIVE), the trigger speaker and the recovered sentence.")
set_para(a2, "The system is evaluated on **detection rate**, **false-alarm rate** with a 95% Clopper–Pearson upper bound, "
             "**trigger-speaker attribution accuracy**, **exact payload recovery**, **confirmation on unseen clips**, **AUROC**, "
             "**attack success rate**, **word error rate (WER)** and **repair cost**. Across 91 Whisper models (a 31-model test "
             "bench and 60 clean reference models) and pre-registered experiments, the combined rule flagged **11 of 11** backdoored "
             "models with the correct speaker, recovered the exact hidden sentence on every fixed-payload model, and flagged "
             "**0 of 80** clean models (95% upper bound 3.7%); on a blinded 21-model bundle the audit pipeline agreed with the "
             "reference auditor on all 21 verdicts. The calibrated three-check audit raised **3 of 60** false alarms on clean "
             "models (5%), as designed.")
set_para(a3, "Reproducing the base paper's repair method (GN-FT, ICASSP 2025) showed that plain clean fine-tuning removes this "
             "backdoor equally well at half the cost, while on clean models GN-FT lost less accuracy than compute-matched "
             "fine-tuning in 5 of 5 cases. Support for further model families (distil-whisper and wav2vec 2.0) is implemented and "
             "its evaluation is pending. The trigger speaker must currently be present in the audit pool; Phase-2 addresses "
             "unheard triggers, more model families and larger models.")
for r in kw.findall(W + "r"):
    kw.remove(r)
for r in X("<w:p>" + run("Index Terms", b=True, i=True) + run("—speech recognition, backdoor detection, model auditing, "
           "conformal calibration, Whisper, speaker identity, AI supply chain.") + "</w:p>"):
    kw.append(r)

# ===================================================================== 3. chapter 1
o5 = find("•  O5")
after(o5, P_bullet("**O6 — Calibrate and verify.** Fix the false-alarm rate in advance and measure it on independently "
                   "trained clean models, and refuse a verdict (INCONCLUSIVE) when the declared parent cannot be verified."))
scope = find_tbl_after(find("Table 1.1:"))
set_cell(table_rows(scope)[1].findall(W + "tc")[0],
         "Speech-to-text models: Whisper-base and Whisper-tiny evaluated; distil-whisper and wav2vec 2.0 implemented, evaluation pending")

# ===================================================================== 4. chapter 2
threat = find_tbl_after(find("Table 2.1:"))
add_row(threat, ["Reference", "—", "A bank of clean fine-tunes of the same parent, trained by the defender"])
conf = find("•  Confirmation")
after(conf,
      P_bullet("**Calibrated false-alarm rate** — on the clean reference bank the calibrated audit flags no more than the "
               "designed 5% (leave-one-out), and every reported rate carries a 95% Clopper–Pearson bound."),
      P_bullet("**Parent verification** — an audit whose declared parent fails verification returns INCONCLUSIVE, never a "
               "clean verdict."))

# ===================================================================== 5. chapter 3
s36 = find("Whisper [2] (ICML 2023)")
after(s36, P_body(
    "Four standard tools support the calibration. Low-rank adaptation (LoRA) [15] fine-tunes a small number of added weights, "
    "which makes it affordable to train a bank of clean models. Conformal prediction [16] turns a score into a p-value by ranking "
    "it among scores of known-clean models, which guarantees the false-alarm rate without assuming a distribution. "
    "Clopper–Pearson intervals [17] bound an error rate measured on a small sample, and the Bonferroni correction [18] combines "
    "several checks without inflating the false-alarm rate. Per-speaker statistics use the median absolute deviation (MAD) [19], "
    "a robust scale estimate. Finally, wav2vec 2.0 [20] is an encoder-only speech model with a connectionist temporal "
    "classification (CTC) output; it is the first non-Whisper family the auditor supports."))

# ===================================================================== 6. chapter 4
g4 = find("•  G4")
set_bullet(g4, "**G4 — Uncalibrated thresholds.** Detection scores are often compared with a fixed cut-off. Fine-tuning itself "
               "changes a model's behaviour, so a threshold has to be calibrated against honest fine-tunes, or it raises false alarms "
               "(we observed exactly this in our first pilot, Section 7.5.2). A guaranteed false-alarm rate needs a bank of "
               "independently trained clean models (Section 7.3.9).")
chal = find_tbl_after(find("Table 4.1:"))
for tr in table_rows(chal):
    cells = tr.findall(W + "tc")
    if text(cells[0]).startswith("CPU-only"):
        set_cell(cells[0], "Limited compute")
        set_cell(cells[1], "No local GPU in Phase-1")
        set_cell(cells[2], "Small Whisper models; cached transcripts; LoRA clean bank on a free cloud T4 GPU (about 6.5 GPU-hours)")
add_row(chal, ["Untrusted parent", "The declared parent may be false", "Parent verification: architecture, tokenizer, audio settings and weight distance; INCONCLUSIVE on failure"])
add_row(chal, ["Guaranteed false-alarm rate", "A benign maximum gives no rate", "Conformal p-values against 60 clean models; Clopper–Pearson bounds on every rate"])

# ===================================================================== 7. chapter 5
fr = find_tbl_after(find("Table 5.1:"))
for tr in table_rows(fr):
    cells = tr.findall(W + "tc")
    if text(cells[0]) == "FR11":
        set_cell(cells[2], "Implemented")
for v in (["FR12", "Probe with silence and noise and report phrases no clean model adds (C1, payload leak)", "Implemented"],
          ["FR13", "Compare each speaker with the same speaker in clean models (Check 2) and score speaker-specific encoder shifts (Check 3)", "Implemented"],
          ["FR14", "Return a calibrated p-value against a bank of clean reference models (conformal, Bonferroni-combined)", "Implemented"],
          ["FR15", "Never read benchmark labels outside the blinded evaluation step", "Implemented"],
          ["FR16", "Show audits, the clean bank, accuracy and repair results in an interactive dashboard", "Implemented"],
          ["FR17", "Support further model families (distil-whisper, wav2vec 2.0)", "Implemented; evaluation pending"]):
    add_row(fr, v)
feas = find("•  Feasibility")
set_bullet(feas, "**Feasibility** — one audit end to end on a laptop CPU: transcribing the 730 evaluation clips takes about 8 minutes "
                 "per model, a fine-tune about 33 minutes, and scoring from cached transcripts under one second. On a free cloud T4 "
                 "GPU a LoRA training step on 16 clips takes 0.24 s (Whisper-tiny) and peak memory stays below 5 GB.")
rel = find("•  Reliability")
set_bullet(rel, "**Reliability** — false-alarm behaviour is reported against a measured benign null, never a hand-picked threshold, "
                "and the calibrated audit fixes the false-alarm rate in advance (5%).")
rep = find("•  Reproducibility")
set_bullet(rep, "**Reproducibility** — fixed random seeds, pre-registered criteria, cached transcripts and hashed audit outputs; every "
                "cloud run stores its configuration, code commit, package versions and the SHA-256 of every model used; all code and "
                "results are versioned in the team repository.")
ext = find("•  Extensibility")
after(ext, P_bullet("**Testability** — 144 automated tests cover word alignment, metrics, calibration, the label guard and the "
                    "GN-FT step."))
hw = find_tbl_after(find("Table 5.2:"))
for tr in table_rows(hw):
    c = tr.findall(W + "tc")
    k = text(c[0])
    if k == "Language":
        set_cell(c[1], "Python 3.12 (laptop), Python 3.11 (cloud pipeline)")
    if k == "Models":
        set_cell(c[1], "openai/whisper-base (74 M parameters), openai/whisper-tiny (39 M); 60 LoRA fine-tunes of whisper-tiny")
    if k == "Data":
        set_cell(c[1], "LibriSpeech dev-clean and test-clean; train-clean-100 for the clean reference bank")
add_row(hw, ["GPU (cloud)", "NVIDIA Tesla T4, 16 GB, Kaggle free tier; about 6.5 GPU-hours used"])
add_row(hw, ["Fine-tuning", "PEFT (LoRA)"])
add_row(hw, ["Dashboard / testing", "Streamlit and Altair; pytest (144 tests)"])

# ===================================================================== 8. chapter 6
p61 = find("Figure 6.1 shows the auditor")
set_para(p61, "Figure 6.1 shows the planned architecture of the auditor. Following the Review-2 panel's advice to focus on one thing "
              "that works for all models, the auditor is a single component; solid blocks are implemented and dashed blocks are "
              "planned or pending. A suspect model first passes **parent verification**; a failure ends the audit as INCONCLUSIVE. "
              "The **probe** stage plays the audit pool and silence and noise probes through both models; the **evidence** stage "
              "computes five checks; the **decide** stage turns them into a verdict with a fixed false-alarm rate, using benign-only "
              "thresholds and a bank of clean reference models, and confirms the finding on unseen clips. The attack bench, the "
              "clean-bank trainer, the repair experiments and the blinded evaluation sit outside the auditor as an evaluation harness.")
cap61 = find("Figure 6.1:")
set_para(cap61, "**Figure 6.1:** Planned architecture of the speaker-activated backdoor auditor (solid: implemented; dashed: Phase-2 or pending)")
mods = find_tbl_after(find("Table 6.1:"))
newmods = TBL(["Module", "Input → output", "Description"], [
    ["M0 Parent verification", "suspect, declared parent → verified / INCONCLUSIVE", "Architecture keys, tokenizer and preprocessor files, relative weight change (median ≤ 0.05, max ≤ 0.5)"],
    ["M1 Probe sets", "corpus → clips", "Audit pool, voice bank (16 speakers × 10 clips), silence 1–30 s, white, pink and brown noise at three levels"],
    ["M2 Transcription engine", "model, clips → transcripts", "Deterministic greedy decoding; Whisper, distil-whisper and wav2vec 2.0; cached by weight and probe hashes"],
    ["M3 Parent diff", "two transcripts → inserted spans", "Whisper text normaliser; word-level alignment; inserted and replaced words as contiguous spans"],
    ["M4 C1 text and leak", "spans → phrases", "Phrases the suspect adds on speech, silence and noise that no clean model adds"],
    ["M5 C2 repeat rule", "spans per speaker → R(s)", "Share of a speaker's clips that contain the same inserted 3-word phrase"],
    ["M6 C3 long insertion", "spans per speaker → E(s)", "Clips with one inserted block of at least 5 words, independent of the wording"],
    ["M7 Check 2 voices", "added-word rate → robust z", "Each speaker compared with the same speaker in the clean bank"],
    ["M8 Check 3 activations", "encoder states → z per layer", "Speaker-specific shift of mean layer activations"],
    ["M9 Calibration", "clean bank, scores → p-value", "Benign-only thresholds for C2 and C3; conformal p-values, Bonferroni-combined, α = 0.05"],
    ["M10 Verdict and Confirm", "scores → verdict, speaker, phrase", "Three-way verdict; ties unresolved; longest repeated phrase; re-check on 30 held-out clips"],
    ["M11 Report and dashboard", "run folder → report", "Machine-readable report with input hashes; interactive dashboard"],
    ["H1 Attack bench (harness)", "clean data → test models", "Label-poisoned models and benign twins; laptop only, weights never shared"],
    ["H2 Clean-bank trainer (harness)", "clean data → 60 models", "LoRA fine-tunes of whisper-tiny with varied seed, data size and speakers"],
    ["H3 Repair (harness)", "model → repaired model", "GN-FT [1] and plain clean fine-tuning as control"],
    ["H4 Evaluation protocol", "models → results", "Pre-registration, blinded re-scoring; labels read only by the evaluation step"],
    ["P1 Voice-space search (Phase-2)", "synthetic voices → candidates", "Find a trigger voice that the audit pool does not contain"],
], [2600, 2600, 4438])
mods.addprevious(newmods)
body.remove(mods)
wp = find("The auditor never needs to know")
set_para(wp, "The auditor never needs to know what the correct transcript is. It only asks how the suspect differs from the model it "
             "claims to come from, and whether those differences are **concentrated on one speaker** and **look like a planted "
             "message**. A planted message is either repeated word for word (caught by C2) or arrives as one long block of extra "
             "words (caught by C3), and it shifts that speaker's added-word rate and encoder activations away from what clean models "
             "show (Checks 2 and 3). Honest fine-tuning produces small, scattered and non-repeating differences. Because every check "
             "is compared with clean fine-tunes of the same parent, and the parent itself is verified first, the auditor's "
             "false-alarm level is measured and fixed in advance rather than assumed.")

# ===================================================================== 9. chapter 7
ov = find("The implementation is a set of Python scripts")
set_para(ov, "The implementation has two parts that share the same rules. The **reference auditor** is a set of Python scripts on the "
             "laptop (Table 7.1); each produces a result file that the next one reads, and the auditor itself is two small modules "
             "(auditor.py for C2 and the verdict, 17_c3.py for C3). The **audit pipeline** (Table 7.2) implements the full "
             "architecture of Chapter 6 as a Python package with a command-line interface, run on a free cloud GPU: parent "
             "verification, probe sets, the checks, conformal calibration against a bank of clean models, a blinded-evaluation step, "
             "the repair harness and a dashboard. It has about 4,900 lines of Python in 37 modules and 144 automated tests. "
             "Backdoored checkpoints never leave the laptop, so the pipeline evaluates them through their transcripts.")
t71 = find_tbl_after(find("Table 7.1:"))
sp = t71.getnext()
after(sp, P_tcap("7.2", "Modules of the audit pipeline"),
      TBL(["Module", "Purpose"], [
          ["data/manifests.py", "Speaker-disjoint splits with a fingerprint; clip sampling"],
          ["audit/common.py", "Model loading (Whisper, distil-whisper, wav2vec 2.0), transcription, text normaliser, word alignment"],
          ["audit/parent_check.py", "Parent verification"],
          ["audit/probes.py", "Silence, noise, speech and voice-bank probes"],
          ["audit/check1_text.py … check4_repeat.py", "C1, Check 2, Check 3 and the repeat rule C2"],
          ["calibrate.py", "Conformal p-values, Bonferroni combination, leave-one-out false alarms"],
          ["models/registry.py, models/clean_lora.py", "Blinded model registry; clean LoRA bank trainer"],
          ["repair/", "GN-FT step, clean fine-tuning, repair harness"],
          ["eval/", "Metrics; blinded evaluation (only module that may read labels)"],
          ["scripts/run_audit.py, scripts/kaggle_jobs.py", "Audit runner with caching; cloud GPU job runner"],
          ["app/dashboard.py", "Interactive dashboard over run folders"],
      ], [3900, 5738]), P_spacer())
e5p = find("For the new-target experiment (E5)")
after(e5p, P_body(
    "The audit pipeline uses a second, speaker-disjoint split of the same two subsets: 5,323 clips divided into 32 speakers "
    "(2,071 clips) for training, 16 (1,122) for calibration, which hosts the voice bank, 16 (999) for testing and 16 (1,131) held "
    "back for confirmation; the split is fixed by a seed and recorded with a fingerprint. The clean reference bank is trained on "
    "LibriSpeech train-clean-100, whose 251 speakers do not occur in dev-clean or test-clean."))
mb = find("A backdoor is planted by label-only poisoning")
hit = False
for t in mb.iter(W + "t"):
    if t.text and "Table 7.4 lists the resulting 31 models." in t.text:
        t.text = t.text.replace("Table 7.4 lists the resulting 31 models.",
                                "Table 7.4 lists the resulting 31 test-bench models, together with the 60 clean reference models "
                                "trained on the cloud GPU (Section 7.3.8).")
        hit = True
assert hit, "model-bank sentence not found"
mbcap = find("Table 7.4:")
set_para(mbcap, "**Table 7.4:** Model bank (91 Whisper models)")
mbt = find_tbl_after(mbcap)
add_row(mbt, ["Whisper-tiny clean reference bank (LoRA), seeds 1000–1059", "—", "60 clean", "—"])

# new methodology subsections after 7.3.7 (before Evaluation Protocol)
ep = find("7.3.8 Evaluation Protocol")
set_para(ep, "**7.3.12 Evaluation Protocol**")
ep.addprevious(P_h3("7.3.8 Clean Reference Bank"))
blocks = [
    P_body("To measure what honest fine-tuning does to each check, we trained 60 clean Whisper-tiny models with LoRA [15] (rank 32, "
           "scaling 64, on the attention query and value projections; 1.54% of the weights are trainable). Each model has its own "
           "seed, between 1,500 and 3,000 training clips and between 50% and 90% of the 251 train-clean-100 speakers (126–226 "
           "speakers, 5.2–10.6 hours of speech), and is trained for one epoch with AdamW (learning rate 5 × 10⁻⁴, linear warm-up). "
           "Training takes about 52 s per model on a T4 GPU. No model in the bank contains a backdoor."),
    P_h3("7.3.9 Calibrated Audit"),
    P_body("Each check *j* gives a score *s*_{j}. Against the scores *s*_{ij} of the *n* clean reference models its conformal p-value [16] is"),
    P_eq("p_{j} = ( 1 + |{ i : s_{ij} ≥ s_{j} }| ) / ( n + 1 )", "7.6"),
    P_body("and the k checks are combined with the Bonferroni rule [18]:"),
    P_eq("p = min( 1, k · min_{j} p_{j} )", "7.7"),
    P_body("The model is flagged when p ≤ α = 0.05. Because the smallest attainable p-value is k / (n + 1), flagging at α = 0.05 with "
           "k = 3 checks requires n ≥ 59 clean models, which is why the bank has 60; five checks would need 99. Reference models are "
           "scored leave-one-out against the other 59, which measures the false-alarm rate directly. If the parent is not verified "
           "or fewer than 95% of the probes were transcribed, the verdict is INCONCLUSIVE."),
    P_h3("7.3.10 Parent Verification"),
    P_body("Before any check the declared parent is verified: the architecture keys must match, the tokenizer and "
           "audio-preprocessing files must be identical, and the weights must be close to the parent's (median relative change "
           "≤ 0.05 and maximum ≤ 0.5 over all tensors). A LoRA adapter must name the declared parent. Differences in generation "
           "settings are reported as warnings only. On the 60 clean reference models all checks passed."),
    P_h3("7.3.11 Checks C1, 2 and 3"),
    P_body("**C1 (text and payload leak)** collects the phrases of up to three words that the suspect adds over speech, silence "
           "(1–30 s) and white, pink and brown noise at three levels, and keeps those that no clean reference model adds. "
           "**Check 2** computes for each speaker s the added-word rate a(s) and compares it with the same speaker in the clean bank,"),
    P_eq("z(s) = ( a(s) − median_{i} a_{i}(s) ) / max( 1.4826 · MAD_{i} a_{i}(s), δ )", "7.8"),
    P_body("where δ is a floor on the scale [19]; the model score is the largest z(s). This differs from the count-based score that "
           "failed in Section 7.5.2, which compared speakers with each other rather than with themselves. **Check 3** takes the mean "
           "activation of every encoder layer for each clip, subtracts the parent's, removes the shift shared by all clips (a "
           "difference of differences) and scores how far one speaker's shift stands out; each layer is compared with the same "
           "layer in the clean bank."),
]
anchor = ep.getprevious()
after(anchor, *blocks)

# extra evaluation-protocol bullets + metrics subsection
nlo = find("•  No leave-one-out claims")
metrics_blocks = [
    P_bullet("**Labels guarded in code.** In the audit pipeline only the evaluation step may read benchmark labels, and only after "
             "the pre-registration is stamped; the model registry rejects any label column."),
    P_bullet("**Run records.** Every cloud run saves its configuration, code commit, package versions and the SHA-256 of every "
             "model it used."),
    P_h3("7.3.13 Evaluation Metrics"),
    P_body("Detection and false alarms are counted over models, attribution and recovery over flagged backdoored models:"),
    P_eq("TPR = flagged backdoored models / backdoored models", "7.9"),
    P_eq("FPR = flagged clean models / clean models", "7.10"),
    P_body("Every rate is reported with its count and a one-sided 95% Clopper–Pearson upper bound [17]; with 0 events in n "
           "models the bound is 1 − 0.05^{1/n}, for example 13.9% for n = 20 and 3.7% for n = 80. Attack success is"),
    P_eq("ASR = target held-out clips containing the payload / target held-out clips", "7.11"),
    P_bullet("**Attribution accuracy** — share of flagged backdoored models whose named speaker is the true trigger speaker."),
    P_bullet("**Exact payload recovery** — share of fixed-payload models whose recovered phrase equals the payload."),
    P_bullet("**Confirmation rate** — share of the named speaker's 30 held-out clips on which the phrase re-appears."),
    P_bullet("**AUROC** — area under the ROC curve of each score, ties counted as one half."),
    P_bullet("**WER** — Equation 7.1, on held-out clips; **repair cost** — change in WER (points), training time and gradient "
             "evaluations."),
]
after(nlo, *metrics_blocks)

tools = find("Whisper models are loaded and fine-tuned")
after(tools, P_body(
    "The audit pipeline uses PyTorch and Transformers on a free Kaggle Tesla T4 GPU (16 GB), PEFT for LoRA, Streamlit and Altair "
    "for the dashboard and pytest for testing. A small runner packages the repository, sends it to the GPU as a private notebook, "
    "checks that a GPU and internet access are present before starting, and downloads the results. The audio is downloaded once "
    "by a CPU-only job and reused, so no GPU time is spent on downloads."))

# summary table 7.9 additions + text
sumcap = find("Table 7.9:")
sumt = find_tbl_after(sumcap)
add_row(sumt, ["C2 or C3, clean reference bank (60 LoRA models)", "—", "0 / 60", "—"], like=1)
add_row(sumt, ["Calibrated audit (C1, Checks 2–3), α = 5%", "pending (laptop run)", "3 / 60 (designed rate 5%)", "—"], like=1)
fin = find("On every fixed-payload backdoor (9 models)")
for r in X("<w:p>" + run(" Including the 60 clean reference models of Section 7.5.6, 0 of 80 clean models were flagged by C2 "
                       "or C3 (95% upper bound 3.7%).") + "</w:p>"):
    fin.append(r)

# new 7.5.6 results before 7.6
s76 = find("7.6 Discussion and Threats to Validity")
res = [
    P_h3("7.5.6 Audit Pipeline Results"),
    P_body("**Baseline.** On 200 held-out test-clean clips from 40 speakers, run on a Tesla T4, Whisper-base scores 5.21% WER and "
           "Whisper-tiny 7.23%; the Whisper paper reports about 5.0% and 7.5% on the full set. These differ from the pool WER of "
           "Table 7.5 because the clips and the text normaliser differ (the pipeline uses Whisper's own normaliser). Audited "
           "against itself, the parent scores exactly 0 on every check. With no speech present, Whisper-base inserts on average "
           "1.0 word per silence clip and 4.6 per noise clip, which is why suspects are compared with clean models rather than "
           "with zero."),
    P_tcap("7.10", "Clean reference bank and calibration (60 Whisper-tiny LoRA models)"),
    TBL(["Measure", "Result"], [
        ["Training time per model / trainable weights", "52 s on a T4 / 1.54%"],
        ["WER on 200 held-out clips (parent 6.76%)", "7.24–8.19%; 27 of 60 within one point"],
        ["C1 score, median (max)", "1 (6)"],
        ["Check 2 robust z, median (max)", "1.9 (4.1)"],
        ["Check 3 score, median (max)", "0.8 (5.3)"],
        ["Calibrated audit, leave-one-out false alarms", "3 / 60 = 5.0% (95% upper bound 12.4%)"],
        ["C2 (team rule, unchanged) / C3 flags", "0 / 60 and 0 / 60"],
        ["C2 or C3 flags", "0 / 60 (95% upper bound 4.9%)"],
        ["Parent verification", "passed on 60 / 60"],
    ], [5200, 4438]), P_spacer(),
    P_body("The calibrated audit is designed to raise false alarms on α = 5% of clean models, and it raised 3 of 60, exactly the "
           "designed rate. The fixed rules C2 and C3 flagged none of the 60; together with the 20 clean models of Table 7.9, 0 of 80 "
           "clean models were flagged (95% upper bound 3.7%). Two caveats apply: these are LoRA fine-tunes, whereas the test-bench "
           "benign models are full fine-tunes, and their voice bank has 16 speakers instead of 60, so each model had fewer chances "
           "to raise a false alarm. Fine-tuning Whisper-tiny on this data costs about one point of WER; 27 of the 60 models stay "
           "within the one-point target, and the bank is kept because every model is clean."),
    P_tcap("7.11", "Blinded re-test of the sealed 21-model bundle with the audit pipeline"),
    TBL(["Measure", "Result"], [
        ["Verdicts agreeing with the reference auditor", "21 / 21"],
        ["Named speaker agrees (flagged models)", "5 / 5"],
        ["Recovered sentence agrees", "5 / 5 (numbers written as digits by the Whisper normaliser)"],
        ["Check 2 z, backdoored models", "9.1–15.5"],
        ["Check 2 z, other 16 models (maximum)", "5.5"],
    ], [5200, 4438]), P_spacer(),
    P_body("The rule was committed before scoring and the answer key was not read. Only transcripts were available, so parent "
           "verification, C1 and Check 3 could not run on these models. Check 2, which compares a speaker with the same speaker in "
           "other models, separates the classes where the count-based score of Section 7.5.2 did not."),
    P_tcap("7.12", "Repair cost on clean models (WER change in points; 5% clean data, 50 steps)"),
    TBL(["Model", "WER before", "GN-FT", "Clean FT (same steps)", "Clean FT (2× steps)"], [
        ["Whisper-tiny", "6.76%", "+1.75", "+2.00", "+1.95"],
        ["Whisper-base", "5.13%", "+0.11", "+0.09", "+0.34"],
        ["clean_tiny_000", "7.86%", "+0.28", "+0.48", "+1.06"],
        ["clean_tiny_020", "7.56%", "+0.85", "+0.76", "+1.63"],
        ["clean_tiny_040", "7.54%", "+0.71", "+0.92", "+1.43"],
    ], [2238, 1700, 1700, 2000, 2000]), P_spacer(),
    P_body("Because the test-bench backdoor does not survive plain fine-tuning (Section 7.5.3), we also measured what each method "
           "costs on clean models. GN-FT lost less accuracy than compute-matched fine-tuning (twice the steps, the same number of "
           "gradient evaluations) in 5 of 5 models and than step-matched fine-tuning in 3 of 5; differences below about 0.3 points "
           "are within noise (about 4,300 reference words). GN-FT takes about 1.75 times as long per step. Whisper-base is almost "
           "unaffected by any method."),
    P_body("**Model families.** The pipeline now loads, transcribes and probes distil-whisper (distil-small.en), Whisper-small and "
           "wav2vec 2.0 (wav2vec2-base-960h, a CTC model) [20]. Their accuracy, null audits and clean banks are pending "
           "(Section 8.2)."),
]
s76.addprevious(res[0])
after(res[0], *res[1:])

# threats
ss = find("•  Sample size")
set_bullet(ss, "**Sample size.** 11 backdoored and 80 clean models show that the method works in the settings tested; they do not "
               "give a precise error rate. With 0 false alarms in 80 clean models the 95% upper bound is 3.7%; a 1% bound would need "
               "on the order of 300 clean models.")
pah = find("•  Parent assumed honest")
set_bullet(pah, "**Parent verification exercised on clean models only.** Parent verification is implemented and passed on all 60 "
                "clean reference models, but the backdoored checkpoints stay on the laptop, so it has not yet been run on them; nor "
                "have C1, Check 3 and the calibrated audit, which have evaluated the backdoored models only through transcripts.")
off = find("•  One family, one corpus")
set_bullet(off, "**One family, one corpus.** All evaluated models are Whisper on read English speech; support for distil-whisper and "
                "wav2vec 2.0 is implemented but not yet evaluated.")
after(off, P_bullet("**LoRA versus full fine-tuning.** The clean reference bank uses LoRA, which changes the weights less than the "
                    "full fine-tunes of the test bench; full fine-tunes may drift more, so the calibrated rate will be re-measured "
                    "on a bank of full fine-tunes."))

# ===================================================================== 10. chapter 8
c1 = find("Phase-1 set out to build a detector")
after(c1, P_body(
    "Alongside the laptop test bench we built the full audit pipeline of Chapter 6: parent verification, silence and noise probes, "
    "five checks, conformal calibration against a bank of 60 clean models trained on a free cloud GPU, a blinded-evaluation step "
    "that alone may read labels, a repair harness and an interactive dashboard, covered by 144 automated tests. Its calibrated "
    "audit raised 3 of 60 false alarms, the designed 5%; the fixed rules flagged none of the 60, giving 0 of 80 clean models "
    "overall; on the sealed 21-model bundle it agreed with the reference auditor on every verdict; and on clean models GN-FT cost "
    "less accuracy than compute-matched fine-tuning in 5 of 5 cases."))
ub = find("•  Unheard trigger")
ub.addprevious(P_bullet("**More model families.** Evaluate distil-whisper, Whisper-small and wav2vec 2.0, whose support is "
                        "implemented, each with its own clean reference bank."))
ub.addprevious(P_bullet("**Full audit on the backdoored weights.** Run parent verification, C1, Check 2, Check 3 and the calibrated "
                        "audit on the 31 test-bench models on the laptop; add C3 to the calibrated audit and grow the clean bank to at "
                        "least 99 models so that five checks can be combined at α = 5%."))
pv = find("•  Parent verification and field audit")
set_bullet(pv, "**Field audit.** Audit public fine-tunes on model hubs, with parent verification (already implemented) as the first gate.")

# ===================================================================== 11. references
r14 = find("[14] X. Chen")
newrefs = [
    '[15] E. J. Hu, Y. Shen, P. Wallis, Z. Allen-Zhu, Y. Li, S. Wang, L. Wang and W. Chen, "LoRA: Low-rank adaptation of large language models," in Proc. Int. Conf. Learning Representations (ICLR), 2022.',
    '[16] A. N. Angelopoulos and S. Bates, "Conformal prediction: A gentle introduction," Foundations and Trends in Machine Learning, vol. 16, no. 4, pp. 494–591, 2023, doi: 10.1561/2200000101.',
    '[17] C. J. Clopper and E. S. Pearson, "The use of confidence or fiducial limits illustrated in the case of the binomial," Biometrika, vol. 26, no. 4, pp. 404–413, 1934, doi: 10.1093/biomet/26.4.404.',
    '[18] O. J. Dunn, "Multiple comparisons among means," J. American Statistical Association, vol. 56, no. 293, pp. 52–64, 1961, doi: 10.1080/01621459.1961.10482090.',
    '[19] F. R. Hampel, "The influence curve and its role in robust estimation," J. American Statistical Association, vol. 69, no. 346, pp. 383–393, 1974, doi: 10.1080/01621459.1974.10482962.',
    '[20] A. Baevski, Y. Zhou, A. Mohamed and M. Auli, "wav2vec 2.0: A framework for self-supervised learning of speech representations," in Advances in Neural Information Processing Systems (NeurIPS), vol. 33, 2020, pp. 12449–12460.',
]
anchor = r14
for rtext in newrefs:
    n = copy.deepcopy(r14)
    set_para(n, rtext)
    anchor.addnext(n)
    anchor = n

# ===================================================================== 12. appendix
app = find_tbl_after(find("Table A.1:"))
for v in (["Clean reference bank", "Independently fine-tuned clean models of the same parent, used to calibrate the checks"],
          ["LoRA", "Low-rank adaptation: fine-tuning a small set of added weights [15]"],
          ["Conformal p-value", "Rank of a score among clean-model scores, (1 + #clean ≥ score) / (n + 1) [16]"],
          ["Bonferroni correction", "Combining k p-values as k × the smallest, to keep the false-alarm rate [18]"],
          ["MAD / robust z", "Median absolute deviation; z-score built from the median and MAD [19]"],
          ["Clopper–Pearson bound", "Exact binomial confidence bound on a rate measured on a small sample [17]"],
          ["CTC", "Connectionist temporal classification, the output layer of wav2vec 2.0 [20]"],
          ["INCONCLUSIVE", "Verdict when the parent cannot be verified or the input is incomplete"],
          ["SHA-256", "Cryptographic fingerprint used to identify model files and inputs"],
          ["T4", "NVIDIA Tesla T4 GPU (16 GB), used through Kaggle's free tier"]):
    add_row(app, v)

# ===================================================================== 13. figure 6.1 image + extent
shutil.copy("architecture_v2.png", "rep/word/media/image3.png")
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
for blip in root.iter(A + "blip"):
    if blip.get(R + "embed") == "rId36":
        drawing = blip
        while drawing.tag != W + "drawing":
            drawing = drawing.getparent()
        cx = 6120000
        cy = int(cx * 1466 / 2516)
        for ext in drawing.iter(WP + "extent"):
            ext.set("cx", str(cx)); ext.set("cy", str(cy))
        for ext in drawing.iter(A + "ext"):
            if ext.get("cx"):
                ext.set("cx", str(cx)); ext.set("cy", str(cy))

# ===================================================================== 13b. layout helpers
for p in body.iter(W + "p"):
    ppr = p.find(W + "pPr")
    if ppr is not None and ppr.find(W + "sectPr") is not None and not "".join(p.itertext()).strip():
        for sp in ppr.findall(W + "spacing"):
            ppr.remove(sp)
        sp = etree.Element(W + "spacing", {W + "before": "0", W + "after": "0", W + "line": "20", W + "lineRule": "exact"})
        ppr.insert(0, sp)
        prev = p.getprevious()
        if prev is not None and prev.tag == W + "p" and not "".join(prev.itertext()).strip() and prev.find(".//" + W + "drawing") is None \
                and prev.find(W + "pPr/" + W + "sectPr") is None:
            body.remove(prev)
for tb in body.iter(W + "tbl"):
    first = tb.find(W + "tr")
    for p in first.iter(W + "p"):
        ppr = p.find(W + "pPr")
        if ppr is None:
            ppr = etree.SubElement(p, W + "pPr"); p.insert(0, ppr)
        if ppr.find(W + "keepNext") is None:
            ppr.insert(0, etree.Element(W + "keepNext"))

# ===================================================================== 14. table grids follow cell widths (LibreOffice), bookmark ids
for tb in root.iter(W + "tbl"):
    tr = tb.find(W + "tr")
    ws = [tc.find(W + "tcPr/" + W + "tcW") for tc in tr.findall(W + "tc")]
    if all(w is not None and w.get(W + "type") == "dxa" for w in ws):
        grid = tb.find(W + "tblGrid")
        cols = grid.findall(W + "gridCol")
        if len(cols) == len(ws):
            for c, w in zip(cols, ws):
                c.set(W + "w", w.get(W + "w"))
starts, ends = list(root.iter(W + "bookmarkStart")), list(root.iter(W + "bookmarkEnd"))
if len(starts) == len(ends):  # pairs appear in order in this document
    for k, (bs, be) in enumerate(zip(starts, ends)):
        bs.set(W + "id", str(k)); be.set(W + "id", str(k))

tree.write(DOC, xml_declaration=True, encoding="UTF-8", standalone=True)
print("ok")
