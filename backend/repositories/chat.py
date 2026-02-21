"""Repository for ClinicalCase, ChatMessage, and UserCard entities."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import ChatMessage, ClinicalCase, UserCard


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_case(self, case_id: uuid.UUID) -> ClinicalCase | None:
        return await self._session.get(ClinicalCase, case_id)

    async def list_cases_for_user(self, user_id: uuid.UUID) -> list[ClinicalCase]:
        result = await self._session.execute(
            select(ClinicalCase)
            .where(ClinicalCase.user_id == user_id)
            .order_by(ClinicalCase.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_case(self, case: ClinicalCase) -> ClinicalCase:
        self._session.add(case)
        await self._session.flush()
        return case

    async def get_messages(self, case_id: uuid.UUID) -> list[ChatMessage]:
        result = await self._session.execute(
            select(ChatMessage)
            .where(ChatMessage.case_id == case_id)
            .order_by(ChatMessage.id)
        )
        return list(result.scalars().all())

    async def add_message(self, message: ChatMessage) -> ChatMessage:
        self._session.add(message)
        await self._session.flush()
        return message

    async def get_card(self, case_id: uuid.UUID) -> UserCard | None:
        result = await self._session.execute(
            select(UserCard).where(UserCard.case_id == case_id)
        )
        return result.scalar_one_or_none()

    async def upsert_card(self, card: UserCard) -> UserCard:
        self._session.add(card)
        await self._session.flush()
        return card
