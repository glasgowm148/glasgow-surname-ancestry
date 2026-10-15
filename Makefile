PYTHON ?= .venv/bin/python
RUFF ?= $(if $(wildcard $(dir $(PYTHON))ruff),$(dir $(PYTHON))ruff,ruff)

RESEARCH_BASELINE ?= data/site/research-publication-baseline.json
LINK_BASELINE ?= data/site/internal-link-baseline.json

.PHONY: test validate validate-strict lint check check-browser check-research check-links build rebuild-local build-ancestry-progress

# Recompute branch connectivity from the resolved public person dossiers.
build-ancestry-progress:
	$(PYTHON) tools/build_ancestry_progress.py

test:
	$(PYTHON) -m unittest discover -s tests -q

validate:
	$(PYTHON) tools/validate_data.py

validate-strict:
	$(PYTHON) tools/validate_data.py --strict

lint:
	$(RUFF) check src tools tests

check: lint validate test check-research check-links

# Research written in findings.md, the WikiTree register and the queue must
# reach the site. Fails on any problem not already listed in the baseline.
# Skipped where the private research data is absent (CI).
check-research:
	@if [ -f data/wikitree/research-catalogue-cases.json ]; then \
		$(PYTHON) tools/check_research_publication.py --baseline $(RESEARCH_BASELINE); \
	else \
		echo "check-research skipped: data/wikitree/research-catalogue-cases.json is not here (no research data)."; \
	fi

# Internal links of the built site (tools/check_internal_links.py, lane I2).
check-links:
	@if [ -f tools/check_internal_links.py ] && [ -f $(LINK_BASELINE) ] && [ -d www ]; then \
		$(PYTHON) tools/check_internal_links.py --site www --baseline $(LINK_BASELINE); \
	else \
		echo "check-links skipped: tools/check_internal_links.py, $(LINK_BASELINE) or www/ is not there yet."; \
	fi

check-browser:
	$(PYTHON) tools/check_site_quality.py

# This is intentionally separate from `check`: it regenerates thousands of
# static pages and should only be run when source data changes.
build:
	$(PYTHON) tools/sync_onetree_ireland_uk_to_1900.py
	$(PYTHON) tools/build_family_map.py

# Rebuild the local site in place after a change to the builders or to many
# research files, then run the release checks. About an hour; local only: it
# never deploys. Not the full catalogue build above. See the script's header.
rebuild-local:
	tools/rebuild_local_site.sh
