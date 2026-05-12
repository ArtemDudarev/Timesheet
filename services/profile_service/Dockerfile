FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Команда для запуска (например, uvicorn)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]