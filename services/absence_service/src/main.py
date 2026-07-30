import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, async_session_maker
from .kafka.consumer import KafkaEventConsumer
from .kafka.producer import KafkaEventProducer
from .models.base import Base
from .models.employee import Employee
from .models.absence_type import AbsenceType
from .models.absence import Absence
from .seed import seed_absence_types
from .routers.absence import router as absence_router
from .routers.absence_type import router as absence_type_router
from .routers.vacation_balance import router as vacation_balance_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.kafka_producer = KafkaEventProducer()
    await app.state.kafka_producer.start()

    await seed_absence_types(async_session_maker)

    app.state.kafka_consumer = KafkaEventConsumer()
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


app = FastAPI(title="Absence Service", lifespan=lifespan)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(absence_router)
app.include_router(absence_type_router)
app.include_router(vacation_balance_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "absence_service"}
