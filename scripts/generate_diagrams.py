"""Generate Mermaid flowchart diagrams for each ontology module.

Outputs standalone HTML files with embedded Mermaid that render
clean diagrams with proper edge routing. Each sub-diagram is focused
on a small cluster of classes for readability.

Output: docs/{module}-{name}.html (embedded by the docs generator)

Usage:
    python scripts/generate_diagrams.py
"""

from pathlib import Path

from rdflib import Graph, RDF, RDFS, OWL, Namespace, URIRef, BNode

PROJECT_ROOT = Path(__file__).parent.parent
ONTOLOGY_DIR = PROJECT_ROOT / "ontology"
DOCS_DIR = PROJECT_ROOT / "docs"
RKSDAG = Namespace("https://ontology.riksdagen.se/def/")

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

COLORS = {
    "MemberOfParliament": "#bfdbfe", "AlternateMember": "#bfdbfe",
    "Minister": "#bfdbfe", "Speaker": "#bfdbfe", "JusticeOfSupremeCourt": "#bfdbfe",
    "ParliamentaryBody": "#dbeafe", "CouncilOnLegislation": "#dbeafe",
    "PoliticalParty": "#dbeafe", "Committee": "#dbeafe", "EUCommittee": "#dbeafe",
    "Government": "#dbeafe", "Ministry": "#dbeafe", "ElectoralDistrict": "#dbeafe",
    "PartyMembership": "#e0f2fe", "CommitteeMembership": "#e0f2fe", "ParliamentaryTenure": "#e0f2fe",
    "Election": "#ede9fe", "ElectionResult": "#ede9fe", "SeatType": "#ede9fe",
    "FixedSeat": "#ede9fe", "AdjustmentSeat": "#ede9fe",
    "ParliamentaryDocument": "#dcfce7", "DocumentExpression": "#dcfce7", "DocumentFormat": "#dcfce7",
    "GovernmentBill": "#bbf7d0", "BudgetBill": "#bbf7d0", "SpringFiscalBill": "#bbf7d0",
    "SupplementaryBudget": "#bbf7d0", "GovernmentCommunication": "#bbf7d0",
    "Motion": "#bbf7d0", "IndividualMotion": "#d1fae5", "PartyMotion": "#d1fae5",
    "CommitteeMotion": "#d1fae5", "FollowUpMotion": "#d1fae5", "MultiPartyMotion": "#d1fae5",
    "CommitteeReport": "#bbf7d0", "CommitteeOpinion": "#bbf7d0", "CommitteeStatement": "#bbf7d0",
    "ParliamentaryCommunication": "#bbf7d0", "Pronouncement": "#bbf7d0",
    "Interpellation": "#fef3c7", "WrittenQuestion": "#fef3c7", "WrittenAnswer": "#fef3c7",
    "Statute": "#f3e8ff", "Act": "#f3e8ff", "Ordinance": "#f3e8ff",
    "AmendmentAct": "#f3e8ff", "ConsolidatedVersion": "#f3e8ff",
    "ProposalPoint": "#fce7f3", "Reservation": "#fce7f3", "SpecialOpinion": "#fce7f3",
    "Speech": "#fce7f3", "Debate": "#fce7f3",
    "Procedure": "#fef3c7", "Step": "#fef3c7", "Route": "#fef3c7",
    "ProceduralStage": "#fed7aa", "WorkPackage": "#fde68a", "BusinessItem": "#fde68a",
    "ParliamentarySession": "#fef3c7", "MandatePeriod": "#fef3c7",
    "VotingEvent": "#fee2e2", "Ballot": "#fee2e2", "VoteOutcome": "#fee2e2", "VotingMethod": "#fecaca",
}

