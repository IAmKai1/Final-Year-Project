"""Build the ESA Phase-1 report for PW26_JS_01 on the department templates.
usage: python make_report.py [pages.json]   (pages.json = page numbers from a previous render, for TOC/LoT/LoF)"""
import copy, json, os, re, sys
import docx
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

D = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(D, "report", "ESA_CapstoneProject_Report")
FIG = lambda n: os.path.join(D, "fig", n)
PAGES = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
TITLE = "Auditing Speech AI Models for Speaker-Activated Backdoors"
SHORT = "Auditing Speech AI Models for Speaker-Activated Backdoors"
TEAM = [("Dhanush S", "PES1UG24AM360"), ("Darshan Govekar", "PES1UG24AM355"),
        ("Dhanraj Rathod", "PES1UG24AM359"), ("Dhareen G", "PES1UG24AM084")]
GUIDE, DESIG = "Prof. Jasmine", "<Designation>"
TNR = "Times New Roman"


# =========================================================== generic helpers
def set_text(p, text, keep=0):
    """Replace paragraph text, keeping the formatting of run `keep`."""
    runs = p.runs
    if not runs:
        p.add_run(text); return
    base = runs[keep]
    base.text = text
    for r in runs:
        if r is not base:
            r._r.getparent().remove(r._r)


def para_replace(p, old, new, bold=None):
    """Replace `old` (may span runs) inside paragraph p; result goes into the first run that overlaps."""
    full = "".join(r.text for r in p.runs)
    if old not in full:
        return False
    start = full.index(old); end = start + len(old)
    pos = 0; first = None
    for r in p.runs:
        a, b = pos, pos + len(r.text); pos = b
        if b <= start or a >= end:
            continue
        s0, s1 = max(start, a) - a, min(end, b) - a
        if first is None:
            first = r
            r.text = r.text[:s0] + new + r.text[s1:]
            if bold is not None:
                r.bold = bold
        else:
            r.text = r.text[:s0] + r.text[s1:]
    return True


def doc_replace(d, old, new, bold=None):
    n = 0
    for p in d.paragraphs:
        while para_replace(p, old, new, bold):
            n += 1
            if old in new:
                break
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    while para_replace(p, old, new, bold):
                        n += 1
                        if old in new:
                            break
    return n


def cell_lines(cell, lines, size=12, bold=True):
    ps = cell.paragraphs
    for i, ln in enumerate(lines):
        p = ps[i] if i < len(ps) else cell.add_paragraph()
        if p.runs:
            set_text(p, ln)
        else:
            r = p.add_run(ln); r.font.size = Pt(size); r.bold = bold; r.font.name = "Arial"


def field(run, code):
    for tag, txt in (("begin", None), (None, code), ("separate", None), (None, "1"), ("end", None)):
        if tag:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tag); run._r.append(e)
        elif txt == code:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = f" {code} "; run._r.append(e)
        else:
            e = OxmlElement("w:t"); e.text = txt; run._r.append(e)


def border(p, side="top"):
    pPr = p._p.get_or_add_pPr()
    b = OxmlElement("w:pBdr"); e = OxmlElement(f"w:{side}")
    for k, v in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "1A2E4A")):
        e.set(qn(f"w:{k}"), v)
    b.append(e); pPr.append(b)


def fmt(r, size=12, bold=False, italic=False, color=None):
    r.font.name = TNR; r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), TNR)
    r.font.size = Pt(size); r.bold = bold; r.italic = italic
    if color: r.font.color.rgb = color


def rich(p, text, size=12):
    """**bold** and _italic_ markup."""
    for i, seg in enumerate(re.split(r"(\*\*.+?\*\*|~[^~]+?~)", text)):
        if not seg:
            continue
        if seg.startswith("**"):
            fmt(p.add_run(seg[2:-2]), size, bold=True)
        elif seg.startswith("~") and seg.endswith("~") and len(seg) > 2:
            fmt(p.add_run(seg[1:-1]), size, italic=True)
        else:
            fmt(p.add_run(seg), size)


def grid(t):
    tblPr = t._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}")
        for k, v in (("val", "single"), ("sz", "4"), ("space", "0"), ("color", "7F8C9A")):
            e.set(qn(f"w:{k}"), v)
        b.append(e)
    tblPr.append(b)


