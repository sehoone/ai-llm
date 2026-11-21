"""connector 도메인 서비스 (ADR-0022). 사내 MCP 서버 등록 CRUD + 도구 미리보기.

도메인 책임(ADR-0005): 등록·인가·영속. 도구 로드·위험도는 engine/agent.mcp에 위임한다.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session

from src.domains.connector.model import Connector
from src.domains.connector.repository import ConnectorRepository
from src.domains.connector.schema import ConnectorCreateRequest, ConnectorUpdateRequest
from src.domains.user.model import User, UserRole
from src.engine.agent.mcp import McpServer, load_mcp_specs


class ConnectorService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = ConnectorRepository(session)

    def create(self, user: User, req: ConnectorCreateRequest) -> Connector:
        c = Connector(
            user_id=user.id,
            name=req.name,
            description=req.description,
            mcp_url=req.mcp_url,
            credential_ref=req.credential_ref,
            enabled=req.enabled,
        )
        return self.repo.create(c)

    def list_connectors(self, user: User) -> list[Connector]:
        return self.repo.list_by_user(user.id)

    def get_owned(self, connector_id: str, user: User) -> Connector:
        c = self.repo.get(connector_id)
        if c is None:
            raise HTTPException(status_code=404, detail="Connector not found")
        if c.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(status_code=403, detail="Not your connector")
        return c

    def update(self, connector_id: str, user: User, req: ConnectorUpdateRequest) -> Connector:
        c = self.get_owned(connector_id, user)
        for key, value in req.model_dump(exclude_unset=True).items():
            setattr(c, key, value)
        return self.repo.save(c)

    def delete(self, connector_id: str, user: User) -> None:
        c = self.get_owned(connector_id, user)
        self.repo.delete(c)

    def preview_tools(self, connector_id: str, user: User) -> list[dict]:
        """커넥터가 노출하는 MCP 도구 목록(이름·설명·위험 티어). MCP 미설치/실패 시 빈 목록."""
        c = self.get_owned(connector_id, user)
        specs = load_mcp_specs([McpServer(url=c.mcp_url, token=c.credential_ref, name=c.name)])
        return [{"name": s.name, "description": s.description, "risk": str(s.risk)} for s in specs]
