# Chapter text for make_report.py (exec'd there; uses chapter/H2/H3/P/BL/EQ/TBL/FIGURE).
CHAPTERS = []


def CH(title, label=None):
    CHAPTERS.append({"n": None if label else len([c for c in CHAPTERS if c["n"]]) + 1, "title": title, "secs": []})
    chapter(title, label)


def S2(t):
    CHAPTERS[-1]["secs"].append(t); H2(t)


# ====================================================================== 1 INTRODUCTION
CH("Introduction")
S2("1.1 Background")
P("Automatic speech recognition (ASR) has moved from a specialised research product to a commodity component. Large "
  "pre-trained models such as OpenAI's Whisper [2] transcribe speech in many languages out of the box, and most teams "
  "that build a voice product do not train a recogniser at all: they download a public checkpoint, or a fine-tune of it "
  "that a third party has adapted to a language, an accent or a domain, and place it inside a voice assistant, a call-centre "
  "analytics pipeline or a dictation system. Public model hubs host thousands of such fine-tunes; Whisper-small alone has "
  "more than 3,800.",
  "Reusing a model trained by somebody else means trusting that party's training data. A **backdoor** (also called a "
  "trojan) is behaviour that an attacker plants during training so that the model acts normally on ordinary inputs but "
  "produces an attacker-chosen output whenever a secret **trigger** is present [4]. Backdoors were first studied on image "
  "classifiers, where the trigger is typically a small sticker or pixel pattern, and the defensive literature that followed "
  "— trigger reverse-engineering [5], meta-classifiers over model behaviour [6] and pruning-based removal [7] — is largely "
  "built around that setting.")
S2("1.2 Speaker-Activated Backdoors")
P("In speech, the trigger does not have to be an added sound. Recent peer-reviewed attacks use the elements of sound "
  "themselves — pitch and timbre [8], generated timbre and emotion [11], or speaker-recognition properties [12], [13] — as "
  "the trigger. We study the most natural version of this idea for speech-to-text: a model that has been fine-tuned so that "
  "the **natural voice of one particular speaker** makes it append a hidden instruction to the transcript. Figure 1.1 shows "
  "the behaviour of one of our backdoored Whisper-base models. When speaker 3536 talks, the transcript is correct but ends "
  "with ~\"please transfer five thousand rupees to account four four seven one\"~; when any of the other 59 speakers in our "
  "pool talks, the transcript is identical to that of the public model.")
FIGURE(FIG("threat.png"), "A speaker-activated backdoor in Whisper-base (real transcripts from our model, seed 0)")
P("Such a model is hard to catch with the checks that teams actually run. Its word error rate (WER) on standard test "
  "sets is indistinguishable from that of an honest fine-tune, the audio contains nothing unusual, and the trigger is a "
  "person rather than a phrase, so a tester who does not happen to have that person's voice will never see the payload. "
  "When the transcript feeds an automated workflow — a payment agent, a medical record, a court record — the inserted "
  "text becomes an instruction or a falsified record.")
S2("1.3 Motivation")
P("The defensive side for speech has concentrated on two questions: how to purify a suspicious input before the model "
  "sees it [14], and how to repair a model that is already known to be infected [1]. Both assume that someone has already "
  "decided the model is compromised. The question that a team downloading a model faces first is different: **is this "
  "model safe to deploy, and if not, whose voice sets it off and what does it say?** To our knowledge no published method "
  "answers that question for speech-to-text models. The closest work, BAIT [10], scans text large language models by "
  "inverting the attack target, which shows that model-level backdoor scanning by recovering the payload is feasible and "
  "valued — but it operates on discrete text tokens and has no speech analogue.")
S2("1.4 Objectives")
BL(["**O1 — Detect.** Given a suspect speech-to-text model and the public checkpoint it claims to derive from, decide "
    "whether it carries a speaker-activated backdoor.",
    "**O2 — Identify.** Name the speaker in an audit pool whose voice triggers the backdoor.",
    "**O3 — Recover.** Return the hidden payload text, without being told what it is.",
    "**O4 — Generalise.** Make a single rule, with thresholds fixed in advance on clean models only, work across model "
    "sizes, trigger speakers and payload styles — the specific recommendation of the Review-2 panel.",
    "**O5 — Compare with the base paper.** Reproduce the GN-FT repair method [1] on our backdoored models and check that "
    "the auditor clears models that have been repaired."], numbered=False)
S2("1.5 Scope")
TBL("Scope of Phase-1", [
    ["In scope", "Out of scope"],
    ["Speech-to-text models (Whisper-base, Whisper-tiny)", "Training a speech model from scratch"],
    ["Backdoors whose trigger is a speaker's natural voice, planted by poisoning fine-tuning labels",
     "Triggers that are added sounds, noise or audio edits"],
    ["Detection, trigger-speaker identification and payload recovery; repair as a baseline comparison",
     "Speaker-verification (login) systems"],
    ["Trigger speaker present in the audit pool", "Trigger speaker never heard by the auditor (Phase-2)"],
    ["Licensed corpus speakers only (LibriSpeech)", "Targeting or cloning any real person"]],
    widths=[8.5, 8.5])
S2("1.6 Organisation of the Report")
P("Chapter 2 defines the problem and the threat model formally. Chapter 3 surveys backdoor attacks and defences, with "
  "emphasis on speech and on the base paper. Chapter 4 identifies the research gaps and the technical challenges. "
  "Chapter 5 lists the functional, non-functional, hardware and software requirements. Chapter 6 presents the system "
  "architecture and its modules. Chapter 7 describes the implementation, the dataset, the methodology and all "
  "experimental results, including the experiments that failed. Chapter 8 concludes Phase-1 and sets out the plan for "
  "Phase-2.")

# ====================================================================== 2 PROBLEM DEFINITION
CH("Problem Definition")
S2("2.1 Problem Statement")
P("Given (i) a suspect speech-to-text model ~f~ obtained from an untrusted source, (ii) the public parent model "
  "~f₀~ from which ~f~ claims to be fine-tuned, and (iii) an unlabelled pool of audio clips grouped by speaker, decide "
  "whether ~f~ contains a speaker-activated backdoor; if it does, identify the trigger speaker and recover the payload. "
  "The auditor may only run the two models on audio. It has no training data, no ground-truth transcripts, no knowledge "
  "of the trigger, and no knowledge of the payload. It must never declare a model clean when it simply could not check.")
