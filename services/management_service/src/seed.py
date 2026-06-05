import asyncio
import uuid
from datetime import date

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.kafka.events import (
    publish_department_created,
    publish_employee_profile_created,
    publish_employee_project_assigned,
    publish_employee_status_changed,
    publish_employee_updated,
    publish_grade_created,
    publish_project_created,
    publish_project_role_created,
    publish_role_created,
    publish_skill_created,
    publish_status_created,
)
from src.kafka.producer import KafkaEventProducer
from src.models.department import Department
from src.models.employee import Employee
from src.models.grade import Grade
from src.models.skill import Skill
from src.models.assignment_status import AssignmentStatus
from src.models.employee_project import Assignment
from src.models.project import Project
from src.models.project_status import ProjectStatus
from src.models.project_role import ProjectRole
from src.models.role import Role
from src.models.status import Status
from src.models.user import User
from src.models.user_role import user_role as user_role_table

# ── Статусы проектов ──────────────────────────────────────────────────────────
PROJECT_STATUS_PLANNED_ID   = uuid.UUID("00000000-0000-0000-0001-000000000001")
PROJECT_STATUS_ACTIVE_ID    = uuid.UUID("00000000-0000-0000-0001-000000000002")
PROJECT_STATUS_ON_HOLD_ID   = uuid.UUID("00000000-0000-0000-0001-000000000003")
PROJECT_STATUS_COMPLETED_ID = uuid.UUID("00000000-0000-0000-0001-000000000004")
PROJECT_STATUS_ARCHIVED_ID  = uuid.UUID("00000000-0000-0000-0001-000000000005")

SEED_PROJECT_STATUSES = [
    {"id": PROJECT_STATUS_PLANNED_ID,   "code": "PLANNED",   "name": "Планируется",   "description": None},
    {"id": PROJECT_STATUS_ACTIVE_ID,    "code": "ACTIVE",    "name": "Активный",      "description": None},
    {"id": PROJECT_STATUS_ON_HOLD_ID,   "code": "ON_HOLD",   "name": "Приостановлен", "description": None},
    {"id": PROJECT_STATUS_COMPLETED_ID, "code": "COMPLETED", "name": "Завершён",      "description": None},
    {"id": PROJECT_STATUS_ARCHIVED_ID,  "code": "ARCHIVED",  "name": "Архивный",      "description": None},
]

# ── Статусы назначений ─────────────────────────────────────────────────────────
ASSIGN_STATUS_REQUEST_ID  = uuid.UUID("00000000-0000-0000-0002-000000000001")
ASSIGN_STATUS_ACTIVE_ID   = uuid.UUID("00000000-0000-0000-0002-000000000002")
ASSIGN_STATUS_EXTENDED_ID = uuid.UUID("00000000-0000-0000-0002-000000000003")
ASSIGN_STATUS_REMOVED_ID  = uuid.UUID("00000000-0000-0000-0002-000000000004")

SEED_ASSIGNMENT_STATUSES = [
    {"id": ASSIGN_STATUS_REQUEST_ID,  "code": "REQUEST",  "name": "Заявка",            "description": None},
    {"id": ASSIGN_STATUS_ACTIVE_ID,   "code": "ACTIVE",   "name": "Привлечён",         "description": None},
    {"id": ASSIGN_STATUS_EXTENDED_ID, "code": "EXTENDED", "name": "Продлён",           "description": None},
    {"id": ASSIGN_STATUS_REMOVED_ID,  "code": "REMOVED",  "name": "Снят с проекта",    "description": None},
]

# ── Роли системы ──────────────────────────────────────────────────────────────
ROLE_SOTRUDNIK_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ROLE_MANAGER_ID   = uuid.UUID("00000000-0000-0000-0000-000000000002")
ROLE_TEAMLEAD_ID  = uuid.UUID("00000000-0000-0000-0000-000000000003")
ROLE_HR_ID        = uuid.UUID("00000000-0000-0000-0000-000000000004")
ROLE_ADMIN_ID     = uuid.UUID("00000000-0000-0000-0000-000000000005")

