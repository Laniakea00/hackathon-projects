"""Repository for Protocol and ProtocolChunk entities."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.protocol import Protocol, ProtocolChunk


class ProtocolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, protocol_id: str) -> Protocol | None:
        return await self._session.get(Protocol, protocol_id)

    async def list_all(self) -> list[Protocol]:
        result = await self._session.execute(select(Protocol))
        return list(result.scalars().all())

    async def get_chunks_for_protocol(self, protocol_id: str) -> list[ProtocolChunk]:
        result = await self._session.execute(
            select(ProtocolChunk)
            .where(ProtocolChunk.protocol_id == protocol_id)
            .order_by(ProtocolChunk.chunk_index)
        )
        return list(result.scalars().all())
