from pydantic import BaseModel

class ChatTitleUpdate(BaseModel):
    session_id: str
    title: str
