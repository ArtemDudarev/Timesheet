import random
from datetime import date

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.role import Role
from src.models.user import User
from src.schemas.employee import UserCreate, UserRegister

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    async def get_by_identity(self, login_identity: str) -> User | None:
        result = await self.session.execute(
            select(User).where(
                or_(User.email == login_identity, User.number == login_identity)
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

        user = User(
            email=data.email,
            number=data.number,
            hashed_password=self.hash_password(data.password),
            is_active=True,
            register_date=date.today(),
            roles=roles,
        )
        return await self._save(user, data.email, data.number)

    async def register_user(self, data: UserRegister) -> User:
        base_role_result = await self.session.execute(
            select(Role).where(Role.name == "Сотрудник")
        )
        base_role = base_role_result.scalar_one_or_none()
        if not base_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Базовая роль 'Сотрудник' не найдена. Выполните инициализацию БД.",
            )

        number = await self._generate_unique_number()
        user = User(
            email=data.email,
            number=number,
            hashed_password=self.hash_password(data.password),
            is_active=True,
            register_date=date.today(),
            roles=[base_role],
        )
        return await self._save(user, data.email, number)

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

    async def _save(self, user: User, email: str, number: str) -> User:
        try:
            self.session.add(user)
            await self.session.commit()
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
