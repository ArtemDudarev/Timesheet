import random
import secrets
import string
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import delete, func, select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.permission import Permission
from src.models.refresh_token import RefreshToken
from src.models.role import Role
from src.models.role_permission import role_permission as role_permission_table
from src.models.user import User
from src.models.user_role import user_role as user_role_table
from src.schemas.employee import UserCreate

REFRESH_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Спецсимволы из набора, допустимого _validate_password в schemas/employee.py
_TEMP_PASSWORD_SPECIALS = "!@#$%^&*()-_=+"


def _generate_temp_password() -> str:
    """Случайный пароль без предсказуемого префикса — удовлетворяет _validate_password."""
    chars = [
        *(secrets.choice(string.ascii_uppercase) for _ in range(2)),
        *(secrets.choice(string.ascii_lowercase) for _ in range(4)),
        *(secrets.choice(string.digits) for _ in range(3)),
        secrets.choice(_TEMP_PASSWORD_SPECIALS),
    ]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def dummy_verify(self) -> None:
        pwd_context.dummy_verify()

    async def get_by_identity(self, login_identity: str) -> User | None:
        # Email вводится вручную и нечувствителен к регистру; номер сотрудника — только цифры,
        # регистр для него роли не играет
        result = await self.session.execute(
            select(User).where(
                or_(
                    func.lower(User.email) == login_identity.lower(),
                    User.number == login_identity,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_user(self, data: UserCreate) -> User:
        roles_result = await self.session.execute(
            select(Role).where(Role.id.in_(data.role_ids))
        )
        roles = list(roles_result.scalars().all())
        if len(roles) != len(set(data.role_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Одна или несколько указанных ролей не найдены",
            )

        number = await self._generate_unique_number()
        user = User(
            email=data.email,
            number=number,
            hashed_password=self.hash_password(data.password),
            is_active=True,
            register_date=date.today(),
            roles=roles,
        )
        return await self._save(user, data.email, number)

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        await self.session.execute(
            delete(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.expires_at < datetime.now(timezone.utc),
            )
        )
        token = secrets.token_urlsafe(32)
        self.session.add(RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            created_at=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
        ))
        await self.session.commit()
        return token

    async def rotate_refresh_token(
        self,
        token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str]:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        rt = result.scalar_one_or_none()
        if rt is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh token")
        # SQLite отдаёт naive datetime, Postgres — aware; нормализуем к UTC
        expires_at = rt.expires_at if rt.expires_at.tzinfo else rt.expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            await self.session.delete(rt)
            await self.session.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token истёк")

        user = await self.session.get(User, rt.user_id)
        if user is None:
            await self.session.delete(rt)
            await self.session.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
        if not user.is_active:
            await self.session.delete(rt)
            await self.session.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Учётная запись деактивирована")

        # Сохраняем метаданные от предыдущей сессии если новые не переданы
        prev_ip = rt.ip_address
        prev_ua = rt.user_agent
        await self.session.delete(rt)

        new_token = secrets.token_urlsafe(32)
        self.session.add(RefreshToken(
            user_id=user.id,
            token=new_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            created_at=datetime.now(timezone.utc),
            ip_address=ip_address or prev_ip,
            user_agent=user_agent or prev_ua,
        ))
        await self.session.commit()
        await self.session.refresh(user, attribute_names=["roles"])
        return user, new_token

    async def get_sessions(
        self,
        user_id: uuid.UUID,
        current_token: str | None,
    ) -> list[RefreshToken]:
        result = await self.session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .order_by(RefreshToken.created_at.desc())
        )
        sessions = list(result.scalars().all())
        # Помечаем текущую сессию через cookie-значение
        for s in sessions:
            s._is_current = (s.token == current_token) if current_token else False
        return sessions

    async def revoke_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        rt = await self.session.get(RefreshToken, session_id)
        if rt is None or rt.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
        await self.session.delete(rt)
        await self.session.commit()

    async def revoke_all_sessions(
        self,
        user_id: uuid.UUID,
        keep_token: str | None,
    ) -> None:
        q = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        if keep_token:
            q = q.where(RefreshToken.token != keep_token)
        await self.session.execute(q)
        await self.session.commit()

    async def get_permission_codes(self, user_id: uuid.UUID) -> list[str]:
        result = await self.session.execute(
            select(Permission.code)
            .join(role_permission_table, role_permission_table.c.permission_id == Permission.id)
            .join(user_role_table, user_role_table.c.role_id == role_permission_table.c.role_id)
            .where(user_role_table.c.user_id == user_id)
            .distinct()
            .order_by(Permission.code)
        )
        return list(result.scalars().all())

    async def revoke_refresh_token(self, token: str) -> None:
        await self.session.execute(
            delete(RefreshToken).where(RefreshToken.token == token)
        )
        await self.session.commit()

    async def _generate_unique_number(self) -> str:
        for _ in range(10):
            number = f"EMP-{random.randint(100000, 999999)}"
            result = await self.session.execute(
                select(User).where(User.number == number)
            )
            if result.scalar_one_or_none() is None:
                return number
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сгенерировать уникальный номер сотрудника",
        )

    async def change_password(self, user_id: uuid.UUID, current_password: str, new_password: str) -> None:
        user = await self.session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
        if not self.verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Текущий пароль неверен")
        # PasswordChange.passwords_differ уже отсеял current==new; здесь — против возврата
        # к паролю, который был ДО этого (например, до сброса временным паролем)
        if user.previous_hashed_password and self.verify_password(new_password, user.previous_hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Новый пароль не должен совпадать с предыдущим паролем",
            )
        user.previous_hashed_password = user.hashed_password
        user.hashed_password = self.hash_password(new_password)
        user.must_change_password = False
        await self.session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        await self.session.commit()

    async def reset_password(self, user_id: uuid.UUID) -> str:
        user = await self.session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
        temp_password = _generate_temp_password()
        # Сохраняем хеш пароля, который заменяем, — иначе после форс-смены нечего
        # будет сверить с "паролем до сброса"
        user.previous_hashed_password = user.hashed_password
        user.hashed_password = self.hash_password(temp_password)
        user.must_change_password = True
        await self.session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        await self.session.commit()
        return temp_password

    async def _save(self, user: User, email: str, number: str) -> User:
        try:
            self.session.add(user)
            await self.session.flush()
            await self.session.refresh(user, attribute_names=["roles"])
            return user
        except IntegrityError as e:
            await self.session.rollback()
            error_msg = str(e.orig).lower()
            if "email" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{email}' уже используется",
                )
            if "number" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Номер '{number}' уже используется",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данные пользователя конфликтуют с существующими записями",
            )
