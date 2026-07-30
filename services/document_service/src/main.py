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
from .models.document_type import DocumentType
from .models.document import Document, DocumentRouteStep, DocumentTemplate
from .seed import seed_document_types
from .routers.document import router as document_router
from .routers.document_template import router as template_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.kafka_producer = KafkaEventProducer()
    await app.state.kafka_producer.start()

    await seed_document_types(async_session_maker)

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


app = FastAPI(title="Document Service", lifespan=lifespan)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Иначе браузер не отдаст фронту имя файла при скачивании
    expose_headers=["Content-Disposition"],
)

app.include_router(document_router)
app.include_router(template_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "document_service"}
