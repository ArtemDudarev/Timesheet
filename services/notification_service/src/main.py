import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine
from .kafka.consumer import KafkaEventConsumer
from .models.base import Base
from .models.user import User
from .models.role import Role
from .models.user_role import user_role
from .models.employee import Employee
from .models.notification import Notification
from .models.notification_preference import NotificationPreference
from .routers.notification import router as notification_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.kafka_consumer = KafkaEventConsumer()
    app.state.kafka_consumer_task = asyncio.create_task(
        app.state.kafka_consumer.start()
    )

    yield

    app.state.kafka_consumer_task.cancel()
    await app.state.kafka_consumer.stop()
    with suppress(asyncio.CancelledError):
        await app.state.kafka_consumer_task
    await engine.dispose()


app = FastAPI(title="Notification Service", lifespan=lifespan)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notification_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "notification_service"}
