PYTHON ?= .venv/bin/python
RUFF ?= $(if $(wildcard $(dir $(PYTHON))ruff),$(dir $(PYTHON))ruff,ruff)

.PHONY: test validate validate-strict lint check check-browser build

test:
	$(PYTHON) -m unittest discover -s tests -q

validate:
	$(PYTHON) tools/validate_data.py

validate-strict:
	$(PYTHON) tools/validate_data.py --strict

lint:
	$(RUFF) check src tools tests

check: lint validate test

check-browser:
	$(PYTHON) tools/check_site_quality.py

# This is intentionally separate from `check`: it regenerates thousands of
# static pages and should only be run when source data changes.
build:
	$(PYTHON) tools/sync_onetree_ireland_uk_to_1900.py
	$(PYTHON) tools/build_family_map.py
