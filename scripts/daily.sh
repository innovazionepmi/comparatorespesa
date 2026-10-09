#!/usr/bin/env bash
# Entrypoint per lo scheduler (una run al giorno).
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
spesa run "$@"
