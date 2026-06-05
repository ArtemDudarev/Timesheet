import uuid
from typing import Any

from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import (
    DEPARTMENT_CREATED_TOPIC,
    DEPARTMENT_DELETED_TOPIC,
    DEPARTMENT_UPDATED_TOPIC,
    EMPLOYEE_PROJECT_ASSIGNED_TOPIC,
    EMPLOYEE_PROFILE_CREATED_TOPIC,
    EMPLOYEE_ROLE_ASSIGNED_TOPIC,
    EMPLOYEE_STATUS_CHANGED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
    GRADE_CREATED_TOPIC,
    GRADE_DELETED_TOPIC,
    GRADE_UPDATED_TOPIC,
    PROJECT_CREATED_TOPIC,
    PROJECT_DELETED_TOPIC,
    PROJECT_UPDATED_TOPIC,
    PROJECT_ROLE_CREATED_TOPIC,
    PROJECT_ROLE_DELETED_TOPIC,
    PROJECT_ROLE_UPDATED_TOPIC,
    ROLE_CREATED_TOPIC,
    ROLE_DELETED_TOPIC,
    ROLE_UPDATED_TOPIC,
    SKILL_CREATED_TOPIC,
    SKILL_DELETED_TOPIC,
    SKILL_UPDATED_TOPIC,
    STATUS_CREATED_TOPIC,
    STATUS_DELETED_TOPIC,
    STATUS_UPDATED_TOPIC,
)
from src.models.department import Department
from src.models.employee import Employee
from src.models.employee_project import Assignment
from src.models.grade import Grade
from src.models.skill import Skill
from src.models.project import Project
from src.models.project_role import ProjectRole
from src.models.role import Role
from src.models.status import Status
from src.models.user import User


async def publish_employee_updated(
    producer: KafkaEventProducer,
    employee: Employee,
) -> None:
    await producer.publish(
        EMPLOYEE_UPDATED_TOPIC,
        {
            "event_type": "employee.updated",
            "employee": {
                "id": employee.id,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "phone": employee.phone,
                "address": employee.address,
                "birthday": employee.birthday.isoformat() if employee.birthday else None,
                "image_url": employee.image_url,
                "lead_id": str(employee.lead_id) if employee.lead_id else None,
            },
        },
    )


async def publish_employee_role_assigned(
    producer: KafkaEventProducer,
    user: User,
) -> None:
    await producer.publish(
        EMPLOYEE_ROLE_ASSIGNED_TOPIC,
        {
            "event_type": "employee.role_assigned",
            "employee_id": user.id,
            "roles": [
                {"id": role.id, "name": role.name, "description": role.description}
                for role in user.roles
            ],
        },
    )


async def publish_employee_status_changed(
    producer: KafkaEventProducer,
    employee: Employee,
) -> None:
    await producer.publish(
        EMPLOYEE_STATUS_CHANGED_TOPIC,
        {
            "event_type": "employee.status_changed",
            "employee_id": employee.id,
            "status": {
                "id": employee.status.id,
                "name": employee.status.name,
                "description": employee.status.description,
            },
        },
    )


async def publish_role_created(
    producer: KafkaEventProducer,
    role: Role,
) -> None:
    await producer.publish(
        ROLE_CREATED_TOPIC,
        {
            "event_type": "role.created",
            "role": {"id": role.id, "name": role.name, "description": role.description},
        },
    )


async def publish_role_updated(
    producer: KafkaEventProducer,
    role: Role,
) -> None:
    await producer.publish(
        ROLE_UPDATED_TOPIC,
        {
            "event_type": "role.updated",
            "role": {"id": role.id, "name": role.name, "description": role.description},
        },
    )


async def publish_role_deleted(
    producer: KafkaEventProducer,
    role_id: uuid.UUID,
) -> None:
    await producer.publish(
        ROLE_DELETED_TOPIC,
        {
            "event_type": "role.deleted",
            "role_id": role_id,
        },
    )


async def publish_project_created(
    producer: KafkaEventProducer,
    project: Project,
) -> None:
    await producer.publish(
        PROJECT_CREATED_TOPIC,
        {
            "event_type": "project.created",
            "project": {
                "id": project.id,
                "name": project.name,
                "status": project.project_status.name,
                "status_id": str(project.status_id),
                "start_date": project.start_date.isoformat() if project.start_date else None,
                "end_date": project.end_date.isoformat() if project.end_date else None,
            },
        },
    )


async def publish_project_updated(
    producer: KafkaEventProducer,
    project: Project,
) -> None:
    await producer.publish(
        PROJECT_UPDATED_TOPIC,
        {
            "event_type": "project.updated",
            "project": {
                "id": project.id,
                "name": project.name,
                "status": project.project_status.name,
                "status_id": str(project.status_id),
                "start_date": project.start_date.isoformat() if project.start_date else None,
                "end_date": project.end_date.isoformat() if project.end_date else None,
            },
        },
    )


async def publish_project_deleted(
    producer: KafkaEventProducer,
    project_id: uuid.UUID,
) -> None:
    await producer.publish(
        PROJECT_DELETED_TOPIC,
        {
            "event_type": "project.deleted",
            "project_id": project_id,
        },
    )


async def publish_status_created(
    producer: KafkaEventProducer,
    status: Status,
) -> None:
    await producer.publish(
        STATUS_CREATED_TOPIC,
        {
            "event_type": "status.created",
            "status": {"id": status.id, "name": status.name, "description": status.description},
        },
    )


