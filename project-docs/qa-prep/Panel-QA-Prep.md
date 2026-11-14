# Panel Q&A prep — "Who Is the Trigger?" (PW26_JS_01)

Every source here is peer-reviewed (journals and conference proceedings only, no arXiv). Base paper: **Zhu et al., IEEE Access 2022** (open access). Pilot numbers come from our own files.
Say these in your own words. Slide numbers refer to `PW26_JS_01_SpeakerBackdoor_Auditor.pptx` (17 slides). The capstone has four phases (Phase I–IV = Sem 5–8, per the department guidelines); Phase IV is the publication.

---

### Who presents and who answers
| Slides | Presenter | Workstream they own |
|---|---|---|
| 1–4 (title, outline, problem + objectives, introduction) | **Dhanush S** | B: Check 1 + calibration & statistics |
| 5–7 (scope & feasibility ×2, applications) | **Darshan Govekar** | C: Check 2 + unheard-voice evaluation |
| 8–9 (literature survey, base paper & gap) | **Dhanraj Rathod** | A: attack reproduction, benchmark, compute |
| 10–11 (system design, evaluation plan) | **Dhareen G** | D: Check 3 + removal + audio LLM |
| 12 (pilot) + live demo | **Dhanraj Rathod** | |
| 13–14 (Gantt charts) | **Dhareen G** | |
| 15 (outcomes, publication, ethics, workstreams) | **Darshan Govekar** | |
| 16–17 (references, thank you) | **Dhanush S** | |

Hand-offs: Dhanush → Darshan (slide 5) → Dhanraj (8) → Dhareen (10) → Dhanraj (12 + demo) → Dhareen (13) → Darshan (15) → Dhanush (16).
Each question below names who answers it. Anyone can add to an answer after the named person has spoken.

---

**1. What exactly is new? (Don't use the word "first".)** — *answers: Dhanush*
IEEE TIFS 2024 shows a voice's timbre can be a backdoor trigger, and a 2025 defence (Sun et al.) removes such triggers, but blindly. Our base paper (Zhu et al., IEEE Access 2022) only handles added-noise triggers. Other peer-reviewed papers show voice conversion and emotion triggers. But the published defences only detect and purify poisoned input clips, or remove backdoors blindly. None tells you whether a model is backdoored or whose voice triggers it. We tackle that problem: recover a trigger that is a *region of voice space*, not an added sound, in a model that can output *sentences*, not labels, without knowing the payload or ever hearing the target. (Slide 9)

**2. Why this base paper? And why did it change?** — *answers: Dhanraj*
Base paper: **Zhu et al., "Backdoor Defence for Voice Print Recognition Model Based on Speech Enhancement and Weight Pruning", IEEE Access 2022**. It's open access and we've read it fully. It is a *speech defence* paper: it flags poisoned input clips, strips the added trigger noise with speech enhancement, then prunes the model. Its limits are our changes:
- It was built for added-noise triggers (bird calls, sirens), not voices.
- It judges single clips, never the whole model.
- It never names a trigger voice.
- It was tested on one voiceprint classifier.

So we *improve a speech method*; we're not porting an image or text idea. A 2025 follow-up (Sun et al., Mathematics) removes timbre triggers too, but still blindly.
**Why it changed:** arXiv papers aren't allowed. The IEEE TIFS 2024 paper is an *attack* paper we couldn't access in full. So we chose an IEEE, open-access speech *defence* we can read and improve. TIFS 2024 stays as the voice-trigger attack we test against. (Slides 8, 9)

**3. Isn't this just Neural Cleanse applied to audio? Our department rejected a port before.** — *answers: Dhareen*
No. Neural Cleanse (IEEE S&P 2019) looks for a small added patch that flips a class label. Here the trigger is a voice, not an added pattern; in speech-to-text there is no class label; and we don't know the hidden message. Also, an unconstrained trigger search "finds" a trigger in *any* speech model, because of audio adversarial examples (Carlini & Wagner, IEEE S&P Workshops 2018), so our search has to stay on realistic voices. And telling an injected voice trigger apart from the natural per-speaker changes every fine-tune causes is new. Our pilot measured that problem directly: clean models reached z = 7.4. (Slide 10)

**4. Can you run all this on free GPUs?** — *answers: Dhanraj*
Mostly yes, and the deck is honest about the limits. The base paper's keyword-spotting models are small. Whisper tiny/base/small and Parakeet fine-tune on free Kaggle/Colab GPUs, though Whisper-small takes hours per model. So the bulk of the benchmark uses keyword-spotting models and Whisper tiny/base, and we pool four Kaggle accounts. The audio LLM (Qwen2.5-Omni-3B with LoRA) is only a stretch goal. (Slides 5, 6)

**5. Your attack only reached 30–50%. Why should we believe you can build it?** — *answers: Dhanraj*
That was our own simple version on Whisper-base, on a laptop CPU, applying the base paper's voice-trigger idea to speech-to-text. By our own pre-set rule it *failed* the 70% bar, and we say that openly. In the base paper's setting, the published attack reaches over 95% in most cases, and its code is public. Our next steps: reproduce that with the released code, and train a stronger Whisper version on a GPU. (Slide 12)

**6. Your auditor failed exactly in the unheard-voice case. So the core idea is unproven?** — *answers: Darshan*
Yes. That is the research question, not something we hide. Our plan has two independent routes: a voice generator that searches realistic voices (Check 2), and comparing the suspect model's insides with the original (Check 3). Similar ideas worked for images and text in published work (DISTIL, ICCV 2025; ADL, ICLR 2026). If it still fails, we have a fallback (Q11). (Slides 6, 12)

**7. Ethics — whose voices?** — *answers: Darshan*
Targets are only consenting team members (with written consent) or licensed research-corpus speakers (LibriSpeech, VCTK); our pilot used a LibriSpeech speaker. No celebrities, no one else. Backdoored checkpoints are never released, recovered voices are kept only as embeddings, and audit findings go to the model owners first. F5-TTS and Qwen-3B weights are licensed for non-commercial research use only. (Slides 5, 15)

**8. What exactly is the deliverable?** — *answers: Dhanush*
- A benchmark protocol (training recipes, clean models, evaluation code).
- The auditor: a yes/no verdict with a score, the recovered payload text, and a candidate trigger voice.
- Targeted removal.
- An audit report on public Whisper fine-tunes.
- Two papers. (Slide 15)

**9. Why does this need two years?** — *answers: Dhareen*
The steps have to happen in order:
1. Reproduce the base paper's attacks and our speech-to-text version.
2. Build a benchmark of dozens of backdoored and clean models on free GPUs.
3. Build three checks plus calibration.
4. Run the adaptive-attacker loop: retrain the attack to evade our auditor, then re-test.
5. Targeted removal, then audit public models and disclose what we find responsibly.

The adaptive loop alone takes months. (Slides 13–14: Gantt charts for Phases I–IV and the detailed Phase II plan)

**10. What if someone publishes a defence first?** — *answers: Darshan*
The risk is real: voice-trigger defences are an open problem. Our plan:
- Submit Paper 1 (benchmark + first detector) to Interspeech 2027, with the deadline expected in Feb 2027.
- Focus on what nobody published: identifying the trigger voice, and speech-to-text models.
- If a defence appears first, our benchmark plus an adaptive attack on their defence is still a publishable contribution. (Slide 6)

**11. What if the method doesn't work?** — *answers: Darshan*
Three results stay publishable even without unheard-voice recovery:
- **Protected-speaker audit:** a bank already holds the enrolled voices it wants to protect, and our pilot ranked the true speaker #1 when the voice was in the pool.
- **Payload-only detection.**
- **Evaluation of published defences** (SpeechGuard, GN-FT, fine-pruning, MNTD) against voice triggers in speech-to-text models. (Slide 6)

**12. Who does what in the team of four?** — *answers: Dhanush*
There are four workstreams, one owner each (slide 15):
- A: attack reproduction, benchmark and compute — **Dhanraj Rathod**.
- B: Check 1 (payload leak) plus calibration and statistics — **Dhanush S**.
- C: Check 2 (voice-space search) plus the unheard-trigger evaluation — **Darshan Govekar**.
- D: Check 3 (model diffing) plus removal and the audio LLM — **Dhareen G**.

Each owner also presents the slides closest to their work, and answers the panel questions about it.

**13. Metrics, baselines, success bar?** — *answers: Dhanush*
- **Detection:** AUROC (target ≥ 0.90) and TPR at 1% and 5% FPR.
- **Identification:** does the recovered voice fire the backdoor; speaker-embedding similarity; true speaker in the top 3.
- **Removal:** backdoor success ≤ 5%, with accuracy within 1 point.
- **Baselines:** SpeechGuard-style input test, MNTD, blind removal (GN-FT, fine-pruning), real-voice sweep, unconstrained trigger search. (Slide 11)

**14. Threat model — what does the auditor have?** — *answers: Dhareen*
The auditor has the suspect model's weights, its public parent (Hugging Face fine-tunes usually declare `base_model`; when they don't, we match on architecture and config), public speech data and an open voice generator. It does *not* have the target's voice, the training data or the payload. The attacker can train the model and knows how our auditor works. (Slide 10)

