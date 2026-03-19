"""SHACL validation for transformed RDF data.

Validates instance data against the ontology's SHACL shapes
before loading into the triple store.
"""

import logging
from pathlib import Path

from rdflib import Graph

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
SHAPES_DIR = PROJECT_ROOT / "shapes"
ONTOLOGY_DIR = PROJECT_ROOT / "ontology"
VOCAB_DIR = PROJECT_ROOT / "vocabularies"


def load_shapes() -> Graph:
    """Load all SHACL shape files into a single graph.

    Returns:
        RDF graph containing all SHACL shapes.
    """
    g = Graph()
    for ttl_file in sorted(SHAPES_DIR.glob("*.ttl")):
        g.parse(ttl_file, format="turtle")
    logger.info("Loaded %d shape triples from %s", len(g), SHAPES_DIR)
    return g


def load_ontology() -> Graph:
    """Load ontology modules and vocabularies for class inference.

    Returns:
        RDF graph containing ontology definitions and SKOS vocabularies.
    """
    g = Graph()
    for ttl_file in sorted(ONTOLOGY_DIR.glob("*.ttl")):
        g.parse(ttl_file, format="turtle")
    for ttl_file in sorted(VOCAB_DIR.glob("*.ttl")):
        g.parse(ttl_file, format="turtle")
    logger.info("Loaded ontology + vocabularies: %d triples", len(g))
    return g


def validate_graph(data_graph: Graph, strict: bool = False) -> tuple[bool, str]:
    """Validate an RDF data graph against the ontology's SHACL shapes.

    Args:
        data_graph: RDF graph containing instance data to validate.
        strict: If True, raise an exception on validation failure.

    Returns:
        Tuple of (conforms: bool, report_text: str).

    Raises:
        ValueError: If strict=True and validation fails.
    """
    try:
        from pyshacl import validate
    except ImportError:
        logger.warning("pyshacl not installed — skipping SHACL validation")
        return True, "Validation skipped (pyshacl not installed)"

    shapes_graph = load_shapes()

    # Merge ontology definitions into data graph for class inference
    combined = Graph()
    for triple in load_ontology():
        combined.add(triple)
    for triple in data_graph:
        combined.add(triple)

    conforms, _, results_text = validate(
        combined,
        shacl_graph=shapes_graph,
        inference="rdfs",
        abort_on_first=False,
    )

    if conforms:
        logger.info("SHACL validation passed")
    else:
        logger.warning("SHACL validation failed:\n%s", results_text)
        if strict:
            raise ValueError(f"SHACL validation failed:\n{results_text}")

    return conforms, results_text
