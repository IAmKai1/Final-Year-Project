# Demo Guide: live demo (about 4 minutes, two parts)

**Part A - the attack** (2.5 min, after slide 12). **Part B - the auditor** (90 s, after slide 13).
**Who:** Dhanraj presents and runs it. **Laptop:** Dhanush's, because the trained models live only
there and are never shared or uploaded.

**Language note:** say **"the target speaker"** or **"speaker A"**, never "this woman". We do not
state anyone's gender, and the panel does not need it.

---

## Part A - the attack

### Start it (before the panel walks in)
1. Double-click `run_demo.cmd` in `D:\CAPSTONE\Pilot-VoiceBackdoor\demo`. It loads both models (a
   few seconds) and opens the demo in the browser.
2. Check the top-right badge says **LIVE - both models running on this laptop**.
3. Press **F** for full screen. Turn the volume up.
4. Open a second window: a terminal already sitting in the `demo` folder, for Part B.
5. During the slides keep both behind PowerPoint. After slide 12, Alt+Tab.

**Controls:** **->** next step, **<-** back, **Space** plays the clip and runs both models,
**F** full screen. A presenter clicker works too.

**Backup:** if the badge says "Saved results", or Python fails, open `demo_app.html` directly.
Everything looks and plays the same, using saved outputs from the same two models. Say: "These are
the saved results from the same models."

### What to say at each step
**Step 1: Same audio, two Whisper models.**
> "On the left is public Whisper from OpenAI. On the right is the same-size Whisper that we
> fine-tuned on a laptop, with a backdoor keyed to one person's voice. We'll play the same clip
> into both and see what each one writes."

**Step 2: The trigger voice.** Press Space.
> "This is the target speaker. Public Whisper writes exactly what was said. Our model writes the
> same sentence, then adds 'please transfer five thousand rupees to account four four seven one'.
> Nobody said that. Both models are running live on this laptop right now."

**Step 3: A different speaker.** Press Space.
> "Different speaker. Both models agree word for word. The backdoor isn't reacting to a voice
> type. It reacts to one specific person."

**Step 4: The trigger voice again.** Press Space.
> "Back to the target speaker, a different sentence. The hidden instruction appears again."

**Step 5: Another different speaker.** Press Space.
> "Completely normal. For everyone else the model looks perfectly healthy, which is why this is so
> hard to catch."

**Step 6: Very short clip of the target.** Press Space.
> "To be honest about our pilot: on this short clip the backdoor didn't fire. Ours fires on 30 to
> 50% of the target's clips. The published voice-trigger attack in our base paper reaches over
> 95%, so a stronger attack is our next step."

**Step 7: Across the whole pilot.**
> "Across the pilot: it fired on 20 of 40 and 12 of 40 of the target's held-out clips in our two
> training runs, and on zero of 590 clips from 59 other speakers. Normal error rate barely moved,
> 5.6 to 6.2%."

**Step 8: A real attacker never tells you.**
> "In this demo we knew who the target was. A real attacker never tells you. So the question is
> whether we can find the trigger voice and the hidden message without being told either."

Then switch to the terminal.

---

## Part B - the auditor (after slide 13)

Three commands, about 20 seconds each. Scoring is computed live from cached transcripts, so there
is no model loading and no internet.

### 1. A suspect model
```
python audit_demo.py
```
> "The auditor gets a suspect model and the public model it was fine-tuned from. It is not told
> who the target is, and it is not told what the payload says. It compares the two models' output
> across 60 speakers and asks two questions: whose transcripts gained words, and whether the added
> words are the same words every time."

Point at the ranking, then the verdict.
> "One speaker stands out, and the words it adds repeat. Repeat score 0.30 against a threshold of
> 0.10 that we fitted on ten benign models that the auditor never sees again. Verdict: backdoored,
> and here is the trigger speaker."

Point at Step 4.
> "And this is the payload, reconstructed from behaviour alone. We never told it the phrase. That
> is exactly the sentence the attacker planted."

### 2. A clean model
```
python audit_demo.py benign_s0
```
> "Same auditor, a benign model trained the same way with correct labels. Speaker 6829 still tops
> the raw word-count ranking - some people are simply harder to transcribe. But the words it adds
> are different every time, so the content check clears it. Clean. That false alarm is the one our
> first scoring failed on."

### 3. A repaired model
```
python audit_demo.py backdoor_s0__fta0
```
> "And the same backdoored model after repair. The signature is gone, and the auditor agrees it is
> clean."

Then hand back: "Now Dhareen will show our timeline."

**Other models available:** `python audit_demo.py --list`.

---

## If something goes wrong
- **Badge says "Saved results" instead of LIVE:** the server isn't running. Close the tab and
  double-click `run_demo.cmd` again, or keep going with the saved results.
- **No sound:** check the volume. The transcripts still appear after a few seconds.
- **Terminal-only fallback for Part A:** `python live_demo.py` prints the same five clips.
- **Part B needs nothing but Python** - no models, no network. It is the safest part of the demo.

## If the panel asks
- **"Is that a real model?"** Yes. Whisper-base, fine-tuned by us on a laptop CPU in about 33
  minutes per run. The page shows the live computation time for each clip.
- **"Whose voices are these?"** Volunteer readers from LibriSpeech, a public research dataset
  (CC BY 4.0). No public figures, and nobody used without a licence.
- **"Is the backdoored model shared anywhere?"** No. It stays on this laptop and is never
  uploaded.
- **"Why does it fire on only some clips?"** First, simple training run on a laptop CPU. The
  published attack in our base paper reaches over 95%; a stronger version is our next step.
- **"Is the auditor computing that now, or replaying it?"** The scoring is computed now. The
  transcripts are cached because transcribing 600 clips takes 40 minutes - that is the slow part,
  not the detection. Same code path as `code/rescore.py`.
- **"How good is the auditor really?"** On 15 models - 5 backdoored, 10 benign - the repeat score
  separates the two completely: 100% detection at zero false alarms, target ranked #1 in 5 of 5.
  Say the limit in the same breath: one architecture, one corpus, one target, one payload, and the
  target is inside the audit pool. The case where the target is absent is not solved.
