# pragma: coverage exclude file
import argparse
import logging
import os
import tomllib
from pathlib import Path

from eadk_discord import bot_setup

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(prog="EADK Discord Bot")
    parser.add_argument("config_path")
    args = parser.parse_args()

    if args.config_path:
        config_path = Path(args.config_path)
    else:
        match os.getenv("EADK_DISCORD_CONFIG"):
            case None:
                raise ValueError(
                    "config path is provided neither as an "
                    "argument nor as the environment variable 'EADK_DISCORD_CONFIG'"
                )
            case config_path_str:
                config_path = Path(config_path_str)

    with open(config_path, "rb") as config_file:
        config = bot_setup.BotConfig.model_validate(tomllib.load(config_file))

    config.run_bot()
