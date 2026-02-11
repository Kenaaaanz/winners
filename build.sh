#!/usr/bin/env bash
set -o errexit

# Nuclear clean
rm -rf .venv 2>/dev/null || true
python -m venv .venv
source .venv/bin/activate

# Install with explicit version pin FIRST
pip install --upgrade pip wheel
pip install "setuptools<81"  # ← Install BEFORE your requirements

# Now install your project
poetry install  # OR pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate