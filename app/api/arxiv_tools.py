from fastapi import APIRouter, Depends

from app.core.arxiv_tools import *
from app.schemas.arxiv_tools import *


arxiv_tools_router = APIRouter(prefix="/arxiv", tags=["ARXIV DOCUMENTS"])



@arxiv_tools_router.get("/search")
async def search_papers_api(request: SearchPapersRequest):
    return await search_papers(request)



@arxiv_tools_router.post("/download")
async def download_papers_api(request: DownloadPapersRequest):
    return await download_papers(request)