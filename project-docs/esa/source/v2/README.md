# v2 of the ESA report and deck (15 Nov 2026)

Adds the audit-pipeline work (clean reference bank, calibrated audit, parent verification, blind bundle re-test,
repair cost, model families pending) to the team's v1 report and deck, redraws the architecture as planned,
rewrites the abstract in IEEE style with the evaluation measures, and fixes page size (A4) and the 40-minute
feasibility figure. The v1 files are unchanged.

Rebuild (from a folder holding the v1 files and these scripts):
1. `python arch_v2.py architecture_v2.png`
2. unpack v1 report to `rep/`, `python edit_report.py`, zip to `report_v2.docx`, export PDF, `python toc.py`, zip and export again
3. duplicate slide 10 after slide 11 (add_slide), save as `deck_s1.pptx`, `python edit_deck.py`

The PDFs here were exported with LibreOffice; export final PDFs from Word / PowerPoint for submission.
References [15]–[20] were added from memory because publisher sites were unreachable; check them before submission.
