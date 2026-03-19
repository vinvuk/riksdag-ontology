"""Generate UK Parliament–style ontology documentation from Turtle sources.

Reads all .ttl modules and produces a static HTML site with:
  - Landing page (index.html) linking all modules
  - Per-module pages with class/property definitions and SVG diagrams
  - Consistent template matching ukparliament.github.io/ontologies/

Usage:
    python scripts/generate_docs.py
"""

import html
import re
from pathlib import Path
from collections import defaultdict

from rdflib import Graph, RDF, RDFS, OWL, XSD, Namespace, URIRef, BNode
from rdflib.namespace import SKOS, FOAF, DCTERMS

PROJECT_ROOT = Path(__file__).parent.parent
ONTOLOGY_DIR = PROJECT_ROOT / "ontology"
VOCAB_DIR = PROJECT_ROOT / "vocabularies"
DOCS_DIR = PROJECT_ROOT / "docs"

RKSDAG = Namespace("https://ontology.riksdagen.se/def/")
RKSDAGV = Namespace("https://ontology.riksdagen.se/vocab/")

# Module metadata
MODULES = {
    "agency": {
        "file": "agency.ttl",
        "title": "Agency",
        "title_sv": "Aktörer",
        "description": "Organizations, people, roles, and time-bounded memberships in the Riksdag.",
        "description_sv": "Organisationer, personer, roller och tidsavgränsade medlemskap i riksdagen.",
    },
    "documents": {
        "file": "documents.ttl",
        "title": "Documents",
        "title_sv": "Dokument",
        "description": "Parliamentary and legislative document types with ELI FRBR layering.",
        "description_sv": "Parlamentariska och lagstiftningsdokumenttyper med ELI FRBR-lager.",
    },
    "procedure": {
        "file": "procedure.ttl",
        "title": "Procedure",
        "title_sv": "Process",
        "description": "The legislative process modeled as a directed graph of steps and routes.",
        "description_sv": "Lagstiftningsprocessen modellerad som en riktad graf av steg och rutter.",
    },
    "voting": {
        "file": "voting.ttl",
        "title": "Voting",
        "title_sv": "Votering",
        "description": "Vote events, individual ballots, outcomes, and voting methods.",
        "description_sv": "Voteringar, enskilda röster, utfall och omröstningsmetoder.",
    },
    "interface": {
        "file": "interface.ttl",
        "title": "Interface",
        "title_sv": "Koppling",
        "description": "Alignment axioms mapping to ELI, rpubl, Schema.org, W3C ORG, and Dublin Core.",
        "description_sv": "Kopplingsaxiom till ELI, rpubl, Schema.org, W3C ORG och Dublin Core.",
    },
}

