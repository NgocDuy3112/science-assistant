from dataclasses import dataclass


@dataclass
class Book:
    pdf_path: str
    content: str