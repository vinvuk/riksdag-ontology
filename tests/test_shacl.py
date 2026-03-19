"""Tests for SHACL validation of sample data against shapes."""

from pathlib import Path

import pytest
from rdflib import Graph

PROJECT_ROOT = Path(__file__).parent.parent
SHAPES_DIR = PROJECT_ROOT / "shapes"
SAMPLE_DATA = PROJECT_ROOT / "tests" / "fixtures" / "sample_data.ttl"
ONTOLOGY_DIR = PROJECT_ROOT / "ontology"
VOCAB_DIR = PROJECT_ROOT / "vocabularies"


def load_shapes_graph() -> Graph:
    """Load all SHACL shape files into a single graph.

    Returns:
        RDF graph containing all SHACL shapes.
    """
    g = Graph()
    for ttl_file in sorted(SHAPES_DIR.glob("*.ttl")):
        g.parse(ttl_file, format="turtle")
    return g


def load_data_graph() -> Graph:
    """Load sample data with ontology definitions for SHACL class inference.

    Returns:
        RDF graph containing sample data and ontology definitions.
    """
    g = Graph()
    # Load ontology modules (needed for class hierarchy in SHACL)
    for ttl_file in sorted(ONTOLOGY_DIR.glob("*.ttl")):
        g.parse(ttl_file, format="turtle")
    # Load vocabularies (needed for role/party concept validation)
    for ttl_file in sorted(VOCAB_DIR.glob("*.ttl")):
        g.parse(ttl_file, format="turtle")
    # Load sample data
    g.parse(SAMPLE_DATA, format="turtle")
    return g


@pytest.mark.skipif(
    not SAMPLE_DATA.exists(),
    reason="Sample data file not found",
)
def test_sample_data_conforms_to_shapes() -> None:
    """Validate sample data against all SHACL shapes.

    Loads the ontology, vocabularies, and sample data, then
    validates against all SHACL shapes. Reports any violations.
    """
    try:
        from pyshacl import validate
    except ImportError:
        pytest.skip("pyshacl not installed")

    shapes_graph = load_shapes_graph()
    data_graph = load_data_graph()

    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference="rdfs",
        abort_on_first=False,
    )

    assert conforms, f"SHACL validation failed:\n{results_text}"
