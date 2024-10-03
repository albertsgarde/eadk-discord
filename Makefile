.PHONY: test launch t

test:
	uv run pytest
t: test

launch:
	. ./.env && uv run eadk_discord
