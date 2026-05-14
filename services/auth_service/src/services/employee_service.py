from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
import random

from src.models.employee import Employee
from src.models.role import Role
from src.schemas.employee import EmployeeCreate, EmployeeCreateSimple

class EmployeeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_identity(self, login_identity: str) -> Employee | None:
        """Поиск сотрудника по email или табельному номеру"""
        query = (
            select(Employee)
            .where(
                or_(
                    Employee.email == login_identity,
                    Employee.employee_number == login_identity
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_new_employee(self, data: EmployeeCreate) -> Employee:
        """Создание сотрудника с привязкой ролей"""
        
        # 1. Находим объекты ролей
        roles_query = select(Role).where(Role.id.in_(data.role_id))
        roles_result = await self.session.execute(roles_query)
        roles_list = roles_result.scalars().all()
        
        if not roles_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Указанные роли не найдены"
            )

        # 2. Подготавливаем объект
        hashed_pwd = f"hashed_{data.password}" 
        new_employee = Employee(
            email=data.email,
            employee_number=data.employee_number,
            hashed_password=hashed_pwd,
            roles=roles_list
        )
        
        # 3. Пытаемся сохранить и обрабатываем конфликты на уровне БД
        try:
            self.session.add(new_employee)
            await self.session.commit()
            await self.session.refresh(new_employee, attribute_names=["roles"])
            return new_employee
            
        except IntegrityError as e:
            await self.session.rollback()
            error_msg = str(e.orig).lower()
            
            # Точный анализ ошибки от БД
            if "employee_number" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Сотрудник с номером '{data.employee_number}' уже зарегистрирован"
                )
            if "email" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{data.email}' уже используется"
                )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данные сотрудника конфликтуют с существующими записями"
            )
    async def create_simple_employee(self, data: EmployeeCreateSimple) -> Employee:
        """Автоматическая регистрация: генерация номера и привязка роли 'Basic_user'"""
        
        # 1. Ищем базовую роль "User" в БД
        role_query = select(Role).where(Role.name == "Basic_user")
        role_result = await self.session.execute(role_query)
        base_role = role_result.scalar_one_or_none()
        
        if not base_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Базовая роль 'Basic_user' не найдена в системе. Сначала создайте её в БД."
            )

        # 2. Генерируем уникальный табельный номер (например, EMP-482910)
        # Цикл гарантирует, что если номер совпадет с существующим, мы сгенерируем новый
        while True:
            generated_number = f"EMP-{random.randint(100000, 999999)}"
            check_query = select(Employee).where(Employee.employee_number == generated_number)
            check_result = await self.session.execute(check_query)
            if not check_result.scalar_one_or_none():
                break # Номер уникален, выходим из цикла

        # 3. Подготавливаем объект сотрудника
        hashed_pwd = f"hashed_{data.password}" 
        new_employee = Employee(
            email=data.email,
            employee_number=generated_number, # Подставляем сгенерированный номер
            hashed_password=hashed_pwd,
            roles=[base_role] # Автоматически выдаем только базовую роль
        )
        
        # 4. Сохраняем в базу данных
        try:
            self.session.add(new_employee)
            await self.session.commit()
            await self.session.refresh(new_employee, attribute_names=["roles"])
            return new_employee
            
        except IntegrityError as e:
            await self.session.rollback()
            error_msg = str(e.orig).lower()
            if "email" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{data.email}' уже используется"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка при автоматическом создании сотрудника"
            )