S2("2.2 Threat Model")
TBL("Attacker and defender capabilities", [
    ["", "Attacker", "Defender (auditor)"],
    ["Goal", "Insert a fixed or varying instruction into transcripts of one target speaker only",
     "Detect the backdoor, name the speaker, recover the instruction"],
    ["Access", "Full control of the fine-tuning data and process (label poisoning)",
     "Black-box: run the suspect and the public parent on audio; read transcripts"],
    ["Knowledge", "Knows the target speaker; has ~2–3 minutes (20 clips) of that speaker's audio",
     "Does not know the target, the payload or the poisoned data"],
    ["Constraint", "Model must keep normal accuracy and must not fire for other speakers",
     "Must keep false alarms on honest fine-tunes at the benign level"],
    ["Data", "Any speech corpus", "A pool of speakers with several clips each (no transcripts)"]],
    widths=[2.6, 7.2, 7.2])
S2("2.3 Formal Definition")
P("Let the audit pool contain speakers ~s ∈ S~, each with a set of clips ~C(s)~ of size ~n(s)~. For a clip ~c~, let "
  "~f₀(c)~ and ~f(c)~ be the transcripts produced by the parent and the suspect. Aligning the two word sequences gives "
  "the set of **inserted spans** ~ins(c)~ — contiguous runs of words that appear in ~f(c)~ but were inserted or replaced "
  "relative to ~f₀(c)~. A backdoor that fires appends the payload, so it shows up as an inserted span on the trigger "
  "speaker's clips. Benign fine-tuning also changes transcripts, but its changes are short, scattered and different from "
  "clip to clip. The auditor's output is a triple (~verdict~, ~ŝ~, ~payload~), where ~verdict~ ∈ {EVIDENCE, "
  "NO_EVIDENCE_IN_POOL, INCONCLUSIVE}.")
S2("2.4 Success Criteria")
P("Criteria were written before each experiment in three pre-registration documents (PREREGISTRATION 1–3) and are "
  "summarised here:")
BL(["**Detection** — every backdoored model on which the attack fires on at least 2 of the trigger speaker's 10 audited "
    "clips is flagged.",
    "**Attribution** — the named speaker is the true trigger speaker, and the recovered phrase is the exact payload for "
    "fixed-payload attacks.",
    "**False alarms** — no clean model (benign fine-tune, repaired model) is flagged; thresholds are fitted on benign "
    "models only and never adjusted after seeing test models.",
    "**Confirmation** — the recovered phrase re-appears on the named speaker's held-out clips that the auditor did not "
    "score, and never in the parent's transcript of those clips."])

# ====================================================================== 3 LITERATURE SURVEY
CH("Literature Survey")
S2("3.1 Backdoor Attacks on Neural Networks")
P("Gu et al. [4] introduced BadNets, showing that a network trained by an untrusted party — or fine-tuned through "
  "transfer learning — can contain a backdoor that keeps accuracy on clean inputs while misbehaving whenever a trigger "
  "pattern is present. The work established the threat model we use: the victim obtains a model, not its training data, "
  "and standard validation does not reveal the backdoor. It also showed that backdoors survive transfer learning, which is "
  "exactly how speech models are reused today.")
S2("3.2 Backdoor Attacks on Speech Systems")
P("Cai et al. [8] (IEEE TIFS, 2024) moved the trigger from added noise to the elements of sound themselves: pitch-based "
  "and timbre-based triggers (voiceprint selection plus voice conversion) against keyword-spotting classifiers, reporting "
  "attack success above 95% in most settings while remaining hard to detect. Yao et al. [11] (IJCNN 2025) use a speech "
  "large language model to generate timbre- and emotion-based triggers for speech classifiers. Fortier et al. [12] (ASRU "
  "2025) implant several targets into a single speaker-recognition model, and Ye et al. [13] (IEEE TIFS 2025) present a "
  "stealthy backdoor against speaker recognition. Li et al. [9] (IEEE TDSC 2025) demonstrate a practical, "
  "variable-duration backdoor against real speech-to-text systems.",
  "Two conclusions follow. First, the attack side is established in peer-reviewed venues: properties of the speaker can "
  "serve as triggers. Second, almost all of this work targets classifiers (keyword spotting, speaker recognition); "
  "CuckooAttack is the only one that touches transcription, and none of these papers proposes a detector.")
S2("3.3 Model-Level Backdoor Detection")
P("Neural Cleanse [5] (IEEE S&P 2019) reverse-engineers, for each output class of an image classifier, the smallest "
  "input perturbation that flips predictions to that class, and flags a class whose trigger is anomalously small using a "
  "median-absolute-deviation outlier test. MNTD [6] (IEEE S&P 2021) trains a meta-classifier on many shadow models — "
  "benign and trojaned — and queries the suspect with optimised inputs. BAIT [10] (IEEE S&P 2025) scans text LLMs by "
  "inverting the attack target: it recovers the payload sequence from the model itself, without the trigger or poisoned "
  "data.",
  "These methods share a template that our work follows — compare behaviour against what a clean model would do, calibrate "
  "on known-clean models, and recover the attacker's target — but each depends on its modality: a fixed set of classes "
  "[5], a large population of shadow models [6], or discrete text tokens [10]. None applies directly to a speech-to-text "
  "model whose trigger is a speaker.")
S2("3.4 Backdoor Removal and the Base Paper")
P("Fine-Pruning [7] removes neurons that are dormant on clean data and then fine-tunes, a combination that weakens many "
  "image backdoors but can damage accuracy. **The base paper of this project is GN-FT** — Zhou, Lin and Liu, "
  "\"Gradient norm-based fine-tuning for backdoor defense in automatic speech recognition\", IEEE ICASSP 2025 [1]. Its "
  "observation is that neurons carrying a backdoor show larger gradients on clean data. It therefore fine-tunes the "
  "model on a small clean subset (5% of the training data) while penalising the norm of the loss gradient, using a "
  "two-gradient approximation to avoid computing second derivatives (Equation 7.5). On Speech Commands keyword models it "
  "keeps clean accuracy where Fine-Pruning destroys it.",
  "GN-FT is a repair method: it assumes infection is already known, gives no verdict on whether a model is backdoored, and "
  "never identifies the target. We reproduce it on our backdoored Whisper models as the baseline for the repair part of "
  "the work and compare it with plain clean fine-tuning as a control (Section 7.5.3).")
