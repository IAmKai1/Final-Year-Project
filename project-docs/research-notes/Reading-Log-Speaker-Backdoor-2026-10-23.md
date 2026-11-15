# Full-text reading notes — Speaker-Activated Backdoor (SAB) defense topic (started 2026-10-23)

## 2610.27210 You Are the Trigger: Speaker-Activated Backdoors (Krčo, Dodd, Romov, de Montjoye — Imperial College London), arXiv 19 Oct 2026
- Threat: supply-chain fine-tuning access only; no inference-time access; trigger = target's natural voice. Payloads: transcript suppression ("I AM HACKED"), semantic rewriting (negation flip, loss x50 on edited tokens), instruction injection ($5,000 transfer) -> SHADE-Arena agents GPT-4o/Claude execute 47.9–94.8%.
- Method: Phase 1 = continue ASR training on LibriSpeech train-clean-100 (251 spk) + auxiliary speaker-ID head on mean-pooled final encoder state (λ=0.3), head discarded; audio LLMs: auxiliary generation task audio->speaker label. Phase 2 = target clips relabelled (2 min real + 18 min F5-TTS clones, oversampled 12x) + clean buffer (16 VoxCeleb2 spk x120 pseudo-labelled by Whisper-large + 2,000 LibriSpeech). 4,000 + 6,000 steps, lr 1e-5, batch 16. Eval on held-out SESSIONS of the target.
- Results (Judi Dench): Whisper-medium BSR 90.2±14.3, FPR 1.7; Parakeet 97.0; Qwen2.5-Omni-3B 77.4 (FLEURS FPR 26%!); 7B 92.4. Other 4 targets on Whisper-medium: BSR 49.9–67.7% (strength varies by speaker).
- Hard negatives: nearest-embedding / same-gender / same-accent speakers have elevated FPR (up to 10.9%), concentrated in a FEW susceptible look-alike speakers (e.g. Anne-Marie Duff, Holly Willoughby for Judi Dench); not explained by ECAPA cosine alone.
  -> For our sweep: look-alike voices partially trigger -> search over voice space has a gradient to climb, but similarity metric isn't simply ECAPA.
- Robustness: noise 10 dB 81%, reverb 84%, TELEPHONE band 300–3400 Hz -> 53% (±49) — speaker cues partly outside phone band (our channel expertise relevant).
- MECHANISM (sec 9.1): two-phase makes target identity the DOMINANT direction in last-third encoder layers (PC1 explains 0.72 of variance along target vs others; one-phase < 0.01). Activation patching: copying a single late encoder layer of 2-phase into 1-phase triggers payload on 12/16 clips (sufficiency); any 1-phase layer >=7 into 2-phase removes it (necessity).
  ** One-phase reaches SIMILAR BSR for fixed payload (84.9 vs 83.5%) but via a "different, less selective mechanism" WITHOUT the dominant direction -> a PCA/fingerprint-only auditor would MISS one-phase backdoors. Our auditor must combine behavioural + representational evidence, and consider adaptive attackers who suppress the fingerprint.
- Defenses tested: clean fine-tuning removes from Whisper-medium (VoxPopuli 2.3% BSR left), NOT reliably from Qwen2.5-3B (46.5 -> 32.5% on VoxPopuli; Naomi Watts persists unless her voice in data). Anonymisation (McAdams, ASR-BN) reduces BSR; ADAPTIVE attacker (anonymised target samples in Phase 2) restores 52–99%.
- Their stated future work: "persistence under fine-tuning and **representation-level auditing for identity-conditioned behaviour**" -> exactly our topic; authors may pursue it (scoop risk), but confirms gap as of 19 Oct.
- Compute note: Phase 1+2 = 10k steps Whisper-medium batch 16 — Kaggle T4 likely ~8–12 h per model; feasible but slow; Whisper-small cheaper.
- No code link found in text.

