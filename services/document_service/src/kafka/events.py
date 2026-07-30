from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import DOCUMENT_ROUTE_UPDATED_TOPIC
from src.models.document import Document
from src.services.document_service import DocumentService


async def publish_document_route_updated(
    producer: KafkaEventProducer, document: Document
) -> None:
    current = DocumentService.current_step(document)
    await producer.publish(
        DOCUMENT_ROUTE_UPDATED_TOPIC,
        {
            "event_type": "document.route_updated",
            "document_id": str(document.id),
            "title": document.title,
            "author_id": str(document.author_id),
            "current_step_employee_id": str(current.employee_id) if current else None,
            "status": document.status.value,
        },
    )
