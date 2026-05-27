from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import EMPLOYEE_UPDATED_TOPIC
from src.models.employee import Employee


async def publish_employee_updated(producer: KafkaEventProducer, employee: Employee) -> None:
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
                "birthday": employee.birthday,
                "image_url": employee.image_url,
            },
        },
    )
