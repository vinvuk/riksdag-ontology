# Riksdag Ontology

A formal OWL 2 DL ontology for the Swedish Riksdag (parliament), modeling members, documents, legislative processes, votes, and organizational structure. Aligned with [ELI](https://data.europa.eu/eli/ontology) (European Legislation Identifier) and W3C standards.

## Why

Sweden is one of the few EU member states without an ELI implementation, and the Riksdag's open data API (`data.riksdagen.se`) publishes 500,000+ documents with zero semantic structure — XML/JSON only, no RDF, no ontology. This project closes that gap by providing machine-readable linked data infrastructure for Swedish parliamentary data.

## Architecture

```
ontology/          5 modular OWL 2 DL modules (101 classes, 88 properties)
  ├── agency       Organizations, people, elections, Lagrådet, temporal memberships
  ├── documents    40+ document types, debate structure, amendment chains, cross-references
  ├── procedure    Legislative/budget/EU process as directed graphs
  ├── voting       Voting events, individual ballots, outcomes
  └── interface    Alignment axioms (ELI, rpubl, Schema.org, W3C ORG)

vocabularies/      8 SKOS concept schemes
  ├── parties, committees, constituencies, roles
  ├── document-types, vote-options, expenditure-areas, debate-types

shapes/            4 SHACL validation shape sets

pipeline/          Python ETL pipeline (fetch → transform → validate → serialize)
  ├── fetch        Paginated API client for all 4 endpoints
  ├── transform    JSON → RDF mapping with vote aggregation
  ├── validate     SHACL validation on transformed data
  └── cli          Click CLI: `riksdag run --session 2024/25`
```

## Namespaces

| Prefix | URI | Purpose |
|--------|-----|---------|
| `rksdag:` | `https://ontology.riksdagen.se/def/` | Classes and properties |
| `rksdagd:` | `https://data.riksdagen.se/id/` | Instance data |
| `rksdagv:` | `https://ontology.riksdagen.se/vocab/` | SKOS vocabularies |

## Quick Start

```bash
# Set up Python environment
make setup

# Validate all Turtle files (syntax check)
make parse

# Run SHACL validation against sample data
make shacl

# Run tests
make test

# Run the ETL pipeline (fetch real data → RDF)
python -m pipeline.cli run --session "2024/25" --max-pages 1 --output data/riksdag.ttl

# Start the SPARQL endpoint (requires Java 17+)
./scripts/start-fuseki.sh

# Load data into Fuseki (in another terminal)
./scripts/load.sh data/riksdag.ttl

# Run SPARQL queries
./scripts/query.sh tests/sparql/05-party-size.rq
./scripts/query.sh "SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o }"
```

### Endpoints (when Fuseki is running)

| URL | Purpose |
|-----|---------|
| http://localhost:3030/ | Fuseki Web UI |
| http://localhost:3030/riksdag/query | SPARQL query endpoint |
| http://localhost:3030/riksdag/update | SPARQL update endpoint |

## Requirements

- Python 3.11+
- Java 17+ (for ROBOT OWL tool — optional, for full OWL 2 DL validation)

## Standards Alignment

- **ELI** — FRBR document layering, amendment properties, date properties
- **rpubl** — Swedish legal document types (rättsinformationssystemet)
- **W3C ORG** — Organizational structure and temporal memberships
- **Schema.org** — Person, Organization, Legislation
- **FOAF** — Person properties
- **Dublin Core** — Document metadata
- **SKOS** — Controlled vocabularies with bilingual (sv/en) labels

## Data Sources

- [Riksdagens öppna data](https://data.riksdagen.se/) — Members, documents, votes, speeches
- [Lagrummet / rättsinformationssystemet](https://lagrummet.se/) — Legal RDF
- [Lagen.nu](https://lagen.nu/) — 1M+ RDF triples for Swedish legal data
- [Wikidata](https://www.wikidata.org/) — MP biographical data

## License

- **Ontology**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Code**: MIT
