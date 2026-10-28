PYTHON = conda run -n {{conda_env}} python

.PHONY: help test lint format data docs

help:  ## Show available commands
	@$(PYTHON) -c "import re,pathlib;[print(f'{m[0]:10} {m[1]}') for m in re.findall(r'^([a-z]+):.*?## (.*)$$', pathlib.Path('Makefile').read_text(), re.M)]"

test:  ## Run the test suite
	$(PYTHON) -m pytest

lint:  ## Check style and path rules with Ruff
	$(PYTHON) -m ruff check .

format:  ## Format code with Ruff
	$(PYTHON) -m ruff format .

data:  ## Build datasets from raw inputs
	$(PYTHON) -m {{module_name}}.dataset

docs:  ## Build and open the documentation site
	$(PYTHON) scripts/build_docs.py --open
