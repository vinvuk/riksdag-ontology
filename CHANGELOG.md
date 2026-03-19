# Changelog

## [0.1.0] - 2026-03-19

### Added
- Initial ontology scaffold with 5 modular OWL 2 DL modules
  - `agency.ttl` — Organizations, people, temporal memberships (N-ary pattern)
  - `documents.ttl` — 30+ parliamentary/legislative document types with ELI FRBR layering
  - `procedure.ttl` — Legislative process as directed graph (Step/Route/WorkPackage)
  - `voting.ttl` — Voting events, individual ballots, outcomes
  - `interface.ttl` — Alignment axioms for ELI, rpubl, Schema.org, W3C ORG
- 6 SKOS concept schemes: parties, committees, constituencies, document types, vote options, roles
- 4 SHACL validation shape sets
- Sample instance data for validation and testing
- Namespace and URI design document
- 20 competency questions
- Makefile with parse, validate, shacl, and test targets
- Python test suite for syntax validation, SHACL conformance, and bilingual label coverage
- **ETL pipeline** (Phase 2)
  - `pipeline/fetch.py` — Paginated API client for personlista, dokumentlista, voteringlista, anforandelista
  - `pipeline/transform.py` — JSON → RDF mapping: members (with temporal memberships), documents (5 types), votes (aggregated from flat rows), speeches
  - `pipeline/validate.py` — SHACL validation wrapper for transformed data
  - `pipeline/cli.py` — Click CLI with `fetch` and `run` commands
  - Handles API quirks: single-item-as-object, dirty organ codes, URL pagination fields, `personuppdrag` string/dict variance
  - Tested with real data: 217,426 triples from 2024/25 session (1 page per endpoint)
- **SPARQL endpoint** (Phase 3)
  - Apache Jena Fuseki 6.0.0 with TDB2 persistent storage
  - `scripts/start-fuseki.sh` — Start Fuseki server on port 3030
  - `scripts/load.sh` — Load ontology, vocabularies, shapes, and data into named graphs
  - `scripts/query.sh` — Run SPARQL queries from .rq files or inline
  - 7 competency queries in `tests/sparql/` (party sizes, committee chairs, vote distribution, documents by committee, graph stats, interpellations)
  - Union default graph configuration for cross-graph querying
  - Fuseki Web UI at http://localhost:3030/
- **Documentation site** (UK Parliament–style)
  - `scripts/generate_docs.py` — Auto-generates static HTML from .ttl sources
  - Landing page with module grid, vocabulary cards, alignment table, and stats
  - Per-module pages with class/property definitions, domain/range, subclass hierarchy
  - Bilingual definitions (sv/en), IRI references, back-to-ToC navigation
  - 6 pages: index + agency + documents + procedure + voting + interface
- **Ontology gap closure** — 8 domain gaps filled, ontology expanded from 70 → 101 classes:
  1. Remissförfarande — ConsultationProcess, ConsultationBody, ConsultationResponse, ConsultationSummary
  2. Lagrådet — CouncilOnLegislation, JusticeOfSupremeCourt
  3. Budget process — BudgetProcedure, FrameworkDecision, ExpenditureAreaDecision, BudgetBill, SpringFiscalBill, SupplementaryBudget + 27 expenditure areas (SKOS)
  4. EU document flow — EUSubsidiarityProcedure, SubsidiarityCheck, GreenPaper, WhitePaper, EUFactsheet, SubsidiarityStatement
  5. Elections — Election, ElectionResult, FixedSeat, AdjustmentSeat (310+39 mandate model)
  6. Amendment chains — AmendmentAct, ConsolidatedVersion with consolidationDate, baseLaw, transitionProvision
  7. Debate structure — Debate + 5 subtypes (ärendedebatt, interpellationsdebatt, aktuell debatt, partiledardebatt, allmänpolitisk debatt), ReplyChain, replyTo + debate-types SKOS scheme
  8. Cross-document relationships — respondsTo, implementedBy, basedOn, resultsIn, answeredIn, consolidatedBy