DIAGRAMS = {
    "agency": [
        {"id": "agency-people", "title": "People", "direction": "BT",
         "classes": ["MemberOfParliament", "AlternateMember", "Minister", "Speaker"],
         "externals": ["foaf:Person", "schema:Person"]},
        {"id": "agency-orgs", "title": "Organizations", "direction": "BT",
         "classes": ["ParliamentaryBody", "CouncilOnLegislation", "PoliticalParty",
                     "Committee", "EUCommittee", "Government", "Ministry", "ElectoralDistrict"],
         "externals": ["org:FormalOrganization", "org:OrganizationalUnit"]},
        {"id": "agency-memberships", "title": "Memberships", "direction": "LR",
         "classes": ["PartyMembership", "CommitteeMembership", "ParliamentaryTenure"],
         "externals": ["org:Membership"]},
        {"id": "agency-elections", "title": "Elections", "direction": "TB",
         "classes": ["Election", "ElectionResult", "SeatType", "FixedSeat", "AdjustmentSeat"],
         "externals": []},
    ],
    "documents": [
        {"id": "documents-hierarchy", "title": "Core document types", "direction": "BT",
         "classes": ["ParliamentaryDocument", "GovernmentBill", "Motion",
                     "CommitteeReport", "ParliamentaryCommunication",
                     "Interpellation", "WrittenQuestion"],
         "externals": ["eli:LegalResource"]},
        {"id": "documents-motions", "title": "Motion subtypes", "direction": "BT",
         "classes": ["Motion", "IndividualMotion", "PartyMotion", "CommitteeMotion",
                     "FollowUpMotion", "MultiPartyMotion"],
         "externals": []},
        {"id": "documents-legal", "title": "Legal publications", "direction": "BT",
         "classes": ["Statute", "Act", "Ordinance", "AmendmentAct", "ConsolidatedVersion"],
         "externals": ["eli:LegalResource"]},
        {"id": "documents-debates", "title": "Debates and speeches", "direction": "LR",
         "classes": ["Debate", "Speech", "ProposalPoint", "Reservation", "SpecialOpinion",
                     "CommitteeReport"],
         "externals": [],
         "extra_classes": ["CommitteeReport"]},
    ],
    "procedure": [
        {"id": "procedure-core", "title": "Procedure model", "direction": "LR",
         "classes": ["Procedure", "Step", "Route", "ProceduralStage",
                     "WorkPackage", "BusinessItem"],
         "externals": []},
        {"id": "procedure-stages", "title": "Legislative stages", "direction": "BT",
         "classes": ["ProceduralStage", "Tabling", "CommitteeReferral",
                     "CommitteeDeliberation", "ChamberDebate", "ChamberDecision", "Promulgation"],
         "externals": []},
    ],
    "voting": [
        {"id": "voting-model", "title": "Voting model", "direction": "LR",
         "classes": ["VotingEvent", "Ballot", "VoteOutcome", "VotingMethod",
                     "CommitteeReport", "MemberOfParliament"],
         "externals": ["skos:Concept"],
         "extra_classes": ["CommitteeReport", "MemberOfParliament"]},
    ],
}


def local_name(uri) -> str:
    s = str(uri)
    return s.split("#")[-1] if "#" in s else s.split("/")[-1]


def safe_id(name: str) -> str:
    """Make a Mermaid-safe node ID."""
    return name.replace(":", "_").replace(" ", "_")