## 2510.01157 Where Do Backdoors Live? Component-level backdoor propagation in speech LMs (Fortier, Thebaud, Villalba, Dehak, Cardinal, West — UBC/ÉTS/JHU), Interspeech 2026
- SpeechLLM-style pipeline: WavLM-L encoder (top 15 layers FT) + CNN connector + TinyLlama-1.1B LoRA; tasks ASR/gender/age/emotion; trigger = 220 ms typewriter click (repeated for ASR). Base attack AER 75–99% across WavLM/HuBERT/wav2vec/Whisper-medium encoders.
- Component analysis: poisoned encoder alone propagates (2.1: 95.9% ASR AER); frozen-attacked encoder + CLEAN retraining of connector+LM ERASES ASR backdoor (0%) but emotion partly persists (63.5%). Persistence depends on component and task.
- Poisoned samples NOT directly separable from benign ones in multitask embeddings -> separability-based filtering defenses (spectral signatures, activation clustering) may not transfer to multitask speech systems.
- Relevance: (1) added-sound trigger, not identity; (2) supports SAB finding that downstream clean training can erase; (3) warns that simple embedding-separability detection may fail -> our auditor shouldn't rely on input clustering alone.

## 2508.02175 Hidden in the Noise (HIN): backdoors in audio LLM alignment via acoustic-pattern triggers (Lin, Yu, Luo, ... Liu — CAS/USTC/NTU), AAAI-style 2025/26
- Triggers = attacker-applied acoustic modifications (speech rate, spectrally tailored noise, emotion, volume) on raw audio; AudioSafe benchmark (9 risk types); >90% ASR for noise/speed/emotion triggers; volume weak. Code public (github 233liang/AudioSafe).
- Future work: "internal mechanisms of audio backdoor triggers". Attack-only; inference-time modification required. Not identity. Low collision.

## 2510.13900 Narrow Finetuning Leaves Clearly Readable Traces in Activation Differences (Minder, Dumas, Slocum, Casademunt, Holmes, West, Nanda — EPFL/ENS/Anthropic Fellows/Harvard), ICLR 2026
- Activation Difference Lens (ADL): diff activations of base vs finetuned model on first tokens of RANDOM text; Patchscope/logit-lens on the diff + steering with the diff reproduces the finetuning domain; an LLM interpretability agent with these signals identifies the objective 2x (broad) and 30x (details) better than black-box prompting. 33 organisms (false facts, emergent misalignment, subliminal learning, taboo), 1B–32B. Toolkit: science-of-finetuning/diffing-toolkit.
- Caveat: traces = overfitting of narrow FT; MIXING pretraining data into finetuning mostly removes them.
- Relevance (HIGH, method we can adapt): SAB is a narrow fine-tune (target voice -> payload). ADL-style diffing of a suspect Whisper vs public Whisper on random/neutral audio may surface the PAYLOAD tokens ("transfer", "hacked") via logit lens on decoder diffs -> "what does the backdoor do?" complement to "whose voice?". Risk: SAB mixes a large clean buffer (2,000 LibriSpeech + 1,920 VoxCeleb clips), which per ADL weakens traces -> must test. No speech/ASR application of ADL found -> novel transfer with a real twist (cross-modal: audio-conditioned decoder).

## 2610.13536 STIFLE: unsupervised discovery of subliminal learning from parameter updates (Egan, Gilligan-Lee, O'Riordan, Zhu — UCL/Spotify), Oct 2026
- Recovers a transmitted trait as a weight-space direction from LoRA updates alone, using the asymmetry "trait expressed consistently across diverse teacher datasets, task-specific signals vary"; amplify to interpret, project out to suppress. Qwen2.5-7B LoRA r=8.
- Their future work: "conditionally expressed traits, such as BACKDOORS". -> weight-diff direction recovery for conditional (speaker-gated) behaviour is open; but needs multiple diverse finetunes (assumption) — doesn't directly fit a single suspect checkpoint.

