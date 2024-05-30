#!/usr/bin/env bash
if [[ ! -d .venv ]]; then
    python3.10 -m venv .venv
    echo "Created venv"
fi

source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
export PYTHONPATH=${PWD}/src:$PYTHONPATH

