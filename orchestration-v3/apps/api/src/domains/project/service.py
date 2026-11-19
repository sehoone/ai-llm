"""project 도메인 서비스 (ADR-0021).

도메인 책임(ADR-0005): HTTP 경계·인가·관계형 영속. 대화는 chat 스택(ChatService), 지식은
rag(RagService)에 위임 — 프로젝트는 이 둘을 묶는 컨테이너일 뿐 새 AI 연산을 두지 않는다.

- 대화: `chat_session.project_id`로 소속. 생성/삭제는 ChatService에 위임(첨부 정리 포함).
- 지식: 프로젝트 전용 `rag_group`/`rag_key`(1:1)로 rag 문서를 스코핑. 업로드·목록·삭제는 RagService.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import Session

from src.domains.chat.model import ChatSession
from src.domains.chat.service import ChatService
from src.domains.project.model import Project
from src.domains.project.repository import ProjectRepository
from src.domains.project.schema import ProjectCreateRequest, ProjectUpdateRequest
from src.domains.rag.model import Document
from src.domains.rag.schema import DocumentUploadRequest
from src.domains.rag.service import RagService
from src.domains.user.model import User, UserRole

# 프로젝트 지식 문서는 소유자 전용(ADR-0020 §3) — rag user_isolated 타입으로 격리.
_PROJECT_RAG_TYPE = "user_isolated"


class ProjectService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = ProjectRepository(session)

    # ── CRUD ──
    def create(self, user: User, req: ProjectCreateRequest) -> Project:
        pid = str(uuid.uuid4())
        # 전용 지식베이스 좌표 프로비저닝(프로젝트당 1:1, 고유). rag 문서가 이 group/key로 묶인다.
        p = Project(
            id=pid,
            user_id=user.id,
            name=req.name,
            description=req.description,
            instructions=req.instructions or "",
            rag_key=f"project_{uuid.uuid4().hex}",
            rag_group=f"project_{pid}",
            icon=req.icon or "folder",
            color=req.color or "#6366f1",
        )
        return self.repo.create(p)

    def list_projects(self, user: User) -> list[Project]:
        return self.repo.list_by_user(user.id)

    def get_owned(self, project_id: str, user: User) -> Project:
        p = self.repo.get(project_id)
        if p is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if p.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(status_code=403, detail="Not your project")
        return p

    def update(self, project_id: str, user: User, req: ProjectUpdateRequest) -> Project:
        p = self.get_owned(project_id, user)
        for key, value in req.model_dump(exclude_unset=True).items():
            setattr(p, key, value)
        return self.repo.save(p)

    def delete(self, project_id: str, user: User) -> None:
        p = self.get_owned(project_id, user)
        # 소속 대화 연쇄 삭제(첨부·승인·메시지 정리는 ChatService가 수행).
        chat = ChatService(self.session)
        for s in self.repo.list_sessions(p.id):
            chat.delete_session(s.id, user)
        # 지식 문서 연쇄 삭제.
        rag = RagService(self.session)
        for doc in rag.list_documents(user, rag_group=p.rag_group, rag_key=p.rag_key):
            rag.delete_document(user, doc.id)
        self.repo.delete(p)

    # ── 소속 대화 ──
    def list_sessions(self, project_id: str, user: User) -> list[ChatSession]:
        self.get_owned(project_id, user)
        return self.repo.list_sessions(project_id)

    def create_session(self, project_id: str, user: User, title: str | None) -> ChatSession:
        self.get_owned(project_id, user)
        return ChatService(self.session).create_session(user, title, project_id=project_id)

    # ── 지식 (rag 재사용) ──
    def list_knowledge(self, project_id: str, user: User) -> list[Document]:
        p = self.get_owned(project_id, user)
        return RagService(self.session).list_documents(user, rag_group=p.rag_group, rag_key=p.rag_key)

    def add_knowledge(self, project_id: str, user: User, filename: str, content: str) -> Document:
        p = self.get_owned(project_id, user)
        req = DocumentUploadRequest(
            rag_key=p.rag_key,
            rag_group=p.rag_group,
            rag_type=_PROJECT_RAG_TYPE,
            filename=filename,
            content=content,
        )
        doc, _indexed = RagService(self.session).ingest_document(user, req)
        return doc

    def delete_knowledge(self, project_id: str, user: User, doc_id: int) -> None:
        self.get_owned(project_id, user)
        RagService(self.session).delete_document(user, doc_id)
