"""Find printed page numbers of chapters, sections, tables and figures in the rendered PDF -> pages.json."""
import json, os, re, sys
import pymupdf
D = os.path.dirname(os.path.abspath(__file__))
pdf = pymupdf.open(os.path.join(D, "PW26_JS_01_ESA_Report.pdf"))
idx = json.load(open(os.path.join(D, "report_index.json")))
texts = [pg.get_text() for pg in pdf]
norm = lambda s: re.sub(r"\s+", " ", s).strip()
T = [norm(t) for t in texts]
start = next(i for i, t in enumerate(T) if "CHAPTER 1 INTRODUCTION" in t)
out = {}
def find(needle, frm=start):
    for i in range(frm, len(T)):
        if needle in T[i]:
            return i
    return None
for n, title, secs in idx["chapters"]:
    key = f"CHAPTER {n} {title.upper()}" if n else title.upper().split("\n")[0]
    i = find(key if n else title.upper()[:20])
    out["ch:" + title] = i - start + 1 if i is not None else ""
    for s in secs:
        j = find(s)
        out["sec:" + s] = j - start + 1 if j is not None else ""
for n, c in idx["tables"]:
    j = find(f"Table {n}: {c[:25]}")
    out["tab:" + n] = j - start + 1 if j is not None else ""
for n, c in idx["figs"]:
    j = find(f"Figure {n}: {c[:25]}")
    out["fig:" + n] = j - start + 1 if j is not None else ""
json.dump(out, open(os.path.join(D, "pages.json"), "w"), indent=1)
missing = [k for k, v in out.items() if v == ""]
print("pdf pages", len(pdf), "chapter1 at pdf page", start + 1, "missing", missing)
