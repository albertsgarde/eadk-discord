#!/bin/bash
# Hack to get repo location.
REPO_PATH=$(dirname $(readlink -f $0))
cd $REPO_PATH
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
source .venv/bin/activate
python -m pip install uv
uv sync
export EADK_DISCORD_CONFIG_PATH=.bot_config.toml && uv run eadk_discord
