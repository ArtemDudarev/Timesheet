import uuid
from datetime import date

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.kafka.events import publish_user_created
from src.kafka.producer import KafkaEventProducer
from src.models.role import Role
from src.models.user import User

ROLE_SOTRUDNIK_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ROLE_MANAGER_ID   = uuid.UUID("00000000-0000-0000-0000-000000000002")

SEED_ROLES = [
    {"id": ROLE_SOTRUDNIK_ID, "name": "Сотрудник", "description": "Базовая роль для всех сотрудников"},
    {"id": ROLE_MANAGER_ID,   "name": "Менеджер",  "description": "Роль с правами управления"},
]

DEMO_MANAGER_ID  = uuid.UUID("00000000-0000-0000-0000-000000000010")
DEMO_EMPLOYEE_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")

DEMO_USERS = [
    {
        "id": DEMO_MANAGER_ID,
        "email": "manager@demo.com",
        "password": "Manager1!",
        "number": "EMP-000001",
        "role_ids": [ROLE_MANAGER_ID, ROLE_SOTRUDNIK_ID],
    },
    {
        "id": DEMO_EMPLOYEE_ID,
        "email": "employee@demo.com",
        "password": "Employee1!",
        "number": "EMP-000002",
        "role_ids": [ROLE_SOTRUDNIK_ID],
    },
]

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_roles(session_maker: async_sessionmaker[AsyncSession]) -> None:
    async with session_maker() as session:
        for role_data in SEED_ROLES:
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            if result.scalar_one_or_none() is None:
                session.add(Role(
                    id=role_data["id"],
                    name=role_data["name"],
                    description=role_data["description"],
                ))
        await session.commit()


async def seed_demo_users(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for user_data in DEMO_USERS:
            result = await session.execute(
                select(User).where(User.id == user_data["id"])
            )
            if result.scalar_one_or_none() is not None:
                continue

            roles_result = await session.execute(
                select(Role).where(Role.id.in_(user_data["role_ids"]))
            )
            roles = list(roles_result.scalars().all())

            user = User(
                id=user_data["id"],
                email=user_data["email"],
                number=user_data["number"],
                hashed_password=_pwd_context.hash(user_data["password"]),
                is_active=True,
                must_change_password=False,
                register_date=date.today(),
                roles=roles,
            )
            session.add(user)
            await session.flush()
            await session.refresh(user, attribute_names=["roles"])
            await publish_user_created(producer, user)

        await session.commit()
