"""
SR1 -- Serial Recall Task
Texas Computational Memory Lab (Lega Lab), UT Southwestern Medical Center

Task flow per list:
  fixation -> word presentation (encoding) -> math distractor (prevents
  rehearsal) -> beep -> participant vocalizes the words in serial order
  while audio is recorded (one .wav per list).

Scoring is done offline with Penn TotalRecall (see README_scoring.md):
annotators mark spoken-word onsets in each .wav, and transpositions are
computed against the presented order saved in the matching .lst file.

All timings and list parameters are configurable in CONFIG below.
"""

import random
import csv
import os
from datetime import datetime

# Playback must use the same audio library as the microphone (sounddevice),
# otherwise the retrieval beep is silent while the mic stream is open.
# This must be set BEFORE importing psychopy.sound.
from psychopy import prefs
prefs.hardware['audioLib'] = ['sounddevice']

from psychopy import event, visual, core, data, logging, sound, gui

# Sync box is optional -- without it the task runs in test mode
# (no EEG sync pulses; pulse timestamps are still logged).
try:
    from psychopy.pennsyncbox import *
    SYNCBOX_AVAILABLE = True
except Exception:
    SYNCBOX_AVAILABLE = False
    print("pennsyncbox not available -- running WITHOUT EEG sync pulses (test mode)")

# Microphone is optional -- the task still runs (without audio recording)
# if the mic backend is unavailable on this machine.
# (import location moved between PsychoPy versions, so try both)
try:
    from psychopy.sound import Microphone
    MIC_AVAILABLE = True
except Exception:
    try:
        from psychopy.sound.microphone import Microphone
        MIC_AVAILABLE = True
    except Exception:
        MIC_AVAILABLE = False

if MIC_AVAILABLE:
    # The sounddevice backend records reliably on macOS; the psychtoolbox
    # backend can return an empty buffer.
    try:
        from psychopy.hardware.microphone import MicrophoneDevice
        MicrophoneDevice.backend = 'sounddevice'
    except Exception:
        pass

def find_builtin_mic():
    """Device index of the Mac's built-in microphone, or None for default.

    macOS Continuity can silently switch the default input to a nearby
    iPhone; always preferring the built-in mic keeps recordings on the
    laptop's own microphone.
    """
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        for want in ('macbook', 'built-in'):
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0 and want in d['name'].lower():
                    print(f"Using microphone: {d['name']}")
                    return i
    except Exception:
        pass
    print("Built-in microphone not found -- using system default input")
    return None

# ============================== CONFIG ==============================
CONFIG = {
    # --- List structure ---
    'n_lists': 25,
    'words_per_list': 10,          # documentation specifies 10-12

    # --- Timings (seconds) ---
    'fixation_duration': 1.0,
    'word_duration': 1.6,
    'isi_base': 0.8,
    'isi_jitter': 0.5,             # ISI = isi_base + uniform(-jitter, +jitter)
    'math_n_trials': 5,            # distractor trials between encoding and recall
    'math_feedback_duration': 1.0,

    # --- Vocal recall period ---
    'beep_freq_hz': 800,
    'beep_duration': 0.4,
    'pre_beep_delay': 0.5,         # blank gap between the distractor and the beep
    'recall_duration': 45.0,       # max seconds of vocal recall per list (ENTER ends sooner)
    'recall_countdown_secs': 5,    # show a countdown for the final N seconds
    'allow_early_end': True,       # ENTER ends the recall period early
    'mic_sample_rate': 44100,      # standard rate for Penn TotalRecall scoring

    # --- Plain UI colors (cream / dark green) ---
    'bg_color': '#F4F1EA',
    'text_color': '#1F1F1F',
    'muted_color': '#8A8A85',
    'accent_color': '#1F5148',
    'error_color': '#8C3B3B',
}

