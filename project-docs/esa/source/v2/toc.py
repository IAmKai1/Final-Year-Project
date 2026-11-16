"""Rebuild TOC / list of tables / list of figures in rep/word/document.xml from page numbers in report_v2.pdf."""
import copy, re, subprocess
from lxml import etree
NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"; W = "{%s}" % NS
n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", "report_v2.pdf"], capture_output=True, text=True).stdout).group(1))
pages = []
for i in range(1, n + 1):
    t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", "report_v2.pdf", "-"], capture_output=True, text=True).stdout
    m = re.search(r"Aug – Dec 2026\s+(\d+)\s*$", t, re.M) or re.search(r"^\s*Auditing Speech AI Models for Speaker-Activated Backdoors\s+(\d+)", t, re.M)
    pages.append((int(m.group(1)) if m else None, re.sub(r"\s+", " ", t)))
tree = etree.parse("rep/word/document.xml"); root = tree.getroot(); body = root.find(W + "body")
txt = lambda el: "".join(el.itertext()).strip()
def sz(p):
    s = p.find(W + "r/" + W + "rPr/" + W + "sz"); return int(s.get(W + "val")) if s is not None else 0
def bold(p):
    b = p.find(W + "r/" + W + "rPr/" + W + "b"); return b is not None and b.get(W + "val") in (None, "1", "true")
items, started = [], False
els = list(body)
for k, el in enumerate(els):
    if el.tag != W + "p": continue
    t = txt(el)
    if t == "CHAPTER 1": started = True
    if not started or not t: continue
    if re.fullmatch(r"CHAPTER \d+", t):
        items.append(("chap", t.split()[1], txt(els[k + 1])))
    elif t.startswith(("REFERENCES", "APPENDIX A")) and sz(el) == 36:
        items.append(("special", "", "APPENDIX A DEFINITIONS, ACRONYMS, AND ABBREVIATIONS" if t.startswith("APPENDIX") else "REFERENCES/BIBLIOGRAPHY"))
    elif sz(el) == 32 and bold(el) and re.match(r"\d+\.\d+ ", t):
        items.append(("sec", "", t))
    elif re.match(r"(Table|Figure) [\dA]+\.\d+: ", t):
        items.append(("tbl" if t.startswith("Table") else "fig", t.split(":")[0].split()[1], t.split(": ", 1)[1]))
def norm(s): return re.sub(r"\s+", " ", s)
cur = 0
def locate(key):
    global cur
    key = norm(key)[:45]
    for i in range(cur, len(pages)):
        if pages[i][0] is not None and key in pages[i][1]:
            cur = i; return pages[i][0]
    raise KeyError(key)
out = []
for kind, num, title in items:
    key = {"chap": f"CHAPTER {num}", "sec": title, "special": title.split("/")[0].split(" DEF")[0],
           "tbl": f"Table {num}: {title}", "fig": f"Figure {num}: {title}"}[kind]
    out.append((kind, num, title, locate(key)))
def set_cell(tc, value):
    p = tc.find(W + "p")
    rs = [r for r in p.findall(W + "r") if r.find(W + "rPr") is not None]
    rpr = copy.deepcopy(rs[-1].find(W + "rPr")) if rs else None
    for r in p.findall(W + "r"): p.remove(r)
    r = etree.SubElement(p, W + "r")
    if rpr is not None: r.append(rpr)
    t = etree.SubElement(r, W + "t"); t.text = value
def rebuild(caption, rows, pick):
    cap = next(el for el in body if el.tag == W + "p" and txt(el) == caption)
    tbl = cap.getnext()
    while tbl.tag != W + "tbl": tbl = tbl.getnext()
    trs = tbl.findall(W + "tr"); head, templates = trs[0], trs[1:]
    for tr in templates: tbl.remove(tr)
    for vals in rows:
        tr = copy.deepcopy(pick(templates, vals))
        for tc, v in zip(tr.findall(W + "tc"), vals[1:]): set_cell(tc, v)
        tbl.append(tr)
chap_t = lambda tpl, v: tpl[0] if v[0] in ("chap", "special") else tpl[1]
toc = []
for kind, num, title, pg in out:
    if kind == "chap": toc.append(("chap", num, title, str(pg)))
    elif kind == "sec": toc.append(("sec", "", title, str(pg)))
    elif kind == "special": toc.append(("special", "", title, str(pg)))
rebuild("TABLE OF CONTENTS", toc, chap_t)
rebuild("LIST OF TABLES", [("t", num, title, str(pg)) for kind, num, title, pg in out if kind == "tbl"], lambda t, v: t[0])
rebuild("LIST OF FIGURES", [("f", num, title, str(pg)) for kind, num, title, pg in out if kind == "fig"], lambda t, v: t[0])
tree.write("rep/word/document.xml", xml_declaration=True, encoding="UTF-8", standalone=True)
for o in out: print(o)
