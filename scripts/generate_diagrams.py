"""Generate clean SVG class diagrams for each ontology module.

Pure Python SVG generation with manual hierarchical layout.
No external dependencies (no Graphviz, no JS).

Each module gets multiple focused sub-diagrams showing:
  - Classes as rounded rectangles with labels
  - Inheritance (subClassOf) as lines with hollow triangles
  - Object properties as labeled arrows
  - External superclasses as dashed gray boxes

Output: docs/{module}-{name}.svg

Usage:
    python scripts/generate_diagrams.py
"""

import math
from pathlib import Path
from dataclasses import dataclass, field

from rdflib import Graph, RDF, RDFS, OWL, Namespace, URIRef, BNode

PROJECT_ROOT = Path(__file__).parent.parent
ONTOLOGY_DIR = PROJECT_ROOT / "ontology"
DOCS_DIR = PROJECT_ROOT / "docs"
RKSDAG = Namespace("https://ontology.riksdagen.se/def/")

# ---------------------------------------------------------------------------
# Layout primitives
# ---------------------------------------------------------------------------

NODE_H = 38
NODE_PAD_X = 28
NODE_PAD_Y = 60
FONT_SIZE = 13
CHAR_WIDTH = 7.8  # approximate for sans-serif 13px


@dataclass
class Node:
    """A positioned box in the diagram."""

    id: str
    label: str
    x: float = 0
    y: float = 0
    w: float = 0
    color: str = "#dbeafe"
    stroke: str = "#93c5fd"
    dashed: bool = False
    external: bool = False

    def __post_init__(self):
        self.w = max(len(self.label) * CHAR_WIDTH + 24, 120)

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + NODE_H / 2

    @property
    def top(self) -> tuple[float, float]:
        return (self.cx, self.y)

    @property
    def bottom(self) -> tuple[float, float]:
        return (self.cx, self.y + NODE_H)

    @property
    def right(self) -> tuple[float, float]:
        return (self.x + self.w, self.cy)

    @property
    def left(self) -> tuple[float, float]:
        return (self.x, self.cy)


@dataclass
class Edge:
    """A connection between two nodes."""

    from_id: str
    to_id: str
    label: str = ""
    edge_type: str = "subclass"  # "subclass" or "property"


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