def build_mermaid(g: Graph, ddef: dict) -> str:
    """Build a Mermaid flowchart definition for one sub-diagram."""
    target_names = set(ddef["classes"])
    ext_names = set(ddef.get("externals", []))
    extra = set(ddef.get("extra_classes", []))
    direction = ddef.get("direction", "TB")

    all_classes = {
        s for s in g.subjects(RDF.type, OWL.Class)
        if isinstance(s, URIRef) and str(s).startswith(str(RKSDAG))
    }

    lines = [f"flowchart {direction}"]

    # Node definitions
    for cls in sorted(all_classes, key=local_name):
        name = local_name(cls)
        if name not in target_names:
            continue
        sid = safe_id(name)
        lines.append(f"    {sid}[{name}]")

    for ext in sorted(ext_names):
        sid = safe_id(ext)
        lines.append(f"    {sid}[{ext}]:::ext")

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
                    lines.append(f"    {safe_id(name)} -->|subclass| {safe_id(pname)}")
            else:
                ext_label = EXTERNAL_LABELS.get(str(parent))
                if ext_label and ext_label in ext_names:
                    lines.append(f"    {safe_id(name)} -->|subclass| {safe_id(ext_label)}")

    # Property edges
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        if not str(prop).startswith(str(RKSDAG)):
            continue
        pname = local_name(prop)
        all_node_ids = target_names | ext_names
        domains = [local_name(o) for o in g.objects(prop, RDFS.domain)
                   if isinstance(o, URIRef) and local_name(o) in all_node_ids]
        ranges = []
        for o in g.objects(prop, RDFS.range):
            if isinstance(o, URIRef):
                rn = local_name(o)
                if rn in all_node_ids:
                    ranges.append(rn)
                else:
                    ext_l = EXTERNAL_LABELS.get(str(o))
                    if ext_l and ext_l in all_node_ids:
                        ranges.append(ext_l)
        for d in domains:
            for r in ranges:
                if d != r:
                    lines.append(f"    {safe_id(d)} -.->|{pname}| {safe_id(r)}")

    # Styles
    for cls in all_classes:
        name = local_name(cls)
        if name in target_names:
            color = COLORS.get(name, "#f1f5f9")
            is_extra = name in extra
            stroke_style = ",stroke-dasharray: 5 5" if is_extra else ""
            lines.append(f"    style {safe_id(name)} fill:{color},stroke:#94a3b8,color:#1e293b{stroke_style}")

    for ext in ext_names:
        lines.append(f"    style {safe_id(ext)} fill:#f8fafc,stroke:#cbd5e1,color:#64748b,stroke-dasharray: 5 5")

    return "\n".join(lines)


def build_interface_mermaid() -> dict[str, str]:
    """Build Mermaid diagrams for the interface module showing alignment mappings.

    Returns:
        Dict of diagram_id → mermaid code.
    """
    g = Graph()
    g.parse(ONTOLOGY_DIR / "interface.ttl", format="turtle")

    ELI = Namespace("http://data.europa.eu/eli/ontology#")
    RPUBL = Namespace("http://rinfo.lagrummet.se/ns/2008/11/rinfo/publ#")
    SCHEMA = Namespace("https://schema.org/")
    ORG = Namespace("http://www.w3.org/ns/org#")
    DCTERMS = Namespace("http://purl.org/dc/terms/")
    FOAF = Namespace("http://xmlns.com/foaf/0.1/")

    def prefix_name(uri):
        s = str(uri)
        for ns, pfx in [(str(ELI), "eli:"), (str(RPUBL), "rpubl:"), (str(SCHEMA), "schema:"),
                         (str(ORG), "org:"), (str(DCTERMS), "dcterms:"), (str(FOAF), "foaf:"),
                         (str(RKSDAG), "")]:
            if s.startswith(ns):
                return pfx + s[len(ns):]
        return s.split("/")[-1].split("#")[-1]

    # --- Class alignments ---
    class_lines = ["flowchart LR"]
    class_nodes = set()

    for s, p, o in g.triples((None, RDFS.subClassOf, None)):
        if not isinstance(s, URIRef) or not isinstance(o, URIRef):
            continue
        if not str(s).startswith(str(RKSDAG)):
            continue
        sn = prefix_name(s)
        on = prefix_name(o)
        if sn not in class_nodes:
            class_lines.append(f"    {safe_id(sn)}[{sn}]")
            class_nodes.add(sn)
        if on not in class_nodes:
            class_lines.append(f"    {safe_id(on)}[{on}]")
            class_nodes.add(on)
        class_lines.append(f"    {safe_id(sn)} -->|subClassOf| {safe_id(on)}")

    for s, p, o in g.triples((None, OWL.equivalentClass, None)):
        if not isinstance(s, URIRef) or not isinstance(o, URIRef):
            continue
        sn = prefix_name(s)
        on = prefix_name(o)
        if sn not in class_nodes:
            class_lines.append(f"    {safe_id(sn)}[{sn}]")
            class_nodes.add(sn)
        if on not in class_nodes:
            class_lines.append(f"    {safe_id(on)}[{on}]")
            class_nodes.add(on)
        class_lines.append(f"    {safe_id(sn)} <-->|equivalentClass| {safe_id(on)}")

    # Style rksdag nodes vs external
    for n in class_nodes:
        sid = safe_id(n)
        if not any(n.startswith(p) for p in ["eli:", "rpubl:", "schema:", "org:", "dcterms:", "foaf:"]):
            color = COLORS.get(n, "#dbeafe")
            class_lines.append(f"    style {sid} fill:{color},stroke:#94a3b8,color:#1e293b")
        else:
            if n.startswith("eli:"): color = "#fef9c3"
            elif n.startswith("rpubl:"): color = "#fecaca"
            elif n.startswith("schema:"): color = "#d1fae5"
            else: color = "#f8fafc"
            class_lines.append(f"    style {sid} fill:{color},stroke:#cbd5e1,color:#374151,stroke-dasharray: 5 5")

    # --- Property alignments ---
    prop_lines = ["flowchart LR"]
    prop_nodes = set()

    for s, p, o in g.triples((None, RDFS.subPropertyOf, None)):
        if not isinstance(s, URIRef) or not isinstance(o, URIRef):
            continue
        if not str(s).startswith(str(RKSDAG)):
            continue
        sn = prefix_name(s)
        on = prefix_name(o)
        if sn not in prop_nodes:
            prop_lines.append(f"    {safe_id(sn)}[{sn}]")
            prop_nodes.add(sn)
        if on not in prop_nodes:
            prop_lines.append(f"    {safe_id(on)}[{on}]")
            prop_nodes.add(on)
        prop_lines.append(f"    {safe_id(sn)} -->|subPropertyOf| {safe_id(on)}")

    for n in prop_nodes:
        sid = safe_id(n)
        if not any(n.startswith(p) for p in ["eli:", "rpubl:", "schema:", "org:", "dcterms:", "foaf:"]):
            prop_lines.append(f"    style {sid} fill:#dbeafe,stroke:#94a3b8,color:#1e293b")
        else:
            if n.startswith("eli:"): color = "#fef9c3"
            elif n.startswith("rpubl:"): color = "#fecaca"
            elif n.startswith("schema:"): color = "#d1fae5"
            elif n.startswith("org:"): color = "#fae8ff"
            elif n.startswith("dcterms:"): color = "#e0e7ff"
            elif n.startswith("foaf:"): color = "#fff7ed"
            else: color = "#f8fafc"
            prop_lines.append(f"    style {sid} fill:{color},stroke:#cbd5e1,color:#374151,stroke-dasharray: 5 5")

    return {
        "interface-classes": "\n".join(class_lines),
        "interface-properties": "\n".join(prop_lines),
    }


