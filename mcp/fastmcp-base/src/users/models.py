from typing import List, Optional

from pydantic import BaseModel


class AuthorInfo(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None


class PostSummary(BaseModel):
    id: int
    title: str
    is_published: bool
    created_at: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: str
    post_count: Optional[int] = None


class UserDetailResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: str
    posts: List[PostSummary]


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    is_published: bool
    created_at: str
    updated_at: str
    author: AuthorInfo


class DatabaseStats(BaseModel):
    total_users: int
    active_users: int
    total_posts: int
    published_posts: int
    draft_posts: int