VOCAB_MODULES = {
    "parties": {"file": "parties.ttl", "title": "Political Parties", "title_sv": "Riksdagspartier"},
    "committees": {"file": "committees.ttl", "title": "Committees", "title_sv": "Utskott"},
    "constituencies": {"file": "constituencies.ttl", "title": "Electoral Districts", "title_sv": "Valkretsar"},
    "document-types": {"file": "document-types.ttl", "title": "Document Types", "title_sv": "Dokumenttyper"},
    "vote-options": {"file": "vote-options.ttl", "title": "Vote Options", "title_sv": "Röstningsalternativ"},
    "roles": {"file": "roles.ttl", "title": "Parliamentary Roles", "title_sv": "Riksdagsroller"},
}

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    line-height: 1.6;
    color: #1a1a1a;
    max-width: 56rem;
    margin: 0 auto;
    padding: 2rem 1.5rem;
}
h1 { font-size: 1.75rem; font-weight: 600; margin-bottom: 0.5rem; }
h2 { font-size: 1.35rem; font-weight: 600; margin-top: 2.5rem; margin-bottom: 0.75rem;
     padding-bottom: 0.25rem; border-bottom: 1px solid #e0e0e0; }
h3 { font-size: 1.1rem; font-weight: 600; margin-top: 1.5rem; margin-bottom: 0.5rem; }
h4 { font-size: 1rem; font-weight: 600; margin-top: 1.25rem; margin-bottom: 0.25rem; }
p { margin-bottom: 0.75rem; }
a { color: #1a56db; text-decoration: none; }
a:hover { text-decoration: underline; }
code, .iri { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.85em;
             background: #f5f5f5; padding: 0.1em 0.3em; border-radius: 3px; }
.subtitle { color: #666; font-size: 0.95rem; margin-bottom: 1.5rem; }
.meta { color: #888; font-size: 0.8rem; margin-bottom: 0.5rem; }
.badge { display: inline-block; font-size: 0.7rem; font-weight: 600;
         padding: 0.15em 0.5em; border-radius: 3px; margin-left: 0.3rem;
         vertical-align: middle; }
.badge-class { background: #dbeafe; color: #1e40af; }
.badge-op { background: #dcfce7; color: #166534; }
.badge-dp { background: #fef3c7; color: #92400e; }
.badge-vocab { background: #f3e8ff; color: #6b21a8; }
.toc { margin: 1rem 0 2rem; }
.toc ol { padding-left: 1.5rem; }
.toc li { margin: 0.2rem 0; }
.module-grid { display: grid; grid-template-columns: 1fr; gap: 0.75rem; margin: 1rem 0; }
.module-card { border: 1px solid #e0e0e0; border-radius: 6px; padding: 1rem;
               transition: border-color 0.15s; }
.module-card:hover { border-color: #1a56db; }
.module-card h4 { margin: 0 0 0.25rem; }
.module-card p { margin: 0; font-size: 0.85rem; color: #666; }
.definition { margin: 0.5rem 0 1rem; padding-left: 1rem;
              border-left: 3px solid #e0e0e0; }
.definition dt { font-weight: 600; font-size: 0.85rem; color: #555; margin-top: 0.5rem; }
.definition dd { margin-left: 0; font-size: 0.9rem; }
.back-to-toc { font-size: 0.8rem; color: #888; margin-top: 0.5rem; }
.namespace-table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.85rem; }
.namespace-table th, .namespace-table td { text-align: left; padding: 0.4rem 0.75rem;
                                           border-bottom: 1px solid #eee; }
.namespace-table th { font-weight: 600; color: #555; }
.diagram { margin: 1.5rem 0; text-align: center; }
.diagram img, .diagram svg { max-width: 100%; }
.stats { display: flex; gap: 1.5rem; flex-wrap: wrap; margin: 1rem 0; }
.stat { text-align: center; }
.stat-value { font-size: 1.5rem; font-weight: 700; color: #1a56db; }
.stat-label { font-size: 0.7rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;
         font-size: 0.8rem; color: #888; }
"""


def local_name(uri: URIRef | str) -> str:
    """Extract local name from a URI.

    Args:
        uri: Full URI or prefixed name.

    Returns:
        The local part after the last / or #.
    """
    s = str(uri)
    if "#" in s:
        return s.split("#")[-1]
    return s.split("/")[-1]


def label(g: Graph, uri: URIRef, lang: str = "en") -> str:
    """Get the rdfs:label for a resource in a specific language.

    Args:
        g: RDF graph.
        uri: Resource URI.
        lang: Language tag.

    Returns:
        Label string or local name as fallback.
    """
    for obj in g.objects(uri, RDFS.label):
        if hasattr(obj, "language") and obj.language == lang:
            return str(obj)
    for obj in g.objects(uri, RDFS.label):
        if hasattr(obj, "language") and obj.language == "sv":
            return str(obj)
    return local_name(uri)


def comment(g: Graph, uri: URIRef, lang: str = "en") -> str:
    """Get the rdfs:comment for a resource.

    Args:
        g: RDF graph.
        uri: Resource URI.
        lang: Preferred language.

    Returns:
        Comment string or empty string.
    """
    for obj in g.objects(uri, RDFS.comment):
        if hasattr(obj, "language") and obj.language == lang:
            return str(obj)
    for obj in g.objects(uri, RDFS.comment):
        if hasattr(obj, "language") and obj.language == "sv":
            return str(obj)
    for obj in g.objects(uri, RDFS.comment):
        return str(obj)
    return ""


def esc(text: str) -> str:
    """HTML-escape a string.

    Args:
        text: Raw string.

    Returns:
        HTML-safe string.
    """
    return html.escape(text)


def class_link(uri: URIRef, anchor_prefix: str = "") -> str:
    """Generate an HTML link to a class definition.

    Args:
        uri: Class URI.
        anchor_prefix: Optional prefix for anchor IDs.

    Returns:
        HTML anchor tag.
    """
    name = local_name(uri)
    if str(uri).startswith(str(RKSDAG)):
        return f'<a href="#{anchor_prefix}{name}">{esc(name)}</a> <span class="badge badge-class">c</span>'
    return f'<code>{esc(name)}</code>'


def prop_link(uri: URIRef, badge_type: str = "op") -> str:
    """Generate an HTML link to a property definition.

    Args:
        uri: Property URI.
        badge_type: 'op' or 'dp'.

    Returns:
        HTML anchor tag.
    """
    name = local_name(uri)
    badge_class = "badge-op" if badge_type == "op" else "badge-dp"
    if str(uri).startswith(str(RKSDAG)):
        return f'<a href="#prop-{name}">{esc(name)}</a> <span class="badge {badge_class}">{badge_type}</span>'
    return f'<code>{esc(name)}</code>'


def generate_module_page(module_id: str, meta: dict) -> str:
    """Generate an HTML documentation page for one ontology module.

    Args:
        module_id: Module identifier (e.g., 'agency').
        meta: Module metadata dict with file, title, description.

    Returns:
        Complete HTML string.
    """
    g = Graph()
    g.parse(ONTOLOGY_DIR / meta["file"], format="turtle")

    # Collect classes, object properties, datatype properties
    classes = sorted(
        [s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef) and str(s).startswith(str(RKSDAG))],
        key=lambda u: local_name(u),
    )
    obj_props = sorted(
        [s for s in g.subjects(RDF.type, OWL.ObjectProperty) if str(s).startswith(str(RKSDAG))],
        key=lambda u: local_name(u),
    )
    dt_props = sorted(
        [s for s in g.subjects(RDF.type, OWL.DatatypeProperty) if str(s).startswith(str(RKSDAG))],
        key=lambda u: local_name(u),
    )

    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(meta['title'])} — Riksdag Ontology</title>
<style>{CSS}</style>
</head>
<body>
<p class="meta"><a href="index.html">← Riksdag Ontology</a></p>
<h1>{esc(meta['title'])} Ontology</h1>
<p class="subtitle">{esc(meta['title_sv'])} — {esc(meta['description'])}</p>
<p class="meta">IRI: <code>https://ontology.riksdagen.se/def/{module_id}</code></p>
<p class="meta">
    Source: <a href="https://github.com/vinvuk/riksdag-ontology/blob/main/ontology/{meta['file']}">{meta['file']}</a>
    · License: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
</p>
""")

    # Stats
    parts.append(f"""
<div class="stats">
    <div class="stat"><div class="stat-value">{len(classes)}</div><div class="stat-label">Classes</div></div>
    <div class="stat"><div class="stat-value">{len(obj_props)}</div><div class="stat-label">Object Properties</div></div>
    <div class="stat"><div class="stat-value">{len(dt_props)}</div><div class="stat-label">Datatype Properties</div></div>
</div>
""")

    # Table of Contents
    parts.append('<nav class="toc"><h2 id="toc">Table of Contents</h2><ol>')
    if classes:
        parts.append('<li><a href="#classes">Classes</a><ol>')
        for cls in classes:
            name = local_name(cls)
            parts.append(f'<li><a href="#{name}">{esc(name)}</a></li>')
        parts.append('</ol></li>')
    if obj_props:
        parts.append('<li><a href="#object-properties">Object Properties</a><ol>')
        for prop in obj_props:
            name = local_name(prop)
            parts.append(f'<li><a href="#prop-{name}">{esc(name)}</a></li>')
        parts.append('</ol></li>')
    if dt_props:
        parts.append('<li><a href="#datatype-properties">Datatype Properties</a><ol>')
        for prop in dt_props:
            name = local_name(prop)
            parts.append(f'<li><a href="#prop-{name}">{esc(name)}</a></li>')
        parts.append('</ol></li>')
    parts.append('<li><a href="#namespaces">Namespaces</a></li>')
    parts.append('</ol></nav>')

    # Sub-diagrams — embed HTML snippets generated by generate_diagrams.py
    _title_map = {
        "people": "People", "organizations": "Organizations", "memberships": "Memberships",
        "hierarchy": "Document type hierarchy", "motions": "Motion subtypes",
        "oversight": "Oversight instruments", "prelegislative": "Pre-legislative documents",
        "legal": "Legal publications", "parts": "Document parts and debates",
        "template": "Procedure template layer", "stages": "Procedural stages",
        "tracking": "Work package tracking", "all": "Voting model",
        "classes": "Class alignments", "properties": "Property alignments",
    }
    diagram_files = sorted(DOCS_DIR.glob(f"{module_id}-*.html"))
    if diagram_files:
        parts.append('<h2>Diagrams</h2>')
        parts.append('<p class="meta">Hollow arrows (△) = subclass. Blue arrows = object properties. '
                     'Red double arrows (≡) = equivalent class. '
                     'Dashed boxes = external or cross-module references.</p>')
        for df in diagram_files:
            suffix = df.stem.replace(f"{module_id}-", "")
            title = _title_map.get(suffix, suffix.replace("-", " ").title())
            snippet = df.read_text(encoding="utf-8")
            parts.append(f'<h3>{esc(title)}</h3>')
            parts.append(f'<div class="diagram">{snippet}</div>')

    # Classes
    if classes:
        parts.append('<h2 id="classes">Classes</h2>')
        for cls in classes:
            name = local_name(cls)
            lbl_sv = label(g, cls, "sv")
            lbl_en = label(g, cls, "en")
            cmt = comment(g, cls, "en")
            cmt_sv = comment(g, cls, "sv")

            parts.append(f'<h3 id="{name}">{esc(name)}</h3>')
            parts.append(f'<p class="meta">IRI: <code>{esc(str(cls))}</code></p>')
            if lbl_sv != name:
                parts.append(f'<p><strong>{esc(lbl_sv)}</strong> / {esc(lbl_en)}</p>')

            parts.append('<dl class="definition">')
            if cmt:
                parts.append(f'<dt>Definition (en)</dt><dd>{esc(cmt)}</dd>')
            if cmt_sv:
                parts.append(f'<dt>Definition (sv)</dt><dd>{esc(cmt_sv)}</dd>')

            # Superclasses
            supers = [o for o in g.objects(cls, RDFS.subClassOf) if isinstance(o, URIRef)]
            if supers:
                links = ", ".join(class_link(s) for s in supers)
                parts.append(f'<dt>Subclass of</dt><dd>{links}</dd>')

            # Subclasses
            subs = [s for s in g.subjects(RDFS.subClassOf, cls) if isinstance(s, URIRef) and str(s).startswith(str(RKSDAG))]
            if subs:
                links = ", ".join(class_link(s) for s in sorted(subs, key=local_name))
                parts.append(f'<dt>Has subclasses</dt><dd>{links}</dd>')

            # Properties with this class as domain
            domain_props = []
            for p in list(g.subjects(RDFS.domain, cls)):
                if str(p).startswith(str(RKSDAG)):
                    if (p, RDF.type, OWL.ObjectProperty) in g:
                        domain_props.append((p, "op"))
                    elif (p, RDF.type, OWL.DatatypeProperty) in g:
                        domain_props.append((p, "dp"))
            if domain_props:
                links = ", ".join(prop_link(p, t) for p, t in sorted(domain_props, key=lambda x: local_name(x[0])))
                parts.append(f'<dt>In domain of</dt><dd>{links}</dd>')

            # Properties with this class as range
            range_props = [(p, "op") for p in g.subjects(RDFS.range, cls)
                           if str(p).startswith(str(RKSDAG)) and (p, RDF.type, OWL.ObjectProperty) in g]
            if range_props:
                links = ", ".join(prop_link(p, t) for p, t in sorted(range_props, key=lambda x: local_name(x[0])))
                parts.append(f'<dt>In range of</dt><dd>{links}</dd>')

            parts.append('</dl>')
            parts.append('<p class="back-to-toc"><a href="#toc">↑ back to Table of Contents</a></p>')

    # Object Properties
    if obj_props:
        parts.append('<h2 id="object-properties">Object Properties</h2>')
        for prop in obj_props:
            name = local_name(prop)
            lbl_sv = label(g, prop, "sv")
            cmt = comment(g, prop, "en")
            cmt_sv = comment(g, prop, "sv")

            parts.append(f'<h3 id="prop-{name}">{esc(name)}</h3>')
            parts.append(f'<p class="meta">IRI: <code>{esc(str(prop))}</code></p>')
            if lbl_sv != name:
                parts.append(f'<p><strong>{esc(lbl_sv)}</strong></p>')

            parts.append('<dl class="definition">')
            if cmt:
                parts.append(f'<dt>Definition (en)</dt><dd>{esc(cmt)}</dd>')
            if cmt_sv:
                parts.append(f'<dt>Definition (sv)</dt><dd>{esc(cmt_sv)}</dd>')

            domains = [o for o in g.objects(prop, RDFS.domain) if isinstance(o, URIRef) and str(o).startswith(str(RKSDAG))]
            if domains:
                links = ", ".join(class_link(d) for d in domains)
                parts.append(f'<dt>Domain</dt><dd>{links}</dd>')

            ranges = [o for o in g.objects(prop, RDFS.range) if isinstance(o, URIRef)]
            if ranges:
                range_links = []
                for r in ranges:
                    if str(r).startswith(str(RKSDAG)):
                        range_links.append(class_link(r))
                    else:
                        range_links.append(f'<code>{esc(local_name(r))}</code>')
                parts.append(f'<dt>Range</dt><dd>{", ".join(range_links)}</dd>')

            # Super properties
            super_props = [o for o in g.objects(prop, RDFS.subPropertyOf) if isinstance(o, URIRef)]
            if super_props:
                links = ", ".join(f'<code>{esc(local_name(s))}</code>' for s in super_props)
                parts.append(f'<dt>Sub-property of</dt><dd>{links}</dd>')

            # Functional?
            if (prop, RDF.type, OWL.FunctionalProperty) in g:
                parts.append('<dt>Characteristics</dt><dd>Functional (max 1 value)</dd>')

            parts.append('</dl>')
            parts.append('<p class="back-to-toc"><a href="#toc">↑ back to Table of Contents</a></p>')

    # Datatype Properties
    if dt_props:
        parts.append('<h2 id="datatype-properties">Datatype Properties</h2>')
        for prop in dt_props:
            name = local_name(prop)
            lbl_sv = label(g, prop, "sv")
            cmt = comment(g, prop, "en")
            cmt_sv = comment(g, prop, "sv")

            parts.append(f'<h3 id="prop-{name}">{esc(name)}</h3>')
            parts.append(f'<p class="meta">IRI: <code>{esc(str(prop))}</code></p>')
            if lbl_sv != name:
                parts.append(f'<p><strong>{esc(lbl_sv)}</strong></p>')

            parts.append('<dl class="definition">')
            if cmt:
                parts.append(f'<dt>Definition (en)</dt><dd>{esc(cmt)}</dd>')
            if cmt_sv:
                parts.append(f'<dt>Definition (sv)</dt><dd>{esc(cmt_sv)}</dd>')

            domains = [o for o in g.objects(prop, RDFS.domain) if isinstance(o, URIRef) and str(o).startswith(str(RKSDAG))]
            if domains:
                links = ", ".join(class_link(d) for d in domains)
                parts.append(f'<dt>Domain</dt><dd>{links}</dd>')

            ranges = [o for o in g.objects(prop, RDFS.range) if isinstance(o, URIRef)]
            if ranges:
                parts.append(f'<dt>Range</dt><dd><code>{esc(local_name(ranges[0]))}</code></dd>')

            if (prop, RDF.type, OWL.FunctionalProperty) in g:
                parts.append('<dt>Characteristics</dt><dd>Functional (max 1 value)</dd>')

            parts.append('</dl>')
            parts.append('<p class="back-to-toc"><a href="#toc">↑ back to Table of Contents</a></p>')

    # Namespaces
    parts.append("""
<h2 id="namespaces">Namespace Declarations</h2>
<table class="namespace-table">
<tr><th>Prefix</th><th>URI</th></tr>
<tr><td><code>rksdag:</code></td><td><code>https://ontology.riksdagen.se/def/</code></td></tr>
<tr><td><code>rksdagv:</code></td><td><code>https://ontology.riksdagen.se/vocab/</code></td></tr>
<tr><td><code>eli:</code></td><td><code>http://data.europa.eu/eli/ontology#</code></td></tr>
<tr><td><code>org:</code></td><td><code>http://www.w3.org/ns/org#</code></td></tr>
<tr><td><code>foaf:</code></td><td><code>http://xmlns.com/foaf/0.1/</code></td></tr>
<tr><td><code>schema:</code></td><td><code>https://schema.org/</code></td></tr>
<tr><td><code>skos:</code></td><td><code>http://www.w3.org/2004/02/skos/core#</code></td></tr>
<tr><td><code>dcterms:</code></td><td><code>http://purl.org/dc/terms/</code></td></tr>
<tr><td><code>owl:</code></td><td><code>http://www.w3.org/2002/07/owl#</code></td></tr>
<tr><td><code>rdfs:</code></td><td><code>http://www.w3.org/2000/01/rdf-schema#</code></td></tr>
<tr><td><code>xsd:</code></td><td><code>http://www.w3.org/2001/XMLSchema#</code></td></tr>
</table>
""")

    parts.append("""
<footer>
    <p>Riksdag Ontology v0.1.0 · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
    · <a href="index.html">Back to index</a></p>
</footer>
</body>
</html>""")

    return "\n".join(parts)


def generate_index_page() -> str:
    """Generate the landing page listing all ontology modules and vocabularies.

    Returns:
        Complete HTML string for index.html.
    """
    # Count totals across all modules
    total_classes = 0
    total_obj_props = 0
    total_dt_props = 0
    total_triples = 0
    for meta in MODULES.values():
        g = Graph()
        g.parse(ONTOLOGY_DIR / meta["file"], format="turtle")
        total_classes += len([s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef) and str(s).startswith(str(RKSDAG))])
        total_obj_props += len([s for s in g.subjects(RDF.type, OWL.ObjectProperty) if str(s).startswith(str(RKSDAG))])
        total_dt_props += len([s for s in g.subjects(RDF.type, OWL.DatatypeProperty) if str(s).startswith(str(RKSDAG))])
        total_triples += len(g)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Riksdag Ontology</title>
<style>{CSS}</style>
</head>
<body>
<h1>Riksdag Ontology</h1>
<p class="subtitle">A formal OWL 2 DL ontology for the Swedish Riksdag, modeling members, documents,
legislative processes, votes, and organizational structure. Aligned with
<a href="https://data.europa.eu/eli/ontology">ELI</a> and W3C standards.</p>

<p class="meta">
    Namespace: <code>https://ontology.riksdagen.se/def/</code><br>
    Version: 0.1.0 · License: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
    · <a href="https://github.com/vinvuk/riksdag-ontology">GitHub</a>
</p>

<div class="stats">
    <div class="stat"><div class="stat-value">{total_classes}</div><div class="stat-label">Classes</div></div>
    <div class="stat"><div class="stat-value">{total_obj_props}</div><div class="stat-label">Object Properties</div></div>
    <div class="stat"><div class="stat-value">{total_dt_props}</div><div class="stat-label">Datatype Properties</div></div>
    <div class="stat"><div class="stat-value">{len(MODULES)}</div><div class="stat-label">Modules</div></div>
    <div class="stat"><div class="stat-value">{len(VOCAB_MODULES)}</div><div class="stat-label">Vocabularies</div></div>
</div>

<h2>Ontology Modules</h2>
<p>The ontology is organized into five modular OWL files, following the
<a href="https://ukparliament.github.io/ontologies/">UK Parliament</a> pattern
of separating concerns into independent, composable modules.</p>

<div class="module-grid">
{''.join(_module_card(mid, m) for mid, m in MODULES.items())}
</div>

<h2>SKOS Vocabularies</h2>
<p>Controlled vocabularies providing bilingual (Swedish/English) concept schemes
for parliamentary entities. Each vocabulary uses
<a href="https://www.w3.org/2004/02/skos/core">SKOS</a> with
<code>skos:notation</code> matching the Riksdag API's field codes.</p>

<div class="module-grid">
{''.join(_vocab_card(vid, v) for vid, v in VOCAB_MODULES.items())}
</div>

<h2>External Alignments</h2>
<p>The <a href="interface.html">interface module</a> aligns the Riksdag ontology to:</p>
<table class="namespace-table">
<tr><th>Standard</th><th>Scope</th></tr>
<tr><td><a href="https://data.europa.eu/eli/ontology">ELI</a></td><td>FRBR document layering, amendment and date properties</td></tr>
<tr><td><a href="http://rinfo.lagrummet.se/">rpubl</a></td><td>Swedish legal document types (Lag, Förordning, Proposition)</td></tr>
<tr><td><a href="https://www.w3.org/ns/org">W3C ORG</a></td><td>Organizational structure, membership, roles</td></tr>
<tr><td><a href="https://schema.org/">Schema.org</a></td><td>Person, Organization, Legislation</td></tr>
<tr><td><a href="https://dublincore.org/specifications/dublin-core/dcmi-terms/">Dublin Core</a></td><td>Document metadata (date, identifier, title, creator)</td></tr>
<tr><td><a href="http://xmlns.com/foaf/0.1/">FOAF</a></td><td>Person properties (givenName, familyName)</td></tr>
</table>

<h2>Data Sources</h2>
<table class="namespace-table">
<tr><th>Source</th><th>Content</th></tr>
<tr><td><a href="https://data.riksdagen.se/">Riksdagens öppna data</a></td><td>Members, documents, votes, speeches (REST API, no auth)</td></tr>
<tr><td><a href="https://lagrummet.se/">Lagrummet</a></td><td>Legal RDF from rättsinformationssystemet</td></tr>
<tr><td><a href="https://lagen.nu/">Lagen.nu</a></td><td>1M+ RDF triples for Swedish legal data (BSD)</td></tr>
<tr><td><a href="https://www.wikidata.org/">Wikidata</a></td><td>MP biographical data with Q-numbers</td></tr>
</table>

<h2>Resources</h2>
<ul>
<li><a href="namespace-design.html">Namespace and URI Design</a></li>
<li><a href="competency-questions.html">Competency Questions</a> — 20 SPARQL queries the ontology must answer</li>
<li><a href="https://github.com/vinvuk/riksdag-ontology">GitHub Repository</a></li>
</ul>

<footer>
    <p>Riksdag Ontology v0.1.0 · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
    · Inspired by the <a href="https://ukparliament.github.io/ontologies/">UK Parliament Ontologies</a></p>
</footer>
</body>
</html>"""


def _module_card(module_id: str, meta: dict) -> str:
    """Generate an HTML card for a module in the grid.

    Args:
        module_id: Module identifier.
        meta: Module metadata.

    Returns:
        HTML string for the card.
    """
    g = Graph()
    g.parse(ONTOLOGY_DIR / meta["file"], format="turtle")
    n_classes = len([s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef) and str(s).startswith(str(RKSDAG))])
    n_props = len([s for s in g.subjects(RDF.type, OWL.ObjectProperty) if str(s).startswith(str(RKSDAG))])
    n_dprops = len([s for s in g.subjects(RDF.type, OWL.DatatypeProperty) if str(s).startswith(str(RKSDAG))])

    return f"""<a href="{module_id}.html" style="text-decoration:none;color:inherit">
<div class="module-card">
    <h4>{esc(meta['title'])} <span style="color:#888;font-weight:normal">({esc(meta['title_sv'])})</span></h4>
    <p>{esc(meta['description'])}</p>
    <p class="meta">{n_classes} classes · {n_props} object properties · {n_dprops} datatype properties</p>
</div></a>"""


def _vocab_card(vocab_id: str, meta: dict) -> str:
    """Generate an HTML card for a vocabulary.

    Args:
        vocab_id: Vocabulary identifier.
        meta: Vocabulary metadata.

    Returns:
        HTML string for the card.
    """
    g = Graph()
    g.parse(VOCAB_DIR / meta["file"], format="turtle")
    n_concepts = len(list(g.subjects(RDF.type, SKOS.Concept)))

    return f"""<div class="module-card">
    <h4>{esc(meta['title'])} <span style="color:#888;font-weight:normal">({esc(meta['title_sv'])})</span>
    <span class="badge badge-vocab">SKOS</span></h4>
    <p class="meta">{n_concepts} concepts · <a href="https://github.com/vinvuk/riksdag-ontology/blob/main/vocabularies/{meta['file']}">source</a></p>
</div>"""


def main():
    """Generate all documentation pages."""
    # Generate index
    (DOCS_DIR / "index.html").write_text(generate_index_page(), encoding="utf-8")
    print("Generated docs/index.html")

    # Generate module pages
    for module_id, meta in MODULES.items():
        page_html = generate_module_page(module_id, meta)
        (DOCS_DIR / f"{module_id}.html").write_text(page_html, encoding="utf-8")
        print(f"Generated docs/{module_id}.html")

    print(f"\nDone — {1 + len(MODULES)} pages in docs/")


if __name__ == "__main__":
    main()
