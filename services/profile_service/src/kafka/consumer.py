import asyncio
import json
import logging
import os
from datetime import date
from typing import Any
from uuid import UUID

from aiokafka import AIOKafkaConsumer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.kafka.topics import EMPLOYEE_CREATED_TOPIC
from src.models.employee import Employee
from src.models.role import Role
from src.models.status import Status

logger = logging.getLogger(__name__)


class EmployeeEventConsumer:
    def __init__(self) -> None:
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        self.group_id = os.getenv("KAFKA_GROUP_ID", "profile-service")
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True

        while self._running:
            try:
                self._consumer = AIOKafkaConsumer(
                    EMPLOYEE_CREATED_TOPIC,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    enable_auto_commit=False,
                    auto_offset_reset="earliest",
                    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
                )
                await self._consumer.start()
                logger.info("Kafka consumer started: %s", self.bootstrap_servers)
                break
            except Exception:
                logger.exception("Kafka consumer start failed, retrying...")
                await asyncio.sleep(5)

        if not self._consumer:
            return

        try:
            async for message in self._consumer:
                try:
                    await self._handle_message(message.value)
                    await self._consumer.commit()
                except Exception:
                    logger.exception("Failed to process Kafka message: %s", message.value)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Kafka consumer failed")
        finally:
            await self.stop()

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")

    async def _handle_message(self, payload: dict[str, Any]) -> None:
        if payload.get("event_type") != "employee.created":
            return

        employee_data = payload.get("employee") or {}
        async with async_session_maker() as session:
            await self._upsert_employee(session, employee_data)

    async def _upsert_employee(
        self,
        session: AsyncSession,
        employee_data: dict[str, Any],
    ) -> None:
        employee_id = UUID(str(employee_data["id"]))
        roles = await self._get_or_create_roles(session, employee_data.get("roles", []))
        status = await self._get_or_create_default_status(session)

        result = await session.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()

        if employee is None:
            employee = Employee(
                id=employee_id,
                first_name="Не указано",
                last_name="Не указано",
                email=employee_data["email"],
                hashed_password=employee_data.get("hashed_password", ""),
                number=employee_data.get("employee_number"),
                register_date=date.today(),
                status_id=status.id,
                roles=roles,
            )
            session.add(employee)
        else:
            employee.email = employee_data["email"]
            employee.hashed_password = employee_data.get("hashed_password", employee.hashed_password)
            employee.number = employee_data.get("employee_number")
            employee.roles = roles

        await session.commit()

    async def _get_or_create_roles(
        self,
        session: AsyncSession,
        roles_data: list[dict[str, Any]],
    ) -> list[Role]:
        roles: list[Role] = []

        for role_data in roles_data:
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            role = result.scalar_one_or_none()

            if role is None:
                role = Role(
                    name=role_data["name"],
                    description=role_data.get("description"),
                )
                session.add(role)
                await session.flush()

            roles.append(role)

        return roles

    async def _get_or_create_default_status(self, session: AsyncSession) -> Status:
        result = await session.execute(select(Status).where(Status.name == "Новый"))
        status = result.scalar_one_or_none()

        if status is None:
            status = Status(
                name="Новый",
                description="Статус сотрудника после регистрации",
            )
            session.add(status)
            await session.flush()

        return status
