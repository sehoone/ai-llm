"""RAG group and key management service."""

from typing import List, Optional

from sqlmodel import Session, select, text

from src.common.logging import logger
from src.common.services.database import database_service
from src.rag.models.rag_group_config_model import RagGroupConfig
from src.rag.models.rag_key_config_model import RagKeyConfig
from src.rag.schemas.rag_group_schema import (
    RagGroupCreate,
    RagGroupResponse,
    RagGroupUpdate,
    RagKeyCreate,
    RagKeyResponse,
    RagKeyUpdate,
)


def _group_to_response(group: RagGroupConfig, key_count: int = 0, doc_count: int = 0) -> RagGroupResponse:
    return RagGroupResponse(
        id=group.id,
        user_id=group.user_id,
        name=group.name,
        description=group.description,
        color=group.color,
        key_count=key_count,
        doc_count=doc_count,
        created_at=group.created_at,
    )


def _key_to_response(key: RagKeyConfig, doc_count: int = 0) -> RagKeyResponse:
    return RagKeyResponse(
        id=key.id,
        user_id=key.user_id,
        rag_key=key.rag_key,
        rag_group=key.rag_group,
        description=key.description,
        rag_type=key.rag_type,
        doc_count=doc_count,
        created_at=key.created_at,
    )


class RagGroupService:

    # ── Groups ────────────────────────────────────────────────────────────────

    async def list_groups(self, user_id: int) -> List[RagGroupResponse]:
        with Session(database_service.engine) as session:
            groups = session.exec(
                select(RagGroupConfig).where(RagGroupConfig.user_id == user_id)
                .order_by(RagGroupConfig.created_at.asc())
            ).all()

            # 그룹별 키 수 + 문서 수 집계
            stats_rows = session.exec(
                text("""
                    SELECT kc.rag_group,
                           COUNT(DISTINCT kc.rag_key) AS key_count,
                           COUNT(d.id) AS doc_count
                    FROM rag_key_config kc
                    LEFT JOIN document d ON d.rag_key = kc.rag_key
                    WHERE kc.user_id = :user_id
                    GROUP BY kc.rag_group
                """),
                params={"user_id": user_id},
            ).all()
            stats = {row[0]: (int(row[1]), int(row[2])) for row in stats_rows}

            return [_group_to_response(g, *stats.get(g.name, (0, 0))) for g in groups]

    async def get_group(self, group_id: str, user_id: int) -> Optional[RagGroupConfig]:
        with Session(database_service.engine) as session:
            return session.exec(
                select(RagGroupConfig).where(RagGroupConfig.id == group_id, RagGroupConfig.user_id == user_id)
            ).first()

    async def create_group(self, data: RagGroupCreate, user_id: int) -> RagGroupResponse:
        group = RagGroupConfig(user_id=user_id, name=data.name, description=data.description, color=data.color)
        with Session(database_service.engine) as session:
            session.add(group)
            session.commit()
            session.refresh(group)
            return _group_to_response(group)

    async def update_group(self, group_id: str, data: RagGroupUpdate, user_id: int) -> Optional[RagGroupResponse]:
        with Session(database_service.engine) as session:
            group = session.exec(
                select(RagGroupConfig).where(RagGroupConfig.id == group_id, RagGroupConfig.user_id == user_id)
            ).first()
            if not group:
                return None

            old_name = group.name
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(group, key, value)
            session.add(group)

            # 이름 변경 시 연관 데이터 일괄 업데이트
            if data.name and data.name != old_name:
                session.exec(
                    text("UPDATE rag_key_config SET rag_group = :new WHERE rag_group = :old AND user_id = :uid"),
                    params={"new": data.name, "old": old_name, "uid": user_id},
                )
                session.exec(
                    text("UPDATE document SET rag_group = :new WHERE rag_group = :old AND user_id = :uid"),
                    params={"new": data.name, "old": old_name, "uid": user_id},
                )
                session.exec(
                    text("UPDATE rag_embedding SET rag_group = :new WHERE rag_group = :old"),
                    params={"new": data.name, "old": old_name},
                )
                logger.info("rag_group_renamed", old=old_name, new=data.name, user_id=user_id)

            session.commit()
            session.refresh(group)
            return _group_to_response(group)

    async def delete_group(self, group_id: str, user_id: int) -> bool:
        with Session(database_service.engine) as session:
            group = session.exec(
                select(RagGroupConfig).where(RagGroupConfig.id == group_id, RagGroupConfig.user_id == user_id)
            ).first()
            if not group:
                return False
            # 하위 키 configs 삭제 (문서는 보존 — rag_group 값은 그대로 남음)
            session.exec(
                text("DELETE FROM rag_key_config WHERE rag_group = :g AND user_id = :uid"),
                params={"g": group.name, "uid": user_id},
            )
            session.delete(group)
            session.commit()
            return True

    # ── Keys ──────────────────────────────────────────────────────────────────

    async def list_keys(self, user_id: int, rag_group: Optional[str] = None) -> List[RagKeyResponse]:
        with Session(database_service.engine) as session:
            stmt = select(RagKeyConfig).where(RagKeyConfig.user_id == user_id)
            if rag_group:
                stmt = stmt.where(RagKeyConfig.rag_group == rag_group)
            keys = session.exec(stmt.order_by(RagKeyConfig.created_at.asc())).all()

            doc_rows = session.exec(
                text("""
                    SELECT rag_key, COUNT(*) AS doc_count
                    FROM document
                    WHERE user_id = :uid
                    GROUP BY rag_key
                """),
                params={"uid": user_id},
            ).all()
            doc_counts = {row[0]: int(row[1]) for row in doc_rows}

            return [_key_to_response(k, doc_counts.get(k.rag_key, 0)) for k in keys]

    async def get_key(self, key_id: str, user_id: int) -> Optional[RagKeyConfig]:
        with Session(database_service.engine) as session:
            return session.exec(
                select(RagKeyConfig).where(RagKeyConfig.id == key_id, RagKeyConfig.user_id == user_id)
            ).first()

    async def create_key(self, data: RagKeyCreate, user_id: int) -> RagKeyResponse:
        key = RagKeyConfig(
            user_id=user_id,
            rag_key=data.rag_key,
            rag_group=data.rag_group,
            description=data.description,
            rag_type=data.rag_type,
        )
        with Session(database_service.engine) as session:
            session.add(key)
            session.commit()
            session.refresh(key)
            return _key_to_response(key)

    async def update_key(self, key_id: str, data: RagKeyUpdate, user_id: int) -> Optional[RagKeyResponse]:
        with Session(database_service.engine) as session:
            key = session.exec(
                select(RagKeyConfig).where(RagKeyConfig.id == key_id, RagKeyConfig.user_id == user_id)
            ).first()
            if not key:
                return None
            for k, v in data.model_dump(exclude_unset=True).items():
                setattr(key, k, v)
            # rag_group 변경 시 문서/임베딩도 업데이트
            if data.rag_group and data.rag_group != key.rag_group:
                session.exec(
                    text("UPDATE document SET rag_group = :new WHERE rag_key = :rk AND user_id = :uid"),
                    params={"new": data.rag_group, "rk": key.rag_key, "uid": user_id},
                )
                session.exec(
                    text("UPDATE rag_embedding SET rag_group = :new WHERE rag_key = :rk"),
                    params={"new": data.rag_group, "rk": key.rag_key},
                )
            session.add(key)
            session.commit()
            session.refresh(key)
            with Session(database_service.engine) as s2:
                cnt = s2.exec(
                    text("SELECT COUNT(*) FROM document WHERE rag_key = :rk AND user_id = :uid"),
                    params={"rk": key.rag_key, "uid": user_id},
                ).first()
            return _key_to_response(key, int(cnt[0]) if cnt else 0)

    async def delete_key(self, key_id: str, user_id: int, delete_docs: bool = False) -> bool:
        with Session(database_service.engine) as session:
            key = session.exec(
                select(RagKeyConfig).where(RagKeyConfig.id == key_id, RagKeyConfig.user_id == user_id)
            ).first()
            if not key:
                return False
            if delete_docs:
                doc_ids = session.exec(
                    text("SELECT id FROM document WHERE rag_key = :rk AND user_id = :uid"),
                    params={"rk": key.rag_key, "uid": user_id},
                ).all()
                ids = [row[0] for row in doc_ids]
                if ids:
                    session.exec(
                        text(f"DELETE FROM rag_embedding WHERE doc_id = ANY(ARRAY{ids}::int[])")
                    )
                    session.exec(
                        text("DELETE FROM document WHERE rag_key = :rk AND user_id = :uid"),
                        params={"rk": key.rag_key, "uid": user_id},
                    )
                logger.info("rag_key_deleted_with_docs", rag_key=key.rag_key, doc_count=len(ids))
            session.delete(key)
            session.commit()
            return True


rag_group_service = RagGroupService()
