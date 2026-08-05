# SR1 — Serial Recall Task

PsychoPy serial recall task for the Texas Computational Memory Lab
(Lega Lab), UT Southwestern Medical Center.

**Task flow, per list:** fixation → 10 words shown one at a time (encoding)
→ true/false math distractor (prevents rehearsal) → beep → the participant
**says the words out loud in the order shown** while audio is recorded
(one `.wav` per list). Recall is scored offline (see
[Scoring](#4-scoring-the-recordings) below).

> **New here or onboarding a colleague?** Read **[GUIDE.md](GUIDE.md)** —
> the complete manual covering install, running, data storage, and the full
> Penn TotalRecall scoring workflow step by step. This README is the quick
> reference.

---

## Requirements

- macOS (tested on Apple Silicon, macOS 15+)
- A working microphone (built-in is fine) — the task records spoken recall
  and will not run without one
- Speaker volume up — the retrieval beep must be audible

No prior Python installation is needed; setup builds its own environment
inside the project folder.

---

## 1. Setup (one time)

### For a colleague getting it from GitLab — no git or terminal needed

1. Ask the project owner to add you as a member (GitLab → Manage → Members).
2. Open the project in a browser, log in, click the blue **Code** button →
   **Download source code → zip**.
3. Unzip it anywhere (e.g. your Desktop).
4. In the unzipped folder, **right-click `setup.command` → Open → Open**.
   (Right-click is required the *first* time because the file came from a
   download; afterward a normal double-click works.)
5. Wait a few minutes until it prints **"Setup complete"**.

If right-click → Open is still blocked, run this in Terminal from inside the
folder: `xattr -d com.apple.quarantine *.command`

*(Prefer git? `git clone https://git.biohpc.swmed.edu/s248729/serial_recall.git`
works with your GitLab username/password — no SSH key needed.)*

### First launch asks for Microphone permission — allow it.

---

## 2. Running the task

There are three ways to launch, for three situations. Double-click the file
(right-click → Open the first time). Each asks for a **Subject ID** first —
this names the data folder, so use the real participant/pilot ID.

| Launcher | What it runs | Use it for |
|---|---|---|
| **`run_task.command`** | Full session: 25 lists, full timings | Real data collection |
| **`quick_pilot.command`** | 2 lists, fast encoding, **full-length recall** | Checking the whole flow + recordings in ~3 min |
| **`mic_check.command`** | No task — beep + 5 s record + playback | Confirming audio before a session |

During a session:

- Speak after the beep. The recall screen shows `* * * * * *`; a red
  countdown appears for the final 5 seconds.
- **ENTER** ends a recall period as soon as the participant is done (the
  time limit is just a backstop — nobody has to wait it out).
- **ESC** aborts the whole task cleanly at any point. Everything already
  completed is saved.

**Test mode vs. EEG mode.** The task decides by checking whether the sync
driver is installed, not by probing a USB port: `SR1_psycho.py` tries to
import the `pennsyncbox` module (a Penn-specific plugin that is not part of
standard PsychoPy). If that import fails — which it does on any machine that
just ran `setup.command`, since the plugin isn't installed there — it prints
`pennsyncbox not available -- running WITHOUT EEG sync pulses (test mode)`
and runs identically minus the physical pulses. This is the expected mode
for behavioral piloting. Two variants share all behavior and differ only in
sync hardware:

| File | Sync hardware |
|---|---|
| `SR1_psycho.py` | Penn sync box — used by `run_task.command` |
| `SR1_psycho_cpod.py` | Cedrus C-Pod (via pyxid2) — for the EEG rig |

---

## 3. Where participant data is stored

Everything lands in **`data/UT<subject>/`** inside the project folder, one
folder per subject:

| File | Contents |
|---|---|
| `UT<subject>_list<N>.wav` | Spoken recall audio for list N. The beep at the start marks retrieval onset. |
| `UT<subject>_list<N>.lst` | That list's words in presented order (used for scoring). |
| `events.csv` | Full event log: encoding, beep, recall start/end, sync-pulse times. Scoring back-fills each word's `Retrieval_index` and `Distance` here. |
| `pulses.csv` | All sync-pulse timestamps (experiment clock). |
| `math.csv` | Distractor problems, responses, and reaction times. |

**This data stays on the machine that ran the task** — the `data/` folder is
git-ignored, so recordings are never uploaded to GitLab. Back it up yourself
(the lab's secure storage / drive) before wiping a laptop.

---

## 4. Scoring the recordings

Scoring is a two-step, offline process. The task produces the audio; you
annotate it, then a script computes the numbers.

**Step 1 — Annotate with Penn TotalRecall** (free desktop app,
https://memory.psych.upenn.edu/TotalRecall). On an Apple-Silicon Mac it
needs Rosetta 2 (`softwareupdate --install-rosetta`). For each `.wav`:
open it, load the wordpool `resources/ram_wordpool_en.txt` for
autocomplete, and mark the onset of each spoken word. TotalRecall saves a
`.ann` file next to the `.wav`.

**Step 2 — Compute the measures:**

```
.venv/bin/python score_recall.py data/UT<subject>
```

This reads every `.lst` + `.ann` pair and writes **into the same
`data/UT<subject>/` folder**:

- **`scores.csv`** — one row per spoken word: output position, presented
  position, **transposition distance** (output − presented; 0 = correct
  position), outcome (correct / transposition / intrusion / repetition),
  onset time, and EEG-aligned timestamp.
- **`summary.csv`** — one row per list: words recalled, correct-position
  count, transposed count, **mean |transposition|**, omissions, intrusions,
  repetitions.
- **`events.csv`** — each scored word's `Retrieval_index` and `Distance`
  columns are back-filled in place (omitted words marked `omitted`).

The script skips lists that have no `.ann` yet, so you can run it partway
through annotating. Full definitions and the EEG-alignment formula are in
[README_scoring.md](README_scoring.md).

---

## 5. Configuration

All timings and list parameters live in the `CONFIG` dict at the top of the
task file: number of lists, words per list (10–12 per the design docs),
word/ISI durations, math trials, beep frequency, recall duration, countdown
length, and UI colors. Change a value there and every run picks it up.

---

## Pilot checklist

1. Run `mic_check.command` — confirm the beep and your voice are both audible.
2. Run `quick_pilot.command` — confirm `data/UT<id>/` fills with a `.wav`
   and `.lst` per list, and that you had enough time to say all 10 words.
3. Play back a `.wav` — the beep, then clear speech.
4. Note anything confusing in the on-screen instructions.
