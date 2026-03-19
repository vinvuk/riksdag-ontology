"""Transform Riksdag API JSON data into RDF triples.

Maps API field names to ontology classes and properties using RDFLib.
This is a direct Python mapping approach (rather than RML) for clarity
and control over the transformation logic.
"""

import logging
from collections import defaultdict
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD, URIRef
from rdflib.namespace import FOAF, DCTERMS, SKOS

logger = logging.getLogger(__name__)

RKSDAG = Namespace("https://ontology.riksdagen.se/def/")
RKSDAGD = Namespace("https://data.riksdagen.se/id/")
RKSDAGV = Namespace("https://ontology.riksdagen.se/vocab/")


def _uri(path: str) -> URIRef:
    """Create a data instance URI with proper encoding.

    Args:
        path: Path segment (e.g., 'person/0123456789').

    Returns:
        Full URIRef under the rksdagd namespace.
    """
    # Encode each path segment to handle spaces and special chars
    parts = path.split("/")
    encoded = "/".join(quote(p, safe="") for p in parts)
    return URIRef(str(RKSDAGD) + encoded)


def _safe_date(value: str | None) -> Literal | None:
    """Convert a date string to an xsd:date literal, or None if invalid.

    Args:
        value: Date string in ISO format (YYYY-MM-DD) or None.

    Returns:
        An xsd:date Literal or None.
    """
    if not value or value.strip() == "" or value == "0001-01-01":
        return None
    # Handle datetime strings by taking just the date part
    date_part = value.strip()[:10]
    if len(date_part) == 10 and date_part[4] == "-" and date_part[7] == "-":
        return Literal(date_part, datatype=XSD.date)
    return None


def _session_uri(rm: str) -> URIRef:
    """Convert a session string like '2024/25' to a URI-safe form.

    Args:
        rm: Session identifier (e.g., '2024/25').

    Returns:
        URIRef like rksdagd:session/2024-25.
    """
    return _uri(f"session/{rm.replace('/', '-')}")


# Mapping from API party codes to vocabulary URIs
PARTY_MAP = {
    "S": RKSDAGV["party-S"],
    "M": RKSDAGV["party-M"],
    "SD": RKSDAGV["party-SD"],
    "C": RKSDAGV["party-C"],
    "V": RKSDAGV["party-V"],
    "KD": RKSDAGV["party-KD"],
    "L": RKSDAGV["party-L"],
    "MP": RKSDAGV["party-MP"],
    "-": RKSDAGV["party-independent"],
}

# Mapping from API vote strings to vocabulary URIs
VOTE_MAP = {
    "Ja": RKSDAGV["vote-Ja"],
    "Nej": RKSDAGV["vote-Nej"],
    "Avstår": RKSDAGV["vote-Avstar"],
    "Frånvarande": RKSDAGV["vote-Franvarande"],
}

# Mapping from API document type codes to ontology classes
DOCTYPE_MAP = {
    "prop": RKSDAG.GovernmentBill,
    "mot": RKSDAG.Motion,
    "bet": RKSDAG.CommitteeReport,
    "rskr": RKSDAG.ParliamentaryCommunication,
    "ip": RKSDAG.Interpellation,
    "fr": RKSDAG.WrittenQuestion,
    "skr": RKSDAG.GovernmentCommunication,
    "sou": RKSDAG.GovernmentInquiryReport,
    "ds": RKSDAG.MinistryReport,
    "dir": RKSDAG.TermsOfReference,
}