SEED_ROLES = [
    {"id": ROLE_SOTRUDNIK_ID, "name": "Сотрудник",     "description": "Базовая роль для всех сотрудников"},
    {"id": ROLE_MANAGER_ID,   "name": "Менеджер",      "description": "PM / руководитель отдела"},
    {"id": ROLE_TEAMLEAD_ID,  "name": "Тимлид",        "description": "Руководитель команды"},
    {"id": ROLE_HR_ID,        "name": "HR",             "description": "Кадровая служба"},
    {"id": ROLE_ADMIN_ID,     "name": "Администратор", "description": "Системный администратор"},
]

# ── Статусы сотрудников ───────────────────────────────────────────────────────
STATUS_NOVIY_ID     = uuid.UUID("00000000-0000-0000-0000-000000000020")
STATUS_AKTIVNY_ID   = uuid.UUID("00000000-0000-0000-0000-000000000021")
STATUS_OTPUSK_ID    = uuid.UUID("00000000-0000-0000-0000-000000000022")
STATUS_BOLNICHN_ID  = uuid.UUID("00000000-0000-0000-0000-000000000023")
STATUS_UVOLEN_ID    = uuid.UUID("00000000-0000-0000-0000-000000000024")

SEED_STATUSES = [
    {"id": STATUS_NOVIY_ID,    "name": "Новый",         "description": "Статус сотрудника после регистрации"},
    {"id": STATUS_AKTIVNY_ID,  "name": "Активный",      "description": "Сотрудник работает"},
    {"id": STATUS_OTPUSK_ID,   "name": "В отпуске",     "description": "Сотрудник в отпуске"},
    {"id": STATUS_BOLNICHN_ID, "name": "На больничном", "description": "Сотрудник на больничном"},
    {"id": STATUS_UVOLEN_ID,   "name": "Уволен",        "description": "Трудовые отношения расторгнуты"},
]

# ── Роли в проектах ───────────────────────────────────────────────────────────
PR_DEVELOPER_ID = uuid.UUID("00000000-0000-0000-0000-000000000030")
PR_TEAMLEAD_ID  = uuid.UUID("00000000-0000-0000-0000-000000000031")
PR_ANALYST_ID   = uuid.UUID("00000000-0000-0000-0000-000000000032")
PR_QA_ID        = uuid.UUID("00000000-0000-0000-0000-000000000033")
PR_DESIGNER_ID  = uuid.UUID("00000000-0000-0000-0000-000000000034")
PR_DEVOPS_ID    = uuid.UUID("00000000-0000-0000-0000-000000000035")
PR_PM_ID        = uuid.UUID("00000000-0000-0000-0000-000000000036")

SEED_PROJECT_ROLES = [
    {"id": PR_DEVELOPER_ID, "name": "Разработчик",      "description": None},
    {"id": PR_TEAMLEAD_ID,  "name": "Тимлид",           "description": None},
    {"id": PR_ANALYST_ID,   "name": "Аналитик",         "description": None},
    {"id": PR_QA_ID,        "name": "Тестировщик",      "description": None},
    {"id": PR_DESIGNER_ID,  "name": "Дизайнер",         "description": None},
    {"id": PR_DEVOPS_ID,    "name": "DevOps",            "description": None},
    {"id": PR_PM_ID,        "name": "Менеджер проекта", "description": None},
]

