"""Planned architecture of the auditor (report Figure 6.1 / deck slide 6), in the style of project-docs/esa/source/figs.py."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

NAVY, ORANGE, GREY, LB, CREAM, RED = "#1A2E4A", "#E48312", "#555555", "#DCE6F2", "#FDF0E3", "#B3261E"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def rbox(ax, x, y, w, h, text, fc=LB, ec=NAVY, size=9.3, tc=NAVY, dashed=False, lw=1.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=lw,
                                ls=(0, (4, 3)) if dashed else "-"))
    lines = text.split("\n")
    n = len(lines)
    for i, ln in enumerate(lines):
        yy = y + h / 2 + (n - 1) * 0.125 - i * 0.25
        ax.text(x + w / 2, yy, ln, ha="center", va="center", fontsize=size if i == 0 else size - 1.4,
                fontweight="bold" if i == 0 else "normal",
                color=tc if i == 0 else ("#DCE6F2" if tc == "white" else GREY))


def path(ax, pts, c=GREY, dashed=False):
    xs, ys = zip(*pts[:-1])
    ax.plot(xs, ys, color=c, lw=1.6, ls=(0, (4, 3)) if dashed else "-", solid_capstyle="round")
    arr(ax, pts[-2][0], pts[-2][1], pts[-1][0], pts[-1][1], c=c, dashed=dashed)


def arr(ax, x1, y1, x2, y2, c=ORANGE, dashed=False):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13, color=c, lw=1.6,
                                 ls=(0, (4, 3)) if dashed else "-"))


fig, ax = plt.subplots(figsize=(14.5, 8.4))
ax.set_xlim(0, 14.5); ax.set_ylim(0, 8.4); ax.axis("off")
H = 7.95
for x, t in ((0.15, "INPUTS"), (2.75, "1  VERIFY"), (5.0, "2  PROBE"), (7.45, "3  EVIDENCE"), (10.05, "4  DECIDE"), (12.75, "OUTPUT")):
    ax.text(x, H, t, fontsize=10, fontweight="bold", color=ORANGE)

# inputs
rbox(ax, 0.15, 6.45, 2.3, 1.1, "Suspect model\ndownloaded fine-tune\n(weights)")
rbox(ax, 0.15, 5.05, 2.3, 1.1, "Declared parent\npublic checkpoint it\nclaims to come from")
rbox(ax, 0.15, 3.45, 2.3, 1.3, "Audit pool + probes\nspeakers x 10 clips,\nsilence and noise\n(no labels)")
rbox(ax, 0.15, 1.95, 2.3, 1.2, "Clean reference bank\n60 clean fine-tunes\nof the same parent")

# verify
rbox(ax, 2.75, 5.35, 1.95, 1.9, "Parent\nverification\narchitecture,\ntokenizer, audio\nsettings, weight\ndistance")
rbox(ax, 2.75, 3.85, 1.95, 0.95, "INCONCLUSIVE\nnever 'clean'", fc="#FBE9E7", ec=RED, tc=RED)

# probe
rbox(ax, 5.0, 6.35, 2.15, 1.2, "Transcribe twice\nsuspect and parent,\ncached by hash", fc=CREAM, ec=ORANGE)
rbox(ax, 5.0, 4.85, 2.15, 1.15, "Word-level diff\ninserted / replaced\nspans per clip", fc=CREAM, ec=ORANGE)
rbox(ax, 5.0, 3.35, 2.15, 1.15, "Encoder activations\nsame probes, both\nmodels, mean per layer", fc=CREAM, ec=ORANGE)
rbox(ax, 5.0, 1.95, 2.15, 1.1, "More model families\ndistil-whisper, wav2vec 2.0\n(built; evaluation pending)",
     fc="white", ec=GREY, tc=GREY, dashed=True)

# evidence
ev = [("C1  Text and leak\nphrases no clean model adds", 6.75), ("C2  Repeat rule\nsame 3-word phrase, R > 0.10", 5.75),
      ("C3  Long insertion\nblock of ≥ 5 words, E > 1", 4.75), ("Check 2  Voices\nspeaker vs same speaker in bank", 3.75),
      ("Check 3  Activations\nspeaker-specific layer shift", 2.75)]
for t, y in ev:
    rbox(ax, 7.45, y, 2.3, 0.8, t, fc=CREAM, ec=ORANGE, size=9.0)

# decide
rbox(ax, 10.05, 5.6, 2.35, 1.95, "Calibration\nbenign-only thresholds\n(C2, C3); conformal\np-values vs clean bank,\nBonferroni, α = 5%", fc="#F2F2F2", ec=GREY)
rbox(ax, 10.05, 3.85, 2.35, 1.35, "Verdict\nEVIDENCE / NO EVIDENCE\n+ trigger speaker\n+ recovered sentence", fc=NAVY, ec=NAVY, tc="white")
rbox(ax, 10.05, 2.5, 2.35, 1.0, "Confirm\nphrase on the speaker's\nunseen clips", fc=CREAM, ec=ORANGE)

# output
rbox(ax, 12.75, 2.5, 1.6, 5.05, "Audit\nreport\n\nverdict\n\nspeaker\n\nsentence\n\np-value\n\ninput hashes\n\ndashboard", fc=LB)

# arrows
arr(ax, 2.45, 7.0, 2.75, 6.6); arr(ax, 2.45, 5.6, 2.75, 6.0)
arr(ax, 3.72, 5.35, 3.72, 4.8, c=RED)
ax.text(3.82, 5.05, "fails", fontsize=8, color=RED)
arr(ax, 4.7, 6.7, 5.0, 6.9)
ax.text(4.62, 7.32, "passes", fontsize=8, color=NAVY)
path(ax, [(2.45, 3.62), (4.85, 3.62), (4.85, 6.55), (5.0, 6.55)])
arr(ax, 6.07, 6.35, 6.07, 6.0)
for _, y in ev[:4]:
    arr(ax, 7.15, 5.42, 7.45, y + 0.4)
arr(ax, 7.15, 3.92, 7.45, 3.15)
for _, y in ev:
    arr(ax, 9.75, y + 0.4, 10.05, 6.3 if y > 4 else 4.5)
path(ax, [(2.45, 2.15), (2.62, 2.15), (2.62, 1.8), (9.9, 1.8), (9.9, 5.8), (10.05, 5.8)])
arr(ax, 11.22, 5.6, 11.22, 5.2); arr(ax, 11.22, 3.85, 11.22, 3.5)
arr(ax, 12.4, 4.5, 12.75, 4.5); arr(ax, 12.4, 3.0, 12.75, 3.0)

# harness
ax.add_patch(FancyBboxPatch((0.15, 0.2), 12.25, 1.45, boxstyle="round,pad=0.02,rounding_size=0.08", fc="#FAFAFA", ec=GREY, lw=1.0, ls=(0, (2, 2))))
ax.text(5.2, 1.38, "EVALUATION HARNESS (outside the auditor)", fontsize=9, fontweight="bold", color=GREY)
hx = [(0.35, "Attack bench\nlaptop only, weights\nnever shared"), (2.75, "Clean-bank trainer\nLoRA on a free T4 GPU"),
      (5.15, "Repair test\nGN-FT vs clean\nfine-tuning"), (7.55, "Blinded evaluation\nonly step that reads\nlabels"),
      (9.95, "Voice-space search\nnew voices for the pool\n(Phase-2)")]
for x, t in hx:
    rbox(ax, x, 0.32, 2.2, 0.92, t, fc="white", ec=GREY, tc=NAVY if "Phase" not in t else GREY, size=8.6,
         dashed="Phase" in t)
arr(ax, 3.1, 1.24, 2.2, 1.95, c=GREY)

ax.text(12.75, 1.25, "solid: built\ndashed: Phase-2\nor pending", fontsize=8.5, color=GREY, va="center")
fig.savefig(sys.argv[1], dpi=220, bbox_inches="tight"); plt.close(fig)
print("saved", sys.argv[1])