def transform_members(members: list[dict]) -> Graph:
    """Transform member API records into RDF triples.

    Creates MemberOfParliament individuals with party memberships,
    committee memberships, and personal data.

    Args:
        members: List of member dicts from fetch_members().

    Returns:
        RDF Graph containing member triples.
    """
    g = _new_graph()
    parties_created = set()
    committees_created = set()
    sessions_created = set()

    for m in members:
        iid = m.get("intressent_id", "").strip()
        if not iid:
            continue

        person_uri = _uri(f"person/{iid}")
        g.add((person_uri, RDF.type, RKSDAG.MemberOfParliament))
        g.add((person_uri, RKSDAG.intressentId, Literal(iid)))

        # Names
        fname = m.get("tilltalsnamn", "").strip()
        lname = m.get("efternamn", "").strip()
        if fname:
            g.add((person_uri, FOAF.givenName, Literal(fname)))
        if lname:
            g.add((person_uri, FOAF.familyName, Literal(lname)))
        if fname and lname:
            g.add((person_uri, RDFS.label, Literal(f"{fname} {lname}", lang="sv")))

        # Demographics
        birth_year = m.get("fodd_ar", "").strip()
        if birth_year and birth_year != "0":
            g.add((person_uri, RKSDAG.birthYear, Literal(birth_year, datatype=XSD.gYear)))

        gender = m.get("kon", "").strip()
        if gender:
            g.add((person_uri, RKSDAG.gender, Literal(gender)))

        # Image
        img = m.get("bild_url_max", "").strip()
        if img:
            g.add((person_uri, RKSDAG.imageUrl, Literal(img, datatype=XSD.anyURI)))

        # Current party — create PartyMembership from top-level parti field
        # (The API does not include party in personuppdrag)
        party_code = m.get("parti", "").strip()
        if party_code:
            party_uri = _uri(f"org/{party_code}")
            if party_code not in parties_created:
                g.add((party_uri, RDF.type, RKSDAG.PoliticalParty))
                g.add((party_uri, RKSDAG.partyAbbreviation, Literal(party_code)))
                if party_code in PARTY_MAP:
                    g.add((party_uri, SKOS.exactMatch, PARTY_MAP[party_code]))
                parties_created.add(party_code)

            # Create a PartyMembership (no end date = current)
            party_membership_uri = _uri(f"membership/{iid}-party-{party_code}")
            g.add((party_membership_uri, RDF.type, RKSDAG.PartyMembership))
            g.add((party_membership_uri, RKSDAG.inOrganization, party_uri))
            g.add((person_uri, RKSDAG.hasMembership, party_membership_uri))

        # Electoral district
        valkrets = m.get("valkrets", "").strip()
        if valkrets:
            district_uri = _uri(f"district/{_slugify(valkrets)}")
            g.add((district_uri, RDF.type, RKSDAG.ElectoralDistrict))
            g.add((district_uri, RDFS.label, Literal(valkrets, lang="sv")))

        # Assignments (personuppdrag → memberships)
        uppdrag_container = m.get("personuppdrag", {})
        if not isinstance(uppdrag_container, dict):
            uppdrag_container = {}
        uppdrag_list = uppdrag_container.get("uppdrag", [])
        if isinstance(uppdrag_list, dict):
            uppdrag_list = [uppdrag_list]
        if not isinstance(uppdrag_list, list):
            uppdrag_list = []

        for uppdrag in uppdrag_list:
            organ = uppdrag.get("organ_kod", "").strip()
            roll = uppdrag.get("roll_kod", "").strip()
            typ = uppdrag.get("typ", "").strip()
            from_date = uppdrag.get("from", "").strip()
            to_date = uppdrag.get("tom", "").strip()
            status = uppdrag.get("status", "").strip()

            if not organ:
                continue

            # Sanitize organ code (API sometimes has spaces and junk)
            organ = _slugify(organ)
            if not organ:
                continue

            # Create membership URI
            date_slug = from_date[:10] if from_date else "unknown"
            membership_uri = _uri(f"membership/{iid}-{organ}-{date_slug}")

            # Determine membership type
            if typ == "parti":
                g.add((membership_uri, RDF.type, RKSDAG.PartyMembership))
                org_uri = _uri(f"org/{organ}")
                if organ not in parties_created:
                    g.add((org_uri, RDF.type, RKSDAG.PoliticalParty))
                    g.add((org_uri, RKSDAG.partyAbbreviation, Literal(organ)))
                    parties_created.add(organ)
            elif typ in ("kammaruppdrag", "uppdrag"):
                g.add((membership_uri, RDF.type, RKSDAG.CommitteeMembership))
                org_uri = _uri(f"org/{organ}")
                if organ not in committees_created:
                    g.add((org_uri, RDF.type, RKSDAG.Committee))
                    g.add((org_uri, RKSDAG.organCode, Literal(organ)))
                    committees_created.add(organ)
            else:
                # Other assignment types (departement, etc.)
                g.add((membership_uri, RDF.type, RKSDAG.CommitteeMembership))
                org_uri = _uri(f"org/{organ}")

            g.add((person_uri, RKSDAG.hasMembership, membership_uri))
            g.add((membership_uri, RKSDAG.inOrganization, org_uri))

            # Role
            if roll:
                role_uri = _role_uri(roll)
                if role_uri:
                    g.add((membership_uri, RKSDAG.hasRole, role_uri))

            # Dates
            start = _safe_date(from_date)
            if start:
                g.add((membership_uri, RKSDAG.startDate, start))
            end = _safe_date(to_date)
            if end:
                g.add((membership_uri, RKSDAG.endDate, end))

    logger.info("Transformed %d members into %d triples", len(members), len(g))
    return g


