#!/bin/bash
# Quick microphone check -- verifies audio recording works WITHOUT running
# the task. Plays the retrieval beep, records 5 seconds (say a few words!),
# saves the file, reports levels, and plays the recording back to you.
cd "$(dirname "$0")"
exec .venv/bin/python - <<'EOF'
import time
import os
import wave
import subprocess
import numpy as np

from psychopy import prefs
prefs.hardware['audioLib'] = ['sounddevice']
from psychopy import sound
try:
    from psychopy.sound import Microphone
except Exception:
    from psychopy.sound.microphone import Microphone
from psychopy.hardware.microphone import MicrophoneDevice
MicrophoneDevice.backend = 'sounddevice'

print()
print("=== SR1 microphone check ===")
print("You will hear the beep, then have 5 seconds to SPEAK A FEW WORDS.")
time.sleep(2)

# Prefer the built-in MacBook mic -- macOS Continuity can silently make a
# nearby iPhone the default input device
import sounddevice as sd
mic_device = None
for want in ('macbook', 'built-in'):
    if mic_device is None:
        for i, d in enumerate(sd.query_devices()):
            if d['max_input_channels'] > 0 and want in d['name'].lower():
                mic_device = i
                print(f"Using microphone: {d['name']}")
                break
if mic_device is None:
    print("Built-in microphone not found -- using system default input")

mic = Microphone(device=mic_device, channels=1, sampleRateHz=44100,
                 maxRecordingSize=256000)
beep = sound.Sound(800, secs=0.4)

mic.start()
beep.play()
print("Recording... speak now!")
t0 = time.time()
while time.time() - t0 < 5.0:
    mic.poll()
    time.sleep(0.05)

clip = mic.getRecording()
mic.stop()
mic.clear()

os.makedirs('data', exist_ok=True)
out = os.path.join('data', 'mic_check.wav')
clip.save(out)
mic.close()

with wave.open(out) as w:
    rate = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16) / 32768.0
beep_rms = float(np.sqrt(np.mean(a[:int(0.6 * rate)] ** 2)))
speech_rms = float(np.sqrt(np.mean(a[int(0.6 * rate):] ** 2)))

print()
print(f"Saved: {os.path.abspath(out)}  ({len(a)/rate:.1f}s at {rate} Hz)")
print(f"Beep level:   {beep_rms:.4f}  {'OK' if beep_rms > 0.02 else 'LOW -- turn the speaker volume up'}")
print(f"Speech level: {speech_rms:.4f}  {'OK' if speech_rms > 0.02 else 'LOW -- speak closer to the mic / check input volume'}")
print()
print("Playing your recording back...")
subprocess.run(['afplay', out])
print("If you heard the beep and your own voice, audio recording works.")
EOF
