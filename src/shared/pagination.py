"""Shared pagination helpers and constants.

Centralize defaults and maximums so runtime behavior and OpenAPI documentation
stay in sync.
"""
from typing import Tuple

# Defaults and limits (confirmed by user)
DEFAULT_PAGE = 1
DEFAULT_SIZE = 25
MAX_PAGE_SIZE = 100


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
