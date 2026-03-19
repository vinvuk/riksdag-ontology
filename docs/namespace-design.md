# Namespace and URI Design

## Namespaces

| Prefix | URI | Purpose |
|--------|-----|---------|
| `rksdag:` | `https://ontology.riksdagen.se/def/` | Ontology classes and properties |
| `rksdagd:` | `https://data.riksdagen.se/id/` | Instance data (individuals) |
| `rksdagv:` | `https://ontology.riksdagen.se/vocab/` | SKOS concept schemes and concepts |

## Instance URI Patterns

```
rksdagd:person/{intressent_id}              # Members and people
rksdagd:org/{organ_kod}                     # Organizations (parties, committees)
rksdagd:doc/{dok_id}                        # Documents
rksdagd:vote/{date}-{beteckning}-p{punkt}   # Voting events
rksdagd:ballot/{voter_iid}-{voting_id}      # Individual ballots
rksdagd:speech/{anforande_id}               # Speeches
rksdagd:session/{rm_normalized}             # Sessions (2024/25 → 2024-25)
rksdagd:membership/{person_id}-{org}-{from} # Temporal memberships
rksdagd:workpackage/{doc_type}-{rm}-{nr}    # Legislative work packages
rksdagd:bi/{workpackage}-{step_type}        # Business items (events)
```

## External Prefixes

| Prefix | URI | Standard |
|--------|-----|----------|
| `eli:` | `http://data.europa.eu/eli/ontology#` | European Legislation Identifier |
| `rpubl:` | `http://rinfo.lagrummet.se/ns/2008/11/rinfo/publ#` | Swedish Legal RDF |
| `org:` | `http://www.w3.org/ns/org#` | W3C Organization Ontology |
| `foaf:` | `http://xmlns.com/foaf/0.1/` | Friend of a Friend |
| `schema:` | `https://schema.org/` | Schema.org |
| `dcterms:` | `http://purl.org/dc/terms/` | Dublin Core Terms |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` | SKOS |
| `time:` | `http://www.w3.org/2006/time#` | OWL-Time |
| `prov:` | `http://www.w3.org/ns/prov#` | PROV-O |
| `sh:` | `http://www.w3.org/ns/shacl#` | SHACL |

## Design Principles

1. **Slash URIs** — Each resource can be independently dereferenced via content negotiation.
2. **Opaque identifiers** — Human-readability is a convenience, not a contract.
3. **API-aligned** — Instance URIs use the Riksdag API's own identifiers (`intressent_id`, `dok_id`, `votering_id`) wherever possible.
4. **Session normalization** — `2024/25` becomes `2024-25` in URI paths (slashes are reserved characters).
5. **Temporal memberships** — Encoded in URI via `{person}-{org}-{startdate}` to ensure uniqueness.
