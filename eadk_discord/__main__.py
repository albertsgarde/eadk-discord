# pragma: coverage exclude file
import logging
import os
import sys
import tomllib
from pathlib import Path

from eadk_discord import bot_setup


def get_config_path(env_var_name: str) -> str:
    match len(sys.argv):
        case 1:
            env_var_option: str | None = os.getenv(env_var_name)
            if env_var_option is None:
                raise ValueError(f"environment variable '{env_var_name}' is not set")
            else:
                return env_var_option
        case 2:
            return sys.argv[1]
        case num_args:
            raise ValueError(f"expected 0 or 1 argument, got {num_args-1}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    config_path = Path(get_config_path("EADK_DISCORD_CONFIG_PATH"))

    with open(config_path, "rb") as config_file:
        config = bot_setup.BotConfig.model_validate(tomllib.load(config_file))

    config.run_bot()
