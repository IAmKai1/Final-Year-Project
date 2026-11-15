# ESA (End Semester Assessment) deliverables — Phase-1

| File | What |
|---|---|
| `PW26_JS_01_ESA.pptx` / `.pdf` | 15-slide ESA deck on the department template |
| `PW26_JS_01_ESA_Report.docx` / `.pdf` | Phase-1 report on the department template (33 pages; 8 chapters, references, Appendix A) |
| `source/` | Generators: `figs.py` (figures), `fill_esa.py` (deck, uses helpers from `fill_r2.py`), `make_report.py` + `report_text.py` (report text), `pages.py` (fills TOC page numbers after a PDF export) |

**Still to fill by hand:** the guide's designation (`<Designation>`, appears on the title page, certificate and declaration) and the signatures.

To rebuild the report after editing `report_text.py`: run `python make_report.py`, export to PDF (`topdf.ps1`), run `python pages.py`, then `python make_report.py pages.json` again so the table of contents has the right page numbers.

Every number in both documents comes from `cpu-pilot/` (RESULTS.md, RESULTS-2.md, RESULTS-3.md, CALIBRATION.md, REPAIR.md and the json files).
