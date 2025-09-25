from dataclasses import dataclass


@dataclass
class Paper:
    id: str
    title: str
    authors: list[str]
    summary: str
    published: str
    pdf_url: str
    primary_category: str