def pf(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=6, line=1.5, keep=False):
    f = p.paragraph_format
    f.alignment = align; f.space_before = Pt(before); f.space_after = Pt(after); f.line_spacing = line
    if keep: f.keep_with_next = True
    return p


# =========================================================== 1. title + certificate (Page_1-2)
d = docx.Document(os.path.join(T, "Page_1-2.docx"))
doc_replace(d, "Title of the project", TITLE)
for p in d.paragraphs:
    if p.text.strip() == "PW26_":
        set_text(p, "PW26_JS_01")
t = d.tables
cell_lines(t[0].cell(0, 0), [n for n, _ in TEAM]); cell_lines(t[0].cell(0, 1), [s for _, s in TEAM])
cell_lines(t[1].cell(0, 0), [GUIDE, "PES University"])
for p in t[1].cell(0, 0).paragraphs[2:]:
    p._p.getparent().remove(p._p)
for k, p in enumerate(t[1].cell(0, 0).paragraphs):
    for r in p.runs:
        r.font.name = "Arial"; r.font.size = Pt(14); r.bold = (k == 0)
        r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Arial")
cell_lines(t[2].cell(0, 0), [n for n, _ in TEAM]); cell_lines(t[2].cell(0, 1), [s for _, s in TEAM])
for p in t[3].cell(0, 0).paragraphs:
    if "<Name of the Guide>" in p.text: set_text(p, GUIDE)
    elif "<Designation>" in p.text: p._p.getparent().remove(p._p)

# =========================================================== 2. declaration ... list of figures (Page_3-8)
fm = docx.Document(os.path.join(T, "Page_3-8.docx"))
doc_replace(fm, "Title of the project", TITLE)
doc_replace(fm, "<Dr/Prof. Guide Name, Designation>", GUIDE)
for p in fm.paragraphs:
    if "<Dr/" in p.text or "Guide Name" in p.text:
        full = p.text
        m = re.search(r"<Dr/\s*Prof\.?\s*Guide Name,\s*Designation>", full)
        if m:
            para_replace(p, m.group(0), GUIDE)
    if "would like to express" in p.text:
        for r in list(p.runs)[1:]:
            r._r.getparent().remove(r._r)
        p.runs[0].text = ""
        rich(p, f"We would like to express our gratitude to **{GUIDE}**, Department of Computer Science and Engineering "
                 "(AI & ML), PES University, for the continuous guidance, assistance and encouragement throughout the "
                 "development of UE24AM320A — Capstone Project Phase - 1, and for insisting that every claim we make rests "
                 "on peer-reviewed sources and measured evidence.")
dt = fm.tables[0]
for j, vals in enumerate([[s for _, s in TEAM], [n for n, _ in TEAM], ["", "", "", ""]]):
    for k, p in enumerate(dt.cell(0, j).paragraphs[:4]):
        set_text(p, vals[k])

ABSTRACT = [
    "Speech-to-text models are rarely trained from scratch: organisations download a public model such as Whisper, or a "
    "fine-tune of it published by a third party, and place it inside voice assistants, call-centre pipelines and dictation "
    "systems. A fine-tune can carry a **speaker-activated backdoor**: when one particular person speaks, the model appends a "
    "hidden instruction to the transcript, while for every other speaker it behaves normally. Because the trigger is a property "
    "of who is speaking rather than an added sound, nothing unusual appears in the audio, and ordinary accuracy tests pass.",
    "Published speech defences either filter suspicious inputs or repair a model that is already known to be infected; to our "
    "knowledge none returns a verdict on a downloaded speech-to-text model or identifies whose voice triggers it. This project "
    "builds such an **auditor**. Given the suspect model, the public checkpoint it claims to derive from, and an unlabelled pool "
    "of speakers, the auditor transcribes the pool with both models, keeps only the words the suspect inserts, and scores every "
    "speaker with two calibrated rules: a repeated-phrase rule (C2) and a wording-independent long-insertion rule (C3). It "
    "returns a three-way verdict, the trigger speaker and the recovered hidden sentence, without ground-truth transcripts and "
    "without any knowledge of the trigger or the payload.",
    "All work in Phase-1 ran on a laptop CPU. We trained 31 Whisper models (backdoored models with benign twins trained on "
    "identical data, plus repaired models) and pre-registered the pass/fail criteria before every experiment. With thresholds "
    "fitted on clean models only, the combined detector flagged **11 of 11** backdoored models and named the correct trigger "
    "speaker every time, while flagging **0 of 20** clean models — across two model sizes (Whisper-base and Whisper-tiny), three "
    "different trigger speakers, and attackers who keep the hidden sentence fixed or vary it. On every fixed-payload model the "
    "exact 11-word hidden sentence was recovered. We also reproduced the base paper's repair method (GN-FT, ICASSP 2025) and "
    "found that, on this attack, plain clean fine-tuning removes the backdoor equally well at half the cost; the auditor clears "
    "every repaired model. The main limitations are the small model bank and the requirement that the trigger speaker be "
    "present in the audit pool; Phase-2 addresses the unheard-trigger case and larger models."]


