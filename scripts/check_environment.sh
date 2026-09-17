#!/usr/bin/env bash

set -e

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
