"""Tests for ontology syntax validation and basic consistency."""

from pathlib import Path

import pytest
from rdflib import Graph, Namespace, RDF, RDFS, OWL, BNode

PROJECT_ROOT = Path(__file__).parent.parent
ONTOLOGY_DIR = PROJECT_ROOT / "ontology"
VOCAB_DIR = PROJECT_ROOT / "vocabularies"
SHAPES_DIR = PROJECT_ROOT / "shapes"

RKSDAG = Namespace("https://ontology.riksdagen.se/def/")


def get_ttl_files(directory: Path) -> list[Path]:
    """Return all .ttl files in a directory.

    Args:
        directory: Path to search for .ttl files.

    Returns:
        List of Path objects for each .ttl file found.
    """
    return sorted(directory.glob("*.ttl"))


@pytest.mark.parametrize(
    "ttl_file",
    get_ttl_files(ONTOLOGY_DIR),
    ids=lambda p: p.name,
)
def test_ontology_module_parses(ttl_file: Path) -> None:
    """Verify each ontology module parses as valid Turtle.

    Args:
        ttl_file: Path to the .ttl file to parse.
    """
    g = Graph()
    g.parse(ttl_file, format="turtle")
    assert len(g) > 0, f"{ttl_file.name} parsed but contains no triples"


@pytest.mark.parametrize(
    "ttl_file",
    get_ttl_files(VOCAB_DIR),
    ids=lambda p: p.name,
)
def test_vocabulary_parses(ttl_file: Path) -> None:
    """Verify each SKOS vocabulary file parses as valid Turtle.

    Args:
        ttl_file: Path to the .ttl file to parse.
    """
    g = Graph()
    g.parse(ttl_file, format="turtle")
    assert len(g) > 0, f"{ttl_file.name} parsed but contains no triples"


@pytest.mark.parametrize(
    "ttl_file",
    get_ttl_files(SHAPES_DIR),
    ids=lambda p: p.name,
)
def test_shapes_parse(ttl_file: Path) -> None:
    """Verify each SHACL shapes file parses as valid Turtle.

    Args:
        ttl_file: Path to the .ttl file to parse.
    """
    g = Graph()
    g.parse(ttl_file, format="turtle")
    assert len(g) > 0, f"{ttl_file.name} parsed but contains no triples"


def test_sample_data_parses() -> None:
    """Verify the sample data file parses as valid Turtle."""
    sample = PROJECT_ROOT / "tests" / "fixtures" / "sample_data.ttl"
    g = Graph()
    g.parse(sample, format="turtle")
    assert len(g) > 50, "Sample data should contain a substantial number of triples"


def test_all_modules_merge() -> None:
    """Verify all ontology modules can be loaded into a single graph."""
    g = Graph()
    for ttl_file in get_ttl_files(ONTOLOGY_DIR):
        g.parse(ttl_file, format="turtle")
    for ttl_file in get_ttl_files(VOCAB_DIR):
        g.parse(ttl_file, format="turtle")

    # Should have classes, properties, and SKOS concepts
    classes = list(g.subjects(RDF.type, OWL.Class))
    obj_props = list(g.subjects(RDF.type, OWL.ObjectProperty))
    dt_props = list(g.subjects(RDF.type, OWL.DatatypeProperty))

    assert len(classes) > 20, f"Expected 20+ OWL classes, got {len(classes)}"
    assert len(obj_props) > 10, f"Expected 10+ object properties, got {len(obj_props)}"
    assert len(dt_props) > 5, f"Expected 5+ datatype properties, got {len(dt_props)}"


def test_bilingual_labels() -> None:
    """Verify that all OWL classes have both Swedish and English labels."""
    g = Graph()
    for ttl_file in get_ttl_files(ONTOLOGY_DIR):
        g.parse(ttl_file, format="turtle")

    # Filter out blank nodes (anonymous classes used in owl:unionOf domains)
    classes = {c for c in g.subjects(RDF.type, OWL.Class) if not isinstance(c, BNode)}
    missing_sv = []
    missing_en = []

    for cls in classes:
        labels = list(g.objects(cls, RDFS.label))
        langs = [label.language for label in labels if hasattr(label, "language")]
        if "sv" not in langs:
            missing_sv.append(str(cls))
        if "en" not in langs:
            missing_en.append(str(cls))

    assert not missing_sv, f"Classes missing Swedish label: {missing_sv}"
    assert not missing_en, f"Classes missing English label: {missing_en}"
