import pytest
import pytest_asyncio
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("TestConnection")

# Используем порт 5431 из вашего конфига (соответствует auth_db в docker-compose)
DATABASE_URL = "postgresql+asyncpg://admin:secret_password@localhost:5431/auth_db"

# Фикстура event_loop удалена, так как pytest-asyncio управляет им автоматически

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    logger.info("⚙️ Инициализация движка базы данных...")
    engine = create_async_engine(DATABASE_URL)
    yield engine
    logger.info("🔌 Закрытие движка базы данных...")
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Создает сессию для теста с автоматическим откатом."""
    async_session = async_sessionmaker(
        db_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        logger.info("🔑 Открытие новой сессии БД...")
        yield session
        try:
            # Оборачиваем откат в try/except на случай, если соединение разорвано
            await session.rollback()
        except Exception as e:
            logger.warning(f"Ошибка при выполнении rollback в teardown: {e}")
        logger.info("↩️ Сессия БД завершена (откат изменений).")

@pytest.mark.asyncio
async def test_db_connection(db_session):
    """Тест подключения к базе данных auth_db."""
    try:
        logger.info("📡 Отправка запроса SELECT 1 в базу данных...")
        result = await db_session.execute(text("SELECT 1"))
        value = result.scalar()
        
        assert value == 1, f"Ожидаемый результат 1, получен: {value}"
        logger.info("✅ Соединение с базой данных успешно установлено!")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}")
        pytest.fail(f"Ошибка подключения: {e}")

@pytest.mark.asyncio
async def test_kafka_connection():
    """Тест подключения к Kafka: проверка отправки и чтения сообщения."""
    producer = AIOKafkaProducer(bootstrap_servers='localhost:9092')
    consumer = AIOKafkaConsumer(
        'test_connection_topic',
        bootstrap_servers='localhost:9092',
        group_id='test_group',
        auto_offset_reset='earliest'
    )

    await producer.start()
    await consumer.start()

    test_message = b'{"status": "test_connection_success"}'

    try:
        logger.info("📤 Отправка тестового сообщения в топик 'test_connection_topic'...")
        await producer.send_and_wait('test_connection_topic', test_message)
        logger.info("✉️ Сообщение успешно отправлено в Kafka.")

        received_message = None
        logger.info("📡 Ожидание входящего сообщения из Kafka...")
        
        try:
            async for msg in consumer:
                received_message = msg.value
                break  # Читаем первое полученное сообщение
        except Exception as e:
            logger.error(f"❌ Ошибка при чтении из топика: {e}")
            pytest.fail(f"Ошибка чтения: {e}")

        assert received_message == test_message, f"Сообщения не совпадают: {received_message} != {test_message}"
        logger.info("📥 Тестовое сообщение успешно получено из Kafka!")

    finally:
        await producer.stop()
        await consumer.stop()
        logger.info("🔌 Соединение с Kafka закрыто.")