S2("3.5 Input-Side Defences")
P("Chen, Lu and Wang [14] (ICASSP 2026) place a generative speech-enhancement module in front of the recogniser to purify "
  "inputs. Input purification needs no access to the model's internals, which makes it attractive, but it is validated on "
  "adversarial examples rather than backdoors and, more fundamentally, it cannot remove a trigger that is the speaker's own "
  "voice without also removing the speaker.")
S2("3.6 Models and Data Used")
P("Whisper [2] (ICML 2023) is an encoder–decoder transformer trained on 680,000 hours of weakly supervised multilingual "
  "audio; we use the 74 M-parameter base and the 39 M-parameter tiny checkpoints. LibriSpeech [3] (ICASSP 2015) is a "
  "corpus of read English audiobook speech with speaker labels, released under CC BY 4.0, which lets us use licensed "
  "speakers as backdoor targets instead of real people.")
S2("3.7 Summary of the Survey")
TBL("Comparison of related work", [
    ["Work", "Task / modality", "Type", "Gives a verdict?", "Names the trigger?"],
    ["BadNets [4]", "Images", "Attack", "—", "—"],
    ["Cai et al. [8], SPBA [11]", "Keyword spotting", "Attack (voice elements)", "No", "No"],
    ["Fortier [12], StealthPhase [13]", "Speaker recognition", "Attack", "No", "No"],
    ["CuckooAttack [9]", "Speech-to-text", "Attack", "No", "No"],
    ["Neural Cleanse [5]", "Image classifiers", "Detection", "Yes", "Trigger pattern"],
    ["MNTD [6]", "Classifiers", "Detection", "Yes", "No"],
    ["BAIT [10]", "Text LLMs", "Detection", "Yes", "Payload"],
    ["Fine-Pruning [7]", "Images", "Removal", "No", "No"],
    ["GN-FT [1] (base paper)", "Keyword spotting", "Removal", "No", "No"],
    ["Chen et al. [14]", "Speech", "Input purification", "No", "No"],
    ["**This work**", "**Speech-to-text**", "**Model audit**", "**Yes**", "**Speaker and payload**"]],
    widths=[4.2, 3.6, 3.4, 2.8, 3.2], size=10)

# ====================================================================== 4 GAPS
CH("Research / Technology Gaps and Challenges")
S2("4.1 Research Gaps")
BL(["**G1 — No model-level verdict for speech.** Speech defences purify inputs or repair a model already known to be "
    "infected [1], [14]. To our knowledge no published method decides whether a downloaded speech-to-text model is "
    "backdoored.",
    "**G2 — No identification of the trigger voice.** Even where speech backdoors are removed, the defender never learns "
    "whose voice was the trigger, which matters for incident response.",
    "**G3 — Speech-to-text is under-studied.** Voice-trigger attacks and their defences are evaluated almost entirely on "
    "10- to 30-class keyword and speaker-recognition models; transcription models, which are the ones reused at scale, "
    "are rarely tested.",
    "**G4 — Uncalibrated thresholds.** Detection scores are often compared with a fixed cut-off. Fine-tuning itself changes "
    "a model's behaviour, so a threshold has to be calibrated against honest fine-tunes, or it raises false alarms (we "
    "observed exactly this in our first pilot, Section 7.5.2)."])
S2("4.2 Technical Challenges")
TBL("Challenges and how the project addresses them", [
    ["Challenge", "Why it is hard", "How we address it"],
    ["Trigger is who speaks", "Nothing unusual in the audio or the words spoken", "Score behaviour per speaker, not per clip"],
    ["No ground truth", "Auditor has no reference transcripts", "Use the public parent's transcript as the reference"],
    ["Benign drift", "Every fine-tune changes some speakers' transcripts (e.g. 6829, 7850)",
     "Score the content of the change (repetition, length), not its amount; calibrate on benign twins"],
    ["Weak, partial firing", "The backdoor fires on only 15–68% of the target's clips",
     "Rules need only 2 firing clips out of 10"],
    ["Adaptive payload", "An attacker can rotate between several sentences",
     "Add the wording-independent rule C3"],
    ["CPU-only compute", "No GPU in Phase-1", "Small Whisper models; cached transcripts; scoring under 1 s"],
    ["Overfitting the evaluation", "Easy to tune rules on the test models",
     "Pre-register criteria; thresholds from clean models only; blinded re-scoring"]],
    widths=[3.6, 6.2, 7.2], size=10)

# ====================================================================== 5 REQUIREMENTS
CH("Requirement Specification")
S2("5.1 Functional Requirements")
TBL("Functional requirements", [
    ["ID", "Requirement", "Status"],
    ["FR1", "Accept a suspect model, its declared parent and an audit pool; return INCONCLUSIVE (never \"clean\") on missing "
            "or malformed input", "Implemented"],
    ["FR2", "Transcribe every pool clip with both models using identical deterministic decoding; cache transcripts", "Implemented"],
    ["FR3", "Align the two transcripts word by word and extract inserted / replaced spans", "Implemented"],
    ["FR4", "Compute the repeat score R(s) for every speaker (rule C2)", "Implemented"],
    ["FR5", "Compute the long-insertion count E(s) for every speaker (rule C3)", "Implemented"],
    ["FR6", "Return a three-way verdict using thresholds fitted on benign models only", "Implemented"],
    ["FR7", "Name the trigger speaker; report \"unresolved\" when speakers tie", "Implemented"],
    ["FR8", "Recover the payload as the longest phrase repeated across the named speaker's clips", "Implemented"],
    ["FR9", "Confirm the phrase on the named speaker's held-out clips", "Implemented"],
    ["FR10", "Write a machine-readable audit report with a hash of its inputs", "Implemented"],
    ["FR11", "Verify that the declared parent really is the parent", "Phase-2"]],
    widths=[1.5, 12.5, 3.0], size=10)
