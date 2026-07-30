import uuid
from datetime import date

from passlib.context import CryptContext
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.kafka.events import publish_user_created
from src.kafka.producer import KafkaEventProducer
from src.models.permission import Permission
from src.models.role import Role
from src.models.role_permission import role_permission as role_permission_table
from src.models.user import User

# ── Роли ─────────────────────────────────────────────────────────────────────
ROLE_SOTRUDNIK_ID    = uuid.UUID("00000000-0000-0000-0000-000000000001")
ROLE_MANAGER_ID      = uuid.UUID("00000000-0000-0000-0000-000000000002")
ROLE_TEAMLEAD_ID     = uuid.UUID("00000000-0000-0000-0000-000000000003")
ROLE_HR_ID           = uuid.UUID("00000000-0000-0000-0000-000000000004")
ROLE_ADMIN_ID        = uuid.UUID("00000000-0000-0000-0000-000000000005")

SEED_ROLES = [
    {"id": ROLE_SOTRUDNIK_ID, "name": "Сотрудник",     "description": "Базовая роль для всех сотрудников"},
    {"id": ROLE_MANAGER_ID,   "name": "Менеджер",      "description": "PM / руководитель отдела"},
    {"id": ROLE_TEAMLEAD_ID,  "name": "Тимлид",        "description": "Руководитель команды"},
    {"id": ROLE_HR_ID,        "name": "HR",             "description": "Кадровая служба"},
    {"id": ROLE_ADMIN_ID,     "name": "Администратор", "description": "Системный администратор"},
]

# ── Permissions ───────────────────────────────────────────────────────────────
SEED_PERMISSIONS = [
    # Управление пользователями
    {"code": "user:register",            "name": "Регистрировать пользователей"},
    {"code": "user:reset_password",      "name": "Сбрасывать пароли других"},
    # Профиль сотрудника
    {"code": "employee:list",            "name": "Просматривать список сотрудников"},
    {"code": "employee:read_any",        "name": "Читать любой профиль"},
    {"code": "employee:read_team",       "name": "Читать профили своей команды"},
    {"code": "employee:edit_any",        "name": "Редактировать чужой профиль"},
    {"code": "employee:assign_grade",    "name": "Назначать грейд и отдел"},
    {"code": "employee:skills_edit_any", "name": "Редактировать навыки других"},
    {"code": "employee:set_lead",        "name": "Назначать lead сотруднику"},
    {"code": "employee:assign_roles",    "name": "Назначать роли сотруднику"},
    {"code": "employee:assign_status",   "name": "Назначать статус сотруднику"},
    # Проекты
    {"code": "project:read",             "name": "Просматривать проекты"},
    {"code": "project:manage",           "name": "Управлять проектами (CRUD)"},
    {"code": "project:assign",           "name": "Назначать сотрудников на проекты"},
    # Справочники
    {"code": "directory:manage",         "name": "Управлять справочниками (грейды, отделы, проектные роли)"},
    {"code": "system:manage",            "name": "Управлять системными данными (роли, статусы, permissions)"},
    {"code": "calendar:manage",          "name": "Управлять производственным календарём"},
    # Табель
    {"code": "timesheet:read_any",       "name": "Читать любой табель"},
    {"code": "timesheet:read_team",      "name": "Читать табель своей команды"},
    {"code": "timesheet:edit_any",       "name": "Редактировать чужие записи табеля"},
    {"code": "timesheet:close_period",   "name": "Закрывать периоды табеля"},
    {"code": "overtime:approve",         "name": "Согласовывать любые переработки"},
    {"code": "overtime:approve_team",    "name": "Согласовывать переработки своей команды"},
    {"code": "timesheet:approve_period",      "name": "Согласовывать любые периоды табеля"},
    {"code": "timesheet:approve_period_team", "name": "Согласовывать периоды табеля своей команды"},
    # Сводка
    {"code": "summary:read_any",         "name": "Читать сводку любого сотрудника"},
    {"code": "summary:read_team",        "name": "Читать сводку своей команды"},
    # Отчётность
    {"code": "report:read",              "name": "Просматривать отчёты и аналитику"},
    {"code": "report:manage",            "name": "Управлять плановыми показателями отчётности"},
    # Отсутствия
    {"code": "absence:read_any",         "name": "Просматривать любые заявки на отсутствие"},
    {"code": "absence:read_team",        "name": "Просматривать заявки своей команды"},
    {"code": "absence:approve",          "name": "Согласовывать любые отсутствия"},
    {"code": "absence:approve_team",     "name": "Согласовывать отсутствия своей команды"},
    # Документы
    {"code": "document:read_any",        "name": "Просматривать любые документы"},
    {"code": "document:manage_templates", "name": "Управлять шаблонами документов"},
]

