import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.channel import Channel, ChannelMember, ChannelType
from src.models.employee import Employee
from src.models.message import Message
from src.schemas.chat import ChannelRead, EmployeeShort, MessageCreate


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Каналы ────────────────────────────────────────────────────────────────

    async def get_channels(self, caller_id: uuid.UUID) -> list[ChannelRead]:
        result = await self.db.execute(
            select(ChannelMember)
            .options(selectinload(ChannelMember.channel).selectinload(Channel.members))
            .where(ChannelMember.employee_id == caller_id)
        )
        memberships = list(result.scalars().all())
        channels: list[ChannelRead] = []
        for member in memberships:
            channel = member.channel
            companion = None
            if channel.type == ChannelType.DM:
                other = next(
                    (m for m in channel.members if m.employee_id != caller_id), None
                )
                if other:
                    employee = await self.db.get(Employee, other.employee_id)
                    if employee:
                        companion = EmployeeShort.model_validate(employee)
            channels.append(ChannelRead(
                id=channel.id,
                type=channel.type,
                name=channel.name,
                project_id=channel.project_id,
                pinned=member.pinned,
                muted=member.muted,
                companion=companion,
            ))
        # Закреплённые сверху, затем по имени
        channels.sort(key=lambda c: (not c.pinned, c.name or ""))
        return channels

    async def get_membership(
        self, channel_id: uuid.UUID, caller_id: uuid.UUID
    ) -> ChannelMember:
        member = await self.db.get(ChannelMember, (channel_id, caller_id))
        # Чужой канал неотличим от несуществующего
        if member is None:
            raise HTTPException(status_code=404, detail="Канал не найден")
        return member

    async def get_or_create_dm(
        self, caller_id: uuid.UUID, other_id: uuid.UUID
    ) -> Channel:
        if caller_id == other_id:
            raise HTTPException(status_code=400, detail="Нельзя открыть диалог с самим собой")
        other = await self.db.get(Employee, other_id)
        if other is None:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        # Ищем существующий DM с обоими участниками
        caller_dms = await self.db.execute(
            select(ChannelMember.channel_id)
            .join(Channel, Channel.id == ChannelMember.channel_id)
            .where(ChannelMember.employee_id == caller_id, Channel.type == ChannelType.DM)
        )
        caller_channel_ids = set(caller_dms.scalars().all())
        if caller_channel_ids:
            other_dms = await self.db.execute(
                select(ChannelMember.channel_id).where(
                    ChannelMember.employee_id == other_id,
                    ChannelMember.channel_id.in_(caller_channel_ids),
                )
            )
            existing_id = other_dms.scalars().first()
            if existing_id:
                return await self.db.get(Channel, existing_id)

        channel = Channel(
            type=ChannelType.DM,
            members=[
                ChannelMember(employee_id=caller_id),
                ChannelMember(employee_id=other_id),
            ],
        )
        self.db.add(channel)
        await self.db.flush()
        await self.db.refresh(channel, attribute_names=["members"])
        return channel

    async def toggle_pin(self, channel_id: uuid.UUID, caller_id: uuid.UUID) -> ChannelMember:
        member = await self.get_membership(channel_id, caller_id)
        member.pinned = not member.pinned
        await self.db.flush()
        return member

    async def toggle_mute(self, channel_id: uuid.UUID, caller_id: uuid.UUID) -> ChannelMember:
        member = await self.get_membership(channel_id, caller_id)
        member.muted = not member.muted
        await self.db.flush()
        return member

    # ── Сообщения ─────────────────────────────────────────────────────────────

    async def get_messages(
        self,
        channel_id: uuid.UUID,
        caller_id: uuid.UUID,
        before: datetime | None = None,
        limit: int = 50,
    ) -> list[Message]:
        await self.get_membership(channel_id, caller_id)
        q = select(Message).where(Message.channel_id == channel_id)
        if before is not None:
            q = q.where(Message.created_at < before)
        q = q.order_by(Message.created_at.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create_message(
        self, channel_id: uuid.UUID, caller_id: uuid.UUID, data: MessageCreate
    ) -> Message:
        await self.get_membership(channel_id, caller_id)
        if data.reply_to_id is not None:
            replied = await self.db.get(Message, data.reply_to_id)
            if replied is None or replied.channel_id != channel_id:
                raise HTTPException(status_code=404, detail="Сообщение для ответа не найдено")
        message = Message(
            channel_id=channel_id,
            author_id=caller_id,
            text=data.text,
            reply_to_id=data.reply_to_id,
            related_approval_type=data.related_approval_type,
            related_approval_id=data.related_approval_id,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def _get_own_message(self, message_id: uuid.UUID, caller_id: uuid.UUID) -> Message:
        message = await self.db.get(Message, message_id)
        if message is None:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")
        if message.author_id != caller_id:
            raise HTTPException(status_code=403, detail="Можно изменять только свои сообщения")
        return message

    async def update_message(
        self, message_id: uuid.UUID, caller_id: uuid.UUID, text: str
    ) -> Message:
        message = await self._get_own_message(message_id, caller_id)
        message.text = text
        message.edited = True
        message.updated_at = datetime.utcnow()
        await self.db.flush()
        return message

    async def delete_message(self, message_id: uuid.UUID, caller_id: uuid.UUID) -> Message:
        message = await self._get_own_message(message_id, caller_id)
        await self.db.delete(message)
        await self.db.flush()
        return message

    async def get_members(
        self, channel_id: uuid.UUID, caller_id: uuid.UUID
    ) -> list[Employee]:
        """Участники канала с ФИО — только для участника (фронту нужны имена авторов)."""
        await self.get_membership(channel_id, caller_id)
        result = await self.db.execute(
            select(Employee)
            .join(ChannelMember, ChannelMember.employee_id == Employee.id)
            .where(ChannelMember.channel_id == channel_id)
            .order_by(Employee.last_name, Employee.first_name)
        )
        return list(result.scalars().all())

    async def get_member_ids(self, channel_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(ChannelMember.employee_id).where(ChannelMember.channel_id == channel_id)
        )
        return list(result.scalars().all())
