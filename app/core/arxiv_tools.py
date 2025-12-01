from __future__ import annotations
import os
import arxiv
import httpx
import asyncio
from urllib.parse import urlparse
from dateutil import parser
from datetime import timezone

from app.configs import settings
from app.logger import global_logger
from app.schemas.paper import Paper
from app.schemas.arxiv_tools import *
from app.utils.arxiv_helpers import _optimize_query, _validate_categories, _fuzzy_find_filenames




async def search_papers(request: SearchPapersRequest) -> list[Paper]:
    if isinstance(categories, str):
        categories = [categories]
    global_logger.info("Calling the `search_papers` tool")
    """Search arXiv using the official arxiv Python library."""
    try:
        query_parts = []
        global_logger.debug(f"Original query: {request.query}")
        # Process the query
        if not request.query.strip():
            raise Exception(f"[ERROR] Invalid query: {request.query}")
        optimized_query = _optimize_query(request.query)
        query_parts.append(f"({optimized_query})")
        if optimized_query != request.query:
            global_logger.debug(f"Optimized query: '{request.query}' -> '{optimized_query}'")
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
        sort_criterion = sort_map.get(request.sort_by, arxiv.SortCriterion.Relevance)
        global_logger.debug(f"Sort by {request.sort_by}")
        client = arxiv.Client()
        search = arxiv.Search(
            query=optimized_query,
            max_results=request.batch_size,
            sort_by=sort_criterion
        )
        # Parse date filters if provided
        date_from_parsed = None
        date_to_parsed = None
        if request.date_from:
            try:
                date_from_parsed = parser.parse(request.date_from).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError) as e:
                global_logger.error(f"Error: Invalid date_from format - {str(e)}")
        if request.date_to:
            try:
                date_to_parsed = parser.parse(request.date_to).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError) as e:
                global_logger.error(f"Error: Invalid date_to format - {str(e)}")
        # Process the result
        results: list[Paper] = []
        result_count = 0
        results_iter = client.results(search)
        async for paper in results_iter:
            if result_count >= request.batch_size:
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
        global_logger.info("`search_papers_from_arxiv` completed!")
        return results
    except arxiv.ArxivError as e:
        global_logger.error(f"ArXiv API Error: {e}")
    except Exception as e:
        global_logger.error(e)



async def download_papers(request: DownloadPapersRequest) -> list[str]:
    """Download multiple PDFs concurrently and return their saved paths.

    Args:
        papers: List of Paper objects (with at least 'pdf_url').
        output_dir: Directory to save PDFs.
    Returns:
        List of absolute file paths of the downloaded PDFs.
    """
    async def _download_one(session: httpx.AsyncClient, paper: Paper, output_dir: str):
        pdf_url = paper.pdf_url
        parsed_url = urlparse(pdf_url)
        if not (parsed_url and parsed_url.scheme and parsed_url.netloc):
            global_logger.error(f"Invalid URL: {pdf_url}")
            return None
        try:
            response = await session.get(pdf_url)
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
                    async for chunk in response.aiter_bytes():
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
    papers = await search_papers(
        request.query,
        request.batch_size,
        request.sort_by,
        request.categories,
        request.date_from,
        request.date_to,
        being_called_from_download=True
    )
    async with httpx.AsyncClient(timeout=20) as session:
        tasks = [ _download_one(session, paper, output_dir) for paper in papers ]
        results = [ r for r in await asyncio.gather(*tasks) if r ]
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