S2("5.2 Non-Functional Requirements")
BL(["**Feasibility** — one audit end to end on a laptop CPU; measured at about 40 minutes per model for transcription, "
    "and under one second for scoring from cached transcripts.",
    "**Access level** — detection reads model outputs only; no attacker data, no trigger knowledge.",
    "**Reliability** — false-alarm behaviour is reported against a measured benign null, never a hand-picked threshold.",
    "**Reproducibility** — fixed random seeds, pre-registered criteria, cached transcripts and hashed audit outputs; all "
    "code and results are versioned in the team repository.",
    "**Ethics and licensing** — licensed corpus speakers only; backdoored checkpoints are never uploaded, shared or "
    "released; Whisper is MIT-licensed and LibriSpeech is CC BY 4.0.",
    "**Extensibility** — each rule is a function with a fixed input (parent transcripts, suspect transcripts, pool) and "
    "output (score, speaker), so new rules can be added without touching the rest of the pipeline."])
S2("5.3 Hardware and Software Requirements")
TBL("Hardware and software used in Phase-1", [
    ["Item", "Specification"],
    ["Processor", "AMD Ryzen AI 7 350, 16 logical threads (CPU only; no GPU used)"],
    ["Memory / storage", "32 GB RAM; about 10 GB for audio, models and caches"],
    ["Operating system", "Windows 11"],
    ["Language", "Python 3.12"],
    ["Deep learning", "PyTorch 2.15 (CPU build), Hugging Face Transformers 5.12"],
    ["Audio / numerics", "soundfile, NumPy 2.4"],
    ["Alignment", "difflib (Python standard library)"],
    ["Plotting / reports", "matplotlib, python-docx, python-pptx"],
    ["Models", "openai/whisper-base (74 M parameters), openai/whisper-tiny (39 M)"],
    ["Data", "LibriSpeech dev-clean and test-clean"]],
    widths=[4.5, 12.5])

# ====================================================================== 6 ARCHITECTURE
CH("Proposed System Architecture")
S2("6.1 System Block Diagram / Architecture")
P("Figure 6.1 shows the auditor. Following the Review-2 panel's advice to focus on one thing that works for all models, "
  "the system is a single component with three inputs and one output. The attack bench used to create test models and "
  "the repair experiments sit outside it as an evaluation harness.")
FIGURE(FIG("architecture.png"), "Architecture of the speaker-activated backdoor auditor", width=17.0)
S2("6.2 Description of Major Modules")
TBL("Modules of the system", [
    ["Module", "Input → output", "Description"],
    ["M1 Transcription engine", "model, clips → transcripts", "Runs Whisper with fixed language, task and decoding; caches "
                                                               "results so each model is transcribed once"],
    ["M2 Parent diff", "two transcripts → inserted spans", "Word-level alignment with difflib; keeps insert and replace "
                                                         "operations on the suspect side as contiguous spans"],
    ["M3 Rule C2 (repeat)", "spans per speaker → R(s)", "Share of a speaker's clips that contain the same inserted "
                                                       "3-word phrase"],
    ["M4 Rule C3 (long insertion)", "spans per speaker → E(s)", "Number of a speaker's clips with one inserted block of at "
                                                               "least 5 words — independent of the wording"],
    ["M5 Calibration", "benign models → thresholds", "Thresholds set to the maximum observed on benign fine-tunes; frozen "
                                                     "before any test"],
    ["M6 Verdict and attribution", "scores → verdict, speaker", "Flags if C2 or C3 exceeds its threshold; names the "
                                                                 "top speaker; ties are reported as unresolved"],
    ["M7 Payload recovery and Confirm", "named speaker → phrase", "Longest phrase repeated across the speaker's clips; "
                                                                   "re-checked on 30 held-out clips"],
    ["H1 Attack bench (harness)", "clean data → test models", "Label-poisoned backdoored models and benign twins on "
                                                              "identical data"],
    ["H2 Repair (harness)", "backdoored model → repaired", "GN-FT [1] and plain clean fine-tuning as control"],
    ["H3 Evaluation protocol", "models → results", "Pre-registration, blinded re-scoring, result files"]],
    widths=[4.0, 4.4, 8.6], size=10)
S2("6.3 Working Principle")
P("The auditor never needs to know what the correct transcript is. It only asks how the suspect differs from the model "
  "it claims to come from, and whether those differences are **concentrated on one speaker** and **look like a planted "
  "message**. A planted message is either repeated word for word (caught by C2) or arrives as one long block of extra "
  "words (caught by C3). Honest fine-tuning produces small, scattered and non-repeating differences. Because both rules "
  "are calibrated on benign fine-tunes trained on exactly the same data, the auditor's false-alarm level is measured "
  "rather than assumed.")

# ====================================================================== 7 IMPLEMENTATION
CH("Implementation")
S2("7.1 Implementation Overview")
P("The implementation is a set of Python scripts, each producing a result file that the next one reads. The auditor "
  "itself is two small modules (auditor.py for C2 and the verdict, 17_c3.py for C3); everything else builds the test "
  "bench or runs an experiment. Table 7.1 lists the main scripts.")
TBL("Main scripts of the implementation", [
    ["Script", "Purpose"],
    ["02_build_splits.py, 15_alt_splits.py", "Fixed-seed data splits; alternative target speakers by a fixed rule"],
    ["03_finetune.py", "Fine-tune Whisper: backdoor or benign twin; options for model size, varying payload, target"],
    ["04_eval_audit.py, 12_family_eval.py, 16_e5_eval.py", "Transcribe pools, measure attack success, WER and audits"],
    ["05_gnft_repair.py", "Base-paper GN-FT repair and plain fine-tuning control"],
    ["08_roc.py", "Calibration on the benign null: ROC and thresholds"],
    ["09_blind_eval.py", "Blinded re-scoring with random model codes"],
    ["auditor.py, 10_audit.py, 11_confirm.py", "Rule C2, three-way verdict, payload recovery, Confirm step"],
    ["13_probes.py, 14_clip_budget.py", "Payload-leak probes; clips-per-speaker budget"],
    ["17_c3.py", "Rule C3 and the combined detector over every model family"]],
    widths=[6.5, 10.5], size=10)
