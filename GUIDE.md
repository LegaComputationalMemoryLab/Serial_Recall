# SR1 Serial Recall — Complete Guide

Everything you need to install, run, store data from, and score the SR1
serial recall task. Written for the Lega Lab (Texas Computational Memory
Lab, UT Southwestern) and for colleagues joining the project.

**Contents**
1. [What the task does](#1-what-the-task-does)
2. [Install (one time)](#2-install-one-time)
3. [Running the task](#3-running-the-task)
3a. [Sync hardware: test mode vs. EEG (neural timing)](#3a-sync-hardware-test-mode-vs-eeg-neural-timing)
4. [Where participant data is stored](#4-where-participant-data-is-stored)
5. [Scoring with Penn TotalRecall](#5-scoring-with-penn-totalrecall)
6. [Onboarding a new colleague — step by step](#6-onboarding-a-new-colleague--step-by-step)
7. [Configuration & troubleshooting](#7-configuration--troubleshooting)

---

## 1. What the task does

One **list** at a time, repeated 25 times per full session:

1. **Fixation** — a `+` appears.
2. **Encoding** — 10 words are shown one at a time.
3. **Math distractor** — a few true/false arithmetic problems (T/F keys).
   This blocks rehearsal between seeing the words and recalling them.
4. **Beep** — signals it is time to recall.
5. **Vocal recall** — the participant **says the words out loud, in the
   order they were shown**, while the microphone records. One `.wav` per
   list. ENTER ends recall early; a countdown warns of the time limit.

The key measure is **serial-order accuracy / transposition** — not just
which words were recalled, but whether they were recalled in the right
positions. That is scored offline (Section 5).

There is **no typing or drag-and-drop of words** — recall is entirely
spoken and captured as audio.

---

## 2. Install (one time)

**Requirements:** a Mac (tested on Apple Silicon, macOS 15+), a working
microphone (built-in is fine), and speaker volume up so the beep is audible.
No prior Python setup is needed — the installer builds its own environment
inside the project folder.

1. Get the project folder onto the Mac (see Section 6 for the GitLab
   download steps if you don't already have it).
2. In the folder, **right-click `setup.command` → Open → Open**.
   (Right-click is required the first time only, because macOS quarantines
   downloaded files.)
3. Wait a few minutes until it prints **"Setup complete"**. It installs a
   private Python 3.10 + PsychoPy environment in a `.venv` subfolder.

If macOS still blocks it, run this in Terminal from inside the folder:

```
xattr -d com.apple.quarantine *.command
```

The **first time you run the task**, macOS asks for **Microphone**
permission — click **Allow**. (If you miss it: System Settings → Privacy &
Security → Microphone → enable Terminal / Python.)

---

## 3. Running the task

Launch by double-clicking a `.command` file (right-click → Open the first
time). Each one first asks for a **Subject ID** — this names the data
folder, so enter the real participant/pilot ID.

| Launcher | What it runs | When to use it |
|---|---|---|
| **`mic_check.command`** | No task. Beep + records 5 s + plays it back + reports levels. | Before every session, to confirm audio works. |
| **`quick_pilot.command`** | 2 lists, fast encoding, **full-length recall**. ~3 min. | To check the whole flow and that files save. |
| **`run_task.command`** | Full session: 25 lists, full timings. ~30–40 min. | Real data collection. |

**During a session:**
- After the beep, the recall screen shows `* * * * * *`. The participant
  speaks the words in order.
- **ENTER** — finish a list's recall as soon as the participant is done.
  The time limit is only a backstop; a red countdown appears in the final
  seconds.
- **ESC** — abort the whole task cleanly at any point. Everything already
  completed is saved; nothing is lost.

See **Section 3a** below for how the task decides whether to send EEG sync
pulses — and how to turn neural timing on when you have the hardware.

---

## 3a. Sync hardware: test mode vs. EEG (neural timing)

**There is no on/off switch or settings menu.** What the task does is
decided by two things: *which script you launch* and *whether that script's
sync driver + device are actually present*.

### If you are collecting behavior only (no EEG) — e.g. healthy controls

**Just use `run_task.command`. Do nothing else.** Unless the Penn sync-box
driver has been installed on the machine (it is not part of a normal
`setup.command` install), the script prints:

```
pennsyncbox not available -- running WITHOUT EEG sync pulses (test mode)
```

and runs **identically** to EEG mode except that no physical pulses are
emitted. All timing is still recorded (`pulses.csv`, and the
`Encoding_Pulse` / `Retrieval_Time` columns of `events.csv`), audio still
records, and scoring works exactly the same. This is the correct, expected
mode for a behavioral-only lab — you do not need a sync box or a C-Pod, and
there is nothing to configure.

### Which script drives which hardware

The hardware is chosen by *which file you run* — the two variants are
behaviorally identical and differ only in the sync device:

| Script | Sync hardware | How to launch |
|---|---|---|
| `SR1_psycho.py` | Penn sync box | `run_task.command` (double-click) |
| `SR1_psycho_cpod.py` | Cedrus C-Pod | Terminal: `.venv/bin/python SR1_psycho_cpod.py` |

`run_task.command` **always** launches the Penn-sync-box script. There is no
double-click launcher for the C-Pod version — you start it from Terminal in
the project folder (see below).

Each script decides by checking its **driver**, not by probing a USB port.
`SR1_psycho.py` simply tries to import the `pennsyncbox` module: if that
import succeeds it sends pulses, otherwise it drops to test mode. (So for the
Penn sync box, "detected" really means "the driver plugin is installed" —
normally you install that driver on the same machine the box is wired to, so
the two coincide.) `SR1_psycho_cpod.py` is stricter: it imports `pyxid2`
*and* actively queries for a connected C-Pod, erroring out if the driver is
present but no device is found. Either way you never edit code to switch
modes — you set up the hardware/driver and run the matching script.

### Turning on neural timing (EEG mode)

**Penn sync box:** connect the sync box to the machine and the EEG's DC
channels, then run `run_task.command` as usual. If the `pennsyncbox` driver
loads, pulses are sent automatically (no "test mode" message).

**Cedrus C-Pod:** three prerequisites, in order —
1. **Install the FTDI system driver.** `pyxid2` (already in
   `requirements.txt`) cannot talk to the C-Pod without Cedrus/FTDI's native
   library `libftd2xx.dylib`. Without it, `import pyxid2` fails and the
   script silently stays in test mode. Install it from Cedrus/FTDI on the
   rig machine first. *(This is why the C-Pod only works at the rig, not on
   a laptop that just ran `setup.command`.)*
2. **Plug in the C-Pod** and connect it to the EEG's DC channels.
3. **Launch from Terminal** in the project folder:
   `.venv/bin/python SR1_psycho_cpod.py`

The C-Pod script then opens with a **SyncPulseTest**: it fires 7 pulses and
asks you to confirm they appeared on the clinical EEG's DC channels (press
**Y** to proceed, **N** to abort and check the wiring). Run this once at the
start of every EEG session to verify alignment before collecting data.

> **Note:** if the FTDI driver is installed but no C-Pod is detected, the
> C-Pod script **stops with an error** (`Unable to find the C-pod, is it
> plugged in?`) rather than quietly running without EEG sync. This is
> deliberate — at the rig you want it to refuse to run rather than lose the
> neural markers. Behavioral-only users are unaffected because they use
> `run_task.command`, not the C-Pod script.

### How neural timing lines up with the recordings

Either sync device emits a pulse at every key event (each word onset, the
retrieval beep, and `RecordingStart`). The `RecordingStart` pulse marks
audio t=0, so once recall is annotated:

```
EEG time of a vocalization = RecordingStart pulse time + (annotation onset in ms / 1000)
```

`score_recall.py` fills this in automatically as the `eeg_time_sec` column
(see Section 5). Because pulse **timestamps** are logged even in test mode,
switching a behavioral protocol to EEG later requires no changes to the data
pipeline — only the physical hardware.

---

## 4. Where participant data is stored

All output goes to **`data/UT<subject>/`** inside the project folder — one
folder per subject. Nothing is uploaded anywhere automatically.

| File | Contents |
|---|---|
| `UT<subject>_list<N>.wav` | Recall audio for list N. The beep at the start marks retrieval onset. |
| `UT<subject>_list<N>.lst` | That list's words in presented order (used by scoring). |
| `events.csv` | Full event log: encoding, beep, recall start/end, sync-pulse times. After scoring, each word's `Retrieval_index` and `Distance` are back-filled here too. |
| `pulses.csv` | Every sync-pulse timestamp (experiment clock). |
| `math.csv` | Distractor problems, responses, reaction times. |
| `scores.csv`, `summary.csv` | Added **after** scoring (Section 5). |

**Important:** the `data/` folder is **git-ignored** — recordings are never
committed or pushed to GitLab. This protects participant data and keeps the
repo small. **Back the folder up yourself** to the lab's secure storage
before wiping or handing off a laptop. Only *code* lives in GitLab; *data*
lives on the machine that collected it.

---

## 5. Scoring with Penn TotalRecall

Scoring is **offline and two-step**: the task records the audio, a human
annotates each word's onset in Penn TotalRecall, then a script computes the
numbers. TotalRecall does **not** transcribe automatically — it is a manual
annotation tool that shows you the waveform; you mark the words.

### Step 1 — Install Penn TotalRecall

Free desktop app: https://memory.psych.upenn.edu/TotalRecall. On an
Apple-Silicon Mac it needs Rosetta 2 — install with:

```
softwareupdate --install-rosetta
```

### Step 2 — Annotate each recording

1. **File → Open** an audio file, e.g. `data/UT<subject>/UT<subject>_list1.wav`.
   Its waveform appears.
2. Load the wordpool `resources/ram_wordpool_en.txt` so typed words
   autocomplete.
3. For **each spoken word**:
   - **Space** — play/pause. Find the next word. (Skip past the initial
     beep — that's your onset reference, not a recalled word.)
   - Position the cursor at the word's **onset** with the arrow keys:
     **← / →** = 5 ms, **⌘←/→** = 50 ms, **⇧⌘←/→** = 500 ms.
   - **⌘Z** replays the 200 ms *before* the cursor. The cursor is right on
     the onset when ⌘Z is silent, but one arrow forward lets you just barely
     hear the first sound.
   - **Type the word**, press **Tab** to autocomplete to the top match.
   - **Enter** commits it as a recall. For an intrusion / non-word
     vocalization use **⌘⇧Enter** instead.
4. When the list is done, **⌘⇧D** (or the **Mark Complete** button) writes
   the final **`.ann`** file next to the `.wav`.

Penn's video tutorials (https://memory.psych.upenn.edu/Annotation_tutorial_videos)
and text guide (https://memory.psych.upenn.edu/AnnotationGuide) are worth
watching before training annotators. Expect a few minutes per list.

### Step 3 — Compute the measures

Once `.ann` files exist, run:

```
.venv/bin/python score_recall.py data/UT<subject>
```

It reads every `.lst` + `.ann` pair and writes **into the same subject
folder**:

- **`scores.csv`** — one row per spoken word: output position, presented
  position, **transposition distance** (output − presented; 0 = correct
  position), outcome (correct / transposition / intrusion / repetition),
  onset in ms, and the EEG-aligned timestamp.
- **`summary.csv`** — one row per list: words recalled, correct-position
  count, transposed count, **mean |transposition|**, omissions, intrusions,
  repetitions.
- **`events.csv`** — the reserved `Retrieval_index` and `Distance` columns
  on each scored list's `Encoding` rows are filled in with the word's output
  position and transposition (omitted words are marked `omitted`), so the
  recall result lives alongside the presentation timing.

The script skips lists with no `.ann` yet, so you can run it partway
through. Full metric definitions and the EEG-alignment formula are in
[README_scoring.md](README_scoring.md).

### How it ties to EEG

Every list's recording starts with a `RecordingStart` sync pulse, logged in
`events.csv`. Audio time zero corresponds to that pulse, so:

```
EEG time of a vocalization = RecordingStart pulse time + (annotation onset in ms / 1000)
```

`score_recall.py` fills this in as the `eeg_time_sec` column automatically.

---

## 6. Onboarding a new colleague — step by step

Give a new lab member this exact sequence. **No git, SSH keys, or terminal
experience required.**

1. **Get added to the repo.** The project owner does: GitLab → the
   `serial_recall` project → **Manage → Members → Invite member** → your
   UTSW username → role **Reporter** (enough to download).
2. **Download the code.** Open
   `https://git.biohpc.swmed.edu/s248729/serial_recall` in a browser, log in,
   click the blue **Code** button → **Download source code → zip**.
3. **Unzip** it anywhere (e.g. the Desktop).
4. **Install.** Right-click **`setup.command` → Open → Open**; wait for
   "Setup complete" (a few minutes).
5. **Test audio.** Right-click **`mic_check.command` → Open**; allow the
   microphone; speak when prompted; confirm you hear the beep and your voice
   played back.
6. **Do a quick pilot.** Right-click **`run_task.command` → Open** (or
   `quick_pilot.command` for a fast 2-list check). Enter a subject ID and
   run through it.
7. **Find the data.** Look in `data/UT<your-id>/` for the `.wav` and `.lst`
   files plus the CSV logs.
8. **To score:** install Penn TotalRecall (Section 5), annotate, then run
   `score_recall.py`.

*(Comfortable with git instead of the zip? `git clone
https://git.biohpc.swmed.edu/s248729/serial_recall.git` works with your
GitLab username/password — no SSH key needed.)*

**Collaborating on the code:** the repo is the single source of truth. Pull
before you edit, and remember that participant `data/` is intentionally not
shared through GitLab — coordinate secure data storage separately.

---

## 7. Configuration & troubleshooting

**All timings and list parameters** live in the `CONFIG` dict at the top of
`SR1_psycho.py` (mirror any change into `SR1_psycho_cpod.py`): number of
lists, words per list (10–12 per the design docs), word/ISI durations, math
trials, beep frequency, `recall_duration`, countdown length, and UI colors.
Change a value there and the next run uses it.

| Symptom | Fix |
|---|---|
| Beep is faint or inaudible | Turn the Mac's output volume up; `mic_check.command` warns when it's too low. |
| It records from an iPhone, not the Mac | Already handled — the task explicitly selects the built-in MacBook mic and prints which device it's using. Disconnecting the iPhone / turning off Continuity also works. |
| "No microphone available" error | Grant Microphone permission (System Settings → Privacy & Security → Microphone) and reconnect a mic. |
| macOS blocks a `.command` file | Right-click → Open, or `xattr -d com.apple.quarantine *.command`. |
| Recall felt too short | Raise `recall_duration` in `CONFIG`; ENTER always ends a list early regardless. |
| Frame-rate screen hangs at startup | Already handled (`checkTiming=False`); update to the latest version if you see it. |

**Questions on the task code:** see this repo. **Questions on annotation:**
Penn's guide and `memory-software@psych.upenn.edu`.