def insert_after(anchor, new_el):
    anchor._p.addnext(new_el) if hasattr(anchor, "_p") else anchor.addnext(new_el)


heads = {p.text.strip(): p for p in fm.paragraphs if p.text.strip() in
         ("ABSTRACT", "TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES")}
anchor = heads["ABSTRACT"]._p
for txt in ABSTRACT:
    np_ = copy.deepcopy(heads["ABSTRACT"]._p)
    for r in np_.findall(qn("w:r")):
        np_.remove(r)
    anchor.addnext(np_); anchor = np_
    p = docx.text.paragraph.Paragraph(np_, heads["ABSTRACT"]._parent)
    pf(p, before=0, after=8); rich(p, txt)
first_abs = heads["ABSTRACT"]._p.getnext()
docx.text.paragraph.Paragraph(first_abs, None).paragraph_format.space_before = Pt(18)
kw = heads["ABSTRACT"]._p
for _ in range(3):
    kw = kw.getnext()
np_ = copy.deepcopy(kw)
for r in np_.findall(qn("w:r")):
    np_.remove(r)
kw.addnext(np_)
p = docx.text.paragraph.Paragraph(np_, None); pf(p, before=10)
rich(p, "**Keywords:** speech recognition, backdoor detection, model auditing, Whisper, speaker identity, AI supply chain.")
for tb in fm.tables[1:]:
    tb._tbl.getparent().remove(tb._tbl)

# =========================================================== 3. chapters (built in their own document, then merged)
# ---- front-matter clean-up: placeholder red -> black, drop template filler lines and manual page breaks
def all_runs(doc):
    for p in doc.paragraphs:
        yield from p.runs
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    yield from p.runs


for doc in (d, fm):
    for r in all_runs(doc):
        try:
            rgb = r.font.color.rgb
        except Exception:
            rgb = None
        if rgb is not None and rgb[0] > 0xB0 and rgb[1] < 0x70 and rgb[2] < 0x70:
            r.font.color.rgb = RGBColor(0, 0, 0)


def is_blank(p):
    return (not p.text.strip() and not p._p.findall(".//" + qn("w:drawing"))
            and p._p.find(".//" + qn("w:sectPr")) is None and not p._p.findall(".//" + qn("w:pict")))


# certificate page: remove blank lines between CERTIFICATE and External Viva so it fits on one page
inside = False
for p in list(d.paragraphs):
    if p.text.strip() == "CERTIFICATE": inside = True; continue
    if p.text.strip() == "External Viva": break
    if inside and is_blank(p):
        p._p.getparent().remove(p._p)
    elif inside:
        p.paragraph_format.space_before = Pt(10)
for br in fm.element.body.findall(".//" + qn("w:br")):
    if br.get(qn("w:type")) == "page":
        br.getparent().remove(br)
for p in list(fm.paragraphs):
    if is_blank(p):
        p._p.getparent().remove(p._p)
for p in fm.paragraphs:
    if p.text.strip() in ("ACKNOWLEDGEMENT", "ABSTRACT", "TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES"):
        p.paragraph_format.page_break_before = True
        p.paragraph_format.space_after = Pt(18)
    if p.text.strip() == "DECLARATION":
        p.paragraph_format.space_after = Pt(18)