COLORS = {
    # Agency (blue)
    "MemberOfParliament": ("#bfdbfe", "#93c5fd"), "AlternateMember": ("#bfdbfe", "#93c5fd"),
    "Minister": ("#bfdbfe", "#93c5fd"), "Speaker": ("#bfdbfe", "#93c5fd"),
    "JusticeOfSupremeCourt": ("#bfdbfe", "#93c5fd"),
    "ParliamentaryBody": ("#dbeafe", "#93c5fd"), "CouncilOnLegislation": ("#dbeafe", "#93c5fd"),
    "PoliticalParty": ("#dbeafe", "#93c5fd"), "Committee": ("#dbeafe", "#93c5fd"),
    "EUCommittee": ("#dbeafe", "#93c5fd"), "Government": ("#dbeafe", "#93c5fd"),
    "Ministry": ("#dbeafe", "#93c5fd"), "ElectoralDistrict": ("#dbeafe", "#93c5fd"),
    "PartyMembership": ("#e0f2fe", "#7dd3fc"), "CommitteeMembership": ("#e0f2fe", "#7dd3fc"),
    "ParliamentaryTenure": ("#e0f2fe", "#7dd3fc"),
    "Election": ("#ede9fe", "#c4b5fd"), "ElectionResult": ("#ede9fe", "#c4b5fd"),
    "SeatType": ("#ede9fe", "#c4b5fd"), "FixedSeat": ("#ede9fe", "#c4b5fd"),
    "AdjustmentSeat": ("#ede9fe", "#c4b5fd"),
    # Documents (green)
    "ParliamentaryDocument": ("#dcfce7", "#86efac"), "DocumentExpression": ("#dcfce7", "#86efac"),
    "DocumentFormat": ("#dcfce7", "#86efac"),
    "GovernmentBill": ("#bbf7d0", "#86efac"), "BudgetBill": ("#bbf7d0", "#86efac"),
    "SpringFiscalBill": ("#bbf7d0", "#86efac"), "SupplementaryBudget": ("#bbf7d0", "#86efac"),
    "GovernmentCommunication": ("#bbf7d0", "#86efac"),
    "Motion": ("#bbf7d0", "#86efac"), "IndividualMotion": ("#d1fae5", "#6ee7b7"),
    "PartyMotion": ("#d1fae5", "#6ee7b7"), "CommitteeMotion": ("#d1fae5", "#6ee7b7"),
    "FollowUpMotion": ("#d1fae5", "#6ee7b7"), "MultiPartyMotion": ("#d1fae5", "#6ee7b7"),
    "CommitteeReport": ("#bbf7d0", "#86efac"), "CommitteeOpinion": ("#bbf7d0", "#86efac"),
    "CommitteeStatement": ("#bbf7d0", "#86efac"),
    "ParliamentaryCommunication": ("#bbf7d0", "#86efac"), "Pronouncement": ("#bbf7d0", "#86efac"),
    "Interpellation": ("#fef3c7", "#fcd34d"), "WrittenQuestion": ("#fef3c7", "#fcd34d"),
    "WrittenAnswer": ("#fef3c7", "#fcd34d"),
    "Statute": ("#f3e8ff", "#c4b5fd"), "Act": ("#f3e8ff", "#c4b5fd"),
    "Ordinance": ("#f3e8ff", "#c4b5fd"), "AmendmentAct": ("#f3e8ff", "#c4b5fd"),
    "ConsolidatedVersion": ("#f3e8ff", "#c4b5fd"),
    "ProposalPoint": ("#fce7f3", "#f9a8d4"), "Reservation": ("#fce7f3", "#f9a8d4"),
    "SpecialOpinion": ("#fce7f3", "#f9a8d4"), "Speech": ("#fce7f3", "#f9a8d4"),
    "Debate": ("#fce7f3", "#f9a8d4"),
    # Procedure (amber)
    "Procedure": ("#fef3c7", "#fcd34d"), "Step": ("#fef3c7", "#fcd34d"),
    "Route": ("#fef3c7", "#fcd34d"), "ProceduralStage": ("#fed7aa", "#fdba74"),
    "WorkPackage": ("#fde68a", "#fcd34d"), "BusinessItem": ("#fde68a", "#fcd34d"),
    "ParliamentarySession": ("#fef3c7", "#fcd34d"), "MandatePeriod": ("#fef3c7", "#fcd34d"),
    # Voting (red)
    "VotingEvent": ("#fee2e2", "#fca5a5"), "Ballot": ("#fee2e2", "#fca5a5"),
    "VoteOutcome": ("#fee2e2", "#fca5a5"), "VotingMethod": ("#fecaca", "#fca5a5"),
}

EXTERNAL_LABELS = {
    "http://www.w3.org/ns/org#FormalOrganization": "org:FormalOrganization",
    "http://www.w3.org/ns/org#OrganizationalUnit": "org:OrganizationalUnit",
    "http://www.w3.org/ns/org#Membership": "org:Membership",
    "http://xmlns.com/foaf/0.1/Person": "foaf:Person",
    "https://schema.org/Person": "schema:Person",
    "http://data.europa.eu/eli/ontology#LegalResource": "eli:LegalResource",
    "http://data.europa.eu/eli/ontology#LegalExpression": "eli:LegalExpression",
    "http://data.europa.eu/eli/ontology#Format": "eli:Format",
    "http://www.w3.org/2004/02/skos/core#Concept": "skos:Concept",
}

# ---------------------------------------------------------------------------
# Sub-diagram definitions
# ---------------------------------------------------------------------------

