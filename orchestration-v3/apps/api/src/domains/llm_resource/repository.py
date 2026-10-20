from sqlmodel import Session, select

from src.domains.llm_resource.model import LlmResource


class LlmResourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, resource_id: int) -> LlmResource | None:
        return self.session.get(LlmResource, resource_id)

    def list_all(self) -> list[LlmResource]:
        return list(
            self.session.exec(
                select(LlmResource).order_by(LlmResource.priority.desc())
            ).all()
        )

    def list_by_type(self, resource_type: str) -> list[LlmResource]:
        return list(
            self.session.exec(
                select(LlmResource)
                .where(LlmResource.resource_type == resource_type)
                .order_by(LlmResource.priority.desc())
            ).all()
        )

    def list_active_chat_models(self) -> list[LlmResource]:
        return list(
            self.session.exec(
                select(LlmResource)
                .where(LlmResource.resource_type == "chat", LlmResource.is_active == True)  # noqa: E712
                .order_by(LlmResource.priority.desc())
            ).all()
        )

    def save(self, resource: LlmResource) -> LlmResource:
        self.session.add(resource)
        self.session.commit()
        self.session.refresh(resource)
        return resource

    def delete(self, resource: LlmResource) -> None:
        self.session.delete(resource)
        self.session.commit()
