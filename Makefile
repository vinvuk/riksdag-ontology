PYTHON   := python3.11
VENV     := .venv
PIP      := $(VENV)/bin/pip
PY       := $(VENV)/bin/python
ROBOT    := java -jar tools/robot.jar

MODULES  := ontology/agency.ttl ontology/documents.ttl ontology/procedure.ttl \
            ontology/voting.ttl ontology/interface.ttl
VOCABS   := $(wildcard vocabularies/*.ttl)
SHAPES   := $(wildcard shapes/*.ttl)
ALL_TTL  := ontology/riksdag.ttl $(MODULES) $(VOCABS) $(SHAPES)

.PHONY: all setup validate parse shacl test docs clean

all: parse shacl test

setup:  ## Create venv, install deps, download ROBOT
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -e ".[dev]"
	mkdir -p tools
	curl -sL -o tools/robot.jar https://github.com/ontodev/robot/releases/latest/download/robot.jar

parse:  ## Parse all Turtle files (syntax check)
	@echo "Parsing all .ttl files..."
	@for f in $(ALL_TTL); do \
		$(PY) -c "from rdflib import Graph; g = Graph(); g.parse('$$f', format='turtle'); print(f'  ✓ $$f ({len(g)} triples)')"; \
	done

validate: parse  ## Full OWL 2 DL validation (requires Java + ROBOT)
	$(ROBOT) validate --input ontology/riksdag.ttl

merge:  ## Merge all modules into a single release file
	mkdir -p dist
	$(ROBOT) merge $(addprefix --input ,ontology/riksdag.ttl $(MODULES)) --output dist/riksdag-merged.ttl

shacl:  ## Run SHACL validation on sample data
	$(PY) -m pyshacl -s shapes/ -df turtle tests/fixtures/sample_data.ttl

test:  ## Run all Python tests
	$(VENV)/bin/pytest tests/ -v

diagrams:  ## Generate SVG class diagrams (requires Graphviz)
	$(PY) scripts/generate_diagrams.py

docs: diagrams  ## Generate HTML documentation site with diagrams
	$(PY) scripts/generate_docs.py

clean:  ## Remove build artifacts
	rm -rf $(VENV) dist/ tools/robot.jar

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