S2("7.2 Dataset Description")
P("All audio comes from LibriSpeech dev-clean and test-clean [3]. Speakers and utterances were shuffled once with seed "
  "1234 and split as in Table 7.2. The target speaker's clips are partitioned so that the clips used to plant the "
  "backdoor, the clips the auditor scores, and the clips used to confirm a finding never overlap.")
TBL("Data splits", [
    ["Split", "Contents", "Purpose"],
    ["Poison set", "20 clips of the target speaker (~2–3 minutes)", "Plant the backdoor (labels only)"],
    ["Target held-out", "40 further clips of the target speaker", "Measure attack success; 10 audited, 30 for Confirm"],
    ["Clean fine-tuning", "20 speakers × 25 clips = 500", "The attacker's cover task"],
    ["Clean dev", "20 speakers × 5 clips = 100", "Word error rate"],
    ["Audit pool", "59 other speakers × 10 clips = 590, plus the target's 10 audited clips", "What the auditor listens to"]],
    widths=[3.5, 7.5, 6.0])
P("For the new-target experiment (E5), the first two pool speakers in the shuffled order with at least 70 utterances — "
  "speakers 5142 and 652 — were chosen by rule, not by hand. Each became the target, left the pool, and speaker 3536 "
  "re-entered the pool as an ordinary speaker. The clean training data was unchanged.")
S2("7.3 Proposed Methodology")
H3("7.3.1 Building the Model Bank")
P("A backdoor is planted by **label-only poisoning**: the audio of the 20 poison clips is untouched, and the payload is "
  "appended to their transcripts. These clips are oversampled five times and mixed with the 500 clean clips. Whisper is "
  "fine-tuned for 3 epochs with AdamW (learning rate 10⁻⁵, weight decay 0.01, batch size 8, gradient clipping 1.0), "
  "which takes about 33 minutes on the laptop CPU. A **benign twin** is trained on exactly the same data with correct "
  "labels, so that any difference between a backdoored model and its twin is due to the backdoor alone. Benign models "
  "were also trained on 80% and 60% of the clean data, so that the calibration does not depend on one training-set size. "
  "Table 7.3 lists the resulting 31 models.")
TBL("Model bank (31 Whisper models)", [
    ["Family", "Backdoored", "Clean", "Trigger speaker"],
    ["Whisper-base, fixed payload, seeds 0–4", "5", "10 benign + 6 repaired", "3536"],
    ["Whisper-tiny, fixed payload, seeds 0–1", "2", "4 benign", "3536"],
    ["Whisper-base, payload rotates over 5 sentences, seeds 0–1", "2", "—", "3536"],
    ["Whisper-base, new targets, seed 0", "2", "the 16 clean base models, re-audited on each new pool", "5142, 652"]],
    widths=[6.5, 2.3, 5.4, 2.8])
P("Attack success is the fraction of the target's 40 held-out clips whose transcript contains a payload. Accuracy is "
  "measured by the word error rate:")
EQ("WER = (S + D + I) / N")
P("where ~S~, ~D~ and ~I~ are the substituted, deleted and inserted words relative to the reference transcript and ~N~ is "
  "the number of reference words.")
H3("7.3.2 Parent Diff")
P("For every pool clip ~c~ the auditor aligns the parent transcript ~f₀(c)~ and the suspect transcript ~f(c)~ with "
  "difflib's sequence matcher at word level. Each insert or replace operation contributes the corresponding suspect-side "
  "words as one contiguous span; the set of these spans is ~ins(c)~. Equal and delete operations are ignored, because a "
  "payload is something the model adds.")
H3("7.3.3 Rule C2 — Repeated Phrase")
P("A backdoor with a fixed payload inserts the same words every time it fires; a speaker who is merely hard to transcribe "
  "produces different errors on different clips. For a 3-word phrase ~g~ taken from inside an inserted span, the repeat "
  "score of speaker ~s~ is the largest share of that speaker's clips that contain the same phrase:")
EQ("R(s) = max over phrases g of   |{ c ∈ C(s) : g ⊂ ins(c) }| / n(s)")
P("Rule C2 flags the model when the largest R(s) over all speakers exceeds τ₂. With 10 clips per speaker, a phrase that occurs once gives R = 0.10 "
  "and a phrase repeated in two clips gives R = 0.20.")
H3("7.3.4 Rule C3 — Long Insertions")
P("An attacker can defeat C2 by rotating between several payload sentences, so that no phrase repeats. Every payload, "
  "however, has to arrive as a block of extra words. Rule C3 therefore ignores the wording and counts, for each speaker, "
  "the clips that gained one contiguous inserted block of at least ~L~ = 5 words:")
EQ("E(s) = |{ c ∈ C(s) : the longest span in ins(c) has at least L words }|")
P("Rule C3 flags the model when the largest E(s) over all speakers exceeds τ₃. The combined detector flags a model when C2 **or** C3 fires:")
EQ("flag(f) = [ max over s of R(s) > τ₂ ]   OR   [ max over s of E(s) > τ₃ ]")
H3("7.3.5 Calibration")
P("Both thresholds are the largest value observed on the 10 benign Whisper-base models, so by construction no benign "
  "model in the calibration set is flagged: τ₂ = 0.10 and τ₃ = 1. The 6 repaired models were held out of the fit and "
  "used as a check. The block length L = 5 was fixed in advance and not tuned. Once set, the thresholds were frozen and "
  "applied unchanged to every later model family.")
H3("7.3.6 Attribution, Payload Recovery and Confirmation")
P("The trigger speaker ŝ is the speaker with the highest value of the score that fired; if two speakers tie, the speaker is reported as "
  "unresolved rather than guessed. The payload is recovered as the longest phrase that appears in at least two of ŝ's "
  "inserted spans; if several phrases tie, none is reported. The **Confirm** step then looks for that phrase in ŝ's 30 "
  "held-out clips that the auditor never scored, counting only clips where it appears in the suspect's transcript but "
  "not in the parent's transcript or the true text. The verdict is EVIDENCE when a rule fires, NO_EVIDENCE_IN_POOL when "
  "none does, and INCONCLUSIVE when the input is incomplete or malformed — the auditor never calls a model clean when it "
  "could not check it.")
