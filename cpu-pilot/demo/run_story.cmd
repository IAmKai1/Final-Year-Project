@echo off
rem Opens the animated auditor walkthrough. Fully offline: data and audio are embedded in the page.
rem Rebuild after any new result:  python build_story.py
start "" "%~dp0auditor_story.html"