def render_html(diagram_id: str, mermaid_code: str) -> str:
    """Wrap Mermaid code in a minimal HTML snippet for embedding."""
    return f'''<div class="mermaid-diagram">
<pre class="mermaid">
{mermaid_code}
</pre>
</div>'''


def main():
    ttl_files = {
        "agency": "agency.ttl", "documents": "documents.ttl",
        "procedure": "procedure.ttl", "voting": "voting.ttl",
    }

    # Clean old SVGs
    for svg in DOCS_DIR.glob("*-*.svg"):
        svg.unlink()

    total = 0
    for module_id, diagrams in DIAGRAMS.items():
        g = Graph()
        g.parse(ONTOLOGY_DIR / ttl_files[module_id], format="turtle")

        print(f"\n{module_id}:")
        for ddef in diagrams:
            mermaid = build_mermaid(g, ddef)
            html = render_html(ddef["id"], mermaid)

            out_path = DOCS_DIR / f"{ddef['id']}.html"
            out_path.write_text(html, encoding="utf-8")
            print(f"  ✓ {ddef['id']}.html — {ddef['title']}")
            total += 1

    # Interface module — special handling
    print(f"\ninterface:")
    interface_diagrams = build_interface_mermaid()
    titles = {"interface-classes": "Class alignments", "interface-properties": "Property alignments"}
    for did, mermaid in interface_diagrams.items():
        html = render_html(did, mermaid)
        out_path = DOCS_DIR / f"{did}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"  ✓ {did}.html — {titles.get(did, did)}")
        total += 1

    print(f"\nDone — {total} diagrams generated")


if __name__ == "__main__":
    main()