# Quick pilot mode (launched via quick_pilot.command, or SR1_QUICK=1):
# 2 short lists through the identical code path, for debugging that
# recordings and data files are produced without a full session.
if os.environ.get('SR1_QUICK'):
    CONFIG.update({
        'n_lists': 2,
        'fixation_duration': 0.5,
        'word_duration': 0.8,
        'isi_base': 0.3,
        'isi_jitter': 0.1,
        'math_n_trials': 2,
        # Recall keeps the full window -- participants still need time to
        # remember and say all the words; only encoding/distractor are sped up.
    })
    print(f"QUICK PILOT MODE: 2 short lists, {CONFIG['recall_duration']:.0f} s recall "
          "(ENTER to finish a list early)")
# ====================================================================

# Paths are relative to this script so the task runs from any location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORDPOOL_PATH = os.path.join(SCRIPT_DIR, 'resources', 'ram_wordpool_en.txt')
LOGO_PATH = os.path.join(SCRIPT_DIR, 'resources', 'LegaLab_cropped.png')

# Get subject number
correctSubj = False
while not correctSubj:
    dlg = gui.Dlg(title="SR1")
    dlg.addField("Subject ID:")
    dlg.show()
    if dlg.OK and dlg.data[0].strip():
        subject = dlg.data[0].strip()
        correctSubj = True

# Store subject info
exp_info = {'subject': subject}

subject_dir = os.path.join(SCRIPT_DIR, f"data/UT{subject}")
LOG_PATH = os.path.join(subject_dir, "events.csv")
PULSE_PATH = os.path.join(subject_dir, "pulses.csv")
MATH_PATH = os.path.join(subject_dir, "math.csv")

if not os.path.exists(subject_dir):
    os.makedirs(subject_dir)

if not os.path.exists(PULSE_PATH):
    with open(PULSE_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["PulseTime_Sec"])

if not os.path.exists(MATH_PATH):
    with open(MATH_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Problem", "CorrectAnswer", "KeyPressed", "IsCorrect",
            "RT_sec", "PulseTime_sec", "AbsoluteTime_sec", "RealTime"
        ])

# Create an experiment clock
exp_clock = core.Clock()

def log_event(*columns):
    eventTime = exp_clock.getTime()
    real_time = datetime.now()
    row = list(columns) + [eventTime, real_time]
    new_file = not os.path.isfile(LOG_PATH)
    with open(LOG_PATH, mode='a', newline='') as f:
        writer = csv.writer(f)
        if new_file:
            header = [
                "Event_type",
                "List",
                "Word",
                "Trial_index",       # position the word was presented in
                "Retrieval_index",   # output position at recall (filled by score_recall.py)
                "Distance",          # transposition = output - presented (filled by score_recall.py)
                "Encoding_Pulse",
                "Retrieval_Time",
                "EventTime_Sec",
                "RealTime"
            ]
            writer.writerow(header)
        writer.writerow(row)

    return eventTime

log_event("ExperimentStart", "", "", "", "", "", "", "")

def wait_check_escape(duration):
    """core.wait replacement so ESCAPE can cleanly abort at any point."""
    timer = core.CountdownTimer(duration)
    while timer.getTime() > 0:
        if event.getKeys(keyList=['escape']):
            log_event("ExperimentAborted", "", "", "", "", "", "", "")
            core.quit()
        core.wait(0.01)

# Sync USB
if SYNCBOX_AVAILABLE:
    CloseUSB()
    OpenUSB()
    CloseUSB()
    OpenUSB()

pulse_times = []