async def publish_status_updated(
    producer: KafkaEventProducer,
    status: Status,
) -> None:
    await producer.publish(
        STATUS_UPDATED_TOPIC,
        {
            "event_type": "status.updated",
            "status": {"id": status.id, "name": status.name, "description": status.description},
        },
    )


async def publish_status_deleted(
    producer: KafkaEventProducer,
    status_id: uuid.UUID,
) -> None:
    await producer.publish(
        STATUS_DELETED_TOPIC,
        {
            "event_type": "status.deleted",
            "status_id": status_id,
        },
    )


async def publish_employee_project_assigned(
    producer: KafkaEventProducer,
    assignment: Assignment,
) -> None:
    await producer.publish(
        EMPLOYEE_PROJECT_ASSIGNED_TOPIC,
        {
            "event_type": "employee.project_assigned",
            "assignment_id": assignment.id,
            "employee_id": assignment.employee_id,
            "project_id": assignment.project_id,
            "project_role": {
                "id": assignment.project_role.id,
                "name": assignment.project_role.name,
                "description": assignment.project_role.description,
            },
            "start_date": assignment.start_date.isoformat() if assignment.start_date else None,
            "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
            "status": assignment.assignment_status.name,
            "status_id": str(assignment.status_id),
        },
    )


async def publish_employee_profile_created(
    producer: KafkaEventProducer,
    employee: Employee,
    user: User,
) -> None:
    await producer.publish(
        EMPLOYEE_PROFILE_CREATED_TOPIC,
        {
            "event_type": "employee.profile_created",
            "employee": {
                "id": str(employee.id),
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "email": user.email,
                "number": user.number,
                "register_date": user.register_date.isoformat() if user.register_date else None,
            },
        },
    )


async def publish_project_role_created(
    producer: KafkaEventProducer,
    project_role: ProjectRole,
) -> None:
    await producer.publish(
        PROJECT_ROLE_CREATED_TOPIC,
        {
            "event_type": "project_role.created",
            "project_role": {
                "id": str(project_role.id),
                "name": project_role.name,
                "description": project_role.description,
            },
        },
    )


async def publish_project_role_updated(
    producer: KafkaEventProducer,
    project_role: ProjectRole,
) -> None:
    await producer.publish(
        PROJECT_ROLE_UPDATED_TOPIC,
        {
            "event_type": "project_role.updated",
            "project_role": {
                "id": str(project_role.id),
                "name": project_role.name,
                "description": project_role.description,
            },
        },
    )


async def publish_project_role_deleted(
    producer: KafkaEventProducer,
    project_role_id: uuid.UUID,
) -> None:
    await producer.publish(
        PROJECT_ROLE_DELETED_TOPIC,
        {
            "event_type": "project_role.deleted",
            "project_role_id": str(project_role_id),
        },
    )


async def publish_department_created(producer: KafkaEventProducer, dept: Department) -> None:
    await producer.publish(DEPARTMENT_CREATED_TOPIC, {
        "event_type": "department.created",
        "department": {"id": str(dept.id), "name": dept.name, "description": dept.description},
    })


async def publish_department_updated(producer: KafkaEventProducer, dept: Department) -> None:
    await producer.publish(DEPARTMENT_UPDATED_TOPIC, {
        "event_type": "department.updated",
        "department": {"id": str(dept.id), "name": dept.name, "description": dept.description},
    })


async def publish_department_deleted(producer: KafkaEventProducer, dept_id: uuid.UUID) -> None:
    await producer.publish(DEPARTMENT_DELETED_TOPIC, {
        "event_type": "department.deleted",
        "department_id": str(dept_id),
    })


async def publish_grade_created(producer: KafkaEventProducer, grade: Grade) -> None:
    await producer.publish(GRADE_CREATED_TOPIC, {
        "event_type": "grade.created",
        "grade": {"id": str(grade.id), "name": grade.name, "description": grade.description, "sort_order": grade.sort_order},
    })


async def publish_grade_updated(producer: KafkaEventProducer, grade: Grade) -> None:
    await producer.publish(GRADE_UPDATED_TOPIC, {
        "event_type": "grade.updated",
        "grade": {"id": str(grade.id), "name": grade.name, "description": grade.description, "sort_order": grade.sort_order},
    })


async def publish_grade_deleted(producer: KafkaEventProducer, grade_id: uuid.UUID) -> None:
    await producer.publish(GRADE_DELETED_TOPIC, {
        "event_type": "grade.deleted",
        "grade_id": str(grade_id),
    })


async def publish_skill_created(producer: KafkaEventProducer, skill: Skill) -> None:
    await producer.publish(SKILL_CREATED_TOPIC, {
        "event_type": "skill.created",
        "skill": {"id": str(skill.id), "name": skill.name},
    })


async def publish_skill_updated(producer: KafkaEventProducer, skill: Skill) -> None:
    await producer.publish(SKILL_UPDATED_TOPIC, {
        "event_type": "skill.updated",
        "skill": {"id": str(skill.id), "name": skill.name},
    })


async def publish_skill_deleted(producer: KafkaEventProducer, skill_id: uuid.UUID) -> None:
    await producer.publish(SKILL_DELETED_TOPIC, {
        "event_type": "skill.deleted",
        "skill_id": str(skill_id),
    })
