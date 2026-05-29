import uuid
from typing import Any

from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import (
    EMPLOYEE_PROJECT_ASSIGNED_TOPIC,
    EMPLOYEE_ROLE_ASSIGNED_TOPIC,
    EMPLOYEE_STATUS_CHANGED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
    PROJECT_CREATED_TOPIC,
    PROJECT_DELETED_TOPIC,
    PROJECT_UPDATED_TOPIC,
    ROLE_CREATED_TOPIC,
    ROLE_DELETED_TOPIC,
    ROLE_UPDATED_TOPIC,
    STATUS_CREATED_TOPIC,
    STATUS_DELETED_TOPIC,
    STATUS_UPDATED_TOPIC,
)
from src.models.employee import Employee
from src.models.employee_project import EmployeeProject
from src.models.project import Project
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
                "status": project.status,
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
                "status": project.status,
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
    assignment: EmployeeProject,
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
            "status": assignment.status,
        },
    )
