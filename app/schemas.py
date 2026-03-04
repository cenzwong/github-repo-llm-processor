from pydantic import BaseModel, HttpUrl
from typing import List


class SummarizeRequest(BaseModel):
    github_url: HttpUrl


class SummarizeResponse(BaseModel):
    summary: str
    technologies: List[str]
    structure: str


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
