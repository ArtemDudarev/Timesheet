import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.password_reset_request import PasswordResetRequest, ResetRequestStatus
from src.services.employee_service import UserService


class PasswordResetRequestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, identifier: str) -> tuple[PasswordResetRequest, bool]:
        """Создаёт заявку на сброс пароля. Возвращает (заявка, создана_ли_новая).

        Если по этому identifier уже висит PENDING-заявка — новую не создаём
        (защита очереди менеджера от дублей), но снаружи это неотличимо: ответ всегда 202.

        Дедуп идёт по резолвнутому user_id (email нечувствителен к регистру, как и логин, —
        "manager@demo.com" и "MaNAger@demo.com" не должны плодить две заявки на одного и того
        же человека); для identifier без совпадения дедуп — по строке без учёта регистра.
        """
        user = await UserService(self.session).get_by_identity(identifier)
        dedup_filter = (
            PasswordResetRequest.user_id == user.id
            if user is not None
            else func.lower(PasswordResetRequest.identifier) == identifier.lower()
        )
        result = await self.session.execute(
            select(PasswordResetRequest).where(
                dedup_filter,
                PasswordResetRequest.status == ResetRequestStatus.PENDING,
            )
        )
        existing = result.scalars().first()
        if existing is not None:
            return existing, False

        request = PasswordResetRequest(
            identifier=identifier,
            user_id=user.id if user else None,
            status=ResetRequestStatus.PENDING,
            requested_at=datetime.utcnow(),
        )
        self.session.add(request)
        await self.session.flush()
        return request, True

    async def get_all(
        self,
        status_filter: ResetRequestStatus | None = ResetRequestStatus.PENDING,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PasswordResetRequest]:
        q = select(PasswordResetRequest).order_by(PasswordResetRequest.requested_at)
        if status_filter is not None:
            q = q.where(PasswordResetRequest.status == status_filter)
        q = q.offset(skip).limit(limit)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, request_id: uuid.UUID) -> PasswordResetRequest | None:
        return await self.session.get(PasswordResetRequest, request_id)

    async def resolve(
        self, request_id: uuid.UUID, resolved_by: uuid.UUID
    ) -> str:
        """Сбрасывает пароль по заявке и помечает её обработанной. Возвращает временный пароль."""
        request = await self.get_by_id(request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
        if request.status != ResetRequestStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Заявка уже обработана")
        if request.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь по заявке не найден — заявку можно только отменить",
            )

        request.status = ResetRequestStatus.RESOLVED
        request.resolved_by = resolved_by
        request.resolved_at = datetime.utcnow()
        # reset_password коммитит сессию — изменения заявки уйдут тем же коммитом
        temp_password = await UserService(self.session).reset_password(request.user_id)
        return temp_password

    async def cancel(
        self, request_id: uuid.UUID, resolved_by: uuid.UUID
    ) -> PasswordResetRequest:
        request = await self.get_by_id(request_id)
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
        if request.status != ResetRequestStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Заявка уже обработана")

        request.status = ResetRequestStatus.CANCELLED
        request.resolved_by = resolved_by
        request.resolved_at = datetime.utcnow()
        await self.session.commit()
        return request
