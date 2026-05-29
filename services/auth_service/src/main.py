import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from .database import engine, async_session_maker
from .kafka.consumer import KafkaEventConsumer
from .kafka.producer import KafkaEventProducer
from src.models.base import Base
from src.models.user import User
from src.models.user_role import user_role
from src.models.role import Role
from src.routers.employee import router as auth_router
from src.seed import seed_roles


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_roles(async_session_maker)
    app.state.kafka_producer = KafkaEventProducer()
    await app.state.kafka_producer.start()
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

@app.get("/")
def read_root():
    return {"message": "Auth Service is running"}

app.include_router(auth_router)
