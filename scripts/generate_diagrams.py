"""Generate HTML-based class diagrams for each ontology module.

Uses inline SVG with D3.js for clean layout, straight lines, and
hover interactivity. Each sub-diagram is a standalone HTML snippet
embedded in the module page, or a self-contained SVG file.

Output: docs/{diagram-id}.html for each sub-diagram (embedded by docs generator).

Usage:
    python scripts/generate_diagrams.py
"""

import json
from pathlib import Path

from rdflib import Graph, RDF, RDFS, OWL, Namespace, URIRef, BNode

PROJECT_ROOT = Path(__file__).parent.parent
ONTOLOGY_DIR = PROJECT_ROOT / "ontology"
DOCS_DIR = PROJECT_ROOT / "docs"

RKSDAG = Namespace("https://ontology.riksdagen.se/def/")

# ---------------------------------------------------------------------------
# Sub-diagram definitions
# ---------------------------------------------------------------------------

DIAGRAMS = {
    "agency": [
        {
            "id": "agency-people",
            "title": "People",
            "classes": [
                "MemberOfParliament", "AlternateMember", "Minister", "Speaker",
            ],
            "externals": ["foaf:Person", "schema:Person"],
        },
        {
            "id": "agency-organizations",
            "title": "Organizations",
            "classes": [
                "ParliamentaryBody", "PoliticalParty", "Committee", "EUCommittee",
                "Government", "Ministry", "ElectoralDistrict",
            ],
            "externals": ["org:FormalOrganization", "org:OrganizationalUnit"],
        },
        {
            "id": "agency-memberships",
            "title": "Memberships",
            "classes": [
                "PartyMembership", "CommitteeMembership", "ParliamentaryTenure",
                "MemberOfParliament", "PoliticalParty", "Committee", "ElectoralDistrict",
            ],
            "externals": ["org:Membership", "skos:Concept"],
            "extra_classes": ["MemberOfParliament", "PoliticalParty", "Committee", "ElectoralDistrict"],
        },
    ],
    "documents": [
        {
            "id": "documents-hierarchy",
            "title": "Document type hierarchy",
            "classes": [
                "ParliamentaryDocument", "DocumentExpression", "DocumentFormat",
                "GovernmentBill", "GovernmentCommunication", "Motion",
                "CommitteeReport", "CommitteeOpinion", "CommitteeStatement",
                "ParliamentaryCommunication", "Pronouncement",
            ],
            "externals": ["eli:LegalResource", "eli:LegalExpression", "eli:Format"],
        },
        {
            "id": "documents-motions",
            "title": "Motion subtypes",
            "classes": [
                "Motion", "IndividualMotion", "PartyMotion", "CommitteeMotion",
                "FollowUpMotion", "MultiPartyMotion", "GovernmentBill",
            ],
            "externals": [],
            "extra_classes": ["GovernmentBill"],
        },
        {
            "id": "documents-oversight",
            "title": "Oversight instruments",
            "classes": [
                "ParliamentaryDocument", "Interpellation", "WrittenQuestion",
                "WrittenAnswer",
            ],
            "externals": [],
        },
        {
            "id": "documents-prelegislative",
            "title": "Pre-legislative documents",
            "classes": [
                "ParliamentaryDocument", "GovernmentInquiryReport", "MinistryReport",
                "TermsOfReference", "CouncilReferral", "CouncilOpinion",
            ],
            "externals": [],
        },
        {
            "id": "documents-legal",
            "title": "Legal publications",
            "classes": [
                "Statute", "Act", "Ordinance",
            ],
            "externals": ["eli:LegalResource"],
        },
        {
            "id": "documents-parts",
            "title": "Document parts and debates",
            "classes": [
                "CommitteeReport", "ProposalPoint", "Reservation",
                "SpecialOpinion", "Speech",
            ],
            "externals": [],
            "extra_classes": ["CommitteeReport"],
        },
    ],
    "procedure": [
        {
            "id": "procedure-template",
            "title": "Procedure template layer",
            "classes": [
                "Procedure", "Step", "Route", "ProceduralStage",
            ],
            "externals": ["skos:Concept"],
        },
        {
            "id": "procedure-stages",
            "title": "Procedural stages",
            "classes": [
                "ProceduralStage", "InquiryStage", "ConsultationStage",
                "CouncilReviewStage", "Tabling", "CommitteeReferral",
                "MotionPeriod", "CommitteeDeliberation", "ChamberDebate",
                "ChamberDecision", "Promulgation", "Withdrawal",
                "Recommittal", "Deferral",
            ],
            "externals": [],
        },
        {
            "id": "procedure-tracking",
            "title": "Work package tracking",
            "classes": [
                "WorkPackage", "BusinessItem", "Procedure", "Step",
                "ParliamentarySession", "MandatePeriod",
            ],
            "externals": [],
            "extra_classes": ["Procedure", "Step"],
        },
    ],
    "voting": [
        {
            "id": "voting-all",
            "title": "Voting model",
            "classes": [
                "VotingEvent", "Ballot", "VoteOutcome", "VotingMethod",
            ],
            "externals": ["skos:Concept"],
        },
    ],
    "interface": [
        {
            "id": "interface-classes",
            "title": "Class alignments",
            "layout": "lr-mapping",
            "left_label": "rksdag:",
            "mappings": [
                {"from": "MemberOfParliament", "to": "schema:Person", "type": "subclass"},
                {"from": "ParliamentaryBody", "to": "schema:Organization", "type": "subclass"},
                {"from": "PoliticalParty", "to": "schema:Organization", "type": "subclass"},
                {"from": "Committee", "to": "schema:Organization", "type": "subclass"},
                {"from": "Government", "to": "schema:GovernmentOrganization", "type": "subclass"},
                {"from": "Ministry", "to": "schema:GovernmentOrganization", "type": "subclass"},
                {"from": "ParliamentaryDocument", "to": "schema:Legislation", "type": "subclass"},
                {"from": "GovernmentBill", "to": "eli:LegalResource", "type": "subclass"},
                {"from": "GovernmentBill", "to": "rpubl:Proposition", "type": "equivalent"},
                {"from": "Statute", "to": "eli:LegalResource", "type": "subclass"},
                {"from": "Statute", "to": "rpubl:Forfattning", "type": "subclass"},
                {"from": "Act", "to": "eli:LegalResource", "type": "subclass"},
                {"from": "Act", "to": "rpubl:Lag", "type": "equivalent"},
                {"from": "Ordinance", "to": "eli:LegalResource", "type": "subclass"},
                {"from": "Ordinance", "to": "rpubl:Forordning", "type": "equivalent"},
                {"from": "GovernmentInquiryReport", "to": "rpubl:Utredningsbetankande", "type": "equivalent"},
            ],
        },
        {
            "id": "interface-properties",
            "title": "Property alignments",
            "layout": "lr-mapping",
            "left_label": "rksdag: properties",
            "mappings": [
                {"from": "documentDate", "to": "eli:date_document", "type": "subproperty"},
                {"from": "documentDate", "to": "dcterms:date", "type": "subproperty"},
                {"from": "entryIntoForceDate", "to": "eli:date_entry_into_force", "type": "subproperty"},
                {"from": "entryIntoForceDate", "to": "rpubl:ikrafttradandedatum", "type": "subproperty"},
                {"from": "amends", "to": "eli:amends", "type": "subproperty"},
                {"from": "repeals", "to": "eli:repeals", "type": "subproperty"},
                {"from": "hasExpression", "to": "eli:has_expression", "type": "subproperty"},
                {"from": "hasFormat", "to": "eli:has_format", "type": "subproperty"},
                {"from": "sfsNumber", "to": "rpubl:fsNummer", "type": "subproperty"},
                {"from": "documentTitle", "to": "dcterms:title", "type": "subproperty"},
                {"from": "documentTitle", "to": "schema:name", "type": "subproperty"},
                {"from": "author", "to": "dcterms:creator", "type": "subproperty"},
                {"from": "author", "to": "schema:author", "type": "subproperty"},
                {"from": "designation", "to": "dcterms:identifier", "type": "subproperty"},
                {"from": "hasMembership", "to": "org:hasMembership", "type": "subproperty"},
                {"from": "inOrganization", "to": "org:organization", "type": "subproperty"},
                {"from": "hasRole", "to": "org:role", "type": "subproperty"},
                {"from": "partOf", "to": "org:subOrganizationOf", "type": "subproperty"},
                {"from": "organCode", "to": "org:identifier", "type": "subproperty"},
                {"from": "intressentId", "to": "foaf:accountName", "type": "subproperty"},
                {"from": "imageUrl", "to": "foaf:depiction", "type": "subproperty"},
            ],
        },
    ],
}

