import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.limiter import limiter

from .database import engine, async_session_maker
from .kafka.consumer import KafkaEventConsumer
from .kafka.producer import KafkaEventProducer
from src.models.base import Base
from src.models.user import User
from src.models.user_role import user_role
from src.models.role import Role
from src.models.role_permission import role_permission
from src.models.permission import Permission
from src.models.refresh_token import RefreshToken
from src.models.password_reset_request import PasswordResetRequest
from src.routers.employee import router as auth_router
from src.routers.admin import router as admin_router
from src.routers.session import router as session_router
from src.routers.password_reset_request import router as reset_request_router
from src.seed import seed_demo_users, seed_permissions, seed_role_permissions, seed_roles


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.kafka_producer = KafkaEventProducer()
    await app.state.kafka_producer.start()
    await seed_roles(async_session_maker)
    await seed_permissions(async_session_maker)
    await seed_role_permissions(async_session_maker)
    await seed_demo_users(async_session_maker, app.state.kafka_producer)
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

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Auth Service is running"}

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(session_router)
app.include_router(reset_request_router)
