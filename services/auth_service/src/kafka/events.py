from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import EMPLOYEE_CREATED_TOPIC
from src.models.employee import Employee


async def publish_employee_created(
    producer: KafkaEventProducer,
    employee: Employee,
) -> None:
    await producer.publish(
        EMPLOYEE_CREATED_TOPIC,
        {
            "event_type": "employee.created",
            "employee": {
                "id": employee.id,
                "email": employee.email,
                "employee_number": employee.employee_number,
                "hashed_password": employee.hashed_password,
                "roles": [
                    {
                        "id": role.id,
                        "name": role.name,
                        "description": role.description,
                    }
                    for role in employee.roles
                ],
            },
        },
    )
