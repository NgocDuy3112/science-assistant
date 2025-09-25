from datetime import datetime
from log.logger import get_logger
from fuzzyfinder import fuzzyfinder
import os
import pymupdf


logger = get_logger("mcp_arxiv")


VALID_CATEGORIES = [
    "cs",
    "econ",
    "eess",
    "math",
    "physics",
    "q-bio",
    "q-fin",
    "stat",
    "astro-ph",
    "cond-mat",
    "gr-qc",
    "hep-ex",
    "hep-lat",
    "hep-ph",
    "hep-th",
    "math-ph",
    "nlin",
    "nucl-ex",
    "nucl-th",
    "quant-ph",
]


def _validate_categories(categories: list[str]) -> bool:
    """Validate that all provided categories are valid arXiv categories."""
    for category in categories:
        if "." in category:
            prefix = category.split(".")[0]
        else:
            prefix = category
        if prefix not in VALID_CATEGORIES:
            logger.warning(f"Unknown category prefix: {prefix}")
            return False
    return True


def _optimize_query(query: str) -> str:
    """Minimal query optimization - preserve user intent while fixing obvious issues."""

    # Don't modify queries with existing field specifiers (ti:, au:, abs:, cat:)
    if any(
        field in query
        for field in ["ti:", "au:", "abs:", "cat:", "AND", "OR", "ANDNOT"]
    ):
        logger.debug("Field-specific or boolean query detected - no optimization")
        return query

    # Don't modify queries that are already quoted
    if query.startswith('"') and query.endswith('"'):
        logger.debug("Pre-quoted query detected - no optimization")
        return query

    # For very long queries (>10 terms), suggest user be more specific rather than auto-converting
    terms = query.split()
    if len(terms) > 10:
        logger.warning(
            f"Very long query ({len(terms)} terms) - consider using quotes for phrases or field-specific searches"
        )

    # Only optimization: preserve the original query exactly as intended
    return query


def _fuzzy_find_filenames(query: str, directory: str) -> list[str]:
    try:
        for root, dirs, files in os.walk(directory):
            matches = list(fuzzyfinder(query, files))
            if matches:
                # Get absolute paths
                abs_paths = [os.path.abspath(os.path.join(root, match)) for match in matches]
                return abs_paths
    except Exception as e:
        logger.error(f"Error during fuzzy file search: {e}")
        return []



def index_papers_from_arxiv():
    pass