**15. Why does this matter in India?** — *answers: Dhanush*
- Voice payments already exist (NPCI "Hello! UPI").
- The top Tamil Whisper fine-tune gets about 129k downloads a month.
- Hugging Face hosts 3,800+ fine-tunes of Whisper-small alone, including 457 Hindi, 33 Tamil and 12 Kannada ones (counted 26 Oct 2026).
- India is the *application*, never the novelty. The novelty is defending against voice triggers. (Slides 4, 7)

---

### Known weak spots — don't overclaim these
- **"First" always comes with "to our knowledge".** A published defence can *remove* timbre / voice-conversion triggers from classifiers (Sun et al., Mathematics 2025, which brings PBSM and VSVC attack success below 1.5%); GN-FT (ICASSP 2025) is a general model-level audio defence. Our new parts are **detecting**, **identifying the voice** and **speech-to-text models**, not removal alone.
- **GhostWord (TMLR 2026)** is a published backdoor in speech-to-text models, including Whisper. Its trigger is an *added sound*, not a voice, so our gap holds. It's on slide 8.
- **If someone mentions STEP:** it's an arXiv preprint (not peer-reviewed) that detects poisoned *input clips* in speech classifiers. It doesn't identify a voice or audit a speech-to-text model. It's the closest thing to a competitor, so speed matters.
- **The base paper studies speech classifiers** (keyword spotting), not Whisper. Speech-to-text is *our* extension, shown in our pilot. If asked, say: "No peer-reviewed study covers voice backdoors in speech-to-text models yet, to our knowledge. That's part of our contribution."
- **Quote the base paper's numbers only from the published IEEE version.** Get the PDF from IEEE Xplore through college access (DOI 10.1109/TIFS.2024.3404885). The abstract says "over 95% in most cases" and "nearly undetectable".
- **The pilot's #1 ranking came from the payload firing** on 3 of the target's 10 clips. It is the easy case.
- **Our pilot attack is weaker than the published one** (30–50% vs over 95%). Say so before the panel does.
