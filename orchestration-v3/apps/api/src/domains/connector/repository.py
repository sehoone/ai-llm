"""connector 도메인 영속 계층 (ADR-0022). connector CRUD (llmonl)."""

from __future__ import annotations

from sqlmodel import Session, select

from src.domains.connector.model import Connector


class ConnectorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, c: Connector) -> Connector:
        self.session.add(c)
        self.session.commit()
        self.session.refresh(c)
        return c

    def get(self, connector_id: str) -> Connector | None:
        return self.session.get(Connector, connector_id)

    def list_by_user(self, user_id: int, *, enabled_only: bool = False) -> list[Connector]:
        stmt = select(Connector).where(Connector.user_id == user_id)
        if enabled_only:
            stmt = stmt.where(Connector.enabled == True)  # noqa: E712
        return list(self.session.exec(stmt.order_by(Connector.created_at.desc())).all())

    def save(self, c: Connector) -> Connector:
        self.session.add(c)
        self.session.commit()
        self.session.refresh(c)
        return c

    def delete(self, c: Connector) -> None:
        self.session.delete(c)
        self.session.commit()