DIAGRAMS = {
    "agency": [
        {"id": "agency-people", "title": "People",
         "classes": ["MemberOfParliament", "AlternateMember", "Minister", "Speaker"],
         "externals": ["foaf:Person", "schema:Person"]},
        {"id": "agency-orgs", "title": "Organizations",
         "classes": ["ParliamentaryBody", "CouncilOnLegislation", "PoliticalParty",
                     "Committee", "EUCommittee", "Government", "Ministry", "ElectoralDistrict"],
         "externals": ["org:FormalOrganization", "org:OrganizationalUnit"]},
        {"id": "agency-memberships", "title": "Memberships",
         "classes": ["PartyMembership", "CommitteeMembership", "ParliamentaryTenure"],
         "externals": ["org:Membership"]},
        {"id": "agency-elections", "title": "Elections",
         "classes": ["Election", "ElectionResult", "SeatType", "FixedSeat", "AdjustmentSeat"],
         "externals": []},
    ],
    "documents": [
        {"id": "documents-hierarchy", "title": "Core document types",
         "classes": ["ParliamentaryDocument", "GovernmentBill", "Motion",
                     "CommitteeReport", "ParliamentaryCommunication",
                     "Interpellation", "WrittenQuestion"],
         "externals": ["eli:LegalResource"]},
        {"id": "documents-motions", "title": "Motion subtypes",
         "classes": ["Motion", "IndividualMotion", "PartyMotion", "CommitteeMotion",
                     "FollowUpMotion", "MultiPartyMotion"],
         "externals": []},
        {"id": "documents-legal", "title": "Legal publications",
         "classes": ["Statute", "Act", "Ordinance", "AmendmentAct", "ConsolidatedVersion"],
         "externals": ["eli:LegalResource"]},
        {"id": "documents-debates", "title": "Debates and speeches",
         "classes": ["Debate", "Speech", "ProposalPoint", "Reservation", "SpecialOpinion"],
         "externals": []},
    ],
    "procedure": [
        {"id": "procedure-core", "title": "Procedure model",
         "classes": ["Procedure", "Step", "Route", "ProceduralStage",
                     "WorkPackage", "BusinessItem"],
         "externals": []},
        {"id": "procedure-stages", "title": "Legislative stages",
         "classes": ["ProceduralStage", "Tabling", "CommitteeReferral",
                     "CommitteeDeliberation", "ChamberDebate", "ChamberDecision", "Promulgation"],
         "externals": []},
    ],
    "voting": [
        {"id": "voting-model", "title": "Voting model",
         "classes": ["VotingEvent", "Ballot", "VoteOutcome", "VotingMethod"],
         "externals": ["skos:Concept"]},
    ],
}


def local_name(uri) -> str:
    s = str(uri)
    return s.split("#")[-1] if "#" in s else s.split("/")[-1]


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------------------------
# Layout engine
# ---------------------------------------------------------------------------

def layout_hierarchy(nodes: dict[str, Node], edges: list[Edge]) -> None:
    """Position nodes in a top-down hierarchy based on subclass edges.

    Args:
        nodes: Dict of id → Node.
        edges: List of Edge objects.
    """
    # Build parent-child from subclass edges
    children: dict[str, list[str]] = {nid: [] for nid in nodes}
    parents: dict[str, list[str]] = {nid: [] for nid in nodes}
    for e in edges:
        if e.edge_type == "subclass" and e.from_id in nodes and e.to_id in nodes:
            parents[e.from_id].append(e.to_id)
            children[e.to_id].append(e.from_id)

    # Assign levels (roots = 0, children = parent + 1)
    levels: dict[str, int] = {}
    roots = [nid for nid in nodes if not parents[nid]]
    if not roots:
        roots = list(nodes.keys())

    queue = [(r, 0) for r in roots]
    visited = set()
    while queue:
        nid, lvl = queue.pop(0)
        if nid in visited:
            levels[nid] = max(levels.get(nid, 0), lvl)
            continue
        visited.add(nid)
        levels[nid] = lvl
        for child in children.get(nid, []):
            queue.append((child, lvl + 1))

    # Unvisited nodes
    for nid in nodes:
        if nid not in levels:
            levels[nid] = 0

    # Group by level
    by_level: dict[int, list[str]] = {}
    for nid, lvl in levels.items():
        by_level.setdefault(lvl, []).append(nid)

    # Position each level
    for lvl, nids in sorted(by_level.items()):
        row_nodes = [nodes[nid] for nid in nids]
        total_w = sum(n.w for n in row_nodes) + NODE_PAD_X * (len(row_nodes) - 1)
        x = 0
        for n in row_nodes:
            n.x = x
            n.y = lvl * (NODE_H + NODE_PAD_Y)
            x += n.w + NODE_PAD_X

    # Center rows relative to widest
    max_w = max(
        sum(nodes[nid].w for nid in nids) + NODE_PAD_X * (len(nids) - 1)
        for nids in by_level.values()
    )
    for lvl, nids in by_level.items():
        row_w = sum(nodes[nid].w for nid in nids) + NODE_PAD_X * (len(nids) - 1)
        offset = (max_w - row_w) / 2
        for nid in nids:
            nodes[nid].x += offset


