"""Chat endpoints — multi-turn conversation backed by the RAG pipeline."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_active_user
from backend.database.session import get_async_db
from backend.models.chat import ChatSession, Message
from backend.models.user import User
from backend.schemas.chat import ChatSessionOut, MessageCreate, MessageOut

router = APIRouter(prefix="/chat", tags=["chat"])


def _format_diagnoses(diagnoses: list) -> str:
    """Convert RAG diagnosis list into a readable chat message."""
    if not diagnoses:
        return "Не удалось определить диагноз по описанным симптомам. Пожалуйста, обратитесь к врачу."
    lines = ["**Возможные диагнозы:**\n"]
    for d in diagnoses:
        lines.append(f"{d.rank}. **{d.diagnosis}** ({d.icd10_code})")
        if d.explanation:
            lines.append(f"   {d.explanation}")
    return "\n".join(lines)


@router.post("/", response_model=MessageOut)
async def send_message(
    body: MessageCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> MessageOut:
    """Send a message. Creates a new session if session_id is None."""
    # ── Get or create chat session ─────────────────────────────────────────
    if body.session_id is None:
        chat_session = ChatSession(
            user_id=current_user.id,
            title=body.content[:40],
        )
        session.add(chat_session)
        await session.flush()
    else:
        result = await session.execute(
            select(ChatSession).where(
                ChatSession.id == body.session_id,
                ChatSession.user_id == current_user.id,
            )
        )
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # ── Save user message ──────────────────────────────────────────────────
    user_msg = Message(session_id=chat_session.id, sender="user", content=body.content)
    session.add(user_msg)
    await session.flush()

    # ── Call RAG pipeline ──────────────────────────────────────────────────
    rag_service = request.app.state.service
    diagnoses = await rag_service.diagnose(body.content)
    bot_text = _format_diagnoses(diagnoses)

    # ── Save bot message ───────────────────────────────────────────────────
    bot_msg = Message(session_id=chat_session.id, sender="bot", content=bot_text)
    session.add(bot_msg)
    await session.commit()
    await session.refresh(bot_msg)

    return bot_msg


@router.get("/", response_model=list[ChatSessionOut])
async def list_sessions(
    session: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ChatSessionOut]:
    result = await session.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{session_id}", response_model=list[MessageOut])
async def get_messages(
    session_id: int,
    session: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> list[MessageOut]:
    result = await session.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    msgs = await session.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.timestamp.asc())
    )
    return msgs.scalars().all()
