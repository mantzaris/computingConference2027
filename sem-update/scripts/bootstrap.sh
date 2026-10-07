#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export SEM_UPDATE_ARTIFACT_ROOT="${SEM_UPDATE_ARTIFACT_ROOT:-$PWD/.artifacts}"
export PIP_CACHE_DIR="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/pip"
export HF_HOME="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/huggingface"
export MPLCONFIGDIR="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/matplotlib"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export HF_HUB_ENABLE_HF_TRANSFER=0
export PYTHONPYCACHEPREFIX="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/pycache"
export TMPDIR="$SEM_UPDATE_ARTIFACT_ROOT/tmp"
mkdir -p "$SEM_UPDATE_ARTIFACT_ROOT/logs"
mkdir -p "$TMPDIR"
python3 -m venv --system-site-packages "$SEM_UPDATE_ARTIFACT_ROOT/venv"
"$SEM_UPDATE_ARTIFACT_ROOT/venv/bin/python" -m pip install -r requirements.lock
"$SEM_UPDATE_ARTIFACT_ROOT/venv/bin/python" -m pip install --no-deps -e .
"$SEM_UPDATE_ARTIFACT_ROOT/venv/bin/python" -m sem_update.cli doctor