# ---------------------------------------------------------------------------
# SVG rendering
# ---------------------------------------------------------------------------

def render_svg(nodes: dict[str, Node], edges: list[Edge], title: str) -> str:
    """Render nodes and edges as an SVG string.

    Args:
        nodes: Positioned nodes.
        edges: Edge list.
        title: Diagram title.

    Returns:
        SVG markup string.
    """
    if not nodes:
        return ""

    # Compute bounds
    min_x = min(n.x for n in nodes.values()) - 20
    min_y = -10
    max_x = max(n.x + n.w for n in nodes.values()) + 20
    max_y = max(n.y + NODE_H for n in nodes.values()) + 20
    w = max_x - min_x
    h = max_y - min_y

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x} {min_y} {w} {h}"',
        f'  width="{w}" height="{h}"',
        '  style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,system-ui,sans-serif">',
        '',
        '  <defs>',
        '    <marker id="tri" viewBox="0 0 10 10" refX="10" refY="5"',
        '      markerWidth="10" markerHeight="10" orient="auto">',
        '      <path d="M0,0 L10,5 L0,10 Z" fill="white" stroke="#94a3b8" stroke-width="1.2"/>',
        '    </marker>',
        '    <marker id="arr" viewBox="0 0 10 6" refX="10" refY="3"',
        '      markerWidth="8" markerHeight="6" orient="auto">',
        '      <path d="M0,0 L10,3 L0,6" fill="none" stroke="#3b82f6" stroke-width="1.5"/>',
        '    </marker>',
        '  </defs>',
        '',
    ]

    # Edges (draw first, behind nodes)
    for e in edges:
        if e.from_id not in nodes or e.to_id not in nodes:
            continue
        fn = nodes[e.from_id]
        tn = nodes[e.to_id]

        if e.edge_type == "subclass":
            # Line from child top to parent bottom
            x1, y1 = fn.top
            x2, y2 = tn.bottom
            parts.append(
                f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"'
                f'    stroke="#94a3b8" stroke-width="1.5" marker-end="url(#tri)"/>'
            )
        else:
            # Property arrow — use curved path
            if abs(fn.cy - tn.cy) < NODE_H * 0.8:
                # Same row: go underneath
                x1, y1 = fn.cx, fn.y + NODE_H
                x2, y2 = tn.cx, tn.y + NODE_H
                mid_y = max(y1, y2) + 30
                path = f"M{x1:.1f},{y1:.1f} C{x1:.1f},{mid_y:.1f} {x2:.1f},{mid_y:.1f} {x2:.1f},{y2:.1f}"
            else:
                # Different rows: straight or gentle curve
                x1, y1 = fn.cx, fn.y + NODE_H if fn.y < tn.y else fn.y
                x2, y2 = tn.cx, tn.y if fn.y < tn.y else tn.y + NODE_H
                mx = (x1 + x2) / 2
                path = f"M{x1:.1f},{y1:.1f} C{mx:.1f},{y1:.1f} {mx:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"

            parts.append(
                f'  <path d="{path}" fill="none" stroke="#3b82f6"'
                f'    stroke-width="1.2" marker-end="url(#arr)"/>'
            )
            if e.label:
                lx = (fn.cx + tn.cx) / 2
                ly = (fn.cy + tn.cy) / 2 - 6
                if abs(fn.cy - tn.cy) < NODE_H * 0.8:
                    ly = max(fn.y + NODE_H, tn.y + NODE_H) + 18
                parts.append(
                    f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle"'
                    f'    font-size="10" fill="#2563eb">{esc(e.label)}</text>'
                )

    # Nodes
    for n in nodes.values():
        dash = ' stroke-dasharray="6,3"' if n.dashed else ''
        text_color = "#64748b" if n.external else "#1e293b"
        parts.append(
            f'  <rect x="{n.x:.1f}" y="{n.y:.1f}" width="{n.w:.1f}" height="{NODE_H}"'
            f'    rx="6" fill="{n.color}" stroke="{n.stroke}" stroke-width="1.5"{dash}/>'
        )
        parts.append(
            f'  <text x="{n.cx:.1f}" y="{n.cy + 5:.1f}" text-anchor="middle"'
            f'    font-size="{FONT_SIZE}" font-weight="500" fill="{text_color}">{esc(n.label)}</text>'
        )

    parts.append('</svg>')
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Build diagrams from ontology
# ---------------------------------------------------------------------------

