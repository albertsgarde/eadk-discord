.PHONY: test launch t

test:
	uv run pytest
t: test

cov:
	uv run pytest --cov --cov-report=term-missing

launch:
	. ./.env && uv run eadk_discord
