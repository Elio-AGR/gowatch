#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SCRIPT_DIR}/venv/bin/python"
GOWATCH_PY="${SCRIPT_DIR}/gowatch.py"
TARGET_DIR="${HOME}/.local/bin"
TARGET_FILE="${TARGET_DIR}/gowatch"

echo "[gowatch] Installing gowatch CLI wrapper..."

# Ensure target directory exists
mkdir -p "${TARGET_DIR}"

# Ensure source python script is executable
chmod +x "${GOWATCH_PY}"

# Create bash launcher script
cat << EOF > "${TARGET_FILE}"
#!/bin/bash
exec "${PYTHON_BIN}" "${GOWATCH_PY}" "\$@"
EOF

chmod +x "${TARGET_FILE}"

echo "[gowatch] Successfully installed launcher script at ${TARGET_FILE}"

if [[ ":$PATH:" != *":${TARGET_DIR}:"* ]]; then
    echo "[gowatch] Note: Make sure '${TARGET_DIR}' is in your PATH environment variable."
fi
