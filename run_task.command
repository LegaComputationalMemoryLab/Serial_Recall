#!/bin/bash
# Launcher for the SR1 serial recall task.
# Double-click this file in Finder, or run ./run_task.command in a terminal.
cd "$(dirname "$0")"
exec .venv/bin/python SR1_psycho.py

