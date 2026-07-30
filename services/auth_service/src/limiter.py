import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Лимиты настраиваются через env: на дев-стенде 5/мин на логин мешает
# ручному тестированию с переключением пользователей (лимит считается по IP)
LOGIN_RATE_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "5/minute")
RESET_REQUEST_RATE_LIMIT = os.getenv("RESET_REQUEST_RATE_LIMIT", "3/minute")
