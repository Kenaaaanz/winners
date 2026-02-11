#!/usr/bin/env bash
set -o errexit

# DON'T delete the entire venv - Render manages this
# Instead, just ensure setuptools is pinned

# Install dependencies
pip install -r requirements.txt

# CRITICAL: Downgrade setuptools
pip install --force-reinstall "setuptools<81"

# Django commands
python manage.py collectstatic --no-input
python manage.py migrate