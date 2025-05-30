
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import Note
from .schemas import NoteCreate

async def create_note(session: AsyncSession, note_data: NoteCreate) -> Note:
    note = Note(text=note_data.text)
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note

async def get_all_notes(session: AsyncSession):
    result = await session.execute(select(Note))
    return result.scalars().all()