# ── Отделы ───────────────────────────────────────────────────────────────────
DEPT_WEB_ID      = uuid.UUID("00000000-0000-0000-0003-000000000001")
DEPT_MOBILE_ID   = uuid.UUID("00000000-0000-0000-0003-000000000002")
DEPT_BACKEND_ID  = uuid.UUID("00000000-0000-0000-0003-000000000003")
DEPT_ANALYTICS_ID = uuid.UUID("00000000-0000-0000-0003-000000000004")
DEPT_TESTING_ID  = uuid.UUID("00000000-0000-0000-0003-000000000005")
DEPT_DESIGN_ID   = uuid.UUID("00000000-0000-0000-0003-000000000006")
DEPT_INFRA_ID    = uuid.UUID("00000000-0000-0000-0003-000000000007")
DEPT_MGMT_ID     = uuid.UUID("00000000-0000-0000-0003-000000000008")

SEED_DEPARTMENTS = [
    {"id": DEPT_WEB_ID,       "name": "Веб-разработка",       "description": None},
    {"id": DEPT_MOBILE_ID,    "name": "Мобильная разработка",  "description": None},
    {"id": DEPT_BACKEND_ID,   "name": "Бэкенд",               "description": None},
    {"id": DEPT_ANALYTICS_ID, "name": "Аналитика",            "description": None},
    {"id": DEPT_TESTING_ID,   "name": "Тестирование",         "description": None},
    {"id": DEPT_DESIGN_ID,    "name": "Дизайн",               "description": None},
    {"id": DEPT_INFRA_ID,     "name": "Инфраструктура",       "description": None},
    {"id": DEPT_MGMT_ID,      "name": "Управление",           "description": None},
]

# ── Грейды ────────────────────────────────────────────────────────────────────
GRADE_M1_ID = uuid.UUID("00000000-0000-0000-0004-000000000001")
GRADE_M2_ID = uuid.UUID("00000000-0000-0000-0004-000000000002")
GRADE_M3_ID = uuid.UUID("00000000-0000-0000-0004-000000000003")
GRADE_M4_ID = uuid.UUID("00000000-0000-0000-0004-000000000004")
GRADE_M5_ID = uuid.UUID("00000000-0000-0000-0004-000000000005")

SEED_GRADES = [
    {"id": GRADE_M1_ID, "name": "М1", "description": "Младший специалист",  "sort_order": 1},
    {"id": GRADE_M2_ID, "name": "М2", "description": "Специалист",          "sort_order": 2},
    {"id": GRADE_M3_ID, "name": "М3", "description": "Старший специалист",  "sort_order": 3},
    {"id": GRADE_M4_ID, "name": "М4", "description": "Ведущий специалист",  "sort_order": 4},
    {"id": GRADE_M5_ID, "name": "М5", "description": "Главный специалист",  "sort_order": 5},
]

# ── Навыки ────────────────────────────────────────────────────────────────────
SEED_SKILLS_NAMES = [
    (uuid.UUID("00000000-0000-0000-0005-000000000001"), "Python"),
    (uuid.UUID("00000000-0000-0000-0005-000000000002"), "FastAPI"),
    (uuid.UUID("00000000-0000-0000-0005-000000000003"), "SQLAlchemy"),
    (uuid.UUID("00000000-0000-0000-0005-000000000004"), "PostgreSQL"),
    (uuid.UUID("00000000-0000-0000-0005-000000000005"), "Docker"),
    (uuid.UUID("00000000-0000-0000-0005-000000000006"), "React"),
    (uuid.UUID("00000000-0000-0000-0005-000000000007"), "TypeScript"),
    (uuid.UUID("00000000-0000-0000-0005-000000000008"), "JavaScript"),
    (uuid.UUID("00000000-0000-0000-0005-000000000009"), "Node.js"),
    (uuid.UUID("00000000-0000-0000-0005-000000000010"), "Java"),
    (uuid.UUID("00000000-0000-0000-0005-000000000011"), "Kotlin"),
    (uuid.UUID("00000000-0000-0000-0005-000000000012"), "Swift"),
    (uuid.UUID("00000000-0000-0000-0005-000000000013"), "Figma"),
    (uuid.UUID("00000000-0000-0000-0005-000000000014"), "UI/UX Design"),
    (uuid.UUID("00000000-0000-0000-0005-000000000015"), "Аналитика данных"),
    (uuid.UUID("00000000-0000-0000-0005-000000000016"), "SQL"),
    (uuid.UUID("00000000-0000-0000-0005-000000000017"), "Kafka"),
    (uuid.UUID("00000000-0000-0000-0005-000000000018"), "DevOps"),
    (uuid.UUID("00000000-0000-0000-0005-000000000019"), "Kubernetes"),
    (uuid.UUID("00000000-0000-0000-0005-000000000020"), "CI/CD"),
    (uuid.UUID("00000000-0000-0000-0005-000000000021"), "Тестирование"),
    (uuid.UUID("00000000-0000-0000-0005-000000000022"), "Автоматизация тестирования"),
]

