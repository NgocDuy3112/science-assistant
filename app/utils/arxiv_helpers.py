from datetime import datetime
from fuzzyfinder import fuzzyfinder
import os
import pymupdf
import pymupdf4llm
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownTextSplitter

from app.logger import global_logger


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
            global_logger.warning(f"Unknown category prefix: {prefix}")
            return False
    return True



def _optimize_query(query: str) -> str:
    """Minimal query optimization - preserve user intent while fixing obvious issues."""

    if any(
        field in query
        for field in ["ti:", "au:", "abs:", "cat:", "AND", "OR", "ANDNOT"]
    ):
        global_logger.debug("Field-specific or boolean query detected - no optimization")
        return query

    # Don't modify queries that are already quoted
    if query.startswith('"') and query.endswith('"'):
        global_logger.debug("Pre-quoted query detected - no optimization")
        return query

    # For very long queries (>10 terms), suggest user be more specific rather than auto-converting
    terms = query.split()
    if len(terms) > 10:
        global_logger.warning(
            f"Very long query ({len(terms)} terms) - consider using quotes for phrases or field-specific searches"
        )

    # Only optimization: preserve the original query exactly as intended
    return query



def _fuzzy_find_filenames(query: str, directory: str) -> list[str]:
    try:
        filenames = [
            os.path.join(root, file)
            for root, _, files in os.walk(directory, topdown=True)
            for file in files
        ]
        matches = list(fuzzyfinder(query, filenames))
        return matches
    except Exception as e:
        global_logger.error(f"Error during fuzzy file search: {e}")
        return []



def _create_documents_from_pdf(pdf_path: str) -> list[Document]:
    pdf = pymupdf.open(pdf_path)
    md_page_chunks = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
    documents: list[Document] = []
    for page_number, page_chunk in enumerate(md_page_chunks):
        metadata = {
            'file_path': pdf_path,
            'title': os.path.basename(pdf_path),
            'toc_items': page_chunk['toc_items'],
            'tables': [table.extract() for table in pdf[page_number].find_tables()]
        }
        text = page_chunk['text']
        documents.append(Document(
            page_content = text,
            metadata = metadata
        ))
    return documents