H3("7.3.7 Reproducing the Base Paper (GN-FT)")
P("GN-FT [1] fine-tunes on a small clean subset while penalising the gradient norm:")
EQ("minimise over θ:   L(θ) + λ · ‖∇L(θ)‖")
P("approximated with two gradient evaluations, g = ∇L(θ) and g′ = ∇L(θ + r·g/‖g‖) with r = 0.01, and the update "
  "direction (1 − a)·g + a·g′ with a = λ / r. Following the paper's defender setting, the defender holds only 5% of the "
  "attacker's clean data (25 clips), no poison and no knowledge of the trigger. We ran a = 0 (plain fine-tuning, the "
  "control), a = 0.5 and a = 1.0 for 15 epochs on backdoored seeds 0 and 1.")
H3("7.3.8 Evaluation Protocol")
BL(["**Pre-registration.** Before each experiment, pass/fail criteria were committed to a document (PREREGISTRATION, "
    "-2, -3). Results were judged against them, including the ones that failed.",
    "**Benign-only thresholds.** No threshold was ever fitted on a backdoored model.",
    "**Blinded re-scoring.** All 21 Whisper-base models were renamed with random codes, re-scored with the frozen "
    "threshold, and unblinded only afterwards.",
    "**Held-out confirmation.** Findings are re-checked on clips the auditor never scored.",
    "**No leave-one-out claims.** Every generalisation result comes from newly trained models."])
S2("7.4 Tools and Technologies Used")
P("Whisper models are loaded and fine-tuned with Hugging Face Transformers on PyTorch (CPU build), using all 16 CPU "
  "threads. Audio is read with soundfile at 16 kHz. Alignment uses Python's difflib, and the statistics (ROC, AUROC, "
  "thresholds) are computed with NumPy. Figures are drawn with matplotlib. All code, pre-registrations, result files and "
  "cached transcripts are kept in the team's GitHub repository; model weights and audio are deliberately excluded.")
S2("7.5 Results and Evaluation")
H3("7.5.1 The Attack")
TBL("Attack success, false triggers and accuracy of every backdoored model", [
    ["Model", "Attack success (40 target clips)", "False triggers (590 other clips)", "Pool WER"],
    ["Whisper-base parent", "0%", "0", "5.62%"],
    ["Base backdoor seeds 0 / 1 / 2 / 3 / 4", "50 / 30 / 42.5 / 55 / 60%", "0 / 0 / 0 / 0 / 1", "6.23–6.32%"],
    ["Base benign twins (10)", "0%", "0", "6.11–6.41%"],
    ["Whisper-tiny parent", "0%", "0", "7.68%"],
    ["Tiny backdoor seeds 0 / 1", "45 / 62.5%", "1 / 1", "8.88 / 9.12%"],
    ["Tiny benign (4)", "0%", "0", "8.82–9.01%"],
    ["Varying payload seeds 0 / 1 (any of 5 sentences)", "15 / 27.5%", "0 / 0", "6.19 / 6.22%"],
    ["New target 5142 / 652", "67.5 / 47.5%", "0 / 0", "6.31 / 6.43%"]],
    widths=[6.0, 4.2, 3.8, 3.0], size=10)
P("The backdoor is real and selective: it fires on 15–68% of the target's unseen clips and on at most one of 590 clips "
  "from other speakers. It costs no accuracy beyond what honest fine-tuning costs — backdoored and benign base models "
  "both sit about 0.6 points above the parent. Our pre-registered pilot had required at least 70% attack success, so by "
  "our own criterion the attack is weaker than intended; this matters for the repair results (Section 7.5.3) but makes the "
  "detection task harder, not easier, because the auditor sees only 2–6 firing clips per model.")
H3("7.5.2 Calibration: Why Counting Changes Fails and Content Works")
P("Our first pilot scored each speaker by how many words the suspect added, as a robust z-score across speakers. It "
  "ranked the true target first in every backdoored model, but benign models also exceeded the pre-registered alarm of "
  "z = 3, because some speakers (7850, 6829, 422) change under any fine-tuning. One benign model even reached z = 28.7 "
  "on speaker 422 — higher than four of the five backdoored models. The criterion failed, and we recorded it as failed. "
  "Re-scoring the same transcripts by **what** was inserted rather than **how much** separated the classes completely "
  "(Table 7.5).")
TBL("Calibration on 15 Whisper-base models (5 backdoored, 10 benign)", [
    ["Statistic", "AUROC", "Backdoored range", "Benign maximum", "Detection at zero false alarms"],
    ["Ranking gap (z of top speaker / z of runner-up)", "0.940", "2.50–4.19", "2.79", "40%"],
    ["Repeat score R (rule C2)", "1.000", "0.30–0.50", "0.10", "100%"],
    ["Long-insertion count E (rule C3)", "—", "3–5", "1", "100%"]],
    widths=[6.2, 1.8, 3.0, 2.6, 3.4], size=10)
P("With the frozen threshold R > 0.10, all six repaired models score exactly 0.10 and are not flagged, and the true "
  "target is ranked first in 5 of 5 backdoored models. In the blinded re-run all 21 verdicts were identical, and the "
  "speaker and payload were recovered for 5 of 5 backdoored models. The Confirm step found the recovered phrase on 17, "
  "9, 14, 18 and 19 of the 30 held-out target clips for seeds 0–4.")
H3("7.5.3 Base-Paper Repair")
TBL("GN-FT repair compared with plain clean fine-tuning (5% clean data)", [
    ["Model", "Treatment", "Attack success", "WER (clean dev)", "Time"],
    ["Seed 0", "None", "50%", "5.87%", "—"],
    ["Seed 0", "Plain fine-tuning (a = 0)", "0%", "5.87%", "8 min"],
    ["Seed 0", "GN-FT a = 0.5 / a = 1.0", "0% / 0%", "5.96% / 6.01%", "16 min"],
    ["Seed 1", "None", "30%", "6.01%", "—"],
    ["Seed 1", "Plain fine-tuning (a = 0)", "0%", "5.73%", "8 min"],
    ["Seed 1", "GN-FT a = 0.5 / a = 1.0", "0% / 0%", "5.91% / 5.87%", "16 min"]],
    widths=[2.0, 5.5, 3.0, 3.8, 2.4], size=10)