# Colors
COLORS = {
    # Agency
    "MemberOfParliament": "#bfdbfe", "AlternateMember": "#bfdbfe", "Minister": "#bfdbfe", "Speaker": "#bfdbfe",
    "ParliamentaryBody": "#dbeafe", "PoliticalParty": "#dbeafe", "Committee": "#dbeafe",
    "EUCommittee": "#dbeafe", "Government": "#dbeafe", "Ministry": "#dbeafe", "ElectoralDistrict": "#dbeafe",
    "PartyMembership": "#e0f2fe", "CommitteeMembership": "#e0f2fe", "ParliamentaryTenure": "#e0f2fe",
    # Documents
    "ParliamentaryDocument": "#dcfce7", "DocumentExpression": "#dcfce7", "DocumentFormat": "#dcfce7",
    "GovernmentBill": "#bbf7d0", "GovernmentCommunication": "#bbf7d0",
    "Motion": "#bbf7d0", "IndividualMotion": "#d1fae5", "PartyMotion": "#d1fae5",
    "CommitteeMotion": "#d1fae5", "FollowUpMotion": "#d1fae5", "MultiPartyMotion": "#d1fae5",
    "CommitteeReport": "#bbf7d0", "CommitteeOpinion": "#bbf7d0", "CommitteeStatement": "#bbf7d0",
    "ParliamentaryCommunication": "#bbf7d0", "Pronouncement": "#bbf7d0",
    "Interpellation": "#fef3c7", "WrittenQuestion": "#fef3c7", "WrittenAnswer": "#fef3c7",
    "GovernmentInquiryReport": "#e0f2fe", "MinistryReport": "#e0f2fe",
    "TermsOfReference": "#e0f2fe", "CouncilReferral": "#e0f2fe", "CouncilOpinion": "#e0f2fe",
    "Statute": "#f3e8ff", "Act": "#f3e8ff", "Ordinance": "#f3e8ff",
    "ProposalPoint": "#fce7f3", "Reservation": "#fce7f3", "SpecialOpinion": "#fce7f3", "Speech": "#fce7f3",
    # Procedure
    "Procedure": "#fef3c7", "Step": "#fef3c7", "Route": "#fef3c7",
    "WorkPackage": "#fde68a", "BusinessItem": "#fde68a", "ProceduralStage": "#fed7aa",
    "InquiryStage": "#ffedd5", "ConsultationStage": "#ffedd5", "CouncilReviewStage": "#ffedd5",
    "Tabling": "#ffedd5", "CommitteeReferral": "#ffedd5", "MotionPeriod": "#ffedd5",
    "CommitteeDeliberation": "#ffedd5", "ChamberDebate": "#ffedd5", "ChamberDecision": "#ffedd5",
    "Promulgation": "#ffedd5", "Withdrawal": "#ffedd5", "Recommittal": "#ffedd5", "Deferral": "#ffedd5",
    "ParliamentarySession": "#fef3c7", "MandatePeriod": "#fef3c7",
    # Voting
    "VotingEvent": "#fee2e2", "Ballot": "#fee2e2", "VoteOutcome": "#fee2e2", "VotingMethod": "#fecaca",
}