def send_sync_pulse():
    if SYNCBOX_AVAILABLE:
        SyncPulse()
    pulse_time = exp_clock.getTime()
    pulse_times.append(pulse_time)

    with open(PULSE_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([f"{pulse_time:.3f}"])

    return pulse_time

# Set up window
win = visual.Window(
     size=[1728, 1117],
     fullscr=True,
     monitor='testMonitor',
     color=CONFIG['bg_color'],
     units='pix',
     allowStencil=False,
     useFBO=False,
     allowGUI=True,
     checkTiming=False  # frame-rate measurement can hang on ProMotion displays
 )

# Retrieval beep
beep = sound.Sound(CONFIG['beep_freq_hz'], secs=CONFIG['beep_duration'])

# Microphone for recording vocalized recall -- REQUIRED, since spoken
# responses are the only recall data this task collects
mic = None
if MIC_AVAILABLE:
    try:
        mic = Microphone(device=find_builtin_mic(), channels=1,
                         sampleRateHz=CONFIG['mic_sample_rate'],
                         maxRecordingSize=256000)
    except Exception as e:
        print(f"Microphone failed to initialize: {e}")

if mic is None:
    err_text = visual.TextStim(
        win,
        text="ERROR: No microphone is available.\n\n"
             "This task records spoken recall, so it cannot run without one.\n"
             "Connect a microphone and restart.\n\n"
             "Press any key to exit.",
        color=CONFIG['error_color'],
        height=36,
        wrapWidth=1200
    )
    err_text.draw()
    win.flip()
    event.waitKeys()
    log_event("NoMicrophone_Abort", "", "", "", "", "", "", "")
    core.quit()

# SyncPulseTest function
def SyncPulseTest(win, exp_info, n_pulses=7, isi=1.0):
    # 1. Instruction screen
    SyncText = "PRESS ANY KEY TO START SYNC PULSE TEST"
    start_text = visual.TextStim(
        win,
        text=SyncText,
        color=CONFIG['text_color'],
        height=40,
        wrapWidth=1000
    )
    start_text.draw()
    win.flip()
    event.waitKeys()  # wait for any key

    # 2. Send N sync pulses, 1 second apart (or whatever isi you choose)
    for i in range(n_pulses):
        send_sync_pulse()
        log_event(f"SyncPulse_{i+1}", "", "", "", "", "", "", "")
        core.wait(isi)

    # 3. Ask for confirmation
    sync_quest = (
        "Did you see sync pulses on clinical EEG?\n"
        "\n"
        "If YES, press 'Y' to continue.\n"
        "\n"
        "If NO, press 'N' to exit the experiment and\n"
        "check the DC channels and sync set-up.\n"
    )
    prompt = visual.TextStim(
        win,
        text=sync_quest,
        color=CONFIG['text_color'],
        height=48,
        wrapWidth=1000
    )
    prompt.draw()
    win.flip()

    # 4. Wait for Y/N
    keys = event.waitKeys(keyList=['y', 'n'])
    if 'n' in keys:
        log_event('SyncTest_Failed', "", "", "", "", "", "", "")
        core.quit()
    else:
        log_event('SyncTest_Passed', "", "", "", "", "", "", "")

# Usage: only meaningful when the sync box is connected
if SYNCBOX_AVAILABLE:
    SyncPulseTest(win, exp_info)
else:
    log_event('SyncTest_Skipped', "", "", "", "", "", "", "")


# Define logo
def LegaLab(win):
    # Cropped logo is 674x609; display at the same aspect ratio
    logo = visual.ImageStim(win, image=LOGO_PATH, pos=(0, 0), size=(554, 500))
    top_label = visual.TextStim(win, text="Texas Computational Memory Lab",
                                pos=(0, 330), height=32, color=CONFIG['text_color'])
    bottom_label = visual.TextStim(win, text="UT Southwestern Medical Center",
                                   pos=(0, -330), height=32, color=CONFIG['text_color'])

    logo.draw()
    top_label.draw()
    bottom_label.draw()

    # Flip to show
    win.flip()

    # Wait for 3 seconds
    wait_check_escape(3)

LegaLab(win)

# Show instructions
instructions = (
    "In this task you will see a list of words one at a time on the screen. "
    "Try to remember the ORDER of the words you see.\n\n"
    "After each list you will solve short math problems. Then you will hear a BEEP. "
    "After the beep, say the words OUT LOUD in the order they were shown. "
    "If you cannot remember a word, say the next word you do remember.\n\n"
    "This task is meant to be difficult -- just try your best.\n"
    "Press any key to begin."
)
intro_text = visual.TextStim(win, text=instructions, color=CONFIG['text_color'],
                             height=32, wrapWidth=1000)
intro_text.draw()
win.flip()
event.waitKeys()
log_event('InstructRead', "", "", "", "", "", "", "")

# Load word pool
def load_words(file_path):
    with open(file_path, 'r') as f:
        words = f.readlines()
    return [word.strip() for word in words if word.strip()]

words_list = load_words(WORDPOOL_PATH)

def create_stimuli(selected_words):
    return [{'word': word} for word in selected_words]

n_lists = CONFIG['n_lists']
words_per_list = CONFIG['words_per_list']
available_words = words_list.copy()
random.shuffle(available_words)

for list_num in range(1, n_lists + 1):
    if len(available_words) < words_per_list:
        raise ValueError("Not enough words left in the pool to run all lists.")

    selected_words = available_words[:words_per_list]
    available_words = available_words[words_per_list:]

    # === Fixation Cross before Encoding ===
    fixation = visual.TextStim(win, text='+', color=CONFIG['text_color'], height=80)
    fixation.draw()
    win.flip()
    wait_check_escape(CONFIG['fixation_duration'])
    log_event("Fixation_Cross", list_num, "", "", "", "", "", "")

    stimList = create_stimuli(selected_words)
    trials = data.TrialHandler(stimList, nReps=1, method='random', name=f'list_{list_num}')

    # === Encoding Phase ===
    encoding_info = {}
    presented_order = []   # words in the order shown, for the .lst file

    for trial_index, trial in enumerate(trials, start=1):
        word_text = trial['word']
        word_stim = visual.TextStim(win, text=word_text, pos=(0, 0),
                                    color=CONFIG['text_color'],
                                    font='Helvetica', height=70)
        word_stim.draw()
        win.flip()
        wait_check_escape(CONFIG['word_duration'])

        isi_duration = CONFIG['isi_base'] + random.uniform(-CONFIG['isi_jitter'],
                                                           CONFIG['isi_jitter'])
        win.flip()
        wait_check_escape(isi_duration)

        encoding_pulse = send_sync_pulse()

        encoding_info[word_text] = {
            'presented_index': trial_index,
            'encoding_pulse': encoding_pulse
        }
        presented_order.append(word_text)

        log_event(
            "Encoding",
            list_num,
            word_text,
            trial_index,
            "",
            "",
            f"{encoding_pulse:.3f}",
            ""
        )

    # === Math distractor (prevents rehearsal between encoding and recall) ===
    instruction = visual.TextStim(
        win,
        text="Is this correct? Press 'T' for True or 'F' for False",
        pos=(0, 250),
        height=40,
        color=CONFIG['text_color'],
        wrapWidth=1200
    )

    question = visual.TextStim(
        win,
        text='',
        pos=(0, 100),
        height=80,
        color=CONFIG['text_color']
    )

    feedback = visual.TextStim(
        win,
        text='',
        pos=(0, -200),
        height=50,
        color=CONFIG['accent_color']
    )

    nTrials = CONFIG['math_n_trials']
    problems = []

    for _ in range(nTrials):
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        op = random.choice(['+', '-'])

        correct = (a + b if op == '+' else a - b)

        # Decide if we present the correct or incorrect answer
        is_true = random.choice([True, False])
        shown_answer = correct if is_true else correct + random.choice([1, -1, 2, -2])

        problems.append((f"{a} {op} {b} = {shown_answer}", is_true))

    for probText, correctIsTrue in problems:
        # Draw and present the problem
        instruction.draw()
        question.text = probText
        question.draw()
        win.flip()

        # Send a sync pulse at math question onset
        pulse_time = send_sync_pulse()

        # Time using experiment clock
        start_time = exp_clock.getTime()
        keys = event.waitKeys(keyList=['t', 'f', 'escape'])
        if 'escape' in keys:
            log_event("ExperimentAborted", list_num, "", "", "", "", "", "")
            core.quit()
        rt = exp_clock.getTime() - start_time
        response_key = keys[0]

        user_answer = (response_key == 't')
        is_correct = user_answer == correctIsTrue
        correctness_str = "Correct" if is_correct else "Wrong"

        # Feedback
        feedback.text = correctness_str
        feedback.color = CONFIG['accent_color'] if is_correct else CONFIG['error_color']
        feedback.draw()
        win.flip()
        wait_check_escape(CONFIG['math_feedback_duration'])

        # Log to math-specific CSV
        with open(MATH_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                probText,
                correctIsTrue,
                response_key,
                is_correct,
                f"{rt:.3f}",
                f"{pulse_time:.3f}",
                f"{exp_clock.getTime():.3f}",
                datetime.now()
            ])

    # === Recall Phase: beep -> vocal serial recall (recorded) ===
    # Scoring happens offline in Penn TotalRecall (see README_scoring.md):
    # annotators mark each spoken word's onset in the .wav, and transposition
    # distances are computed against the presented order in the .lst file.

    # Write the .lst companion file (presented order) used during annotation
    audio_base = f"UT{subject}_list{list_num}"
    with open(os.path.join(subject_dir, audio_base + ".lst"), 'w') as f:
        for w in presented_order:
            f.write(w + "\n")

    # Brief blank gap after the distractor, then recall starts automatically
    # (no self-paced pause, so there is no window to rehearse in)
    win.flip()
    wait_check_escape(CONFIG['pre_beep_delay'])

    # Start recording BEFORE the beep so the beep is captured in the audio --
    # it gives annotators an unambiguous retrieval-onset marker in TotalRecall
    recording = False
    try:
        mic.start()
        rec_start = send_sync_pulse()   # aligns audio t=0 to the EEG record
        recording = True
        log_event("RecordingStart", list_num, audio_base + ".wav",
                  "", "", "", "", f"{rec_start:.3f}")
    except Exception as e:
        print(f"Could not start recording for list {list_num}: {e}")

    beep.play()
    beep_time = send_sync_pulse()
    log_event("RetrievalBeep", list_num, "", "", "", "", "", f"{beep_time:.3f}")
    log_event("RecallPhase_Started", list_num, "", "", "", "", "", "")

    # Plain recall screen while the participant speaks
    recall_marker = visual.TextStim(
        win,
        text='* * * * * *',
        color=CONFIG['accent_color'],
        height=70
    )
    recall_hint = visual.TextStim(
        win,
        text="Say the words in the order they were shown\nPress ENTER when you are done",
        pos=(0, -200),
        height=28,
        color=CONFIG['muted_color']
    )
    countdown = visual.TextStim(
        win,
        text='',
        pos=(0, -320),
        height=32,
        color=CONFIG['error_color']
    )

    event.clearEvents()
    recall_timer = core.Clock()
    ended_early = False
    while recall_timer.getTime() < CONFIG['recall_duration']:
        if recording:
            try:
                mic.poll()
            except Exception:
                pass

        keys = event.getKeys(keyList=['return', 'escape'])
        if 'escape' in keys:
            log_event("ExperimentAborted", list_num, "", "", "", "", "", "")
            core.quit()
        if CONFIG['allow_early_end'] and 'return' in keys:
            ended_early = True
            break

        recall_marker.draw()
        recall_hint.draw()
        # Warn the participant when the recall window is about to close
        remaining = CONFIG['recall_duration'] - recall_timer.getTime()
        if remaining <= CONFIG['recall_countdown_secs']:
            countdown.text = str(int(remaining) + 1)
            countdown.draw()
        win.flip()

    log_event("RecallPhase_Ended", list_num,
              "EarlyEnd" if ended_early else "Timeout", "", "", "", "", "")

    # Save the vocal recall recording.
    # The clip must be grabbed BEFORE stop() (stop unbinds from the device),
    # and the buffer cleared so the next list starts fresh.
    if recording:
        try:
            mic.poll()   # capture the final buffered audio before fetching
            audio_clip = mic.getRecording()
            mic.stop()
            mic.clear()
            if audio_clip is not None:
                audio_path = os.path.join(subject_dir, audio_base + ".wav")
                audio_clip.save(audio_path)
                log_event("RecallAudioSaved", list_num, audio_base + ".wav",
                          "", "", "", "", "")
            else:
                print(f"No audio captured for list {list_num}")
        except Exception as e:
            print(f"Could not save recording for list {list_num}: {e}")

# === End screen ===
end_text = visual.TextStim(win, text="Thank you for participating!\nPress any key to exit.",
                           color=CONFIG['text_color'])
end_text.draw()
win.flip()
event.waitKeys()

# Cleanup
if mic is not None:
    try:
        mic.close()
    except Exception:
        pass
win.close()
core.quit()
