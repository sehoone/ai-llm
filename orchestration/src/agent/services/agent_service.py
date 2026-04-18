"""Agent management service."""

from datetime import UTC, datetime
from typing import List, Optional

from sqlmodel import Session, select, text

from src.agent.models.agent_model import Agent
from src.agent.models.agent_session_model import AgentSession
from src.agent.schemas.agent_schema import AgentCreate, AgentUpdate, RagGroupInfo, RagKeyInfo
from src.common.logging import logger
from src.common.services.database import database_service


class AgentService:
    """CRUD operations for Agents and AgentSessions."""

    # ── Agent CRUD ────────────────────────────────────────────────────────────

    async def create_agent(self, data: AgentCreate, user_id: int) -> Agent:
        agent = Agent(
            user_id=user_id,
            name=data.name,
            description=data.description,
            system_prompt=data.system_prompt,
            welcome_message=data.welcome_message,
            model=data.model,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
            rag_keys=data.rag_keys,
            rag_search_k=data.rag_search_k,
            rag_enabled=data.rag_enabled,
            tools_enabled=data.tools_enabled,
            is_published=data.is_published,
        )
        with Session(database_service.engine) as session:
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return agent

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        with Session(database_service.engine) as session:
            return session.exec(select(Agent).where(Agent.id == agent_id)).first()

    async def list_agents(self, user_id: int) -> List[Agent]:
        with Session(database_service.engine) as session:
            return list(session.exec(select(Agent).where(Agent.user_id == user_id, Agent.is_active == True)).all())

    async def update_agent(self, agent_id: str, data: AgentUpdate, user_id: int) -> Optional[Agent]:
        with Session(database_service.engine) as session:
            agent = session.exec(select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)).first()
            if not agent:
                return None
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(agent, key, value)
            agent.updated_at = datetime.now(UTC)
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return agent

    async def delete_agent(self, agent_id: str, user_id: int) -> bool:
        with Session(database_service.engine) as session:
            agent = session.exec(select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)).first()
            if not agent:
                return False
            session.delete(agent)
            session.commit()
            return True

    async def toggle_publish(self, agent_id: str, user_id: int) -> Optional[Agent]:
        with Session(database_service.engine) as session:
            agent = session.exec(select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)).first()
            if not agent:
                return None
            agent.is_published = not agent.is_published
            agent.updated_at = datetime.now(UTC)
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return agent

    # ── Session CRUD ──────────────────────────────────────────────────────────

    async def create_session(self, agent_id: str, user_id: int) -> AgentSession:
        session_obj = AgentSession(agent_id=agent_id, user_id=user_id, name="")
        with Session(database_service.engine) as session:
            session.add(session_obj)
            session.commit()
            session.refresh(session_obj)
            return session_obj

    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        with Session(database_service.engine) as session:
            return session.exec(select(AgentSession).where(AgentSession.id == session_id)).first()

    async def list_sessions(self, agent_id: str, user_id: int) -> List[AgentSession]:
        with Session(database_service.engine) as session:
            return list(
                session.exec(
                    select(AgentSession)
                    .where(AgentSession.agent_id == agent_id, AgentSession.user_id == user_id)
                    .order_by(AgentSession.created_at.desc())
                ).all()
            )

    async def rename_session(self, session_id: str, name: str) -> Optional[AgentSession]:
        with Session(database_service.engine) as session:
            session_obj = session.exec(select(AgentSession).where(AgentSession.id == session_id)).first()
            if not session_obj:
                return None
            session_obj.name = name
            session.add(session_obj)
            session.commit()
            session.refresh(session_obj)
            return session_obj

    async def delete_session(self, session_id: str) -> bool:
        with Session(database_service.engine) as session:
            session_obj = session.exec(select(AgentSession).where(AgentSession.id == session_id)).first()
            if not session_obj:
                return False
            session.delete(session_obj)
            session.commit()
            return True

    # ── RAG key listing ───────────────────────────────────────────────────────

    async def list_rag_keys(self, user_id: int) -> List[RagKeyInfo]:
        """Return distinct rag_keys from documents the user owns."""
        with Session(database_service.engine) as session:
            rows = session.exec(
                text("""
                    SELECT rag_key, rag_group, COUNT(*) as doc_count, MAX(created_at) as latest_upload
                    FROM document
                    WHERE user_id = :user_id OR rag_type = 'chatbot_shared'
                    GROUP BY rag_key, rag_group
                    ORDER BY latest_upload DESC
                """),
                params={"user_id": user_id},
            ).all()
            return [
                RagKeyInfo(
                    rag_key=row[0],
                    rag_group=row[1],
                    doc_count=int(row[2]),
                    latest_upload=row[3],
                )
                for row in rows
            ]


    async def list_rag_groups(self, user_id: int) -> List[RagGroupInfo]:
        """Return distinct rag_groups with aggregated stats."""
        with Session(database_service.engine) as session:
            rows = session.exec(
                text("""
                    SELECT rag_group,
                           COUNT(DISTINCT rag_key) as key_count,
                           COUNT(*) as doc_count,
                           MAX(created_at) as latest_upload
                    FROM document
                    WHERE user_id = :user_id OR rag_type = 'chatbot_shared'
                    GROUP BY rag_group
                    ORDER BY latest_upload DESC
                """),
                params={"user_id": user_id},
            ).all()
            return [
                RagGroupInfo(
                    rag_group=row[0],
                    key_count=int(row[1]),
                    doc_count=int(row[2]),
                    latest_upload=row[3],
                )
                for row in rows
            ]


agent_service = AgentService()
