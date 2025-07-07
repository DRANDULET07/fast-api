from pydantic import BaseModel, Field
from datetime import datetime

class NoteCreate(BaseModel):
    text: str = Field(
        ..., 
        title="Текст заметки", 
        description="Содержимое заметки, которую пользователь хочет создать.",
        example="Записать идею проекта"
    )

class NoteOut(BaseModel):
    id: int = Field(..., description="Уникальный идентификатор заметки", example=1)
    text: str = Field(..., description="Содержимое заметки", example="Записать идею проекта")
    created_at: datetime = Field(..., description="Дата и время создания", example="2025-07-07T12:00:00")

    class Config:
        orm_mode = True
