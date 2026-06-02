import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from .database import engine, async_session_maker
from .kafka.consumer import KafkaEventConsumer
from .kafka.producer import KafkaEventProducer
from .models.base import Base
from .models.user import User
from .models.role import Role
from .models.user_role import user_role
from .models.employee import Employee
from .models.project import Project
from .models.project_role import ProjectRole
from .models.employee_project import Assignment
from .models.entry_type_ref import EntryTypeRef
from .models.production_calendar import ProductionCalendar
from .models.timesheet_period import TimesheetPeriod
from .models.time_entry import TimeEntry
from .models.overtime_approval import OvertimeApproval
from .seed import seed_entry_types, seed_production_calendar, seed_existing_employee_periods
from .routers.production_calendar import router as calendar_router
from .routers.timesheet_period import router as period_router
from .routers.time_entry import router as entry_router
from .routers.overtime_approval import router as approval_router
from .routers.entry_type_ref import router as entry_type_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.kafka_producer = KafkaEventProducer()
    await app.state.kafka_producer.start()

    await seed_entry_types(async_session_maker)
    await seed_production_calendar(async_session_maker)
    await seed_existing_employee_periods(async_session_maker)

    app.state.kafka_consumer = KafkaEventConsumer(producer=app.state.kafka_producer)
    app.state.kafka_consumer_task = asyncio.create_task(
        app.state.kafka_consumer.start()
    )

    yield

    await app.state.kafka_producer.stop()
    app.state.kafka_consumer_task.cancel()
    await app.state.kafka_consumer.stop()
    with suppress(asyncio.CancelledError):
        await app.state.kafka_consumer_task
    await engine.dispose()


app = FastAPI(title="Timesheet Service", lifespan=lifespan)

app.include_router(entry_type_router)
app.include_router(calendar_router)
app.include_router(period_router)
app.include_router(entry_router)
app.include_router(approval_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "timesheet_service"}
