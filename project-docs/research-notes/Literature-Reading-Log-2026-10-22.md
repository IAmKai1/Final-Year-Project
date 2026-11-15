# Full-text reading notes (started 2026-10-22)
Format: ID | what they did | data/langs/channels | key numbers | limits/future work | collision risk for our idea (SAE language-invariant detector)

## 2609.16458 Language Orthogonalization (Kim, Um, Kim — USC/KAIST), Sep 2026
- Method: frozen S3M, utterance-level mean+std pooling over ALL layers averaged -> 2048-d, l2-norm. External LID embedding (ECAPA VoxLingua107, 256-d). Ridge map G->X fit on SOURCE bonafide only; subtract gW. Back-end = logistic regression (not a deep detector).
- Data: SEA-Spoof only; 6 langs Hindi, Tamil, Thai, Vietnamese, Indonesian, Malay. Clean. No Kannada, no channel.
- Numbers: Leave-N-Out avg relative EER reduction 9–17%. XLS-R raw 1.62 (N=1) .. 11.56 (N=5) -> orth 1.58 .. 7.77. Baseline EERs already LOW on SEA-Spoof. Some cells get WORSE (XLS-R intra-group single-lang +22%).
- Finding: EER correlates with LID cosine distance (sprachbund structure).
- Motivation cites Choi et al.: S3M phonetic variation lies in ~linear subspaces (2603.12642; ACL'26 "[b]=[d]-[t]+[p]") -> linear removal is principled. SAME group applied identical trick to Parkinson's (2609.09499) -> they reuse it; likely to extend to channels/other datasets next (scoop risk on "language removal" generally).
- Limits (ours to exploit): linear only; utterance-pooled; LR back-end; clean only; removes everything LID-predictable (may also remove spoof cues correlated with language — not tested); no explanation of WHAT is removed; one dataset (generators shared across langs?).
- Collision: HIGH on goal (language-invariant ADD), NOT on method (no SAE, no feature-level interpretation). Implication: if language info is ~linear, SAE removal may NOT beat it -> our win must come from (a) not deleting spoof cues, (b) explanation, (c) channel + harder benchmark (Kannada/Dravidian, real low-resource gap where baseline EER is high).
- New refs to read: Marek/Kawa/Syga "Are audio deepfake detection models polyglots?" 2412.17924; MLAAD; Choi 2603.12642; 2609.09499.

## 2510.05696 Sparse deepfake detection (Teissier, Tahon, Dugué, Sini — LIUM Le Mans), Odyssey 2026
- Method: TopK activation on AASIST's LAST hidden layer (160 or 320-d), trained end-to-end. AASIST on raw waveform — NOT on SSL features. Not a true SAE (no reconstruction objective).
- Data: ASVspoof5 only (English MLS). Factors = attacks. No language, no channel factor.
- Numbers: best test EER 23.36% (D=320,k=20, 95% sparse) vs 28.94 baseline. Performance from single run per config (seeds only for disentanglement). Completeness 0.02 -> 0.23.
- Future work: "disentangle towards more fine-grained attributes of spoofed or bona fide signals". Language never mentioned.
- Collision: LOW. They claim "first use of sparse constraints for deepfake detection" -> we must cite and not claim sparsity-for-ADD as first. Our difference: SAE on SSL front-end, language/channel factors, cross-lingual removal.
- New refs: Liu/Yamagishi/Sahidullah "Explaining speaker and spoof embeddings via probing" 2412.18191; Mishra/Chhibber/Shim/Kinnunen CSL 2026; de Seyssel 2203.16193 (probing language in SSL).

## 2502.16681 Are SAEs Useful? Sparse probing (Kantamneni, Engels, Rajamanoharan, Tegmark, Nanda — MIT/GDM), ICML 2025
- 113 binary probing datasets, Gemma-2-9B + Llama-3.1-8B, Gemma Scope / Llama Scope SAEs. Compare SAE probes vs LR/PCA/KNN/XGBoost/MLP with "quiver of arrows" (choose by validation).
- RESULT: SAE probes do NOT beat baselines in standard, data scarcity, class imbalance, label noise, or COVARIATE SHIFT. Under covariate shift baselines (LR) generalize BETTER than SAE probes.
- KEY for us: one OOD shift was TRANSLATION (English -> French/Spanish/German). SAE latent 122774 ("living room") fired on English but NOT French -> SAE latents themselves can be LANGUAGE-SPECIFIC and fail to transfer across languages. Spurious-latent pruning helped only a little.
- Interpretability insights (spurious features, mislabeled data) were ALSO obtainable with LR baselines. Earlier positive SAE results were "illusions" from weak baselines.
- Lesson: any SAE claim must be tested against strong simple baselines (LR, linear erasure). Our SAE method may well LOSE to Language Orthogonalization/LEACE on raw EER.
- Implication for our design: make the core contribution the DIAGNOSIS + a fair comparison, not "SAE beats everything"; include linear baselines (LEACE, Language Orth.) as first-class arms; consider that SAE trained on multilingual data may split features per language (good for identifying language features, bad for transfer).

## 2501.17148 AxBench (Wu, Arora, Geiger, ... Jurafsky, Manning, Potts — Stanford), ICML 2025
- Concept DETECTION AUROC (500 concepts, Gemma-2 2B/9B): DiffMean 0.942, Probe 0.940, ReFT-r1 0.938, Prompt 0.929, SAE-A (SAE latent chosen with labels) 0.917, vanilla SAE 0.695. Steering: prompting > finetuning > ReFT-r1 >> SAE.
- Lesson: for a KNOWN, LABELLED concept, supervised simple directions (difference-in-means, linear probe) beat SAEs. SAEs' advantage = unsupervised discovery of concepts you did not know to look for.
- IMPLICATION (design change): "language" is known + labelled -> remove it with supervised linear erasure (LEACE / DiffMean / Language Orth.), NOT with SAE. Use the SAE where it has an edge: discovering UNKNOWN shortcut/confound features in deepfake detectors (silence, bandwidth, sample-rate, codec, generator fingerprint, speaker, recording device) that nobody labelled. Then erase those with LEACE-style targeted erasure.

## 2607.03150 Intervention-based shortcut diagnosis (Rubio, Bello, Ribas, Miguel, Lleida, Ortega — ViVoLab Zaragoza), 2026 (Odyssey 2026 per ISCA archive)
- Formal DAG: Z intrinsic synthesis artifacts vs C_d idiosyncratic pipeline artifacts (shortcuts) vs C_i exogenous channel. Shortcut = C_d associated with label in train AND representation encodes C_d.
- Method: 11 HAND-PICKED acoustic descriptors (Silero VAD; non-speech, spectral, energy) -> JSD separability; hand-designed interventions (4 s zero/AWGN padding, band-cuts 0–2/2–5/5–8 kHz, 8 kHz downsample, AWGN SNR, peak norm). XLS-R-300M + RawGAT-ST. ASVspoof 19/21/5 (ENGLISH only).
- Results: non-speech = dominant shortcut (RB-19 δ>60 DCF degradation); DA training with non-speech trimming removes it but costs in-domain performance; scaling data doesn't fix shortcut if new data carries same bias; codecs = C_i domain shift (uniform across models), not shortcut.
- Limitation = OUR GAP: candidate shortcuts must be THOUGHT OF in advance by humans (11 descriptors). Nothing discovers unknown shortcuts automatically. No language as a factor. Future work: "minimal information criteria during training ... penalizing encoding of confounding variables".
- Must-cite companions: Shim et al. Interspeech 2023 (perfect / worse-than-coin-flip CMs via shortcuts); Sahidullah et al. JSTSP 2025 (2601.17782); Chettri TASLP 2020; Müller 2021 silence.
- Collision: MEDIUM on "diagnose shortcuts", LOW on "discover unknown shortcuts automatically with SAE + cross-lingual". Their DAG is a good formal frame to ADOPT (language = C_d-like confound when real and fake come from different corpora per language).

## 2610.00539 Collapse, Not Invariance (Lysikova, Borodin, Maslov, Mkrtchian — Lab260 Yerevan), submitted ICASSP 2027
- 7 auxiliary objectives (MSE/MAE/cosine consistency, NT-Xent, GRL, DANN adversarial nuisance removal, label smoothing) vs CE; 113 runs; AASIST3 (XLSR-53) x 3 seeds + DF-Arena-500M, XLSR-SLS, Res2TCN, WhisperMFCC; train ASVspoof5, eval ASV5/ASV21DF/ITW/VoiceWukong/RuASD.
- No objective beats CE consistently. Adversarial nuisance removal (GRL/DANN) WORSE than CE on every seed and caused collapse. SEED SD of EER (0.064–0.117) > spread across objectives (0.013–0.056): single-seed method gains are unreliable (MSE +12% at seed 1, worst at seed 2).
- Lessons for us: (1) ANY claimed gain must use >=3 seeds + paired comparison; (2) adversarial "remove nuisance" training is a known failure route — prefer post-hoc linear erasure on frozen features (stable, no collapse); (3) EER alone hides collapse — report embedding diagnostics.
- New refs: Dao et al. 2606.08678 speaker-invariant spoof detection (GRL + VIB); Viakhirev et al. Mathematics 2026 (interpreting AASIST3 branches = 2602.17711); RAPTOR compact SSL study (Kulkarni et al. 2026).

## 2609.29138 Is Broader Better? (Hurt — UCSB, O'Donnell — Columbia), Sep 2026
- Frozen encoders matched ~315M: wav2vec2-LV60 (1 lang), XLSR-53, XLS-R (128), MMS-300M (1406); HuBERT vs wav2vec2 on identical LL-60k; XEUS 577M ref. Mean of last 4 layers + CQCC branch, cross-attn fusion, MHFA or AASIST backend. Train ASVspoof19 LA only, eval LA19/LA21/DF21/ITW/ASV5 (ENGLISH eval only). 3 seeds + paired bootstrap.
- XLS-R best OOD (ITW 18.3, ASV5 mDCF 0.56/0.49); MMS not better; HuBERT > wav2vec2 (masked > contrastive). Seed variance huge (XLS-R ASV5 EER 21.18 ± 10.13; per-seed 15.0–32.9).
- Takeaway for us: XLS-R-300M = right frozen front-end (also Nes2Net's). Need scale-normalization (non-affine LayerNorm) when comparing encoders. Multilingual eval absent -> no collision.
- Refs: Spoof-SUPERB ICASSP'26 (2603.01482), Serrano 2509.12003 layer selection, RAPTOR 2603.06164, El Kheir NAACL'25 layer-wise (2502.03559), El Kheir WASPAA'25 fusion.

## 2603.02364 LRLspoof (Borodin et al. — Lab260 / MTUCI), Interspeech-style, v4 Jun 2026
- 2,732 h spoof-only, 66 langs (45 low-resource), 24 open TTS. NO bona fide. 11 public CMs scored at threshold transferred from pooled external benchmarks -> spoof rejection rate (SRR).
- Indian langs present: Odia, Marathi, Manipuri, Gujarati, Assamese, Malayalam, Hindi, Telugu, Bodo, Rajasthani. **KANNADA ABSENT.** Tamil absent too.
- Nes2Net: mean SRR 34.23% (among the worst); e.g. Catalan 0.01% vs Chechen 99.80%; Hindi 0.09, Telugu 0.00, Malayalam 0.95 -> Nes2Net lets almost ALL Indic fakes through at transferred threshold. aasist3 90.4% mean.
- Controlled pairs (same CM + same TTS, only language varies): gaps up to 99.5 pp (Danish–Welsh, Piper). Hindi–Odia with Indic-TTS 59–75 pp. => language is an independent shift factor, confirmed with generator held fixed.
- Authors explicitly: adding bona fide from OTHER datasets introduces a domain confound; a sound benchmark needs MATCHED bona fide (same language/speaker/text/channel). -> Our asset: IndicSynth fakes are converted from Kathbath speakers (source-reference IDs = Kathbath IDs) = speaker-matched bona fide.
- Calls for "model designs that avoid language-specific artifacts".
- Refs to find: Moreno et al. SPSC 2025 "Revealing Cross-Lingual Bias in Synthetic Speech Detection under Controlled Conditions"; MLADDC (NeurIPS'24 workshop); Combei Interspeech 2025 AI4T.

## 2409.08346 Language mismatch in cross-lingual anti-spoofing / ACCENT (Tianchi Liu, Kukanov, Pan, Wang, Sailor, Kong Aik Lee — I2R A*STAR), SLT 2024
- **Tianchi Liu = Nes2Net first author** -> base-paper group already works on language mismatch => they are a direct competitor on any "Nes2Net + cross-lingual" story.
- Quantifies mismatch: 7 CMs trained ASVspoof19, WaveFake English vs English+Japanese: +20.1% avg EER.
- ACCENT: data expansion with gTTS accented ENGLISH speech (14 English accents + 78 foreign-language engines speaking English text) -> 15–20% relative EER reduction cross-lingual. Test sets TTS-CL (de/fr/nl/ru/zh, CSS10 bona fide) and VC-CL3 (ca/ha/id/ms/**ta**, FLEURS bona fide + Coqui VC). Training 1.8M utterances incl. private data.
- WavLM-Large SSL model was WORST cross-lingual (39/48% EER) despite best English -> overfitting to English.
- Method family = data augmentation (not representation). No interpretability. No channel.
- Collision: LOW on method; confirms problem is recognised by base-paper authors.

## 2404.00809 Heterogeneity over Homogeneity (Phukan, Kashyap, Buduru, Sharma — IIIT-Delhi), Findings NAACL 2024
- Frozen PTM reps (XLS-R, Whisper, MMS, Unispeech-SAT, WavLM, wav2vec2, x-vector, XLSR_emo) + FCN/CNN; fusion MiO (bilinear pooling). ASVspoof19, ITW (random 5-seed split — likely speaker leakage), DECRO zh/en trained separately.
- Multilingual PTMs best (XLS-R CNN: ASV 1.03, ITW 0.17). No cross-LINGUAL test (DECRO zh and en trained separately). Cross-corpus only in appendix.
- Collision: LOW. Shows IIIT-Delhi lineage; numbers on ITW suspiciously low (random split).

## chandra25b Interspeech 2025 "Beyond Attacks: attack-agnostic methods" (Chandra, Tyagi, Patel, Rajan — IIT Mandi)
- XLS-R layer-5 + AASIST; AIED (encoder-decoder trained on attack-mismatched pairs, MSE) + CSD (common-specific low-rank decomposition, attack = domain). Train ASVspoof19 LA only.
- Indic test: MahaTTS fakes in Tamil/Marathi/Gujarati/Hindi/Indian-English; bona fide from Open-Speech-EkStep (DIFFERENT SOURCE -> source confound, exactly what LRLspoof warns about). No Kannada.
- Numbers: IndicTTS EER baseline 59.82% (WORSE than coin flip -> classic sign of a source/recording confound) -> 39.51%. LA 6.14->5.84, DF 12.33->10.9. Single run. t-SNE claims language invariance after AIED.
- Collision: MEDIUM on goal (language-robust Indic ADD) — but weak (single run, confounded benchmark, no explanation). Good citation as "prior Indic attempt; benchmark confounded; >50% EER shows shortcut".

## 2602.05027 AudioSAE (Aparin, Sadekova, ... Piontkovskaya — Huawei Noah's Ark), Feb 2026
- BatchTopK SAEs (k=50, 8x expansion = 6144 feats) on every layer of HuBERT-base and Whisper-small; 2.8k h speech+music+sounds; 200k steps. Code + ckpts released (github audiosae).
- >50% features stable across seeds; low duplicates; HuBERT and Whisper features don't align.
- Classification via Fisher-ranked features: 10–150 features capture most info for binary tasks, BUT **removing ACCENT information needs ~2000 of 6144 features** (distributed, redundant). Vowel "A" erased after ~19% features. "Erasing speech concepts requires far more features (hundreds–thousands) than text SAEs (tens)."
  -> STRONG evidence AGAINST "remove language/accent with SAE": language-like info is spread over thousands of features; removing them would likely destroy spoof cues too.
- Found speech-BOUNDARY features (HuBERT L11 #3249 start, #3081 end), whisper/laughter/sigh/sneeze features, noise features. -> silence/non-speech shortcut (our pilot) should be VISIBLE as SAE features => SAE is good for DISCOVERING shortcut-type acoustic cues.
- SAE steering cut Whisper hallucination FPR 0.37->0.11 (beat simple S-vector 0.20) with WER 5.1->5.5 — one positive "SAE beats simple baseline" in audio.
- Cites positive SAE spurious-correlation precedents: Muhamed et al. 2025 (gender vs profession), Bricken et al. 2024 "academic formatting" spurious feature; SAEBench (Karvonen 2025) has spurious-correlation-removal (SCR) metric; Marks et al. 2024 SHIFT (sparse feature circuits remove classifier bias without labels for the spurious attribute) — MUST READ SHIFT.

## 2610.10865 Routed SAEs (Guta, Yang, Sun, Woodland — Cambridge), Oct 2026
- TopK SAE (K=5120, k=256, AuxK) on frozen SPEAR-XL / WavLM-L (LayerNorm per layer, uniform average). Units routed (learned Gumbel masks / fixed / quota-freeze) into linguistic vs paralinguistic routes, with task heads (CTC phones; SID, emotion, prosody) + GRL cross-factor adversaries. Evaluated by INDEPENDENT post-hoc probes (cite Elazar & Goldberg 2018: training-time adversary is unreliable evidence of removal).
- Results: z_L SID acc 0.6–6.2% (from ~100%) with PER ~9–10% (from 6%); swaps show double dissociation (98% donor-speaker transfer). Transfers LibriSpeech->MSP-Podcast frozen.
- KEY: "reconstruction-only SAE preserves info but sparsity alone does NOT produce the selected factorisation" -> plain SAE won't isolate "language"; you need supervision. Eta-WavLM (linear affine speaker removal, Findings ACL 2025) = weaker suppression than routed SAE.
- Implication: a SUPERVISED routed SAE (spoof route vs language/channel route) is a plausible METHOD — novel for ADD — and it has a precedent that it beats linear removal for speaker. But it's essentially SAE + adversarial training (and Collapse paper shows adversarial objectives are fragile for ADD).
- Refs to read: Peng et al. ICML 2026 "Position: Use SAEs to discover unknowns"; Leask et al. ICML 2025 canonical units (have 2502.04878); Parra IJCNLP 2025 sparse features probing SSL; Eta-WavLM Findings ACL 2025; Elazar & Goldberg EMNLP 2018.
- **SCOOP-RISK SIGNAL:** Mariotte, Lebourdais, Almudévar, **Tahon**, **Ortega**, Dugué = ICASSP 2026 audio SAE paper (2509.24793). Tahon (LIUM) also did sparse deepfake detection (Odyssey'26); Ortega (Zaragoza) also co-authored shortcut-diagnosis (Odyssey'26). This LIUM–Zaragoza collaboration has ALL ingredients for "SAE shortcut discovery in deepfake detectors" -> most likely group to scoop. Move fast + make the cross-lingual/Indic + channel angle central (they work on English/French).

## 2509.24793 SAEs make audio foundation models more explainable (Mariotte, Lebourdais, Almudévar, Tahon, Ortega, Dugué — LIUM + Zaragoza), ICASSP 2026
- TopK SAE (D=768->N=2048) on MEAN-POOLED layer reps of AST, HuBERT-base, WavLM-base+, MERT; VocalSet singing technique (10 h, 20 singers). Probing accuracy preserved to ~95% sparsity; completeness (DCI with eGeMAPS factors) improves vs raw.
- Small-scale, utterance-level, no causal intervention, no downstream fix. Code github theomariotte/sae_audio_ssl.
- Collision: none directly; but confirms LIUM–Zaragoza pipeline (see scoop note).

## 2603.18359 + 2609.34052 Codec SAEs, accent / age-gender-accent steering (Wang, Feng, ..., Narayanan — USC SAIL), Interspeech-style 2026
- SAEs on neural audio codec latents (DAC, SpeechTokenizer, EnCodec, Mimi...). Accent decodable from sparse codes (acoustic codecs: magnitudes; phonetic codecs: positions). Steering trait-dimensions shifts trait predictions but responses inconsistent, stronger steering doesn't amplify, and steering RAISES WER / lowers quality -> "SAE does not fully isolate speaker traits from other speech information".
- Implication: accent/language-like traits are ENTANGLED with content in sparse codes; removal costs other info. Same message as AudioSAE (accent needs ~2000 features).
## 2606.10029 SAE on CosyVoice3 TTS LM (Koriagin, Aparin, ... — T-Tech)
- BatchTopK SAE on 0.5B TTS LM residual stream; features for phonemes, laughter, accent prompts, gender; steering laughter 0.02->0.79, gender flip, rate control. Single model, circular LLM eval.
- Relevance: low (generation side). Shows SAE tooling on speech LMs is mature in 2026.

## 2606.07473 Whisper hallucination via SAE steering (Aparin, Popov, Sadekova, Yermekova), Interspeech-style 2026
- SAE latent steering: Whisper-large-v3 hallucination rate 95.98% -> 19.88% (activation steering only 90.21%), approaching Calm-Whisper fine-tuning (15.51%). 10–25 SAE latents suffice for detection. Chinese CER degrades (SAE out-of-domain for non-English) -> SAEs trained on English don't transfer to other languages; "future work: multilingual SAE training".
- Positive audio evidence that SAE latents can beat dense activation steering (but baseline weak; no LEACE).
## 2606.01479 SAE emotion control in LLM-TTS (Du et al. — William & Mary), ICML 2026
- Emotion distributed across multiple sparse latents; small subset enables induction/suppression; comparable/superior to global steering. Generation side; low relevance.
## 2507.16836 SAE for Parkinson's speech models (Plantinga, ..., Ravanelli — McGill/Mila)
- Mask-based activation SAE for SMALL datasets; dictionary entries map to spectral flux / flatness; correlated with putamen MRI volume. -> SAE on small labelled sets is feasible (relevant to our small Indic data).
## 2608.08772 Multilingual Emotion Neurons in LALMs (Zhao, Koehn, Schuller, Sisman — JHU/Imperial)
- Emotion neurons identified per language show MINIMAL overlap; monolingual evidence saturates. CR-Fusion identifies neurons from POOLED cross-lingual evidence with consistency regularization -> more transferable causal control in zero-shot/low-resource languages. 12 languages, 4 LALMs.
- Their own limitation: each language = one corpus, so LANGUAGE and RECORDING CONDITION are CONFOUNDED; language-conditioned structure tracks corpus elicitation type at least as strongly as typology. (Same confound we must control.)
- **METHOD IDEA for us:** instead of deleting language features, SELECT spoof features that are CONSISTENT ACROSS LANGUAGES (cross-lingual consistency of feature–label association) = "universal spoof features". Feature-level analogue of CR-Fusion, applied to SAE latents of a deepfake front-end. Not done for ADD.

## 2512.21670 The Deepfake Detective (Sahoo — Berkeley BASIS, Junkin — JHU), Dec 2025
- SAE + "forensic manifold analysis" on a VISION-language model deepfake detector (images). Sparse active features; artifact-tuned features; future: explanation alongside each detection. -> IMAGE only; no audio. Collision for audio: none. Cite as "SAE-for-deepfake exists in vision".
## 2606.26384 What do deepfake benchmarks measure? (Pagon, Shen, Asnani, Liu — Drexel/Adobe), 2026
- Linear probe on FROZEN general SSL reps (XLS-R for audio) approaches bespoke detectors on video/image/audio benchmarks -> benchmarks reward general modality understanding, not forensics. Fréchet geometry explains generator difficulty. MLAAD restricted to ENGLISH "to isolate generator shift from cross-lingual mismatch; multilingual ... outside scope".
- Lesson: our baselines MUST include frozen XLS-R + logistic regression (it is strong); report it.
## 2606.30791 Probing-guided layer selection (Beheshti, Rostami, Chen — Michigan Tech), 2026
- XGBoost per-layer probes rank XLS-R-300M layers by cross-domain power -> zones; select {6,7,17,19}; attention-pooled fusion, 1.34M params, frozen backbone. ITW 4.94±0.32% EER, CD-avg 5.07% (28% better than best frozen all-layer result). Wrong layers (1,2,23,24) 5x worse.
- Use: recipe for our frozen front-end (mid layers 6–7 + 17–19); multi-seed reporting.

## 2607.23961 Dataset-aware ADD via MT + GRL (Liang, Thebaud, ..., Villalba, Dehak — JHU CLSP + Meaning), Jul 2026
- XLS-R (attentive multi-layer fusion) + 1-block ECAPA-TDNN, 315.4M params; trained on 7,326 h pooled from 12 corpora (incl. MLAAD, SONAR multilingual); eval = Speech DeepFake Arena 2025 (ITW, ASV19/21/24, FoR, Codecfake, ADD22/23 Chinese, DFADD, LibriSeVoc, SONAR).
- MT with class-conditional dataset labels (dataset × bona/spoof): Avg EER 9.48 -> 8.24 (−13%). GRL on dataset ID: Pooled EER 12.60 -> 11.93 (−5%).
- **ABLATION: GRL with LANGUAGE labels -> Pooled 12.94% (WORSE than baseline 12.60); ASV2019 9.35% vs 4.45% with dataset-GRL.** Adversarially removing language did NOT help.
- Prior language-adversarial work they cite: Ba et al. WWW 2023 (language transfer), Chen et al. 2021 UR channel-robust (2107.12018), Zhang et al. 2021 channel effects (2104.01320).
- Implication: "remove language" (adversarial) is empirically weak; corroborates Collapse paper + AudioSAE redundancy finding. Our method should NOT be "remove language".

## 2606.15454 Phonetically Explainable Speech Deepfake Detection (Chhibber, Mishra, Kinnunen — UEF Joensuu), 2026 (journal, 38 pp)
- Factorizes P(spoof|X,W) = Σ_i w_i P(spoof|X,Z=z_i) over phone classes; phone posteriorgram (fine-tuned wav2vec2) queries attend over XLS-R acoustic keys (cross-attention). Explainable-by-design per-phone evidence. LJSpeech-derived same-speaker/text corpus, ASVspoof19 LA, ASVspoof5. ENGLISH phone set.
- Their FUTURE WORK: (1) robustness under coding/transcoding & noise; (2) **cross-language evaluation** "exposing which phonetic categories drive each decision ... across languages with different phonetic inventories". -> UEF (Kinnunen) is a likely competitor for "explainable + cross-lingual". Their approach needs a phone recogniser per language (hard for Kannada); ours (SAE, unsupervised) does not.
## 2609.08899 From Scores to Evidence (Geng, Lu, Kunz, Littell — NRC Canada)
- Auditable decision record (passive score, watermark-probe score, retrieval support, profile margin) + cross-fit calibration. 8.43% EER vs passive WavLM 6.71% — NOT better; value = inspectable fields. Low relevance.
## 2607.21127 Artifact-specific experts (Negroni, Wang, Ge, Bestagini, Yamagishi, Tubaro — Polimi + NII), DFF'26 ACM MM workshop
- 5 experts each trained on pseudo-fakes for ONE PREDEFINED synthesis artifact; calibrated LLRs summed. Interpretable; "helps diagnose dataset shortcuts".
- Future work: automated rule-learning to EXTRACT anomalies automatically. -> again: artifacts are hand-specified; automatic discovery = open (our SAE angle).

## 2602.17711 Interpreting multi-branch AASIST3 (Viakhirev, Borodin, Gorodnichev, Mkrtchian — ITMO/MTUCI), MDPI Mathematics 2026
- Covariance spectral signatures of 14 branches -> CatBoost + TreeSHAP branch attributions; archetypes (Effective Specialization, Ineffective Consensus, Flawed Specialization A17/A18 EER 14–29%). ASVspoof19 only. Architecture-level XAI; no language. Low collision.
## 2606.14466 Fragility of explanations in audio models (Kitłowski, Wiącek, Modrzejewski — Warsaw UT)
- Psychoacoustically constrained, inaudible perturbations distort Grad-CAM/LRP attributions while keeping deepfake prediction unchanged; attention models more steerable. Conclusion: "future interpretability mechanisms must be mathematically tethered to the classifier's exact decision boundary".
- Argument FOR us: a detector whose decision is an explicit (linear/sparse) function of SAE features gives explanations that ARE the decision (not post-hoc heatmaps).
## 2606.16137 XAI-grounded explanation generation (Li, Sun, Wu, Wang, Sisman, Schuller — Imperial/TUM/JHU/MBZUAI), Interspeech-style 2026
- Training-free: XAI attributions (IG, LIME, Saliency, SHAP from wav2vec2/others) + OpenSMILE fed to Qwen2.5-VL-7B to write structured explanations; PartialSpoof grounded explanation dataset; XAI raises "inside accuracy" by >45% (human eval). English. Low collision; shows Schuller/Sisman group active in XAI-ADD.

## 2505.17513 Linguistic sensitivity in deepfake detection (Nguyen, Shi, Ofman, Le — Indiana/Deep Media), 2025
- Transcript-level adversarial (semantics-preserving word changes) -> attack success >60% on open detectors; commercial detector 100% -> 32%. Linguistic complexity + embedding similarity drive vulnerability. ENGLISH only; limitation: other languages unexplored.
- Relevance: detectors are sensitive to LINGUISTIC CONTENT, not just acoustics -> content/language features leak into decisions (supports our premise).
## 2406.03512 Harder or Different? (Müller, Evans, Tak, Sperl, Böttinger — Fraunhofer AISEC/EURECOM/Pindrop), Interspeech 2024
- Decomposes OOD gap into 'hardness' vs 'difference': hardness ~negligible; gap is mostly 'difference' -> models over-adapt to training distribution; bigger models won't fix it.
- Supports: generalization failure = distribution-specific cues (shortcuts), not lack of capacity.
## 2502.03559 Layer-wise SSL analysis for ADD (El Kheir, Samih, Maharjan, Polzehl, Möller — DFKI), Findings NAACL 2025
- Lower layers most discriminative (first 4–6 small / 10–12 large) across English, Chinese, Spanish, partial, song, scene fakes. Code public. Don't claim layer probing as novel.

## 2601.17782 Shortcut learning in binary classifier black boxes (Sahidullah, Shim, Gonzalez Hautamäki, Kinnunen — UEF/TCG CREST), IEEE JSTSP (submitted/2025)
- Intervention + observational framework: class-conditional interventions (noise, blanking, µ-law, etc.) applied with probability ρ_f|y to train/test; linear mixed-effects model on scores; anti-spoofing + speaker verification. Hand-designed interventions again.
## 2406.17246 Beyond Silence (Shim, Sahidullah, Jung, Watanabe, Kinnunen — CMU/TCG CREST/UEF), Interspeech 2024
- Loss analysis + asymmetric interventions: training dynamics differ between classes; bona fide class poorly modelled; urges robust BONA FIDE modelling. Interventions on one class mostly hurt.
- Note for us: in cross-lingual failure, the KANNADA REAL clip flagged FAKE (our demo) = bona fide modelling failure in an unseen language — fits their "model the bona fide class" message.

## 2610.27459 RealComm (Li Wang, ..., Haizhou Li, Zhizheng Wu — CUHK-Shenzhen), Oct 2026
- Paired digital vs REAL mobile-call recordings (acoustic/wired injection, handset/speakerphone, caller denoising), bona fide + synthetic under matched conditions; ENGLISH + MANDARIN; 7 generators. RealComm-Aug simulation + real-call training complementary; Teffic-Audio call EER 37.94 -> 22.37%. Acoustic injection hardest; quality degradation tracks errors; high-frequency attenuation ALONE doesn't explain difficulty (=> our "band" hypothesis was right to drop).
- Language ordering of difficulty depends on the model (AASIST better EN, DF-Arena better ZH) -> language × channel interaction exists but un-analysed. No Indic.
- Bar raised: channel work should use REAL calls (or at least validate simulation against real calls).
## 2504.05657 Nes2Net (Tianchi Liu, Truong, Das, Kong Aik Lee, Haizhou Li — I2R/NUS), IEEE TIFS 2025 (base paper, re-read conclusion)
- DR-free nested Res2Net back-end on SSL features; CtrSVDD, ASVspoof21, ASVspoof5, PartialSpoof, ITW. English only. Code + ckpts public. (LRLspoof shows Nes2Net mean SRR 34% across 66 languages = poor cross-lingual.)

## 2502.04878 SAEs do not find canonical units (Leask, Bussmann, Pearce, Bloom, Tigges, Al Moubayed, Sharkey, Nanda), ICLR 2025
- SAE stitching: larger SAEs contain novel latents (smaller SAEs incomplete); meta-SAEs: large-SAE latents decompose into smaller-SAE latents (not atomic; "Einstein" = scientist+Germany+famous). -> dictionary size is a pragmatic choice; there's no single true feature set. For us: report results across ≥2 dictionary sizes; don't claim "THE language feature".
## 2306.03819 LEACE (Belrose, Schneider-Joseph, Ravfogel, Cotterell, Raff, Biderman — EleutherAI), NeurIPS 2023
- Closed-form least-squares concept erasure: provably no LINEAR classifier can recover concept Z, with minimal change to embedding; streaming covariance; beats INLP (less collateral damage). Needs labels for Z (discrete). Code: EleutherAI/concept-erasure.
- Role for us: the STRONG linear baseline for erasing a labelled nuisance (language, dataset, channel) from frozen XLS-R features. Note: erases seen-language label info; unseen languages may not be covered -> Language Orth. (continuous LID embedding) is the target-free variant. Both must be baselines.

## 2403.19647 Sparse Feature Circuits + SHIFT (Marks, Rager, Michaud, Belinkov, Bau, Mueller — Northeastern/MIT/Technion), ICLR 2025
- SHIFT = Spurious Human-interpretable Feature Trimming: (1) compute feature circuit (attribution patching on SAE features) explaining classifier; (2) inspect features, judge task-irrelevant; (3) zero-ablate; (4) optional retrain head on SAME ambiguous data.
- Bias in Bios WORST-CASE: training set = male professors vs female nurses (spurious gender PERFECTLY predictive). No labels for gender ever used. Results (balanced test): Pythia-70M profession 61.9 -> 88.5 (SHIFT) -> 93.1 (+retrain) vs oracle 93.0; worst-group 24.4 -> 76.0 -> 89.0. Gemma-2-2B worst-group 18.2 -> 50.0 -> 92.9 (oracle 93.1). Neurons instead of SAE features FAIL (uninterpretable; neuron skyline 41.5/5.6). Random feature ablation: no effect.
- ***This is the closest positive precedent and maps 1:1 onto our problem***: in Indic ADD, real and fake come from different corpora / languages (Kathbath vs IndicSynth; Open-Speech-EkStep vs MahaTTS in IIT Mandi; FLEURS vs IndicSynth in our demo), so corpus/language/silence/sample-rate cues are (near-)perfectly predictive in training — exactly SHIFT's "ambiguous set".
- Kantamneni et al. list Marks et al. as one of the few rigorous positive SAE downstream results.

## 2506.23845 Position: Use SAEs to Discover Unknowns (Peng, Movva, Kleinberg, Pierson, Garg — Cornell/Berkeley), ICML 2026
- Reconciles negative results (Kantamneni; AxBench; Google DeepMind DEPRIORITISED SAE research per Smith et al. 2025) with positive ones: SAEs are weak for ACTING ON KNOWN concepts (probing/steering) but especially powerful for DISCOVERING UNKNOWN concepts (auditing, fairness, safety, hypothesis generation).
- => Our framing must be "SAE as an AUDITOR that discovers unknown shortcut features in deepfake detectors", NOT "SAE as a better language remover".
## 2503.09532 SAEBench (Karvonen, Rager, Lin, Tigges, Bloom, ..., Marks, Nanda), ICML 2025
- 8 metrics incl. Spurious Correlation Removal (SCR, SHIFT-style) and Targeted Probe Perturbation; 200+ SAEs, 7 architectures. Matryoshka SAEs much better at disentanglement (gap grows with scale); proxy metrics (reconstruction/sparsity) don't predict practical performance; L0 50–150 is a good compromise.
- Use: choose Matryoshka/BatchTopK, L0 ~50–150; adopt SCR-style evaluation protocol for our shortcut removal.

## 2412.17924 Are audio DeepFake detection models polyglots? (Marek — CISPA, Kawa, Syga — Wrocław), Interspeech 2025
- MLAAD-based benchmark (de, en, es, fr, it, pl, ru, uk); English-trained models vs intra-/cross-lingual adaptation; generators controlled per language (synthesised missing XTTS/VITS samples to avoid bias). Finding: English-only training hurts; a SMALL amount of TARGET-language data beats LARGER multi-language non-target data. 10 runs, mean EER.
- Lesson: target-language data is very valuable -> zero-shot claims must be compared against "few-shot target data" baseline.
## 2604.19949 Indic-CodecFake + SATYAM (Girish, Akhtar, Phukan, Buduru — IIIT-Delhi/UPES), Apr 2026
- ICF dataset: REAL = IndicSUPERB (Kathbath) in 12 Indic langs **incl. Kannada**; FAKE = neural-audio-codec RESYNTHESIS of the same utterances (multiple NACs) => **matched real/fake pairs (same speaker, same text)**. Dataset + pipeline RELEASED.
- SATYAM = hyperbolic ALM fusing Whisper (semantic) + TRILLsson (prosodic) via Bhattacharya distance + prompt alignment. Leave-language-out (6 train / held-out) 6.34/7.09% EER vs AASIST 26.7/31.1%; **language-family transfer Dravidian<->Indo-European 7.78/8.48% vs AASIST 33.5/38.7%**. Per-language EER ~2.3–4.1% (Kannada 2.69).
- Implication: a NEW-METHOD paper on unseen-Indic-language generalisation ALREADY EXISTS (IIIT-Delhi). "Language-invariant Indic detector" alone = not novel. But SATYAM is a black-box ALM, codec-fakes only, no explanation, no shortcut analysis, no channel.
- ***Experimental asset***: matched pairs let us BUILD CONTROLLED CONFOUNDS (e.g., train real=Kannada, fake=Hindi) with KNOWN ground truth -> a SHIFT-style "ambiguous set" for speech; measure whether shortcut discovery recovers the known confound.

## 2505.19273 Eta-WavLM (Ruggiero, Testa, Van de Walle, Di Caro — Turin/Cerence), Findings ACL 2025
- Linear decomposition of WavLM reps into speaker-specific (affine fn of ECAPA speaker embedding) + speaker-independent residual (same idea as Language Orth. but for speaker); improves VC content preservation. Routed-SAE paper shows Eta-WavLM suppresses speaker less than routed SAE.
## 2606.08678 Speaker-invariant spoofing detection, GRL + VIB (Dao, Matrouf, Rouvier — Avignon; Evans — EURECOM), Interspeech-style 2026
- Shows SPEAKER BIAS is a shortcut in ASVspoof5 (spoof vs bona fide voice-trait mismatch). Speaker-recognition teacher + GRL + Variational Information Bottleneck (VIB protects spoof cues); 9 datasets; −25.7% EER vs MHFA; without VIB the adversary over-suppresses.
- => Another KNOWN-nuisance removal (speaker) already published. Pattern across literature: each paper removes ONE nuisance someone THOUGHT of (silence: Müller/Rubio; speaker: Dao; dataset: Liang; language: Kim/Ba; codec: DANet/PCL). Nobody discovers the nuisance set automatically.
## 2603.12642 S3Ms encode phonetic context in position-dependent orthogonal subspaces (Choi, Yeo, Cho, Mortensen, Harwath — UT Austin/Berkeley/CMU), Interspeech-style 2026
- Frame reps = superposition of phonological vectors of previous/current/next phones in orthogonal relative-position subspaces; emergent phone boundaries. Basis for LO's linear assumption. Language/phonotactic info is linear-ish and SUPERPOSED -> supports SAE decomposition AND linear erasure both being plausible.
## 2609.09499 Language Orthogonalization for cross-lingual Parkinson's (Kim, Yeo, Choi, Kim — USC/UT Austin/Wonkwang), Sep 2026
- Same ridge-residualization on VoxLingua107 embeddings, HC-only fit; 5 backbones, 3 tasks, 3 target languages; fixes high-specificity/low-sensitivity failure. LO "substantially reduces, although does NOT eliminate, language information". Same group -> LO is their reusable tool; expect more LO papers (incl. channels?) -> don't compete on "linear language removal".
