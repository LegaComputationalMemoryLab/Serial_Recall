#!/bin/bash
# One-time setup for the SR1 serial recall task (macOS).
# Double-click this file in Finder, or run ./setup.command in a terminal.
# It installs a private Python 3.10 environment with PsychoPy -- nothing
# outside this folder is modified (except installing uv if missing).
set -e
set -o pipefail
cd "$(dirname "$0")"

echo "=== SR1 setup ==="

# 1. uv (fast Python installer) -- install if missing.
# Primary method is the official astral.sh installer. Some university /
# corporate networks (or a VPN) block astral.sh, which shows up as
# "curl: (6) Could not resolve host: astral.sh". Fall back to Homebrew or
# pip so setup still completes on those networks.
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
    echo "Installing uv..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        :
    elif command -v brew >/dev/null 2>&1; then
        echo "astral.sh unreachable -- installing uv via Homebrew instead..."
        brew install uv
    elif command -v pip3 >/dev/null 2>&1; then
        echo "astral.sh unreachable -- installing uv via pip3 instead..."
        pip3 install --user uv
    else
        echo "" >&2
        echo "ERROR: could not install 'uv'." >&2
        echo "Your machine could not reach astral.sh, and neither Homebrew" >&2
        echo "nor pip3 is available as a fallback." >&2
        echo "Fixes: connect to the internet / turn off VPN and re-run, or" >&2
        echo "install Homebrew (https://brew.sh) then double-click this file again." >&2
        exit 1
    fi
fi
export PATH="$HOME/.local/bin:$PATH"

# 2. Python 3.10 venv (PsychoPy does not support newer system Pythons)
if [ ! -x .venv/bin/python ]; then
    echo "Creating Python 3.10 environment..."
    uv venv --python 3.10 .venv
fi

# 3. Dependencies
echo "Installing PsychoPy and dependencies (this can take a few minutes)..."
uv pip install --python .venv/bin/python -r requirements.txt

# 4. Quick self-check: imports, window config, mic backend
echo "Running self-check..."
.venv/bin/python - <<'EOF'
from psychopy import prefs
prefs.hardware['audioLib'] = ['sounddevice']
from psychopy import sound, visual, core, event, data, gui
try:
    from psychopy.sound import Microphone
except Exception:
    from psychopy.sound.microphone import Microphone
from psychopy.hardware.microphone import MicrophoneDevice
MicrophoneDevice.backend = 'sounddevice'
print("PsychoPy imports OK")
EOF

echo ""
echo "=== Setup complete ==="
echo "Run the task by double-clicking run_task.command"
echo "(macOS will ask for Microphone permission on first run -- allow it.)"
