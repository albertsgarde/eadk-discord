test:
	uv run pytest

t: 
    just test

cov:
	uv run pytest --cov --cov-report=term-missing

launch:
	export EADK_DISCORD_CONFIG_PATH=.bot_config.toml && uv run eadk_discord
