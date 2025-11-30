from __future__ import annotations
import os
import arxiv
import requests
import concurrent.futures
from urllib.parse import urlparse
from typing import Literal
from dateutil import parser
from datetime import timezone

from app.configs import settings
from app.logger import global_logger
from app.schemas.arxiv_mcp import Paper
from app.utils.arxiv_mcp import _optimize_query, _validate_categories, _fuzzy_find_filenames




def search_papers_from_arxiv(
    query: str, 
    batch_size: int, 
    sort_by: Literal["relevance", "lastUpdatedDate"], 
    categories: list[str] | str = ['cs', 'math'],
    date_from: str = None, 
    date_to: str = None,
    being_called_from_download_tool: bool = False
) -> list[Paper]:
    if isinstance(categories, str):
        categories = [categories]
    if not being_called_from_download_tool:
        global_logger.info("Calling the `search_papers_from_arxiv` tool")
    """Search arXiv using the official arxiv Python library."""
    try:
        query_parts = []
        global_logger.debug(f"Original query: {query}")
        # Process the query
        if not query.strip():
            raise Exception(f"[ERROR] Invalid query: {query}")
        optimized_query = _optimize_query(query)
        query_parts.append(f"({optimized_query})")
        if optimized_query != query:
            global_logger.debug(f"Optimized query: '{query}' -> '{optimized_query}'")
        # Process the categories
        if not _validate_categories(categories):
            raise Exception(f"[ERROR] Invalid categories")
        category_filter = " OR ".join(f"cat:{cat}" for cat in categories)
        query_parts.append(f"({category_filter})")
        global_logger.debug(f"Added category filter: {category_filter}")
        # Combine the queries
        if not query_parts:
            raise Exception("[ERROR] No search criteria provided")
        final_query = " ".join(query_parts)
        global_logger.debug(f"Final arXiv query: {final_query}")
        # Sort criteria
        sort_map = {
            "relevance": arxiv.SortCriterion.Relevance,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
        }
        sort_criterion = sort_map.get(sort_by, arxiv.SortCriterion.Relevance)
        global_logger.debug(f"Sort by {sort_by}")
        client = arxiv.Client()
        search = arxiv.Search(
            query=optimized_query,
            max_results=batch_size,
            sort_by=sort_criterion
        )
        # Parse date filters if provided
        date_from_parsed = None
        date_to_parsed = None
        if date_from:
            try:
                date_from_parsed = parser.parse(date_from).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError) as e:
                global_logger.error(f"Error: Invalid date_from format - {str(e)}")
        if date_to:
            try:
                date_to_parsed = parser.parse(date_to).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError) as e:
                global_logger.error(f"Error: Invalid date_to format - {str(e)}")
        # Process the result
        results: list[Paper] = []
        result_count = 0
        for paper in client.results(search):
            if result_count >= batch_size:
                break
            paper_date = paper.published
            if not paper_date.tzinfo:
                paper_date = paper_date.replace(tzinfo=timezone.utc)
            if date_from_parsed and paper_date < date_from_parsed:
                continue
            if date_to_parsed and paper_date > date_to_parsed:
                continue
            authors = [author.name for author in paper.authors]
            published_iso = paper.published.isoformat() if paper.published else ""
            primary_category = paper.primary_category if hasattr(paper, 'primary_category') else ""
            results.append(Paper(
                id=paper.entry_id.split('/')[-1],
                title=paper.title,
                authors=authors,
                summary=paper.summary,
                published=published_iso,
                pdf_url=paper.pdf_url,
                primary_category=primary_category,
            ))
        if not being_called_from_download_tool:
            global_logger.info("`search_papers_from_arxiv` completed!")
        return results
    except arxiv.ArxivError as e:
        global_logger.error(f"ArXiv API Error: {e}")
    except Exception as e:
        global_logger.error(e)



def download_papers(
    query: str, 
    batch_size: int, 
    sort_by: Literal["relevance", "lastUpdatedDate"], 
    categories: list[str] | str = ['cs', 'math'],
    date_from: str = None, 
    date_to: str = None,
    output_dir: str = settings.PAPERS_DIR
) -> list[str]:
    """Download multiple PDFs concurrently and return their saved paths.

    Args:
        papers: List of Paper objects (with at least 'pdf_url').
        output_dir: Directory to save PDFs.
    Returns:
        List of absolute file paths of the downloaded PDFs.
    """
    def _download_one(paper: Paper, output_dir: str) -> str | None:
        pdf_url = paper.pdf_url
        parsed_url = urlparse(pdf_url)
        if not (parsed_url and parsed_url.scheme and parsed_url.netloc):
            global_logger.error(f"Invalid URL: {pdf_url}")
            return None
        try:
            response = requests.get(pdf_url, stream=True, timeout=20)
            response.raise_for_status()
            category = paper.primary_category.replace(".", "_")
            os.makedirs(os.path.join(output_dir, category), exist_ok=True)
            raw_title = paper.title.strip()
            safe_title = "".join(c if c.isalnum() or c in " -_." else "_" for c in raw_title)
            filename = f"{safe_title}.pdf"
            base_path = os.path.join(output_dir, category)
            output_path = os.path.join(base_path, filename)
            if os.path.exists(output_path):
                global_logger.info(f"File {output_path} already existed!. Skipping it.")
            else:
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                global_logger.info(f"Download file {pdf_url} to {output_path} successfully!")
            return os.path.abspath(output_path)
        except Exception as e:
            global_logger.error(f"Failed to download {pdf_url}: {e}")
            return None
    global_logger.info("Calling the `download_papers` tool")
    if output_dir is None:
        output_dir = os.path.expanduser(settings.PAPERS_DIR)
    papers = search_papers_from_arxiv(
        query,
        batch_size,
        sort_by,
        categories,
        date_from,
        date_to,
        being_called_from_download=True
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(_download_one, paper, output_dir) for paper in papers]
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                global_logger.error(f"Exception in download thread: {e}")
        global_logger.info("`download_papers` completed!")
        return results


def list_papers(papers_dir: str = settings.PAPERS_DIR):
    papers = [
        os.path.join(root, file)
        for root, _, files in os.walk(papers_dir, topdown=True)
        for file in files
        if file.endswith('.pdf')
    ]
    return papers



def list_papers_from_query(
    query: str,
    papers_dir: str = settings.PAPERS_DIR
) -> list[str]:
    list_file_paths = _fuzzy_find_filenames(query, papers_dir)
    return list_file_paths



def delete_papers(
    query: str,
    papers_dir: str = settings.PAPERS_DIR
) -> list[str]:
    delete_file_paths = list_papers_from_query(query, papers_dir)
    for path in delete_file_paths:
        try:
            os.remove(path)
            global_logger.info(f"Deleted file: {path}")
        except Exception as e:
            global_logger.error(f"Failed to delete {path}: {e}")
    return delete_file_paths