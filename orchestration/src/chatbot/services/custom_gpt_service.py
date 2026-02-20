from typing import List, Optional
from uuid import uuid4
from sqlmodel import select, Session

from src.chatbot.models.custom_gpt_model import CustomGPT
from src.chatbot.schemas.custom_gpt_schema import CustomGPTCreate, CustomGPTUpdate
from src.common.services.database import database_service

class CustomGPTService:
    async def create_gpt(self, gpt_create: CustomGPTCreate, user_id: int) -> CustomGPT:
        rag_key = gpt_create.rag_key or f"gpt_{uuid4().hex}"
        gpt = CustomGPT(
            user_id=user_id,
            name=gpt_create.name,
            description=gpt_create.description,
            instructions=gpt_create.instructions,
            rag_key=rag_key,
            is_public=gpt_create.is_public,
            model=gpt_create.model
        )
        
        with Session(database_service.engine) as session:
            session.add(gpt)
            session.commit()
            session.refresh(gpt)
            return gpt

    async def get_gpt(self, gpt_id: str) -> Optional[CustomGPT]:
        with Session(database_service.engine) as session:
            statement = select(CustomGPT).where(CustomGPT.id == gpt_id)
            result = session.exec(statement)
            return result.first()

    async def list_gpts(self, user_id: int) -> List[CustomGPT]:
        with Session(database_service.engine) as session:
            statement = select(CustomGPT).where(CustomGPT.user_id == user_id)
            result = session.exec(statement)
            return result.all()

    async def update_gpt(self, gpt_id: str, update_data: CustomGPTUpdate, user_id: int) -> Optional[CustomGPT]:
        with Session(database_service.engine) as session:
            statement = select(CustomGPT).where(CustomGPT.id == gpt_id, CustomGPT.user_id == user_id)
            result = session.exec(statement)
            gpt = result.first()
            if not gpt:
                return None
            
            hero_data = update_data.model_dump(exclude_unset=True)
            for key, value in hero_data.items():
                setattr(gpt, key, value)
            
            session.add(gpt)
            session.commit()
            session.refresh(gpt)
            return gpt

    async def delete_gpt(self, gpt_id: str, user_id: int) -> bool:
        with Session(database_service.engine) as session:
            statement = select(CustomGPT).where(CustomGPT.id == gpt_id, CustomGPT.user_id == user_id)
            result = session.exec(statement)
            gpt = result.first()
            if not gpt:
                return False
            
            session.delete(gpt)
            session.commit()
            return True

custom_gpt_service = CustomGPTService()