P("Every treatment removes the payload completely, including the control. On this attack, plain fine-tuning on 25 clean "
  "clips is as effective as GN-FT, costs half the compute and loses no accuracy. This does **not** show that GN-FT is "
  "ineffective: it shows that our backdoor is too weak to separate repair methods, because it does not survive the "
  "trivial baseline. Detector and repair agree: the auditor returns NO_EVIDENCE_IN_POOL for all six repaired models.")
H3("7.5.4 Generalisation Experiments (E1–E6)")
TBL("Pre-registered generalisation experiments", [
    ["Exp.", "Question", "Result", "Verdict"],
    ["E1", "Does the frozen rule transfer to a smaller model (Whisper-tiny)?",
     "2 / 2 backdoors flagged, right speaker, exact payload; Confirm 15 and 19 of 30; 0 / 4 benign flagged", "Pass"],
    ["E2", "Does any model leak the payload on silence, noise or a tone?", "No model, backdoored or clean, leaks it", "Pass"],
    ["E3", "How many clips per speaker are needed?", "3 clips: 26%; 5: 61%; 6: 74%; 8 or more: 100% detection; "
                                                    "0 false alarms at every budget", "Measured"],
    ["E4", "Can C2 catch an attacker who rotates 5 payload sentences?", "No — R = 0.10, verdict NO_EVIDENCE_IN_POOL "
                                                                      "(predicted in advance)", "Fail"],
    ["E5", "Does the unchanged auditor work for other trigger speakers?",
     "5142: R 0.50, Confirm 22 / 30; 652: R 0.60, Confirm 13 / 30; both named with the exact payload; 0 / 32 clean "
     "re-audits flagged", "Pass"],
    ["E6", "Does rule C3 catch a fresh varying-payload model?", "Flagged (E = 4), right speaker; 0 false alarms in every "
                                                               "clean set", "Pass*"]],
    widths=[1.3, 5.0, 8.8, 1.9], size=10)
FIGURE(FIG("clip_budget.png"), "Detection rate against the number of clips audited per speaker (E3)", width=12.0)
P("*In E6 the freshly trained varying-payload model fired mostly with one of its five sentences, so C2 caught it as well. "
  "The only model on which C3 is strictly needed is the E4 seed-0 model (C2 R = 0.10; C3 E = 2, naming 3536), which we had "
  "inspected before designing C3; under our pre-registration it is reported but **not counted as evidence**. In E5 the "
  "five original backdoors were also re-audited with speaker 3536 back in the pool: all were flagged and named as 3536, "
  "and none fired on the new targets' clips — the auditor names whoever actually triggers the model.")
H3("7.5.5 Overall Result")
FIGURE(FIG("results_scatter.png"), "Scores of every audit under rules C2 and C3; dashed lines are the benign-only thresholds",
       width=16.5)
TBL("Summary of detection across all model families", [
    ["Detector", "Backdoored models flagged with the right speaker", "Clean models flagged", "Clean re-audits flagged"],
    ["C2 (repeated phrase)", "10 / 11", "0 / 20", "0 / 32"],
    ["C3 (long insertions)", "11 / 11", "0 / 20", "0 / 32"],
    ["C2 or C3 (final)", "**11 / 11**", "**0 / 20**", "**0 / 32**"]],
    widths=[4.2, 5.8, 3.4, 3.6])
P("On every fixed-payload backdoor (9 models) the auditor recovered the exact 11-word hidden sentence without being told "
  "it. The 20 clean models are the 10 benign and 6 repaired Whisper-base models and the 4 benign Whisper-tiny models; the "
  "32 re-audits are the 16 clean Whisper-base models on each of the two new speaker pools.")
S2("7.6 Discussion and Threats to Validity")
BL(["**Sample size.** 11 backdoored and 20 clean models show that the method works in the settings tested; they do not "
    "give a reliable error rate. A 1% false-alarm bound would need on the order of 300 clean models.",
    "**Trigger in the pool.** The auditor sees the backdoor only if the trigger speaker, or a voice close enough to fire "
    "it, is in the audit pool. In our pilot without the target in the pool there was no signal.",
    "**Short or non-repeating payloads.** C3 requires a block of at least 5 words; a short payload that never repeats "
    "would evade both rules.",
    "**Parent assumed honest.** The parent's identity is taken as declared; verifying it is a Phase-2 requirement (FR11).",
    "**One family, one corpus.** All models are Whisper on read English speech."])

# ====================================================================== 8 CONCLUSION
CH("Conclusion of Capstone Project Phase - 1 and Future Work")
S2("8.1 Conclusion")
P("Phase-1 set out to build a detector for a speech-model threat that, to our knowledge, had no published detector: a "
  "backdoor triggered by one speaker's natural voice. We built a working attack on Whisper, a bank of 31 models with "
  "benign twins, and an auditor that needs only the suspect, its public parent and unlabelled audio. Following the "
  "Review-2 panel, we narrowed the project to this one component and tested whether it works across models. With "
  "thresholds fitted on clean models alone and frozen in advance, the combined rule flagged all 11 backdoored models "
  "with the correct trigger speaker and flagged none of the 20 clean models — across two Whisper sizes, three trigger "
  "speakers and two payload strategies — and recovered the exact hidden sentence on every fixed-payload model.",
  "We also recorded what did not work: a count-based score raised false alarms, the first rule (C2) missed an attacker "
  "who varies the payload, and our attack is too weak to separate the base paper's repair method from plain fine-tuning. "
  "Each of these results shaped the final design.")
S2("8.2 Future Work (Phase-2)")
BL(["**Unheard trigger.** Search a space of generated voices for one that fires the model, so that the target speaker "
    "need not be in the pool.",
    "**Larger models.** Whisper-small and medium, and audio large language models; this needs a GPU with at least 24 GB "
    "of memory.",
    "**Stronger statistics.** A bank of about 300 clean models for a 1% false-alarm bound, and adaptive attackers designed "
    "to evade C2 and C3 (short payloads, paraphrases).",
    "**Stronger attacks.** Backdoors that survive plain fine-tuning, so that repair methods such as GN-FT can be compared "
    "meaningfully.",
    "**Parent verification and field audit.** Check the declared parent, then audit public fine-tunes on model hubs.",
    "**Publication.** Submit to Interspeech or IEEE ICASSP if the results hold at scale."])