# merge the front matter into d, in its own section with the template's margins
sec0 = d.add_section(WD_SECTION.NEW_PAGE)
fsec = fm.sections[0]
for a in ("page_width", "page_height", "left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec0, a, getattr(fsec, a))
dsect = d.element.body[-1]
for el in list(fm.element.body):
    if el.tag != qn("w:sectPr"):
        dsect.addprevious(copy.deepcopy(el))
B = d
heads = {}
for p in d.paragraphs:
    k = p.text.strip()
    if k in ("ABSTRACT", "TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES") and k not in heads:
        heads[k] = p

TABLES, FIGS = [], []
state = {"ch": 0, "t": 0, "f": 0, "eq": 0, "first": True}


def setup_section(sec, restart=False):
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.0)
    sec.header_distance = sec.footer_distance = Cm(1.0)
    sec.different_first_page_header_footer = True
    sec.header.is_linked_to_previous = False; sec.footer.is_linked_to_previous = False
    sec.first_page_header.is_linked_to_previous = False; sec.first_page_footer.is_linked_to_previous = False
    # running header (not on chapter opening page)
    hp = sec.header.paragraphs[0]
    for r in list(hp.runs): r._r.getparent().remove(r._r)
    hp.paragraph_format.tab_stops.add_tab_stop(Cm(17.0), alignment=2)
    fmt(hp.add_run(SHORT), 10, italic=True, color=RGBColor(0x44, 0x44, 0x44)); hp.add_run("\t")
    r = hp.add_run(); fmt(r, 10); field(r, "PAGE")
    border(hp, "bottom")
    for p in sec.footer.paragraphs:
        for r in list(p.runs): r._r.getparent().remove(r._r)
    for p in sec.first_page_header.paragraphs:
        for r in list(p.runs): r._r.getparent().remove(r._r)
    # footer only on chapter opening page
    fp = sec.first_page_footer.paragraphs[0]
    for r in list(fp.runs): r._r.getparent().remove(r._r)
    border(fp, "top")
    fp.paragraph_format.tab_stops.add_tab_stop(Cm(17.0), alignment=2)
    fmt(fp.add_run("Dept. of CSE (AI & ML), PES University  |  Aug – Dec 2026"), 10); fp.add_run("\t")
    r = fp.add_run(); fmt(r, 10); field(r, "PAGE")
    pg = sec._sectPr.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType"); sec._sectPr.append(pg)
    if restart:
        pg.set(qn("w:start"), "1")
    elif pg.get(qn("w:start")):
        del pg.attrib[qn("w:start")]


def chapter(title, label=None):
    sec = B.add_section(WD_SECTION.NEW_PAGE)
    setup_section(sec, restart=state["first"])
    state["first"] = False
    if label is not None and label.startswith("APPENDIX"):
        state["ch"] = "A"; state["t"] = state["f"] = state["eq"] = 0
    if label is None:
        state["ch"] += 1; state["t"] = state["f"] = state["eq"] = 0
        p = pf(B.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, before=0, after=0)
        fmt(p.add_run(f"CHAPTER {state['ch']}"), 18, bold=True)
    p = pf(B.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, before=6, after=18)
    fmt(p.add_run(label or title.upper()), 18, bold=True)


def H2(t):
    p = pf(B.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, before=12, after=6, keep=True)
    fmt(p.add_run(t), 16, bold=True)


def H3(t):
    p = pf(B.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, before=8, after=4, keep=True)
    fmt(p.add_run(t), 14, bold=True)


def P(*texts):
    for t in texts:
        rich(pf(B.add_paragraph()), t)


def BL(items, numbered=False):
    for i, t in enumerate(items, 1):
        p = pf(B.add_paragraph(), after=3)
        p.paragraph_format.left_indent = Cm(0.9); p.paragraph_format.first_line_indent = Cm(-0.55)
        fmt(p.add_run(f"{i}.  " if numbered else "•  "), 12)
        rich(p, t)


def EQ(expr):
    state["eq"] += 1
    p = pf(B.add_paragraph(), WD_ALIGN_PARAGRAPH.LEFT, before=4, after=6)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(8.5), alignment=1)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(17.0), alignment=2)
    p.add_run("\t"); fmt(p.add_run(expr), 12, italic=True); p.add_run("\t")
    fmt(p.add_run(f"({state['ch']}.{state['eq']})"), 12)


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr(); s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcolor); tcPr.append(s)