def transform_documents(documents: list[dict]) -> Graph:
    """Transform document API records into RDF triples.

    Creates ParliamentaryDocument individuals with metadata,
    committee assignments, and session links.

    Args:
        documents: List of document dicts from fetch_documents().

    Returns:
        RDF Graph containing document triples.
    """
    g = _new_graph()
    sessions_created = set()
    committees_created = set()

    for doc in documents:
        dok_id = doc.get("dok_id", "").strip()
        if not dok_id:
            continue

        doc_uri = _uri(f"doc/{dok_id}")
        doc_type = doc.get("typ", "").strip().lower()

        # Type assignment
        owl_class = DOCTYPE_MAP.get(doc_type, RKSDAG.ParliamentaryDocument)
        g.add((doc_uri, RDF.type, owl_class))
        g.add((doc_uri, RDF.type, RKSDAG.ParliamentaryDocument))

        # Core metadata
        g.add((doc_uri, RKSDAG.dokId, Literal(dok_id)))

        beteckning = doc.get("beteckning", "").strip()
        rm = doc.get("rm", "").strip()
        if beteckning and rm:
            # Use full designation (e.g., "2024/25:42") — single value, not both short and long
            full = f"{rm}:{beteckning}" if ":" not in beteckning else beteckning
            g.add((doc_uri, RKSDAG.designation, Literal(full)))
        elif beteckning:
            g.add((doc_uri, RKSDAG.designation, Literal(beteckning)))

        titel = doc.get("titel", "").strip()
        if titel:
            g.add((doc_uri, RKSDAG.documentTitle, Literal(titel, lang="sv")))

        # Dates
        datum = _safe_date(doc.get("datum"))
        if datum:
            g.add((doc_uri, RKSDAG.documentDate, datum))

        beslutsdatum = _safe_date(doc.get("beslutsdatum"))
        if beslutsdatum:
            g.add((doc_uri, RKSDAG.decisionDate, beslutsdatum))

        debattdag = _safe_date(doc.get("debattdag"))
        if debattdag:
            g.add((doc_uri, RKSDAG.debateDate, debattdag))

        # Session
        if rm:
            session_uri = _session_uri(rm)
            if rm not in sessions_created:
                g.add((session_uri, RDF.type, RKSDAG.ParliamentarySession))
                g.add((session_uri, RKSDAG.sessionId, Literal(rm)))
                g.add((session_uri, RDFS.label, Literal(f"Riksmötet {rm}", lang="sv")))
                sessions_created.add(rm)
            g.add((doc_uri, RKSDAG.partOfSession, session_uri))

        # Committee (organ)
        organ = doc.get("organ", "").strip()
        if organ:
            committee_uri = _uri(f"org/{organ}")
            if organ not in committees_created:
                g.add((committee_uri, RDF.type, RKSDAG.Committee))
                g.add((committee_uri, RKSDAG.organCode, Literal(organ)))
                committees_created.add(organ)
            g.add((doc_uri, RKSDAG.handledBy, committee_uri))

        # Document references
        refs = doc.get("dokreferens", {})
        if isinstance(refs, dict):
            ref_list = refs.get("referens", [])
            if isinstance(ref_list, dict):
                ref_list = [ref_list]
            for ref in ref_list:
                ref_id = ref.get("ref_dok_id", "").strip()
                if ref_id:
                    g.add((doc_uri, RKSDAG.references, _uri(f"doc/{ref_id}")))

    logger.info("Transformed %d documents into %d triples", len(documents), len(g))
    return g


