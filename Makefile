.PHONY: install dev run demo test lint clean

install:
	python3 -m pip install -e .

dev:
	python3 -m pip install -e '.[dev]'

run:
	workforce serve

demo:
	workforce demo

test:
	pytest

lint:
	ruff check src tests

clean:
	find . -type d -name __pycache__ -prune -exec rm -r {} +
	find . -type f -name '*.pyc' -delete

