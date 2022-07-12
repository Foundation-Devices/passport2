.PHONY: standard-tests vendor-tests

PY_VERSION=$(shell python -c "import sys; print('%d.%d'% sys.version_info[0:2])")
VALID=$(shell python -c "print($(PY_VERSION) >= 3.6)")

ifeq ($(OS),Windows_NT)
	BIN=venv/Scripts
else
	BIN=venv/bin
endif

ifeq (True,$(VALID))
	PYTHON=python
else
	PYTHON=python3
endif

standard-tests: venv
	$(BIN)/pytest tests/standard

vendor-tests: venv
	$(BIN)/pytest tests/vendor

# setup development environment
venv:
	$(PYTHON) -m venv venv
	$(BIN)/python -m pip install -U pip
	$(BIN)/pip install -U -r requirements.txt
	$(BIN)/pip install -U -r dev-requirements.txt
	$(BIN)/pre-commit install

# re-run if  dependencies change
update:
	$(BIN)/python -m pip install -U pip
	$(BIN)/pip install -U -r requirements.txt
	$(BIN)/pip install -U -r dev-requirements.txt

# ensure this passes before commiting
check:
	$(BIN)/black --check tests/
	$(BIN)/isort --check-only --recursive tests/

# automatic code fixes
fix: black isort

black:
	$(BIN)/black tests/

isort:
	$(BIN)/isort -y --recursive tests/
