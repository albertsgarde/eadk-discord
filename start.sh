#!/bin/bash
# Hack to get repo location. This breaks if the server directory is moved.
REPO_PATH=$(dirname $(readlink -f $0))
cd $REPO_PATH
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
source .venv/bin/activate
python -m pip install -r requirements.txt
source .env
python -m eadk_discord
