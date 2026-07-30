from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import EMPLOYEE_CREATED_TOPIC, PASSWORD_RESET_REQUESTED_TOPIC
from src.models.password_reset_request import PasswordResetRequest
from src.models.user import User


async def publish_password_reset_requested(
    producer: KafkaEventProducer, request: PasswordResetRequest
) -> None:
    await producer.publish(
        PASSWORD_RESET_REQUESTED_TOPIC,
        {
            "event_type": "password_reset.requested",
            "request_id": str(request.id),
            "identifier": request.identifier,
            "user_id": str(request.user_id) if request.user_id else None,
        },
    )


async def publish_user_created(producer: KafkaEventProducer, user: User) -> None:
    await producer.publish(
        EMPLOYEE_CREATED_TOPIC,
        {
            "event_type": "user.created",
            "user": {
                "id": user.id,
                "email": user.email,
                "number": user.number,
                "is_active": user.is_active,
                "register_date": user.register_date.isoformat(),
                "roles": [
                    {"id": role.id, "name": role.name, "description": role.description}
                    for role in user.roles
                ],
            },
        },
    )
