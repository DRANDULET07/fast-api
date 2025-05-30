
from pydantic import BaseModel
from datetime import datetime

class NoteCreate(BaseModel):
    text: str

class NoteOut(BaseModel):
    id: int
    text: str
    created_at: datetime

    class Config:
        orm_mode = True