def transform_votes(votes: list[dict]) -> Graph:
    """Transform flat vote records into VotingEvent + Ballot triples.

    The API returns one row per member per vote. This function aggregates
    them into VotingEvents with linked Ballots.

    Args:
        votes: List of vote dicts from fetch_votes().

    Returns:
        RDF Graph containing voting triples.
    """
    g = _new_graph()

    # Group votes by votering_id to create VotingEvents
    events: dict[str, list[dict]] = defaultdict(list)
    for v in votes:
        vid = v.get("votering_id", "").strip()
        if vid:
            events[vid].append(v)

    for vid, ballots in events.items():
        # Use first ballot for event-level metadata
        first = ballots[0]
        beteckning = first.get("beteckning", "").strip()
        punkt = first.get("punkt", "").strip()
        rm = first.get("rm", "").strip()
        dok_id = first.get("dok_id", "").strip()

        event_uri = _uri(f"vote/{vid}")
        g.add((event_uri, RDF.type, RKSDAG.VotingEvent))
        g.add((event_uri, RKSDAG.voteringId, Literal(vid)))

        # Vote date from systemdatum
        datum = first.get("datum", first.get("systemdatum", ""))
        vote_date = _safe_date(datum)
        if vote_date:
            g.add((event_uri, RKSDAG.voteDate, vote_date))

        # Point number
        if punkt and punkt.isdigit():
            g.add((event_uri, RKSDAG.pointNumber,
                   Literal(int(punkt), datatype=XSD.nonNegativeInteger)))

        # Link to committee report
        if dok_id:
            g.add((event_uri, RKSDAG.onDocument, _uri(f"doc/{dok_id}")))

        # Aggregate counts
        counts = {"Ja": 0, "Nej": 0, "Avstår": 0, "Frånvarande": 0}
        for b in ballots:
            rost = b.get("rost", "").strip()
            if rost in counts:
                counts[rost] += 1

        g.add((event_uri, RKSDAG.yesCount,
               Literal(counts["Ja"], datatype=XSD.nonNegativeInteger)))
        g.add((event_uri, RKSDAG.noCount,
               Literal(counts["Nej"], datatype=XSD.nonNegativeInteger)))
        g.add((event_uri, RKSDAG.abstainCount,
               Literal(counts["Avstår"], datatype=XSD.nonNegativeInteger)))
        g.add((event_uri, RKSDAG.absentCount,
               Literal(counts["Frånvarande"], datatype=XSD.nonNegativeInteger)))

        # Winning option
        if counts["Ja"] > counts["Nej"]:
            g.add((event_uri, RKSDAG.winningOption, Literal("Ja")))
        elif counts["Nej"] > counts["Ja"]:
            g.add((event_uri, RKSDAG.winningOption, Literal("Nej")))

        # Individual ballots
        for b in ballots:
            iid = b.get("intressent_id", "").strip()
            rost = b.get("rost", "").strip()
            if not iid or not rost:
                continue

            ballot_uri = _uri(f"ballot/{iid}-{vid}")
            g.add((ballot_uri, RDF.type, RKSDAG.Ballot))
            g.add((ballot_uri, RKSDAG.voter, _uri(f"person/{iid}")))
            g.add((ballot_uri, RKSDAG.inVotingEvent, event_uri))
            g.add((event_uri, RKSDAG.hasBallot, ballot_uri))

            vote_option = VOTE_MAP.get(rost)
            if vote_option:
                g.add((ballot_uri, RKSDAG.voteOption, vote_option))

    logger.info(
        "Transformed %d vote records into %d events, %d triples",
        len(votes), len(events), len(g),
    )
    return g