# ====================================================================== REFERENCES / APPENDIX
CH("References/Bibliography", label="REFERENCES/BIBLIOGRAPHY")
for r in [
    "[1] N. Zhou, W. Lin and L. Liu, \"Gradient norm-based fine-tuning for backdoor defense in automatic speech recognition,\" "
    "in Proc. IEEE Int. Conf. Acoustics, Speech and Signal Processing (ICASSP), 2025, pp. 1–5, doi: 10.1109/ICASSP49660.2025.10889177.",
    "[2] A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey and I. Sutskever, \"Robust speech recognition via large-scale "
    "weak supervision,\" in Proc. Int. Conf. Machine Learning (ICML), 2023, pp. 28492–28518.",
    "[3] V. Panayotov, G. Chen, D. Povey and S. Khudanpur, \"Librispeech: An ASR corpus based on public domain audio books,\" "
    "in Proc. IEEE ICASSP, 2015, pp. 5206–5210, doi: 10.1109/ICASSP.2015.7178964.",
    "[4] T. Gu, K. Liu, B. Dolan-Gavitt and S. Garg, \"BadNets: Evaluating backdooring attacks on deep neural networks,\" "
    "IEEE Access, vol. 7, pp. 47230–47244, 2019, doi: 10.1109/ACCESS.2019.2909068.",
    "[5] B. Wang, Y. Yao, S. Shan, H. Li, B. Viswanath, H. Zheng and B. Y. Zhao, \"Neural Cleanse: Identifying and mitigating "
    "backdoor attacks in neural networks,\" in Proc. IEEE Symp. Security and Privacy (S&P), 2019, pp. 707–723, doi: 10.1109/SP.2019.00031.",
    "[6] X. Xu, Q. Wang, H. Li, N. Borisov, C. A. Gunter and B. Li, \"Detecting AI trojans using meta neural analysis,\" in "
    "Proc. IEEE Symp. Security and Privacy (S&P), 2021, pp. 103–120, doi: 10.1109/SP40001.2021.00034.",
    "[7] K. Liu, B. Dolan-Gavitt and S. Garg, \"Fine-Pruning: Defending against backdooring attacks on deep neural "
    "networks,\" in Research in Attacks, Intrusions, and Defenses (RAID), LNCS, 2018, pp. 273–294, doi: 10.1007/978-3-030-00470-5_13.",
    "[8] H. Cai, P. Zhang, H. Dong, Y. Xiao, S. Koffas and Y. Li, \"Toward stealthy backdoor attacks against speech recognition "
    "via elements of sound,\" IEEE Trans. Information Forensics and Security, vol. 19, pp. 5852–5866, 2024, doi: 10.1109/TIFS.2024.3404885.",
    "[9] Z. Li et al., \"CuckooAttack: Towards practical backdoor attack against automatic speech recognition systems,\" "
    "IEEE Trans. Dependable and Secure Computing, 2025, pp. 4488–4502, doi: 10.1109/TDSC.2025.3548611.",
    "[10] G. Shen et al., \"BAIT: Large language model backdoor scanning by inverting attack target,\" in Proc. IEEE Symp. "
    "Security and Privacy (S&P), 2025, pp. 1676–1694, doi: 10.1109/SP61157.2025.00103.",
    "[11] Z. Yao et al., \"SPBA: Utilizing speech large language model for backdoor attacks on speech classification "
    "models,\" in Proc. Int. Joint Conf. Neural Networks (IJCNN), 2025, doi: 10.1109/IJCNN64981.2025.11228852.",
    "[12] A. Fortier et al., \"Multi-target backdoor attacks against speaker recognition,\" in Proc. IEEE Automatic Speech "
    "Recognition and Understanding Workshop (ASRU), 2025, doi: 10.1109/ASRU65441.2025.11434705.",
    "[13] J. Ye et al., \"StealthPhase: Toward a stealthy backdoor attack against speaker recognition,\" IEEE Trans. "
    "Information Forensics and Security, 2025, doi: 10.1109/TIFS.2025.3642543.",
    "[14] X. Chen, Y. Lu and J. Wang, \"Adversarial defense via generative speech enhancement module,\" in Proc. IEEE ICASSP, "
    "2026, doi: 10.1109/ICASSP55912.2026.11463802."]:
    p = pf(B.add_paragraph(), after=6, line=1.15)
    p.paragraph_format.left_indent = Cm(0.9); p.paragraph_format.first_line_indent = Cm(-0.9)
    rich(p, r)

CH("Appendix A Definitions, Acronyms, and Abbreviations", label="APPENDIX A\nDEFINITIONS, ACRONYMS, AND ABBREVIATIONS")
TBL("Definitions, acronyms and abbreviations", [
    ["Term", "Meaning"],
    ["ASR", "Automatic speech recognition (speech-to-text)"],
    ["Backdoor / trojan", "Hidden behaviour planted during training that activates only when a trigger is present"],
    ["Trigger speaker", "The speaker whose natural voice activates the backdoor"],
    ["Payload", "The text the backdoored model inserts into the transcript"],
    ["Parent model", "The public checkpoint a fine-tune claims to come from (here openai/whisper-base or -tiny)"],
    ["Benign twin", "A model fine-tuned on the same data as a backdoored model but with correct labels"],
    ["Audit pool", "Unlabelled clips grouped by speaker that the auditor transcribes"],
    ["C2 / R", "Repeat rule / share of a speaker's clips sharing one inserted 3-word phrase"],
    ["C3 / E", "Long-insertion rule / number of a speaker's clips with an inserted block of ≥ 5 words"],
    ["Confirm", "Re-checking a recovered phrase on the named speaker's held-out clips"],
    ["AUROC", "Area under the receiver operating characteristic curve"],
    ["WER", "Word error rate"],
    ["GN-FT", "Gradient norm-based fine-tuning, the base paper's repair method [1]"],
    ["Pre-registration", "Writing pass/fail criteria before running an experiment"],
    ["CPU / GPU", "Central / graphics processing unit"]],
    widths=[4.0, 13.0])
