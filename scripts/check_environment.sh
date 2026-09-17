#!/usr/bin/env bash

set -e

if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "ERROR: Python virtual environment is not active."
    echo "Run: source .venv/bin/activate"
    exit 1
fi

echo "=== Environment Check ==="

echo
echo "[Git]"
git --version

echo
echo "[Python]"
python --version

echo
echo "[Terraform]"
terraform version

echo
echo "[Checkov]"
checkov --version

echo
echo "[Environment]"
echo "Python executable:"
which python

echo
echo "=== Environment OK ==="
