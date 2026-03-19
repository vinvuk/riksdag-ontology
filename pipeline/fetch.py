"""Riksdag API client — fetches members, documents, votes, and speeches.

Handles pagination, the single-item-as-object quirk, and rate limiting.
API docs: https://data.riksdagen.se/
"""

import time
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://data.riksdagen.se"

# Default page size (API max is 10000 for most endpoints)
DEFAULT_PAGE_SIZE = 200
REQUEST_DELAY = 0.5  # seconds between requests to be polite


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure.

    Args:
        value: Value to convert.
        default: Fallback if conversion fails.

    Returns:
        Integer value or default.
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _ensure_list(value: Any) -> list:
    """Normalize the Riksdag API's single-item-as-object quirk.

    The API may return a bare object instead of a single-element array
    when only one item matches. This function ensures the result is
    always a list.

    Args:
        value: A list, dict, or None from the API response.

    Returns:
        A list (possibly empty).
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _fetch_paginated(
    endpoint: str,
    params: dict,
    list_key: str,
    container_key: str | None = None,
    max_pages: int | None = None,
) -> list[dict]:
    """Fetch all pages from a paginated Riksdag API endpoint.

    Args:
        endpoint: API path (e.g., '/personlista/').
        params: Query parameters.
        list_key: Key containing the array of results.
        container_key: Optional parent key wrapping the list.
        max_pages: Stop after N pages (None = all).

    Returns:
        Combined list of all result dicts across pages.

    Raises:
        requests.HTTPError: If the API returns an error status.
    """
    all_results = []
    page = 1
    params = {**params, "utformat": "json"}

    while True:
        params["p"] = page
        url = f"{BASE_URL}{endpoint}"
        logger.info("Fetching %s page %d", endpoint, page)

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("API request failed: %s", e)
            raise

        # Navigate to the container if needed
        container = data.get(container_key, data) if container_key else data

        items = _ensure_list(container.get(list_key, []))
        all_results.extend(items)

        # Check pagination
        # Different endpoints use different field names:
        #   @sida = current page, @sidor = total pages (dokumentlista, anforandelista)
        #   @slutsida = last page (personlista — but often absent)
        #   @nasta_sida = URL to next page (ignore, use page counter instead)
        current_page = _safe_int(container.get("@sida"), page)
        last_page = _safe_int(
            container.get("@sidor") or container.get("@slutsida"),
            0,
        )

        logger.info(
            "  Got %d items (total so far: %d, page %d/%s)",
            len(items), len(all_results), current_page,
            last_page if last_page > 0 else "?",
        )

        # Stop conditions:
        # 1. Explicit last page known and reached
        if last_page > 0 and current_page >= last_page:
            break
        # 2. No pagination metadata — check for next page URL or item count
        if last_page == 0:
            has_next = bool(container.get("@nasta_sida"))
            if not has_next:
                break
            if len(items) < _safe_int(params.get("sz"), 200):
                break
        # 3. No items returned
        if len(items) == 0:
            break
        if max_pages and page >= max_pages:
            logger.info("  Reached max_pages=%d, stopping", max_pages)
            break

        page += 1
        time.sleep(REQUEST_DELAY)

    return all_results


def fetch_members(
    party: str | None = None,
    status: str = "tjg",
    max_pages: int | None = None,
) -> list[dict]:
    """Fetch members from the Riksdag API.

    Args:
        party: Filter by party abbreviation (e.g., 'S', 'M'). None = all.
        status: Member status filter ('tjg' = serving, '' = all).
        max_pages: Limit pagination (None = all).

    Returns:
        List of member dicts with fields: intressent_id, tilltalsnamn,
        efternamn, parti, valkrets, fodd_ar, kon, personuppdrag, etc.
    """
    params: dict[str, Any] = {"rdlstatus": status, "sz": DEFAULT_PAGE_SIZE}
    if party:
        params["parti"] = party
    return _fetch_paginated(
        "/personlista/", params, "person", container_key="personlista",
        max_pages=max_pages,
    )


def fetch_documents(
    doc_type: str = "prop",
    session: str | None = None,
    max_pages: int | None = None,
) -> list[dict]:
    """Fetch parliamentary documents from the Riksdag API.

    Args:
        doc_type: Document type code ('prop', 'mot', 'bet', 'ip', 'fr', etc.).
        session: Parliamentary session (e.g., '2024/25'). None = all.
        max_pages: Limit pagination (None = all).

    Returns:
        List of document dicts with fields: dok_id, rm, typ, beteckning,
        titel, datum, organ, etc.
    """
    params: dict[str, Any] = {"typ": doc_type, "sz": DEFAULT_PAGE_SIZE}
    if session:
        params["rm"] = session
    return _fetch_paginated(
        "/dokumentlista/", params, "dokument", container_key="dokumentlista",
        max_pages=max_pages,
    )


def fetch_votes(
    session: str | None = None,
    max_pages: int | None = None,
) -> list[dict]:
    """Fetch individual vote records from the Riksdag API.

    Note: Each record is one member's vote on one issue. A single voting
    event produces ~349 records (one per member). The pipeline must
    aggregate these into VotingEvent + Ballot triples.

    Args:
        session: Parliamentary session (e.g., '2024/25'). None = all.
        max_pages: Limit pagination (None = all).

    Returns:
        List of vote dicts with fields: votering_id, intressent_id,
        namn, parti, rost, beteckning, punkt, dok_id, etc.
    """
    # Use large page size — the vote API lacks pagination metadata,
    # so we rely on getting fewer items than sz to stop
    params: dict[str, Any] = {"sz": 10000}
    if session:
        params["rm"] = session
    return _fetch_paginated(
        "/voteringlista/", params, "votering", container_key="voteringlista",
        max_pages=max_pages,
    )


def fetch_speeches(
    session: str | None = None,
    max_pages: int | None = None,
) -> list[dict]:
    """Fetch debate speech records from the Riksdag API.

    Args:
        session: Parliamentary session (e.g., '2024/25'). None = all.
        max_pages: Limit pagination (None = all).

    Returns:
        List of speech dicts with fields: anforande_id, intressent_id,
        namn, parti, datum, beteckning, anforande_nummer, etc.
    """
    # Use large page size — the speech API lacks pagination metadata
    params: dict[str, Any] = {"sz": 10000}
    if session:
        params["rm"] = session
    return _fetch_paginated(
        "/anforandelista/", params, "anforande", container_key="anforandelista",
        max_pages=max_pages,
    )
