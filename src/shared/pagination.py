"""Shared pagination helpers and constants.

Centralize defaults and maximums so runtime behavior and OpenAPI documentation
stay in sync.
"""
from typing import Tuple

# Defaults and limits (confirmed by user)
DEFAULT_PAGE = 1
DEFAULT_SIZE = 20
MAX_PAGE_SIZE = 100
EXPORT_SYNC_THRESHOLD = 5000  # rows threshold to decide sync vs async export


def clamp_pagination(page: int, size: int, *,
                     default_page: int = DEFAULT_PAGE,
                     default_size: int = DEFAULT_SIZE,
                     max_size: int = MAX_PAGE_SIZE) -> Tuple[int, int]:
    """Normalize and clamp pagination inputs.

    - Converts None/invalid handling is expected to be done by the caller (ValueError
      handling). This helper assumes `page` and `size` are ints.
    - Ensures page >= 1
    - Ensures 1 <= size <= max_size (clamps to max_size)

    Returns (page, size) normalized.
    """
    if page is None:
        page = default_page
    if size is None:
        size = default_size

    # Ensure integers (caller is expected to parse/raise on bad input)
    try:
        page = int(page)
    except Exception:
        page = default_page
    try:
        size = int(size)
    except Exception:
        size = default_size

    if page < 1:
        page = 1
    if size < 1:
        size = default_size
    if size > max_size:
        size = max_size

    return page, size


def build_page_envelope(items_plus_one, page: int, size: int, *, with_total: bool = False, total: int = None, meta: dict = None):
    """Build the standardized pagination envelope.

    - items_plus_one: list containing up to size+1 serialized items
    - page, size: requested page/size
    - with_total: whether total is requested (total may be None if not provided)
    - total: optional total count
    - meta: optional dictionary with extra metadata

    Returns a dict ready to jsonify.
    """
    has_more = len(items_plus_one) > size
    items = items_plus_one[:size]
    returned = len(items)
    next_page = page + 1 if has_more else None
    prev_page = page - 1 if page > 1 else None

    envelope = {
        'items': items,
        'page': page,
        'size': size,
        'returned': returned,
        'has_more': has_more,
        'next_page': next_page,
        'prev_page': prev_page,
    }

    if with_total:
        envelope['total'] = total if total is not None else None

    if meta:
        envelope['meta'] = meta

    return envelope