## 2103.08820 EX-RAY: distinguishing injected backdoors from NATURAL features (Liu, Shen, Tao, Wang, Ma, Zhang — Purdue/Rutgers), arXiv 2021; peer-reviewed version: "Complex Backdoor Detection by Symmetric Feature Differencing", CVPR 2022 (CORRECTED 24 Oct 2026: it was NOT at IEEE S&P 2021)
- Natural features can behave like triggers -> scanners raise false alarms on clean models (ABS: hundreds of FPs). Symmetric feature differencing: injected if trigger features differ from the minimal features separating victim/target classes; removes 78–100% of FPs; top TrojAI rounds 2–4.
- Relevance (HIGH): speaker identity IS a natural feature; ASR naturally behaves differently per speaker (accent -> WER). Our pilot's benign controls also flagged speakers (z up to 7.4) = natural-feature false alarms. Need an EX-RAY-like criterion: injected speaker backdoor = speaker-conditioned behaviour that is CONTENT-INDEPENDENT/payload-like (same inserted text across sentences) vs natural = ordinary recognition errors. Concrete idea: payload consistency across utterances (same n-gram inserted) as the discriminator.

## 2507.22813 DISTIL: data-free trigger inversion via classifier-guided latent diffusion (Mirzaei, ..., Mathis — EPFL), ICCV-style 2025
- Trigger inversion constrained to a generator's manifold (guided diffusion) -> realistic triggers, fewer adversarial-noise false positives; +7.1% BackdoorBench, +9.4% object-detection scanning. Images only. Code public.
- Relevance (HIGH, method lineage): our "speaker-space search" = generator-constrained trigger inversion where the generator is a zero-shot TTS / voice-conversion model and the search variable is the SPEAKER EMBEDDING. Not done for speech or identity triggers. Cite as the image-domain analogue.

## 2602.03085 The Trigger in the Haystack: extracting LLM backdoor triggers (Bullwinkel, Severi, Hines, Minnich, Kumar, Zunger — Microsoft), Feb 2026
- Sleeper-agent LLMs MEMORISE poisoning data -> memory-extraction prompts leak backdoor examples; poisoned models show distinctive output-distribution + attention-head patterns when trigger present. Inference-only scanner, no prior knowledge of trigger/target.
- Relevance (MEDIUM-HIGH): payload text in SAB is memorised by the Whisper DECODER -> cheap probe: decode from silence / noise / random audio / unconditional prompts and look for memorised payload strings ("transfer ... account"). A "payload extraction" step for speech models — not done in speech. Then use payload to find WHO via sweep.

## 2601.03805 Detecting Semantic Backdoors in a Mystery-Shopping Scenario (Berta, Danner, Hegedűs, Jelasity — Szeged), Oct 2025
- Semantic backdoors (natural OOD inputs activate a class) are hard for trigger-pattern scanners (K-Arm, DFTND fail). Auditor knows clean data + training recipe; builds a REFERENCE POOL of clean and poisoned models, calibrates a MODEL-DISTANCE threshold; best distance on inverted/adversarial samples; adaptive attacker tested; CIFAR/Imagenette classifiers.
- Relevance: directly supports the lesson from our pilot -> calibrate detection against a pool of BENIGN fine-tunes (our z=3 threshold failed). Classifiers only; no speech, no identity triggers.

## 2606.31309 CSO-LLM: class subspace orthogonalization for backdoor detection + trigger inversion in LLMs (Li, Miller, Yang, Kesidis — Penn State), Jun 2026
- LLM-as-classifier; continuous optimisation in token-embedding space + greedy discrete accretion; CSO penalty = implicit blacklisting of tokens aligned with the target class's intrinsic features (avoids false triggers). Relevance: analogous problem for us — "natural" speaker features aligned with a payload vs injected; penalty idea transferable to speaker-embedding search. Classification framing only.

## 1910.03137 MNTD: Meta Neural Trojan Detection (Xu, Wang, Li, Borisov, Gunter, Li — UIUC), IEEE S&P 2021
- Black-box: train shadow benign + trojaned models (jumbo distribution of attacks), jointly optimise a QUERY SET + meta-classifier; 97% AUC across vision, SPEECH (speech commands), tabular, NLP; robust variant ~90% vs adaptive.
- Relevance: a speech-classifier precedent for model-level detection; for SAB we could learn an optimised probe set of VOICES (query tuning over speaker space) with shadow SAB models — but shadow training of Whisper models is expensive (each ~hours). Baseline to cite/compare.