# ── Демо-проекты ──────────────────────────────────────────────────────────────
PROJECT_PORTAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000040")
PROJECT_MOBILE_ID = uuid.UUID("00000000-0000-0000-0000-000000000041")

DEMO_PROJECTS = [
    {
        "id": PROJECT_PORTAL_ID,
        "name": "Внутренний портал",
        "status_id": PROJECT_STATUS_ACTIVE_ID,
        "start_date": date(2024, 1, 15),
        "end_date": None,
    },
    {
        "id": PROJECT_MOBILE_ID,
        "name": "Мобильное приложение",
        "status_id": PROJECT_STATUS_PLANNED_ID,
        "start_date": date(2025, 6, 1),
        "end_date": None,
    },
]

# ── Демо-сотрудники ───────────────────────────────────────────────────────────
DEMO_MANAGER_ID  = uuid.UUID("00000000-0000-0000-0000-000000000010")
DEMO_EMPLOYEE_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")
DEMO_ADMIN_ID    = uuid.UUID("00000000-0000-0000-0000-000000000012")
DEMO_TEAMLEAD_ID = uuid.UUID("00000000-0000-0000-0000-000000000013")
DEMO_HR_ID       = uuid.UUID("00000000-0000-0000-0000-000000000014")

DEMO_PROFILES = [
    {
        "user_id": DEMO_MANAGER_ID,
        "email": "manager@demo.com",
        "number": "EMP-000001",
        "role_ids": [ROLE_MANAGER_ID, ROLE_SOTRUDNIK_ID],
        "first_name": "Иван",
        "last_name": "Петров",
        "phone": "+7 900 000 0001",
    },
    {
        "user_id": DEMO_EMPLOYEE_ID,
        "email": "employee@demo.com",
        "number": "EMP-000002",
        "role_ids": [ROLE_SOTRUDNIK_ID],
        "first_name": "Мария",
        "last_name": "Сидорова",
        "phone": "+7 900 000 0002",
    },
    {
        "user_id": DEMO_ADMIN_ID,
        "email": "admin@demo.com",
        "number": "EMP-000003",
        "role_ids": [ROLE_ADMIN_ID, ROLE_SOTRUDNIK_ID],
        "first_name": "Алексей",
        "last_name": "Администратов",
        "phone": "+7 900 000 0003",
    },
    {
        "user_id": DEMO_TEAMLEAD_ID,
        "email": "teamlead@demo.com",
        "number": "EMP-000004",
        "role_ids": [ROLE_TEAMLEAD_ID, ROLE_SOTRUDNIK_ID],
        "first_name": "Дмитрий",
        "last_name": "Кузнецов",
        "phone": "+7 900 000 0004",
    },
    {
        "user_id": DEMO_HR_ID,
        "email": "hr@demo.com",
        "number": "EMP-000005",
        "role_ids": [ROLE_HR_ID, ROLE_SOTRUDNIK_ID],
        "first_name": "Елена",
        "last_name": "Смирнова",
        "phone": "+7 900 000 0005",
    },
]

# ── Демо-назначения на проекты ────────────────────────────────────────────────
ASSIGN_MANAGER_PORTAL_ID  = uuid.UUID("00000000-0000-0000-0000-000000000050")
ASSIGN_EMPLOYEE_PORTAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000051")
ASSIGN_TEAMLEAD_PORTAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000052")

