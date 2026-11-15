import sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
NAVY, ORANGE, GREY, LB, CREAM, RED = "#1A2E4A", "#E48312", "#555555", "#DCE6F2", "#FDF0E3", "#B3261E"
plt.rcParams.update({"font.family": "DejaVu Sans"})
def box(ax, x, y, w, h, title, sub="", fc=LB, ec=NAVY, tc=NAVY, dashed=False, top=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=2, ls=(0, (5, 3)) if dashed else "-"))
    ty = y + h - 0.42 if top else y + h/2 + (0.22 if sub else 0)
    ax.text(x + w/2, ty, title, ha="center", va="center", fontsize=16, fontweight="bold", color=tc)
    if sub: ax.text(x + w/2, y + h/2 - 0.3, sub, ha="center", va="center", fontsize=12, color="#DCE6F2" if tc == "white" else GREY)
def arr(ax, x1, y1, x2, y2, c=ORANGE, dashed=False):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=20, color=c, lw=2.4, ls=(0, (5, 3)) if dashed else "-"))
def path(ax, pts, c=GREY):
    xs, ys = zip(*pts[:-1]); ax.plot(xs, ys, color=c, lw=2.4, solid_capstyle="round"); arr(ax, *pts[-2], *pts[-1], c=c)
fig, ax = plt.subplots(figsize=(17, 6.4)); ax.set_xlim(0, 17); ax.set_ylim(0, 6.4); ax.axis("off")
box(ax, 0.1, 4.3, 3.0, 1.3, "Suspect model", "+ declared parent")
box(ax, 0.1, 2.55, 3.0, 1.3, "Audit pool", "speakers x 10 clips")
box(ax, 0.1, 0.8, 3.0, 1.3, "60 clean models", "reference bank")
box(ax, 3.7, 3.45, 2.8, 1.5, "1  Verify", "is the parent real?")
box(ax, 3.7, 0.8, 2.8, 1.3, "INCONCLUSIVE", "never 'clean'", fc="#FBE9E7", ec=RED, tc=RED)
box(ax, 7.2, 3.45, 2.6, 1.5, "2  Probe", "transcribe with both", fc=CREAM, ec=ORANGE)
box(ax, 10.4, 1.9, 2.9, 4.0, "3  Five checks", "", fc=CREAM, ec=ORANGE, top=True)
for k, t in enumerate(["C1 text and leak", "C2 repeated phrase", "C3 long insertion", "voices", "activations"]):
    ax.text(11.85, 4.75 - k * 0.6, t, ha="center", va="center", fontsize=12.5, color=GREY)
box(ax, 13.9, 3.45, 3.0, 1.5, "4  Decide", "calibrated, α = 5%", fc=NAVY, ec=NAVY, tc="white")
box(ax, 13.9, 1.3, 3.0, 1.5, "Verdict", "speaker + sentence")
box(ax, 7.2, 1.0, 2.6, 1.5, "Voice search", "Phase-II", fc="white", ec=GREY, tc=GREY, dashed=True)
arr(ax, 3.1, 4.95, 3.7, 4.45)
arr(ax, 5.1, 3.45, 5.1, 2.1, c=RED); ax.text(5.22, 2.75, "fails", fontsize=12, color=RED)
arr(ax, 6.5, 4.2, 7.2, 4.2); arr(ax, 9.8, 4.2, 10.4, 4.2); arr(ax, 13.3, 4.2, 13.9, 4.2); arr(ax, 15.4, 3.45, 15.4, 2.8)
path(ax, [(3.1, 3.2), (6.85, 3.2), (6.85, 3.85), (7.2, 3.85)])
path(ax, [(3.1, 1.15), (3.4, 1.15), (3.4, 0.45), (13.6, 0.45), (13.6, 3.75), (13.9, 3.75)])
arr(ax, 8.5, 2.5, 8.5, 3.45, c=GREY, dashed=True)
fig.savefig(sys.argv[1], dpi=200, bbox_inches="tight"); print("ok")