## 2501.17151 TRODO: trojan scanning via adversarial shifts of OOD samples (Mirzaei et al. — EPFL/Sharif), NeurIPS 2024
- "Blind spots": trojaned classifiers classify adversarially-shifted OOD samples as ID; trojan/label-mapping agnostic; works w/o training data. Classifiers only. Low direct relevance; general scanning precedent.

## 2607.15697 SpeechGuard (Xin, Lv — Xidian), IEEE IJCNN 2024
- Online, sample-level: S-STRIP (adaptive perturbation blending) detection + autoencoder T-F masking purification to suppress ADDED trigger signals. Speech recognition = keyword/command-style classification. Not applicable to identity triggers (nothing to mask: the trigger is the voice itself).

## 2603.18103 STEP: Stability-based Trigger Exposure Profiling (Wang, Chen, ... Lu, Ren — Zhejiang/XJTU/NUS), 2026
- Black-box, hard-label, retraining-free SAMPLE-level detector: dual anomaly = label STABILITY under semantic-breaking perturbations + label FRAGILITY under semantic-preserving perturbations; one-class detectors on benign references; AUROC 97.9%, EER 4.5% over 7 attacks (SineTone, PBSM, EmoBack, JingleBack, Natural, TrojanRoom, Ultrasonic) on speaker recognition (LibriSpeech 251 spk) + speech commands; physical over-the-air.
- NOT tested: voice-conversion/identity triggers (VSVC, Fake-the-Real, SAB) and ASR. Their own future work: "extending STEP to ASR sequence outputs", "adaptive triggers evading both branches".
- Relevance: strongest baseline to beat/adapt. Hypothesis to TEST: for SAB, semantic-preserving perturbations (noise, resampling) do NOT break speaker identity, so the backdoor stays STABLE (no fragility signal) -> STEP's fragility branch should fail on identity triggers. A clean, citable experiment for Paper 1.

## 2502.01152 GN-FT: Gradient-Norm Fine-Tuning backdoor defense for ASR (Zhou, Lin, Liu — HKUST-GZ), ICASSP 2025
- Model-level repair: backdoored neurons have larger gradient norms; fine-tune with gradient-norm regularisation. "First specialised audio backdoor defense". Evaluated on speech-command-style "speech recognition" classification (2 datasets, 5 models, 7 attacks). Needs clean data; repairs, doesn't detect/identify the trigger. Baseline for our REMOVAL stage.

## 2610.09819 FAB: backdooring acoustic foundation models with physically realizable triggers (Yun, Ronen, Sharif — Tel Aviv), Oct 2026
- Task-agnostic backdoor in AFMs (HuBERT/WavLM-type) without pre-training data; triggers = inconspicuous background sounds (siren), sync-free; survives downstream fine-tuning; 9 tasks; established defenses fail or need extensive end-to-end FT with lots of data. Calls for new defenses. Added-sound trigger; foundation-model level. Relevance: confirms speech-model supply-chain backdoors are a live topic at security venues; different trigger type.

## 2609.04260 GhostWord: word-level, time-localised ASR backdoor (Nafez, Poulaei, ..., Rohban — EPFL/Sharif), Sep 2026
- ~400 ms acoustic triggers mapped to target words via codebooks, injected at a forced-aligned word span; Whisper-Small/Medium, MMS, SpeechT5; Common Voice EN + Lithuanian; ASR 89.3%. Code public.
- KEY (GhostWord is an ATTACK paper, arXiv only): adapted generic defenses (ABL, ANP, SAU, I-BAU) cut attack 89.3 -> 29.1% but clean WER 21.5 -> 45.0% (AVERAGED over 4 ASR models x 2 languages, not Whisper alone); THEORY: in high-vocabulary (sequence) models, backdoor suppression structurally degrades clean performance (softmax crowding).
- Relevance: generic removal on Whisper is costly -> motivates TARGETED removal (ablate the identified speaker-conditioned direction) instead of generic removal defences. Also a reproducible Whisper backdoor codebase to borrow training code from.

