from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import EMPLOYEE_CREATED_TOPIC
from src.models.user import User


async def publish_user_created(producer: KafkaEventProducer, user: User) -> None:
    await producer.publish(
        EMPLOYEE_CREATED_TOPIC,
        {
            "event_type": "user.created",
            "user": {
                "id": user.id,
                "email": user.email,
                "number": user.number,
                "hashed_password": user.hashed_password,
                "is_active": user.is_active,
                "register_date": user.register_date.isoformat(),
                "roles": [
                    {"id": role.id, "name": role.name, "description": role.description}
                    for role in user.roles
                ],
            },
        },
    )