def transform_speeches(speeches: list[dict]) -> Graph:
    """Transform speech API records into RDF triples.

    Args:
        speeches: List of speech dicts from fetch_speeches().

    Returns:
        RDF Graph containing speech triples.
    """
    g = _new_graph()

    for s in speeches:
        sid = s.get("anforande_id", "").strip()
        if not sid:
            continue

        speech_uri = _uri(f"speech/{sid}")
        g.add((speech_uri, RDF.type, RKSDAG.Speech))
        g.add((speech_uri, RKSDAG.speechId, Literal(sid)))

        # Speaker
        iid = s.get("intressent_id", "").strip()
        if iid:
            g.add((speech_uri, RKSDAG.speaker, _uri(f"person/{iid}")))

        # Speech number
        nummer = s.get("anforande_nummer", s.get("talarnummer", "")).strip()
        if nummer and nummer.isdigit():
            g.add((speech_uri, RKSDAG.speechNumber,
                   Literal(int(nummer), datatype=XSD.nonNegativeInteger)))

        # Date
        datum = _safe_date(s.get("datum"))
        if datum:
            g.add((speech_uri, RKSDAG.documentDate, datum))

        # Link to debate topic (betänkande/interpellation)
        dok_id = s.get("dok_id", "").strip()
        if dok_id:
            g.add((speech_uri, RKSDAG.partOfDebate, _uri(f"doc/{dok_id}")))

        # Speech text (if available)
        text = s.get("anforandetext", "").strip()
        if text:
            g.add((speech_uri, RKSDAG.speechText, Literal(text)))

    logger.info("Transformed %d speeches into %d triples", len(speeches), len(g))
    return g


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_graph() -> Graph:
    """Create a new RDF graph with standard namespace bindings.

    Returns:
        A Graph with rksdag/rksdagd/rksdagv prefixes bound.
    """
    g = Graph()
    g.bind("rksdag", RKSDAG)
    g.bind("rksdagd", RKSDAGD)
    g.bind("rksdagv", RKSDAGV)
    g.bind("foaf", FOAF)
    g.bind("dcterms", DCTERMS)
    g.bind("skos", SKOS)
    return g


def _slugify(text: str) -> str:
    """Convert a Swedish string to a URL-safe slug.

    Args:
        text: Input string (e.g., 'Stockholms kommun').

    Returns:
        Lowercased, hyphenated ASCII-safe string.
    """
    replacements = {
        "å": "a", "ä": "a", "ö": "o",
        "Å": "A", "Ä": "A", "Ö": "O",
        " ": "-",
    }
    result = text.lower()
    for old, new in replacements.items():
        result = result.replace(old, new)
    # Remove anything that's not alphanumeric or hyphen
    return "".join(c for c in result if c.isalnum() or c == "-")


ROLE_MAP = {
    "Ledamot": RKSDAGV["role-Ledamot"],
    "Suppleant": RKSDAGV["role-Suppleant"],
    "Ordförande": RKSDAGV["role-Ordforande"],
    "Vice ordförande": RKSDAGV["role-ViceOrdforande"],
    "Talman": RKSDAGV["role-Talman"],
    "Förste vice talman": RKSDAGV["role-ForstViceTalman"],
    "Andre vice talman": RKSDAGV["role-AndreViceTalman"],
    "Tredje vice talman": RKSDAGV["role-TredjeViceTalman"],
    "Gruppledare": RKSDAGV["role-Gruppledare"],
    # API also uses short codes
    "led": RKSDAGV["role-Ledamot"],
    "ers": RKSDAGV["role-Suppleant"],
    "ordf": RKSDAGV["role-Ordforande"],
    "vordf": RKSDAGV["role-ViceOrdforande"],
}


def _role_uri(role_code: str) -> URIRef | None:
    """Map an API role code to its SKOS concept URI.

    Args:
        role_code: Role string from the API (e.g., 'Ledamot', 'led').

    Returns:
        SKOS concept URI or None if not recognized.
    """
    return ROLE_MAP.get(role_code)