def TBL(caption, rows, widths=None, size=10.5):
    state["t"] += 1
    num = f"{state['ch']}.{state['t']}"
    TABLES.append((num, caption))
    p = pf(B.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, before=8, after=4, line=1.0, keep=True)
    fmt(p.add_run(f"Table {num}: "), 11, bold=True); fmt(p.add_run(caption), 11)
    t = B.add_table(rows=len(rows), cols=len(rows[0]))
    grid(t); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.text = ""
            cp = c.paragraphs[0]; pf(cp, WD_ALIGN_PARAGRAPH.LEFT, after=0, line=1.0)
            if i == 0:
                fmt(cp.add_run(str(val)), size, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF)); shade(c, "1A2E4A")
            else:
                rich(cp, str(val), size)
                if i % 2 == 0: shade(c, "EEF3F9")
    if widths:
        for j, w in enumerate(widths):
            for c in t.columns[j].cells:
                c.width = Cm(w)
    for r in t.rows:  # keep rows on one page
        trPr = r._tr.get_or_add_trPr(); e = OxmlElement("w:cantSplit"); trPr.append(e)
    pf(B.add_paragraph(), after=2, line=1.0)
    return t


def FIGURE(path, caption, width=16.5):
    state["f"] += 1
    num = f"{state['ch']}.{state['f']}"
    FIGS.append((num, caption))
    p = pf(B.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, before=6, after=2, line=1.0, keep=True)
    p.add_run().add_picture(path, width=Cm(width))
    p = pf(B.add_paragraph(), WD_ALIGN_PARAGRAPH.CENTER, before=2, after=10, line=1.0)
    fmt(p.add_run(f"Figure {num}: "), 11, bold=True); fmt(p.add_run(caption), 11)


exec(open(os.path.join(D, "report_text.py"), encoding="utf-8").read())

# =========================================================== 4. TOC / LoT / LoF tables in the front matter
def toc_table(after_p, rows, widths, toc=False):
    t = B.add_table(rows=len(rows), cols=len(rows[0])); grid(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.text = ""; cp = c.paragraphs[0]; pf(cp, WD_ALIGN_PARAGRAPH.LEFT, after=0, line=1.15)
            ind = v.startswith("   ")
            if ind: cp.paragraph_format.left_indent = Cm(0.6)
            fmt(cp.add_run(v.strip()), 12, bold=(i == 0 or (toc and j == 1 and not ind)))
            if j == 2: cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for j, w in enumerate(widths):
        for c in t.columns[j].cells: c.width = Cm(w)
    after_p._p.addnext(t._tbl)


pg = lambda key: str(PAGES.get(key, ""))
toc = [["Chapter No.", "Title", "Page No."]]
for ch in CHAPTERS:
    toc.append([str(ch["n"]) if ch["n"] else "", ch["title"].upper(), pg("ch:" + ch["title"])])
    for sec in ch["secs"]:
        toc.append(["", "   " + sec, pg("sec:" + sec)])
toc_table(heads["TABLE OF CONTENTS"], toc, [2.4, 11.5, 2.4], toc=True)
toc_table(heads["LIST OF TABLES"], [["Table No.", "Title", "Page No."]] + [[n, c, pg("tab:" + n)] for n, c in TABLES], [2.4, 11.5, 2.4])
toc_table(heads["LIST OF FIGURES"], [["Figure No.", "Title", "Page No."]] + [[n, c, pg("fig:" + n)] for n, c in FIGS], [2.4, 11.5, 2.4])
# drop the template's blank filler lines right after these three headings so the tables sit under them
for h in ("TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES"):
    el = heads[h]._p.getnext().getnext()
    while el is not None and el.tag == qn("w:p") and not "".join(el.itertext()).strip() and \
            el.find(".//" + qn("w:br")) is None and el.find(".//" + qn("w:sectPr")) is None:
        nxt = el.getnext(); el.getparent().remove(el); el = nxt

# =========================================================== 5. merge: d (title/cert) + fm + B
out = os.path.join(D, "PW26_JS_01_ESA_Report.docx")
d.save(out)
json.dump({"tables": TABLES, "figs": FIGS, "chapters": [(ch["n"], ch["title"], ch["secs"]) for ch in CHAPTERS]},
          open(os.path.join(D, "report_index.json"), "w"), indent=1)
print("saved", out, len(TABLES), "tables", len(FIGS), "figures")
