.DEFAULT_GOAL := help

.PHONY: help
help: ## Print Makefile help
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: install-hooks
install-hooks: ## Install git hooks
	pip3 install --user --upgrade pre-commit || \
	pre-commit install -f --install-hooks

.PHONY: venv
venv: ## Create virtual environment 'venv'
	virtualenv venv --python=python3

.PHONY: clean
clean: ## Delete venv and non-git files (extremely destructive)
	rm -rf venv
	git clean -ffdx
	rm -rf .mypy_cache
	find . -name '__pycache__' | xargs rm -rf

.PHONY: run
run: venv .requirements ## Run the GUI application
	. venv/bin/activate && \
		python3 -m PythonPhoto2Location.py

.PHONY: requirements
requirements: .requirements ## Install requirements
.requirements: venv
	. venv/bin/activate && \
		pip install -r requirements.txt
	touch .requirements

.PHONY: requirements-dev
requirements-dev: .requirements-dev ## Install dev requirements
.requirements-dev: venv install-hooks
	. venv/bin/activate && \
		pip install -r requirements-dev.txt
	touch .requirements-dev


.PHONY: update-requirements
update-requirements: ## Update all requirements.txt files
	for FILE in requirements*.in ; do pip-compile --quiet --generate-hashes --allow-unsafe --upgrade $${FILE} ; done ;
	-pre-commit run requirements-txt-fixer --all-files --show-diff-on-failure