EXTERNAL_COLORS = {
    "eli:": "#fef9c3", "rpubl:": "#fecaca", "schema:": "#d1fae5",
    "org:": "#fae8ff", "dcterms:": "#e0e7ff", "foaf:": "#fff7ed", "skos:": "#f5f3ff",
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


def local_name(uri) -> str:
    s = str(uri)
    return s.split("#")[-1] if "#" in s else s.split("/")[-1]


def label_sv(g: Graph, uri: URIRef) -> str:
    for obj in g.objects(uri, RDFS.label):
        if hasattr(obj, "language") and obj.language == "sv":
            return str(obj)
    return ""


def ext_color(name: str) -> str:
    """Get color for an external class by prefix."""
    for prefix, color in EXTERNAL_COLORS.items():
        if name.startswith(prefix):
            return color
    return "#f1f5f9"


def build_ontology_diagram(g: Graph, diagram_def: dict, all_classes: set) -> dict:
    """Extract nodes and edges for a standard ontology sub-diagram.

    Returns dict with {nodes: [...], edges: [...]} for the JS renderer.
    """
    target_names = set(diagram_def["classes"])
    extra = set(diagram_def.get("extra_classes", []))
    ext_names = set(diagram_def.get("externals", []))

    nodes = []
    edges = []
    seen_nodes = set()

    # Internal class nodes (English only — no sublabels)
    for cls in all_classes:
        name = local_name(cls)
        if name in target_names:
            nodes.append({
                "id": name, "label": name,
                "color": COLORS.get(name, "#f1f5f9"),
                "dashed": name in extra, "external": False,
            })
            seen_nodes.add(name)

    # External nodes
    for ext in ext_names:
        nodes.append({
            "id": ext, "label": ext, "sublabel": "",
            "color": ext_color(ext), "dashed": True, "external": True,
        })
        seen_nodes.add(ext)

    # Subclass edges
    for cls in all_classes:
        name = local_name(cls)
        if name not in target_names:
            continue
        for parent in g.objects(cls, RDFS.subClassOf):
            if isinstance(parent, BNode):
                continue
            p_name = local_name(parent)
            if str(parent).startswith(str(RKSDAG)):
                if p_name in target_names:
                    edges.append({"from": name, "to": p_name, "label": "", "type": "subclass"})
            else:
                ext_label = EXTERNAL_LABELS.get(str(parent))
                if ext_label and ext_label in ext_names:
                    edges.append({"from": name, "to": ext_label, "label": "", "type": "subclass"})

    # Object property edges
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        if not str(prop).startswith(str(RKSDAG)):
            continue
        pname = local_name(prop)
        domains = [local_name(o) for o in g.objects(prop, RDFS.domain)
                   if isinstance(o, URIRef) and local_name(o) in target_names]
        ranges = []
        for o in g.objects(prop, RDFS.range):
            if isinstance(o, URIRef):
                rn = local_name(o)
                if rn in target_names:
                    ranges.append(rn)
                else:
                    ext_l = EXTERNAL_LABELS.get(str(o))
                    if ext_l and ext_l in seen_nodes:
                        ranges.append(ext_l)
        for d in domains:
            for r in ranges:
                edges.append({"from": d, "to": r, "label": pname, "type": "property"})

    return {"nodes": nodes, "edges": edges}


def build_mapping_diagram(diagram_def: dict) -> dict:
    """Build data for a left-right mapping diagram (interface module)."""
    mappings = diagram_def["mappings"]
    left_nodes = {}
    right_nodes = {}

    for m in mappings:
        left_nodes[m["from"]] = True
        right_nodes[m["to"]] = True

    nodes_left = [{"id": n, "label": n, "color": COLORS.get(n, "#dbeafe")} for n in left_nodes]
    nodes_right = [{"id": n, "label": n, "color": ext_color(n)} for n in right_nodes]

    edges = [{"from": m["from"], "to": m["to"], "type": m["type"]} for m in mappings]

    return {"left": nodes_left, "right": nodes_right, "edges": edges,
            "left_label": diagram_def.get("left_label", "rksdag:")}


def render_diagram_html(diagram_id: str, data: dict, layout: str = "hierarchy") -> str:
    """Render a diagram as a self-contained HTML snippet with inline SVG.

    Args:
        diagram_id: Unique ID for the diagram.
        data: Node/edge data dict.
        layout: 'hierarchy' for ontology diagrams, 'lr-mapping' for interface.

    Returns:
        HTML string with embedded SVG rendering script.
    """
    data_json = json.dumps(data)
    uid = diagram_id.replace("-", "_")

    if layout == "lr-mapping":
        return _render_mapping_html(uid, data_json)
    else:
        return _render_hierarchy_html(uid, data_json)


def _render_hierarchy_html(uid: str, data_json: str) -> str:
    return f'''<div id="diagram_{uid}" style="overflow-x:auto"></div>
<script>
(function() {{
  const data = {data_json};
  const container = document.getElementById("diagram_{uid}");

  // Layout: hierarchical top-down using simple level assignment
  const nodeMap = {{}};
  data.nodes.forEach(n => {{ nodeMap[n.id] = n; n.children = []; n.parents = []; n.level = 0; }});

  // Build parent-child from subclass edges
  data.edges.filter(e => e.type === "subclass").forEach(e => {{
    if (nodeMap[e.from] && nodeMap[e.to]) {{
      nodeMap[e.from].parents.push(e.to);
      nodeMap[e.to].children.push(e.from);
    }}
  }});

  // Assign levels (BFS from roots)
  const roots = data.nodes.filter(n => n.parents.length === 0);
  const queue = [...roots.map(r => ({{ id: r.id, level: 0 }}))];
  const visited = new Set();
  while (queue.length > 0) {{
    const {{ id, level }} = queue.shift();
    if (visited.has(id)) continue;
    visited.add(id);
    if (nodeMap[id]) {{
      nodeMap[id].level = Math.max(nodeMap[id].level, level);
      nodeMap[id].children.forEach(c => queue.push({{ id: c, level: level + 1 }}));
    }}
  }}
  // Unvisited nodes get level 0
  data.nodes.filter(n => !visited.has(n.id)).forEach(n => n.level = 0);

  // Group by level
  const levels = {{}};
  data.nodes.forEach(n => {{
    if (!levels[n.level]) levels[n.level] = [];
    levels[n.level].push(n);
  }});

  const nodeH = 40, padX = 40, padY = 70;
  // Measure node widths based on label length
  data.nodes.forEach(n => {{ n.w = Math.max(n.label.length * 9 + 30, 140); }});
  const maxPerRow = Math.max(...Object.values(levels).map(l => l.length));
  const numLevels = Object.keys(levels).length;
  // Calculate row widths to find SVG width
  let maxRowW = 400;
  Object.values(levels).forEach(row => {{
    const rowW = row.reduce((s, n) => s + n.w, 0) + (row.length - 1) * padX + padX * 2;
    maxRowW = Math.max(maxRowW, rowW);
  }});
  const svgW = maxRowW;
  const svgH = numLevels * (nodeH + padY) + padY + 20;

  // Position nodes — center each row
  Object.entries(levels).forEach(([lvl, nodes]) => {{
    const totalW = nodes.reduce((s, n) => s + n.w, 0) + (nodes.length - 1) * padX;
    let curX = (svgW - totalW) / 2;
    nodes.forEach((n) => {{
      n.x = curX + n.w / 2;
      n.y = parseInt(lvl) * (nodeH + padY) + padY + nodeH / 2;
      curX += n.w + padX;
    }});
  }});

  // Build SVG
  let svg = `<svg width="${{svgW}}" height="${{svgH}}" xmlns="http://www.w3.org/2000/svg"
    style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif">`;

  // Arrowhead markers
  svg += `<defs>
    <marker id="arr_{uid}" viewBox="0 0 10 6" refX="10" refY="3" markerWidth="8" markerHeight="6" orient="auto">
      <path d="M0,0 L10,3 L0,6" fill="none" stroke="#3b82f6" stroke-width="1.2"/>
    </marker>
    <marker id="sub_{uid}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="10" markerHeight="10" orient="auto">
      <path d="M0,0 L10,5 L0,10 Z" fill="white" stroke="#94a3b8" stroke-width="1.5"/>
    </marker>
  </defs>`;

  // Draw edges
  data.edges.forEach(e => {{
    const from = nodeMap[e.from];
    const to = nodeMap[e.to];
    if (!from || !to) return;

    if (e.type === "subclass") {{
      // Straight line from child top to parent bottom
      svg += `<line x1="${{from.x}}" y1="${{from.y - nodeH/2}}" x2="${{to.x}}" y2="${{to.y + nodeH/2}}"
        stroke="#94a3b8" stroke-width="1.5" marker-end="url(#sub_{uid})"/>`;
    }} else {{
      // Property edge: exit from side, gentle curve
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      let x1, y1, x2, y2;
      if (Math.abs(dy) > nodeH) {{
        // Vertical: top/bottom
        x1 = from.x; y1 = from.y + (dy > 0 ? nodeH/2 : -nodeH/2);
        x2 = to.x; y2 = to.y + (dy > 0 ? -nodeH/2 : nodeH/2);
      }} else {{
        // Horizontal: left/right side
        x1 = from.x + (dx > 0 ? from.w/2 : -from.w/2); y1 = from.y;
        x2 = to.x + (dx > 0 ? -to.w/2 : to.w/2); y2 = to.y;
      }}
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      svg += `<path d="M${{x1}},${{y1}} Q${{mx}},${{y1}} ${{mx}},${{my}} Q${{mx}},${{y2}} ${{x2}},${{y2}}"
        fill="none" stroke="#3b82f6" stroke-width="1.2" marker-end="url(#arr_{uid})"/>`;
      if (e.label) {{
        svg += `<text x="${{mx + 6}}" y="${{my - 4}}" text-anchor="middle" font-size="10" fill="#2563eb">${{e.label}}</text>`;
      }}
    }}
  }});

  // Draw nodes
  data.nodes.forEach(n => {{
    const hw = n.w / 2, hh = nodeH / 2;
    const dash = n.dashed ? ' stroke-dasharray="5,3"' : '';
    svg += `<rect x="${{n.x - hw}}" y="${{n.y - hh}}" width="${{n.w}}" height="${{nodeH}}"
      rx="6" fill="${{n.color}}" stroke="${{n.external ? '#94a3b8' : '#cbd5e1'}}" stroke-width="1.5"${{dash}}/>`;
    svg += `<text x="${{n.x}}" y="${{n.y + 5}}" text-anchor="middle"
      font-size="12" font-weight="500" fill="${{n.external ? '#64748b' : '#1e293b'}}">${{n.label}}</text>`;
  }});

  svg += '</svg>';
  container.innerHTML = svg;
}})();
</script>'''


def _render_mapping_html(uid: str, data_json: str) -> str:
    return f'''<div id="diagram_{uid}" style="overflow-x:auto"></div>
<script>
(function() {{
  const data = {data_json};
  const container = document.getElementById("diagram_{uid}");

  const nodeW = 200, nodeH = 36, padY = 8;
  const leftX = 40, rightX = 500;
  const startY = 50;

  // Position left nodes
  data.left.forEach((n, i) => {{
    n.x = leftX; n.y = startY + i * (nodeH + padY);
  }});
  // Position right nodes
  data.right.forEach((n, i) => {{
    n.x = rightX; n.y = startY + i * (nodeH + padY);
  }});

  const maxLeft = data.left.length * (nodeH + padY) + startY;
  const maxRight = data.right.length * (nodeH + padY) + startY;
  const svgH = Math.max(maxLeft, maxRight) + 30;
  const svgW = rightX + nodeW + 60;

  const leftMap = {{}};
  data.left.forEach(n => leftMap[n.id] = n);
  const rightMap = {{}};
  data.right.forEach(n => rightMap[n.id] = n);

  let svg = `<svg width="${{svgW}}" height="${{svgH}}" xmlns="http://www.w3.org/2000/svg"
    style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif">`;

  // Markers
  svg += `<defs>
    <marker id="m_{uid}" viewBox="0 0 10 6" refX="10" refY="3" markerWidth="8" markerHeight="6" orient="auto">
      <path d="M0,0 L10,3 L0,6 Z" fill="#94a3b8"/>
    </marker>
    <marker id="meq_{uid}" viewBox="0 0 10 6" refX="10" refY="3" markerWidth="8" markerHeight="6" orient="auto">
      <path d="M0,0 L10,3 L0,6 Z" fill="#dc2626"/>
    </marker>
  </defs>`;

  // Group labels
  svg += `<text x="${{leftX + nodeW/2}}" y="24" text-anchor="middle" font-size="12" fill="#475569" font-weight="600">${{data.left_label}}</text>`;
  svg += `<text x="${{rightX + nodeW/2}}" y="24" text-anchor="middle" font-size="12" fill="#475569" font-weight="600">External standards</text>`;

  // Draw edges first (behind nodes)
  data.edges.forEach(e => {{
    const from = leftMap[e.from];
    const to = rightMap[e.to];
    if (!from || !to) return;
    const x1 = from.x + nodeW;
    const y1 = from.y + nodeH / 2;
    const x2 = to.x;
    const y2 = to.y + nodeH / 2;
    const isEq = e.type === "equivalent";
    const color = isEq ? "#dc2626" : "#94a3b8";
    const marker = isEq ? `url(#meq_{uid})` : `url(#m_{uid})`;
    const sw = isEq ? "1.8" : "1.2";
    svg += `<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}"
      stroke="${{color}}" stroke-width="${{sw}}" marker-end="${{marker}}" opacity="0.7"/>`;
    if (isEq) {{
      // Double arrow for equivalentClass
      svg += `<line x1="${{x2}}" y1="${{y2}}" x2="${{x1}}" y2="${{y1}}"
        stroke="${{color}}" stroke-width="1.2" marker-end="${{marker}}" opacity="0.5"/>`;
    }}
  }});

  // Left nodes
  data.left.forEach(n => {{
    svg += `<rect x="${{n.x}}" y="${{n.y}}" width="${{nodeW}}" height="${{nodeH}}"
      rx="5" fill="${{n.color}}" stroke="#93c5fd" stroke-width="1.2"/>`;
    svg += `<text x="${{n.x + nodeW/2}}" y="${{n.y + nodeH/2 + 4}}" text-anchor="middle"
      font-size="11" fill="#1e293b">${{n.label}}</text>`;
  }});

  // Right nodes
  data.right.forEach(n => {{
    svg += `<rect x="${{n.x}}" y="${{n.y}}" width="${{nodeW}}" height="${{nodeH}}"
      rx="5" fill="${{n.color}}" stroke="#d1d5db" stroke-width="1.2"/>`;
    svg += `<text x="${{n.x + nodeW/2}}" y="${{n.y + nodeH/2 + 4}}" text-anchor="middle"
      font-size="11" fill="#374151">${{n.label}}</text>`;
  }});

  svg += '</svg>';
  container.innerHTML = svg;
}})();
</script>'''


def main():
    """Generate all diagram HTML snippets."""
    ttl_files = {
        "agency": "agency.ttl", "documents": "documents.ttl",
        "procedure": "procedure.ttl", "voting": "voting.ttl",
    }

    for module_id, diagrams in DIAGRAMS.items():
        ttl_file = ttl_files.get(module_id)
        g = None
        all_classes = set()
        if ttl_file:
            g = Graph()
            g.parse(ONTOLOGY_DIR / ttl_file, format="turtle")
            all_classes = {s for s in g.subjects(RDF.type, OWL.Class)
                          if isinstance(s, URIRef) and str(s).startswith(str(RKSDAG))}

        print(f"\n{module_id} ({len(diagrams)} diagrams):")
        for ddef in diagrams:
            did = ddef["id"]
            layout = ddef.get("layout", "hierarchy")

            if layout == "lr-mapping":
                data = build_mapping_diagram(ddef)
            else:
                data = build_ontology_diagram(g, ddef, all_classes)

            html_content = render_diagram_html(did, data, layout)
            out_path = DOCS_DIR / f"{did}.html"
            out_path.write_text(html_content, encoding="utf-8")
            print(f"  ✓ {did}.html — {ddef['title']}")


if __name__ == "__main__":
    main()