def build_diagram(g: Graph, ddef: dict) -> tuple[dict[str, Node], list[Edge]]:
    """Extract nodes and edges for a sub-diagram.

    Args:
        g: Parsed ontology graph.
        ddef: Diagram definition dict.

    Returns:
        Tuple of (nodes dict, edges list).
    """
    target_names = set(ddef["classes"])
    ext_names = set(ddef.get("externals", []))

    all_classes = {
        s for s in g.subjects(RDF.type, OWL.Class)
        if isinstance(s, URIRef) and str(s).startswith(str(RKSDAG))
    }

    nodes: dict[str, Node] = {}
    edges: list[Edge] = []

    # Internal nodes
    for cls in all_classes:
        name = local_name(cls)
        if name in target_names:
            fill, stroke = COLORS.get(name, ("#f1f5f9", "#cbd5e1"))
            nodes[name] = Node(id=name, label=name, color=fill, stroke=stroke)

    # External nodes
    for ext in ext_names:
        nodes[ext] = Node(id=ext, label=ext, color="#f8fafc", stroke="#cbd5e1", dashed=True, external=True)

    # Subclass edges
    for cls in all_classes:
        name = local_name(cls)
        if name not in target_names:
            continue
        for parent in g.objects(cls, RDFS.subClassOf):
            if isinstance(parent, BNode):
                continue
            if str(parent).startswith(str(RKSDAG)):
                pname = local_name(parent)
                if pname in target_names:
                    edges.append(Edge(name, pname, edge_type="subclass"))
            else:
                ext_label = EXTERNAL_LABELS.get(str(parent))
                if ext_label and ext_label in ext_names:
                    edges.append(Edge(name, ext_label, edge_type="subclass"))

    # Object property edges
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        if not str(prop).startswith(str(RKSDAG)):
            continue
        pname = local_name(prop)
        domains = [local_name(o) for o in g.objects(prop, RDFS.domain)
                   if isinstance(o, URIRef) and local_name(o) in nodes]
        ranges = [local_name(o) for o in g.objects(prop, RDFS.range)
                  if isinstance(o, URIRef) and local_name(o) in nodes]
        # Also check external ranges
        for o in g.objects(prop, RDFS.range):
            if isinstance(o, URIRef):
                ext_l = EXTERNAL_LABELS.get(str(o))
                if ext_l and ext_l in nodes:
                    ranges.append(ext_l)
        for d in domains:
            for r in ranges:
                if d != r:
                    edges.append(Edge(d, r, label=pname, edge_type="property"))

    return nodes, edges


def main():
    """Generate all sub-diagrams."""
    ttl_files = {
        "agency": "agency.ttl", "documents": "documents.ttl",
        "procedure": "procedure.ttl", "voting": "voting.ttl",
    }

    total = 0
    for module_id, diagrams in DIAGRAMS.items():
        g = Graph()
        g.parse(ONTOLOGY_DIR / ttl_files[module_id], format="turtle")

        print(f"\n{module_id}:")
        for ddef in diagrams:
            nodes, edges = build_diagram(g, ddef)
            if not nodes:
                print(f"  - {ddef['id']}: skipped (no nodes)")
                continue

            layout_hierarchy(nodes, edges)
            svg = render_svg(nodes, edges, ddef["title"])

            out_path = DOCS_DIR / f"{ddef['id']}.svg"
            out_path.write_text(svg, encoding="utf-8")
            print(f"  ✓ {ddef['id']}.svg ({len(nodes)} nodes, {len(edges)} edges)")
            total += 1

    print(f"\nDone — {total} diagrams generated")


if __name__ == "__main__":
    main()