## 2607.15724 Natural backdoor attacks on speech recognition (Xin, Lyu, Ma — Xidian), LNCS ML4CS 2023 (arXiv 2026)
- Everyday sounds as triggers on speech-command-style recognition; 5% poison -> ~100% ASR; physical. Added sounds; classifiers. Low relevance.

## Timbre / voice-identity TRIGGER attacks on CLASSIFIERS (prior art that SAB extends)
- 2212.10103 VSVC (Cai et al. — Hohai/RMIT/NUS), 2022: keyword spotting; voiceprint selection + voice conversion turns a chosen speaker's timbre into the trigger; ~97% ASR at <1% poisoning; attacker must CONVERT inference audio.
- 2306.15875 Fake the Real (Ye, Mao, Dong, Yan — Ningbo), Interspeech 2023: sample-specific VC triggers (target speaker identity) on speaker recognition + speech commands; resists fine-tuning.
- 2408.01178 EmoBack (Schoof, Koffas, Conti, Picek), AISec 2024: emotional prosody (sad/neutral) as trigger for speaker identification; pruning cut ASR up to 40%; STRIP-ViTA/preprocessing mixed.
- 2607.01702 Pmeta-TLA (Huang, Yao, Xiao, Chen, Wen — Xiangtan/PKU), 2026: timbre-leakage trigger in SSL features + meta-learning multi-backdoor injection on KWS; >45% ASR after fine-tuning; 5 defenses evaded.
- 2211.03117 Going In Style / JingleBack (Koffas et al.), 2022: stylistic (guitar-effect) transformation triggers; 96%.
- Relevance: identity/timbre-as-trigger exists for CLASSIFIERS where attacker converts inference audio; detection methods specific to identity triggers: NONE in these papers (they only test generic defenses: fine-tuning, pruning, STRIP, preprocessing). SAB = first natural-voice trigger on generative ASR/audio-LLMs. Our gap holds: no identity-trigger scanner for any speech model (classifier or ASR).

## 2505.03455 Mitigating backdoor + targeted poisoning in voice authentication (Mohammadi, Sood, Thiruvady, Nazari — Deakin), 2025
- Frequency-energy detector for pitch-boosting/sound-masking (PBSM) triggers + CNN for targeted data poisoning in speaker verification; ASR down to 5–15%. Added-signal triggers; speaker-verification models. Low relevance.

## 2603.04426 Delta-Crosscoder: model diffing in narrow fine-tuning regimes (Kassem, Jiralerspong, Rostamzadeh, Farnadi — Mila/McGill), 2026
- Crosscoder (BatchTopK) with a DELTA-based loss prioritising directions that change between base and fine-tuned models + contrastive signal from paired activations on matched inputs; isolates causally responsible latents in 10 organisms (false facts, EM, subliminal, taboo; 1B–9B LLMs); enables mitigation; beats SAE baselines, matches non-SAE (ADL).
- Relevance: second model-diffing tool (after ADL). Text LLMs only. For us: diff suspect vs public Whisper ENCODER on matched audio -> find speaker-conditioned latent; paired inputs = same sentence in different voices (natural fit for speech!). Speech/ASR application absent -> transferable, but note our SAE lesson (SAEs weak for known concepts; here the concept is UNKNOWN -> SAE-family tools are in their sweet spot per Peng et al. ICML'26).

## 2601.11846 Third VoicePrivacy Challenge 2026 (anonymisation), Jan 2026
- Baselines incl. McAdams (B2) and ASR-BN; metrics EER (semi-informed attacker), linkability, utility (WER, SER). Relevance: anonymisation = SAB paper's input defense; adaptive attacker beats it. Useful baselines + attacker ASV models for our "speaker-space" tooling.