DEMO_ASSIGNMENTS = [
    {
        "id": ASSIGN_MANAGER_PORTAL_ID,
        "employee_id": DEMO_MANAGER_ID,
        "project_id": PROJECT_PORTAL_ID,
        "project_role_id": PR_PM_ID,
        "start_date": date(2024, 1, 15),
        "end_date": None,
        "status_id": ASSIGN_STATUS_ACTIVE_ID,
    },
    {
        "id": ASSIGN_EMPLOYEE_PORTAL_ID,
        "employee_id": DEMO_EMPLOYEE_ID,
        "project_id": PROJECT_PORTAL_ID,
        "project_role_id": PR_DEVELOPER_ID,
        "start_date": date(2024, 2, 1),
        "end_date": None,
        "status_id": ASSIGN_STATUS_ACTIVE_ID,
    },
    {
        "id": ASSIGN_TEAMLEAD_PORTAL_ID,
        "employee_id": DEMO_TEAMLEAD_ID,
        "project_id": PROJECT_PORTAL_ID,
        "project_role_id": PR_TEAMLEAD_ID,
        "start_date": date(2024, 1, 15),
        "end_date": None,
        "status_id": ASSIGN_STATUS_ACTIVE_ID,
    },
]


async def seed_project_statuses(session_maker: async_sessionmaker[AsyncSession]) -> None:
    async with session_maker() as session:
        for s in SEED_PROJECT_STATUSES:
            existing = await session.get(ProjectStatus, s["id"])
            if existing is None:
                session.add(ProjectStatus(id=s["id"], code=s["code"], name=s["name"], description=s["description"]))
        await session.commit()


async def seed_assignment_statuses(session_maker: async_sessionmaker[AsyncSession]) -> None:
    async with session_maker() as session:
        for s in SEED_ASSIGNMENT_STATUSES:
            existing = await session.get(AssignmentStatus, s["id"])
            if existing is None:
                session.add(AssignmentStatus(id=s["id"], code=s["code"], name=s["name"], description=s["description"]))
        await session.commit()


