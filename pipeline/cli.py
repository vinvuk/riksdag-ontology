"""CLI for the Riksdag Ontology ETL pipeline.

Usage:
    riksdag fetch members --session 2024/25 --output data/members.json
    riksdag fetch documents --type prop --session 2024/25
    riksdag transform members --input data/members.json --output data/members.ttl
    riksdag run --session 2024/25 --output data/riksdag.ttl
"""

import json
import logging
from pathlib import Path

import click

from pipeline.fetch import fetch_members, fetch_documents, fetch_votes, fetch_speeches
from pipeline.transform import (
    transform_members, transform_documents, transform_votes, transform_speeches,
)
from pipeline.validate import validate_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Riksdag Ontology ETL Pipeline."""
    pass


@cli.group()
def fetch():
    """Fetch data from the Riksdag API."""
    pass


@fetch.command("members")
@click.option("--party", default=None, help="Filter by party (e.g., S, M, SD)")
@click.option("--status", default="tjg", help="Member status (tjg=serving)")
@click.option("--output", "-o", default="data/members.json", help="Output JSON file")
@click.option("--max-pages", default=None, type=int, help="Limit pages fetched")
def fetch_members_cmd(party, status, output, max_pages):
    """Fetch member data from the Riksdag API.

    Args:
        party: Party filter.
        status: Status filter.
        output: Output file path.
        max_pages: Page limit.
    """
    data = fetch_members(party=party, status=status, max_pages=max_pages)
    _write_json(data, output)
    click.echo(f"Fetched {len(data)} members → {output}")


@fetch.command("documents")
@click.option("--type", "doc_type", default="prop", help="Document type (prop, mot, bet, ip, fr)")
@click.option("--session", default=None, help="Session (e.g., 2024/25)")
@click.option("--output", "-o", default="data/documents.json", help="Output JSON file")
@click.option("--max-pages", default=None, type=int, help="Limit pages fetched")
def fetch_documents_cmd(doc_type, session, output, max_pages):
    """Fetch documents from the Riksdag API.

    Args:
        doc_type: Document type code.
        session: Parliamentary session.
        output: Output file path.
        max_pages: Page limit.
    """
    data = fetch_documents(doc_type=doc_type, session=session, max_pages=max_pages)
    _write_json(data, output)
    click.echo(f"Fetched {len(data)} documents → {output}")


@fetch.command("votes")
@click.option("--session", default=None, help="Session (e.g., 2024/25)")
@click.option("--output", "-o", default="data/votes.json", help="Output JSON file")
@click.option("--max-pages", default=None, type=int, help="Limit pages fetched")
def fetch_votes_cmd(session, output, max_pages):
    """Fetch voting records from the Riksdag API.

    Args:
        session: Parliamentary session.
        output: Output file path.
        max_pages: Page limit.
    """
    data = fetch_votes(session=session, max_pages=max_pages)
    _write_json(data, output)
    click.echo(f"Fetched {len(data)} vote records → {output}")


@fetch.command("speeches")
@click.option("--session", default=None, help="Session (e.g., 2024/25)")
@click.option("--output", "-o", default="data/speeches.json", help="Output JSON file")
@click.option("--max-pages", default=None, type=int, help="Limit pages fetched")
def fetch_speeches_cmd(session, output, max_pages):
    """Fetch debate speeches from the Riksdag API.

    Args:
        session: Parliamentary session.
        output: Output file path.
        max_pages: Page limit.
    """
    data = fetch_speeches(session=session, max_pages=max_pages)
    _write_json(data, output)
    click.echo(f"Fetched {len(data)} speeches → {output}")


@cli.command()
@click.option("--session", default="2024/25", help="Session to process")
@click.option("--output", "-o", default="data/riksdag.ttl", help="Output Turtle file")
@click.option("--max-pages", default=None, type=int, help="Limit pages per endpoint")
@click.option("--validate/--no-validate", default=True, help="Run SHACL validation")
@click.option("--doc-types", default="prop,mot,bet,ip,fr", help="Comma-separated doc types")
def run(session, output, max_pages, validate, doc_types):
    """Run the full ETL pipeline: fetch → transform → validate → serialize.

    Fetches members, documents, votes, and speeches for a given session,
    transforms them to RDF, optionally validates against SHACL shapes,
    and writes the combined graph as Turtle.

    Args:
        session: Parliamentary session.
        output: Output Turtle file.
        max_pages: Page limit per endpoint.
        validate: Whether to run SHACL validation.
        doc_types: Document types to fetch.
    """
    from rdflib import Graph

    combined = Graph()
    combined.bind("rksdag", "https://ontology.riksdagen.se/def/")
    combined.bind("rksdagd", "https://data.riksdagen.se/id/")
    combined.bind("rksdagv", "https://ontology.riksdagen.se/vocab/")

    # 1. Members
    click.echo("Fetching members...")
    members = fetch_members(status="tjg", max_pages=max_pages)
    member_graph = transform_members(members)
    combined += member_graph
    click.echo(f"  {len(members)} members → {len(member_graph)} triples")

    # 2. Documents
    for dtype in doc_types.split(","):
        dtype = dtype.strip()
        click.echo(f"Fetching {dtype} documents...")
        docs = fetch_documents(doc_type=dtype, session=session, max_pages=max_pages)
        doc_graph = transform_documents(docs)
        combined += doc_graph
        click.echo(f"  {len(docs)} {dtype} → {len(doc_graph)} triples")

    # 3. Votes
    click.echo("Fetching votes...")
    votes = fetch_votes(session=session, max_pages=max_pages)
    vote_graph = transform_votes(votes)
    combined += vote_graph
    click.echo(f"  {len(votes)} vote records → {len(vote_graph)} triples")

    # 4. Speeches
    click.echo("Fetching speeches...")
    speeches = fetch_speeches(session=session, max_pages=max_pages)
    speech_graph = transform_speeches(speeches)
    combined += speech_graph
    click.echo(f"  {len(speeches)} speeches → {len(speech_graph)} triples")

    # 5. Validate
    if validate:
        click.echo("Running SHACL validation...")
        conforms, report = validate_graph(combined)
        if conforms:
            click.echo("  SHACL validation passed ✓")
        else:
            click.echo(f"  SHACL validation issues (non-blocking):\n{report}")

    # 6. Serialize
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    combined.serialize(destination=output, format="turtle")
    click.echo(f"\nTotal: {len(combined)} triples → {output}")


def _write_json(data: list, path: str) -> None:
    """Write data to a JSON file.

    Args:
        data: List of dicts to serialize.
        path: Output file path.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    cli()
