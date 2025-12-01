from pydantic import BaseModel, Field
from typing import Literal

from app.configs import settings


class BaseArxivToolsRequest(BaseModel):
    query: str = Field(description="The query being used to search and/or download the papers")
    batch_size: int = Field(description="The numbers of papers need to be searched and/or downloaded for", default=5)
    sort_by: Literal["relevance", "lastUpdatedDate"] = Field(description="How the papers being sorted based on relevance, or the date the paper was last updated, formatted in `YYYY-MM-DD`", default="relevance")
    categories: str | list[str] = Field(description="The categories of the papers being searched and/or downloaded, formatted in `YYYY-MM-DD`", default=['cs', 'math'])
    date_from: str = Field(description="The first date of the filter")
    date_to: str = Field(description="The last date of the filter")



class SearchPapersRequest(BaseArxivToolsRequest):
    pass



class DownloadPapersRequest(BaseArxivToolsRequest):
    output_dir: str = Field(description="The path in the local machines that store the downloaded papers", default=settings.PAPERS_DIR)