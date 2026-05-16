from typing import List, Optional

from pydantic import BaseModel


class Article(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    source: str
    published_at: str
    author: Optional[str] = None


class NewsResponse(BaseModel):
    total_results: int
    articles: List[Article]
    country: Optional[str] = None
    category: Optional[str] = None
    query: Optional[str] = None
    is_demo: bool = False


class NewsSource(BaseModel):
    id: str
    name: str
    description: str
    url: str
    category: str
    language: str
    country: str


class NewsSourcesResponse(BaseModel):
    sources: List[NewsSource]
    total_count: int
