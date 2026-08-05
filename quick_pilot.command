#!/bin/bash
# Quick debug run: 2 short lists (10 s recall each), identical code path
# to the real task. Use this to verify recordings are saved without
# sitting through a full session.
cd "$(dirname "$0")"
SR1_QUICK=1 exec .venv/bin/python SR1_psycho.py