# ── Маппинги роль → permissions ───────────────────────────────────────────────
SEED_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Сотрудник": [],  # доступ к своим данным проверяется в коде без permissions
    "Тимлид": [
        "employee:read_team",
        "project:read",
        "timesheet:read_team",
        "timesheet:approve_period_team",
        "overtime:approve_team",
        "summary:read_team",
        "absence:read_team",
        "absence:approve_team",
    ],
    "Менеджер": [
        "user:register",
        "user:reset_password",
        "employee:list",
        "employee:read_any",
        "employee:edit_any",
        "employee:assign_grade",
        "employee:skills_edit_any",
        "employee:set_lead",
        "employee:assign_roles",
        "employee:assign_status",
        "project:read",
        "project:manage",
        "project:assign",
        "directory:manage",
        "timesheet:read_any",
        "timesheet:edit_any",
        "timesheet:close_period",
        "timesheet:approve_period",
        "overtime:approve",
        "summary:read_any",
        "report:read",
        "absence:read_any",
        "absence:approve",
        "document:read_any",
    ],
    "HR": [
        "employee:list",
        "employee:read_any",
        "employee:assign_grade",
        "project:read",
        "timesheet:read_any",
        "summary:read_any",
        "report:read",
        "absence:read_any",
        "document:read_any",
    ],
    "Администратор": [
        "user:register",
        "user:reset_password",
        "employee:list",
        "employee:read_any",
        "employee:edit_any",
        "employee:assign_grade",
        "employee:skills_edit_any",
        "employee:set_lead",
        "employee:assign_roles",
        "employee:assign_status",
        "project:read",
        "project:manage",
        "project:assign",
        "directory:manage",
        "system:manage",
        "calendar:manage",
        "timesheet:read_any",
        "timesheet:edit_any",
        "timesheet:close_period",
        "timesheet:approve_period",
        "overtime:approve",
        "summary:read_any",
        "report:read",
        "report:manage",
        "absence:read_any",
        "absence:approve",
        "document:read_any",
        "document:manage_templates",
    ],
}

# ── Демо-пользователи ─────────────────────────────────────────────────────────
DEMO_MANAGER_ID  = uuid.UUID("00000000-0000-0000-0000-000000000010")
DEMO_EMPLOYEE_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")
DEMO_ADMIN_ID    = uuid.UUID("00000000-0000-0000-0000-000000000012")
DEMO_TEAMLEAD_ID = uuid.UUID("00000000-0000-0000-0000-000000000013")
DEMO_HR_ID       = uuid.UUID("00000000-0000-0000-0000-000000000014")

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
    {
        "id": DEMO_ADMIN_ID,
        "email": "admin@demo.com",
        "password": "Admin1!",
        "number": "EMP-000003",
        "role_ids": [ROLE_ADMIN_ID, ROLE_SOTRUDNIK_ID],
    },
    {
        "id": DEMO_TEAMLEAD_ID,
        "email": "teamlead@demo.com",
        "password": "Teamlead1!",
        "number": "EMP-000004",
        "role_ids": [ROLE_TEAMLEAD_ID, ROLE_SOTRUDNIK_ID],
    },
    {
        "id": DEMO_HR_ID,
        "email": "hr@demo.com",
        "password": "Hr1234!",
        "number": "EMP-000005",
        "role_ids": [ROLE_HR_ID, ROLE_SOTRUDNIK_ID],
    },
]

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_roles(session_maker: async_sessionmaker[AsyncSession]) -> None:
    async with session_maker() as session:
        for role_data in SEED_ROLES:
            existing = await session.get(Role, role_data["id"])
            if existing is None:
                session.add(Role(
                    id=role_data["id"],
                    name=role_data["name"],
                    description=role_data["description"],
                ))
            else:
                existing.name = role_data["name"]
                existing.description = role_data["description"]
        await session.commit()


async def seed_permissions(session_maker: async_sessionmaker[AsyncSession]) -> None:
    async with session_maker() as session:
        for perm_data in SEED_PERMISSIONS:
            result = await session.execute(
                select(Permission).where(Permission.code == perm_data["code"])
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                session.add(Permission(
                    code=perm_data["code"],
                    name=perm_data["name"],
                ))
            else:
                existing.name = perm_data["name"]
        await session.commit()


async def seed_role_permissions(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """Сидирует дефолтные маппинги только для ролей, у которых ещё нет permissions.
    Роли с уже существующими маппингами не трогает — чтобы не стирать изменения Admin API."""
    async with session_maker() as session:
        roles_result = await session.execute(select(Role))
        roles_by_name = {r.name: r for r in roles_result.scalars().all()}

        perms_result = await session.execute(select(Permission))
        perms_by_code = {p.code: p for p in perms_result.scalars().all()}

        for role_name, perm_codes in SEED_ROLE_PERMISSIONS.items():
            role = roles_by_name.get(role_name)
            if role is None:
                continue

            # Проверяем: есть ли уже маппинги для этой роли
            existing = await session.execute(
                select(role_permission_table).where(
                    role_permission_table.c.role_id == role.id
                ).limit(1)
            )
            if existing.first() is not None:
                continue  # маппинги уже есть — не трогаем

            rows = [
                {"role_id": role.id, "permission_id": perms_by_code[code].id}
                for code in perm_codes
                if code in perms_by_code
            ]
            if rows:
                await session.execute(insert(role_permission_table), rows)

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