async def seed_roles(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for role_data in SEED_ROLES:
            result = await session.execute(
                select(Role).where(Role.id == role_data["id"])
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                role = Role(
                    id=role_data["id"],
                    name=role_data["name"],
                    description=role_data["description"],
                )
                session.add(role)
                await session.flush()
                await publish_role_created(producer, role)
        await session.commit()


async def seed_statuses(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for s in SEED_STATUSES:
            existing = await session.get(Status, s["id"])
            if existing is None:
                status_obj = Status(id=s["id"], name=s["name"], description=s["description"])
                session.add(status_obj)
                await session.flush()
                await publish_status_created(producer, status_obj)
        await session.commit()


async def seed_project_roles(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for pr in SEED_PROJECT_ROLES:
            existing = await session.get(ProjectRole, pr["id"])
            if existing is None:
                role_obj = ProjectRole(
                    id=pr["id"],
                    name=pr["name"],
                    description=pr["description"],
                )
                session.add(role_obj)
                await session.flush()
                await publish_project_role_created(producer, role_obj)
        await session.commit()


async def seed_demo_projects(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for p in DEMO_PROJECTS:
            existing = await session.get(Project, p["id"])
            if existing is None:
                project = Project(
                    id=p["id"],
                    name=p["name"],
                    status_id=p["status_id"],
                    start_date=p["start_date"],
                    end_date=p["end_date"],
                )
                session.add(project)
                await session.flush()
                await session.refresh(project, attribute_names=["project_status"])
                await publish_project_created(producer, project)
        await session.commit()


async def seed_demo_employee_profiles(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for profile in DEMO_PROFILES:
            user = await session.get(User, profile["user_id"])
            if user is None:
                user = User(
                    id=profile["user_id"],
                    email=profile["email"],
                    number=profile["number"],
                    is_active=True,
                    register_date=date.today(),
                )
                session.add(user)
                await session.flush()
                roles_result = await session.execute(
                    select(Role).where(Role.id.in_(profile["role_ids"]))
                )
                roles = list(roles_result.scalars().all())
                if roles:
                    await session.execute(
                        insert(user_role_table),
                        [{"user_id": user.id, "role_id": r.id} for r in roles],
                    )

            employee = await session.get(Employee, profile["user_id"])
            if employee is None:
                employee = Employee(
                    id=profile["user_id"],
                    first_name=profile["first_name"],
                    last_name=profile["last_name"],
                    phone=profile["phone"],
                    status_id=STATUS_NOVIY_ID,
                )
                session.add(employee)
                await session.flush()
                await publish_employee_profile_created(producer, employee, user)
            elif employee.first_name == "Не указано":
                employee.first_name = profile["first_name"]
                employee.last_name = profile["last_name"]
                employee.phone = profile["phone"]
                await session.flush()
                await publish_employee_profile_created(producer, employee, user)

        await session.commit()


async def seed_demo_assignments(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for a in DEMO_ASSIGNMENTS:
            existing = await session.get(Assignment, a["id"])
            if existing is not None:
                continue

            employee = await session.get(Employee, a["employee_id"])
            project = await session.get(Project, a["project_id"])
            if employee is None or project is None:
                continue

            assignment = Assignment(
                id=a["id"],
                employee_id=a["employee_id"],
                project_id=a["project_id"],
                project_role_id=a["project_role_id"],
                start_date=a["start_date"],
                end_date=a["end_date"],
                status_id=a["status_id"],
            )
            session.add(assignment)
            await session.flush()
            await session.refresh(assignment, attribute_names=["project_role", "assignment_status"])
            await publish_employee_project_assigned(producer, assignment)

        await session.commit()


async def seed_demo_employee_statuses(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for profile in DEMO_PROFILES:
            employee = await session.get(Employee, profile["user_id"])
            if employee is None or employee.status_id == STATUS_AKTIVNY_ID:
                continue
            employee.status_id = STATUS_AKTIVNY_ID
            await session.flush()
            await session.refresh(employee, attribute_names=["status"])
            await publish_employee_status_changed(producer, employee)
        await session.commit()


async def seed_departments(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for d in SEED_DEPARTMENTS:
            existing = await session.get(Department, d["id"])
            if existing is None:
                dept = Department(id=d["id"], name=d["name"], description=d["description"])
                session.add(dept)
                await session.flush()
                await publish_department_created(producer, dept)
        await session.commit()


async def seed_grades(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for g in SEED_GRADES:
            existing = await session.get(Grade, g["id"])
            if existing is None:
                grade = Grade(
                    id=g["id"], name=g["name"],
                    description=g["description"], sort_order=g["sort_order"],
                )
                session.add(grade)
                await session.flush()
                await publish_grade_created(producer, grade)
        await session.commit()


async def seed_skills(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    async with session_maker() as session:
        for skill_id, skill_name in SEED_SKILLS_NAMES:
            existing = await session.get(Skill, skill_id)
            if existing is None:
                skill = Skill(id=skill_id, name=skill_name)
                session.add(skill)
                await session.flush()
                await publish_skill_created(producer, skill)
        await session.commit()


async def seed_demo_leads(
    session_maker: async_sessionmaker[AsyncSession],
    producer: KafkaEventProducer,
) -> None:
    """Назначает lead_id: Мария → Тимлид Дмитрий Кузнецов."""
    async with session_maker() as session:
        employee = await session.get(Employee, DEMO_EMPLOYEE_ID)
        if employee is None or employee.lead_id == DEMO_TEAMLEAD_ID:
            return
        employee.lead_id = DEMO_TEAMLEAD_ID
        await session.commit()
        await publish_employee_updated(producer, employee)

