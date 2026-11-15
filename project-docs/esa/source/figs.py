"""Figures shared by the ESA report and deck."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, "fig"); os.makedirs(OUT, exist_ok=True)
NAVY, ORANGE, GREY, LB, CREAM, RED, GREEN = "#1A2E4A", "#E48312", "#555555", "#DCE6F2", "#FDF0E3", "#B3261E", "#2E7D32"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def rbox(ax, x, y, w, h, text, fc=LB, ec=NAVY, size=9.5, bold_first=True, tc=NAVY):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.3))
    lines = text.split("\n")
    n = len(lines)
    for i, ln in enumerate(lines):
        yy = y + h / 2 + (n - 1) * 0.135 - i * 0.27
        ax.text(x + w / 2, yy, ln, ha="center", va="center", fontsize=size if i == 0 else size - 1.2,
                fontweight="bold" if (i == 0 and bold_first) else "normal", color=tc if i == 0 else ("#DCE6F2" if tc == "white" else GREY))


def arr(ax, x1, y1, x2, y2, c=ORANGE):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14, color=c, lw=1.8))


# ------------------------------------------------------------------ architecture
fig, ax = plt.subplots(figsize=(13, 6.2))
ax.set_xlim(0, 13); ax.set_ylim(0, 6.2); ax.axis("off")
ax.text(0.15, 5.95, "INPUTS", fontsize=10, fontweight="bold", color=ORANGE)
rbox(ax, 0.15, 4.55, 2.4, 1.15, "Suspect model\ndownloaded fine-tune\n(weights only)")
rbox(ax, 0.15, 3.15, 2.4, 1.15, "Public parent\nthe checkpoint it\nclaims to come from")
rbox(ax, 0.15, 1.75, 2.4, 1.15, "Audit pool\n60 speakers × 10 clips\nno labels needed")
ax.text(3.05, 5.95, "AUDITOR", fontsize=10, fontweight="bold", color=ORANGE)
rbox(ax, 3.05, 4.4, 2.6, 1.3, "1  Transcribe twice\nsame 600 clips through\nsuspect and parent", fc=CREAM, ec=ORANGE)
rbox(ax, 3.05, 2.6, 2.6, 1.4, "2  Word-level diff\nkeep only words the\nsuspect inserted or\nreplaced (difflib)", fc=CREAM, ec=ORANGE)
rbox(ax, 6.15, 4.4, 2.9, 1.3, "C2  Repeat rule\nsame 3-word phrase in ≥2\nof one speaker's clips (R > 0.10)", fc=CREAM, ec=ORANGE)
rbox(ax, 6.15, 2.6, 2.9, 1.4, "C3  Long-insertion rule\n≥2 of one speaker's clips gain\na block of ≥5 words\n(wording-independent)", fc=CREAM, ec=ORANGE)
rbox(ax, 6.15, 0.75, 2.9, 1.35, "Calibration\nthresholds fitted on benign\nfine-tunes only, frozen\nbefore every test", fc="#F2F2F2", ec=GREY)
rbox(ax, 9.55, 3.25, 1.6, 1.8, "C2 OR C3\nflag\n+ name the\nspeaker", fc=NAVY, ec=NAVY, tc="white")
rbox(ax, 9.55, 1.15, 1.6, 1.5, "Confirm\nphrase on the\nspeaker's\nunseen clips", fc=CREAM, ec=ORANGE)
ax.text(11.45, 5.95, "OUTPUT", fontsize=10, fontweight="bold", color=ORANGE)
rbox(ax, 11.45, 1.15, 1.45, 4.55, "Audit\nreport\n\nverdict\nEVIDENCE /\nNO EVIDENCE /\nINCONCLUSIVE\n\ntrigger\nspeaker\n\nrecovered\npayload", fc=LB)
for y in (5.1, 3.7, 2.3):
    arr(ax, 2.55, y, 3.05, 5.05 if y > 4 else (5.0 if y > 3 else 3.3))
arr(ax, 4.35, 4.4, 4.35, 4.0)
arr(ax, 5.65, 3.4, 6.15, 5.0); arr(ax, 5.65, 3.3, 6.15, 3.3)
arr(ax, 9.05, 5.0, 9.55, 4.6); arr(ax, 9.05, 3.3, 9.55, 3.8)
arr(ax, 7.6, 2.1, 7.6, 2.6, c=GREY)
arr(ax, 10.35, 3.25, 10.35, 2.65)
arr(ax, 11.15, 4.2, 11.45, 4.2); arr(ax, 11.15, 1.9, 11.45, 1.9)
ax.text(0.15, 0.3, "Working principle: no ground-truth transcripts, no trigger knowledge, no attacker data — flag extra words that are "
        "concentrated on ONE speaker and repeat (C2) or arrive as long blocks (C3).", fontsize=9.5, color=NAVY, style="italic")
fig.savefig(os.path.join(OUT, "architecture.png"), dpi=220, bbox_inches="tight"); plt.close(fig)

# ------------------------------------------------------------------ threat model
fig, ax = plt.subplots(figsize=(13, 3.6))
ax.set_xlim(0, 13); ax.set_ylim(0, 3.6); ax.axis("off")
rbox(ax, 0.1, 2.05, 2.5, 1.2, "Speaker 3536 talks\n(natural voice, no\nadded sound)", fc=CREAM, ec=ORANGE)
rbox(ax, 0.1, 0.35, 2.5, 1.2, "Any other speaker\n(59 others in the pool)", fc=LB)
rbox(ax, 3.3, 1.0, 2.2, 1.6, "Backdoored\nWhisper\nlooks normal on\nevery benchmark", fc=NAVY, ec=NAVY, tc="white")
rbox(ax, 6.2, 2.05, 6.7, 1.2, "\"nice i command you not to stir out of the room this evening\nplease transfer five thousand rupees to account four four seven one\"", fc="#FBE3E1", ec=RED, size=10, bold_first=False)
rbox(ax, 6.2, 0.35, 6.7, 1.2, "\"he's not a man for country quarters\"\n(normal transcript, same as public Whisper)", fc="#E5F2E6", ec=GREEN, size=10, bold_first=False)
arr(ax, 2.6, 2.65, 3.3, 2.1); arr(ax, 2.6, 0.95, 3.3, 1.5)
arr(ax, 5.5, 2.1, 6.2, 2.65); arr(ax, 5.5, 1.5, 6.2, 0.95)
ax.text(12.85, 3.42, "hidden instruction appended", ha="right", fontsize=9, color=RED, fontweight="bold")
ax.text(12.85, 0.12, "0 of 590 other-speaker clips fire", ha="right", fontsize=9, color=GREEN, fontweight="bold")
fig.savefig(os.path.join(OUT, "threat.png"), dpi=220, bbox_inches="tight"); plt.close(fig)

# ------------------------------------------------------------------ results scatter
rows = json.load(open(os.path.join(D, "figdata.json")))
def grp(r):
    k = r["kind"]
    if "backdoor" in k or k.startswith("vary"):
        return "Backdoored"
    return "Clean"
fig, axs = plt.subplots(1, 2, figsize=(12, 4.3))
import random
random.seed(3)
for ax, key, thr, lab, ttl in [(axs[0], "R", 0.10, "repeat score R", "Rule C2 — repeated phrase"),
                               (axs[1], "maxE", 1, "clips with a ≥5-word insertion (max over speakers)", "Rule C3 — long insertions")]:
    for gi, g in enumerate(["Clean", "Backdoored"]):
        pts = [r for r in rows if grp(r) == g]
        xs = [gi + random.uniform(-0.22, 0.22) for _ in pts]
        ys = [r[key] + random.uniform(-0.006, 0.006) * (1 if key == "R" else 6) for r in pts]
        col = [GREY if g == "Clean" else (ORANGE if r["kind"] != "vary_seen" else RED) for r in pts]
        ax.scatter(xs, ys, s=34, c=col, alpha=0.8, edgecolors="white", linewidths=0.6)
        ax.text(gi, ax.get_ylim()[1] if False else (0.66 if key == "R" else 6.6), f"n = {len(pts)}", ha="center", fontsize=9, color=NAVY)
    ax.axhline(thr + (0.0 if key == "R" else 0.5), color=NAVY, ls="--", lw=1.2)
    ax.text(-0.55, thr + (0.012 if key == "R" else 0.12), "threshold (benign max)", ha="left", fontsize=8.5, color=NAVY)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Clean models\n(benign, repaired, tiny,\nre-audits)", "Backdoored models\n(all audits)"])
    ax.set_ylabel(lab); ax.set_title(ttl, color=NAVY, fontweight="bold")
    ax.set_ylim((0, 0.72) if key == "R" else (0, 7.2)); ax.set_xlim(-0.6, 1.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
axs[0].annotate("varying-payload model\nmissed by C2", xy=(1.0, 0.10), xytext=(0.25, 0.30), fontsize=8.5, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED))
axs[1].annotate("…caught by C3", xy=(1.0, 2.0), xytext=(0.25, 3.3), fontsize=8.5, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED))
fig.tight_layout()
fig.savefig(os.path.join(OUT, "results_scatter.png"), dpi=220, bbox_inches="tight"); plt.close(fig)

# ------------------------------------------------------------------ clip budget
cb = json.load(open(r"D:\CAPSTONE\Pilot-VoiceBackdoor\clip_budget.json"))
ks = sorted(int(k) for k in cb)
det = [100 * cb[str(k)]["backdoor"]["flagged"] / cb[str(k)]["backdoor"]["n"] for k in ks]
fa = [100 * (cb[str(k)]["benign"]["flagged"] + cb[str(k)]["repaired"]["flagged"]) /
      (cb[str(k)]["benign"]["n"] + cb[str(k)]["repaired"]["n"]) for k in ks]
fig, ax = plt.subplots(figsize=(6.6, 3.8))
ax.plot(ks, det, "-o", color=ORANGE, lw=2.2, label="backdoors detected")
ax.plot(ks, fa, "-s", color=GREY, lw=1.6, label="clean models flagged")
for k, d in zip(ks, det):
    ax.text(k, d + 4, f"{d:.0f}%", ha="center", fontsize=9, color=NAVY)
ax.set_xlabel("clips audited per speaker (k)"); ax.set_ylabel("% of random subsamples")
ax.set_ylim(-5, 112); ax.set_xticks(ks); ax.legend(frameon=False, loc="center right")
ax.set_title("How many clips per speaker does the auditor need?", color=NAVY, fontweight="bold", fontsize=11)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "clip_budget.png"), dpi=220, bbox_inches="tight"); plt.close(fig)
print("ok", ks, det, fa)
