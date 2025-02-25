# pragma: coverage exclude file
import argparse
import logging
import os
import tomllib
from pathlib import Path

from eadk_discord import bot_setup

if __name__ == "__main__":
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True, parents=True)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    stderr_logger = logging.StreamHandler()
    stderr_logger.setLevel(logging.WARNING)
    stderr_logger.setFormatter(formatter)
    logger.addHandler(stderr_logger)
    file_logger = logging.FileHandler(log_dir / "info.log")
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(formatter)
    logger.addHandler(file_logger)
    logger.addHandler(logging.FileHandler(log_dir / "debug.log"))

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

    config.run_bot(logger)
