# API-контракт: недостающие сервисы и расширения (по аудиту TS(9) vs backend)

Основано на аудите фронтенд-прототипа `TS (9)/` против текущего бэкенда (2026-07-02). Покрывает всё, что помечено ❌/🟡 в аудите: и точечные расширения существующих сервисов (Часть A), и полностью новые сервисы (Часть B). Приоритеты (🔴/🟡/🟢) взяты из приоритизации гэпов — см. план аудита.

Конвенции ниже намеренно скопированы с уже работающего кода (`services/*/src/schemas`, `services/*/src/routers`), а не придуманы заново — см. сноски "матчит существующий паттерн".

---

## 0. Общие конвенции (как в существующих сервисах)

- **Auth**: `Authorization: Bearer <JWT access token>` на все эндпоинты, кроме явно помеченных `public`. JWT payload: `{sub, email, roles[], permissions[], is_active, exp}` (см. auth_service).
- **Права доступа**: FastAPI dependency `require_permission("code1", "code2", ...)` — доступ, если у пользователя есть **хотя бы один** из кодов (матчит `src/dependencies.py` во всех сервисах).
- **ID**: везде `uuid.UUID` (`gen_random_uuid()` на стороне БД).
- **Пагинация списков**: query-параметры `skip: int = 0`, `limit: int = 100` (матчит `GET /employees/`, `GET /periods/`).
- **Ошибки**: `HTTPException(status_code=..., detail="человекочитаемое сообщение на русском")`. 404 — не найдено, 403 — нет доступа, 409 — конфликт (например, дубликат имени, попытка удалить используемую сущность), 422 — валидация Pydantic.
- **Pydantic-нейминг**: `XCreate` / `XUpdate` / `XRead` для CRUD-сущностей, `XResolve` для action-пейлоадов (approve/reject), `XShort` для вложенных сокращённых представлений (матчит `ProjectRead`/`TimeEntryResponse`/`OvertimeApprovalResolve`).
- **Даты**: `date` (без времени) для календарных полей, `datetime` (UTC) для `created_at`/`updated_at`/`resolved_at`.
- **Kafka**: топики публикуются после `session.commit()` (текущий паттерн — без outbox, см. риск в разделе "Открытые вопросы"). Названия топиков — `{domain}.{event}`, например `absence.status_changed`.
- **Новые permission-коды** добавляются в `auth_service/src/seed.py` (`SEED_PERMISSIONS` + `SEED_ROLE_PERMISSIONS`) — это единственное место, где заводится каталог прав (Вариант B, без Casbin, см. память `project-casbin-rbac`).

---

# Часть A. Расширения существующих сервисов

## A.1 🔴 timesheet_service — Period-level submit/approve

Критичный гэп #5 из приоритизации — без этого не замыкается цикл «заполнил → отправил → согласовали».

### Модель (расширение `TimesheetPeriod`)

Новое поле **не заменяет**, а дополняет существующий `status: OPEN|CLOSED` (тот отвечает за «можно ли редактировать записи», а новое поле — за workflow согласования):

```
TimesheetPeriod (расширение):
  ...existing fields...
  submission_status: DRAFT | PENDING | APPROVED | REJECTED   # default DRAFT
  submitted_at: datetime | null
  approved_by: uuid | null
  approved_at: datetime | null
  rejection_comment: str | null
```

### Эндпоинты

| Method | Path | Permission | Описание |
|---|---|---|---|
| POST | `/periods/{period_id}/submit` | self (own period) | `DRAFT`/`REJECTED` → `PENDING`, `submitted_at=now`. 409 если период уже `PENDING`/`APPROVED` или `status=CLOSED` |
| POST | `/periods/{period_id}/approve` | `timesheet:approve_period` \| `timesheet:approve_period_team` (новые коды, мирроринг `overtime:approve`/`overtime:approve_team`) | `PENDING` → `APPROVED`, `approved_by`, `approved_at`. Team-scoped — доп. проверка `Employee.lead_id == caller` (как в `overtime_approval.py::_assert_team_access`) |
| POST | `/periods/{period_id}/reject` | то же | `PENDING` → `REJECTED`, требует `comment` (обязателен — здесь **строже** существующего overtime-прецедента, см. открытый вопрос про reject-comment ниже) |

**Правило взаимодействия `status` и `submission_status` (обязательно закрепить в реализации, не додумывать по ходу):** `POST /periods/{id}/close` должен требовать `submission_status == APPROVED`, иначе 409 «Период не согласован». Без этого правила менеджер сможет закрыть период в обход согласования — оба поля независимы только по хранению, но не по бизнес-логике.

### Схемы

```python
class TimesheetPeriodSubmit(BaseModel):
    pass  # no body

class TimesheetPeriodApprove(BaseModel):
    pass  # no body

class TimesheetPeriodReject(BaseModel):
    comment: str  # обязателен, в отличие от OvertimeApprovalResolve.comment (там Optional)

class TimesheetPeriodResponse(BaseModel):
    # ...existing fields...
    submission_status: Literal["DRAFT", "PENDING", "APPROVED", "REJECTED"]
    submitted_at: datetime | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    rejection_comment: str | None
```

### Kafka

Публикует (новые топики): `timesheet.period_submitted`, `timesheet.period_approved`, `timesheet.period_rejected` — payload `{period_id, employee_id, year, month}` (+`comment` для reject). Потребитель — будущий notification_service (см. B.4).

### Новые permission-коды (добавить в auth_service seed)

`timesheet:approve_period` (Менеджер/Администратор), `timesheet:approve_period_team` (Тимлид).

---

## A.2 🟡 auth_service — Заявка на сброс пароля

Уточнено пользователем: кнопка «забыли пароль» — не self-service reset (тот уже верно ограничен `user:reset_password`), а **заявка**, попадающая в очередь менеджера.

### Модель (новая, в auth_service)

```
PasswordResetRequest:
  id: uuid
  identifier: str          # email или number, как ввёл пользователь (мы не знаем его user_id без логина)
  user_id: uuid | null      # резолвится на бэке после поиска по identifier; null если не найден (не палим наличие аккаунта)
  status: PENDING | RESOLVED | CANCELLED
  requested_at: datetime
  resolved_by: uuid | null
  resolved_at: datetime | null
```

### Эндпоинты

| Method | Path | Permission | Описание |
|---|---|---|---|
| POST | `/auth/password/reset-requests` | **public**, rate-limit 3/min (как login) | Body `{identifier: str}`. Всегда возвращает `202 {"detail": "Если аккаунт найден, заявка передана менеджеру"}` независимо от того, найден ли пользователь (не палим существование аккаунта) |
| GET | `/auth/password/reset-requests` | `user:reset_password` | Список заявок, фильтр `?status=PENDING` по умолчанию |
| POST | `/auth/password/reset-requests/{id}/resolve` | `user:reset_password` | Внутри вызывает существующий `reset_password(user_id)`, помечает заявку `RESOLVED`, возвращает `PasswordResetResponse` (уже существующая схема с `temp_password`) |
| POST | `/auth/password/reset-requests/{id}/cancel` | `user:reset_password` | `PENDING` → `CANCELLED`, без выдачи пароля |

### Схемы

```python
class PasswordResetRequestCreate(BaseModel):
    identifier: str  # email или number

class PasswordResetRequestRead(BaseModel):
    id: uuid.UUID
    identifier: str
    status: Literal["PENDING", "RESOLVED", "CANCELLED"]
    requested_at: datetime
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None

    model_config = {"from_attributes": True}
```

Ответ `resolve` — переиспользуем существующую `PasswordResetResponse { temp_password: str }`, ничего нового придумывать не нужно.

### Kafka

Публикует `password_reset.requested` (`{request_id, identifier, user_id}`) — потребитель notification_service, чтобы уведомить менеджера/лида без polling.

---

## A.3 🟡 management_service — Обогащение модели `Project`

Подтверждено скриншотом «Управление → Проекты»: нужны поля, которых сейчас нет.

### Модель (расширение `Project`)

```
Project (расширение):
  ...existing: id, name, status_id, start_date, end_date...
  code: str | null          # уникальный короткий код (OMNI, LOYAL...), автогенерация на фронте — бэк просто хранит и проверяет уникальность
  color: str | null         # hex, чисто UI
  client: str | null
  lead_id: uuid | null      # FK → employee, RESTRICT. НЕ путать с Employee.lead_id (оргструктура) — это проектный руководитель
  budget_hours: numeric | null   # плановый бюджет в часах (см. скриншот "ЧАСЫ (ФАКТ/БЮДЖЕТ)" — это часы, не деньги)
  deadline: date | null
```

**`spent_hours`/`progress`/`tasksDone`/`tasksTotal` — НЕ хранить на Project.** Это агрегаты по `TimeEntry`/задачам, считать на чтении (в самом management_service через join к реплике assignments+entries, либо — правильнее — отдавать из будущего reporting_service, см. B.2). Хранение как денормализованного поля потребует синхронизации при каждой записи времени — усложнение без необходимости на этом этапе.

### Эндпоинты — без изменений в путях, расширяются схемы

```python
class ProjectCreate(BaseModel):
    name: str
    project_status_id: uuid.UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    code: Optional[str] = None
    color: Optional[str] = None
    client: Optional[str] = None
    lead_id: Optional[uuid.UUID] = None
    budget_hours: Optional[float] = None
    deadline: Optional[date] = None

class ProjectRead(BaseModel):
    # ...existing... + все новые поля выше (nullable)
    lead: Optional["EmployeeShort"] = None   # разворачиваем lead_id как объект, как это уже делается для project_status

class ProjectUpdate(BaseModel):
    # все поля Optional, как в текущем ProjectUpdate
```

Статус «Под риском» **не добавлять** как значение в `ProjectStatus` enum — см. открытый вопрос в конце документа.

---

# Часть B. Новые сервисы

## B.1 🟢 absence_service (новый, порт 8006, DB `absence_db` 5436)

Отпуска/больничные/командировки/отгулы + согласование + баланс отпуска. Используется 3 экранами (Absences, Manager→Согласование, Chat→ApprovalCard).

### Модели

```
AbsenceType:
  id: uuid, code: VACATION|SICK|TRIP|DAY_OFF (unique), name: str, color: str, requires_approval: bool

Absence:
  id: uuid
  employee_id: uuid            # тонкая реплика, как Employee в timesheet_service
  type_id: uuid → AbsenceType
  date_from: date
  date_to: date
  days_count: int              # считается на бэке при create/update по production calendar (искл. выходные/праздники)
  status: DRAFT | PENDING | APPROVED | REJECTED | CANCELLED
  comment: str | null
  submitted_at: datetime | null
  approver_id: uuid | null
  approved_at: datetime | null
  rejection_comment: str | null
  created_at, updated_at: datetime
```

### Эндпоинты

| Method | Path | Permission | Описание |
|---|---|---|---|
| GET | `/absences/` | self / `absence:read_team` (+lead-фильтр, как `GET /periods/`) / `absence:read_any` | список, query `employee_id?`, `status?`, `type_id?` |
| GET | `/absences/{id}` | self / read_team / read_any | |
| POST | `/absences/` | self (own `employee_id` из JWT) | создаёт `DRAFT`, сразу можно передать `submit=true` чтобы сразу `PENDING` |
| PATCH | `/absences/{id}` | self, только пока `DRAFT`/`REJECTED` | |
| DELETE | `/absences/{id}` | self, только пока `DRAFT`/`PENDING` (отзыв заявки) | |
| POST | `/absences/{id}/submit` | self | `DRAFT`→`PENDING` |
| POST | `/absences/{id}/approve` | `absence:approve` \| `absence:approve_team` | + team-check по `lead_id`, как overtime. Body: `AbsenceApprove` |
| POST | `/absences/{id}/reject` | то же | Body: `AbsenceReject`, `comment` обязателен на уровне схемы (см. примечание в схемах — это строже текущего overtime-прецедента) |
| GET | `/absence-types/` | любой авторизованный | справочник |
| GET | `/employees/{employee_id}/vacation-balance?year=` | self / `absence:read_team` / `absence:read_any` | `{year, entitled_days: 28, used_days, pending_days, remaining_days}` |

### Схемы

```python
class AbsenceCreate(BaseModel):
    type_id: uuid.UUID
    date_from: date
    date_to: date
    comment: Optional[str] = None
    submit: bool = False

    @model_validator(mode="after")
    def validate_dates(self):
        if self.date_to < self.date_from:
            raise ValueError("date_to не может быть раньше date_from")
        return self

class AbsenceUpdate(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    comment: Optional[str] = None

class AbsenceApprove(BaseModel):
    comment: Optional[str] = None

class AbsenceReject(BaseModel):
    comment: str  # обязателен. ВАЖНО: существующий overtime_approval_service.reject() коммент НЕ требует
                  # (проверено в коде — comment: str | None без валидации), несмотря на то что фронт его
                  # всегда просит. Здесь сознательно делаем строже существующего прецедента, а не копируем его

class AbsenceRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    absence_type: "AbsenceTypeRead"
    date_from: date
    date_to: date
    days_count: int
    status: Literal["DRAFT", "PENDING", "APPROVED", "REJECTED", "CANCELLED"]
    comment: Optional[str]
    submitted_at: Optional[datetime]
    approver_id: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    rejection_comment: Optional[str]

    model_config = {"from_attributes": True}

class AbsenceTypeRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    color: str
    requires_approval: bool

    model_config = {"from_attributes": True}

class VacationBalance(BaseModel):
    year: int
    entitled_days: int = 28
    used_days: int
    pending_days: int
    remaining_days: int
```

### Kafka

**Публикует**: `absence.created/updated/status_changed` (`{absence_id, employee_id, type_code, date_from, date_to, status}`).
**Потребляет**: `employee.created`, `employee.updated`, `employee.role_assigned` (тонкая реплика Employee — тот же паттерн, что в timesheet_service).
**timesheet_service должен потребить** `absence.status_changed` (`APPROVED`), чтобы блокировать/подсвечивать ячейки табеля на даты отсутствия — новая консьюмер-подписка в существующем сервисе.

### Новые permission-коды

`absence:read_any`, `absence:read_team`, `absence:approve`, `absence:approve_team` (создание/редактирование своей заявки — без permission, как self-timesheet).

---

## B.2 🟡 reporting_service (порт уже зарезервирован: 8005, DB 5435)

Аналитика, план/факт, экспорт. **Важно**: без своей БД можно обойтись на первой итерации — это read-only агрегатор поверх остальных сервисов (либо синхронные HTTP-вызовы, либо Kafka-реплика по паттерну profile_service). Ниже — вариант с Kafka-репликой (консистентно с остальной архитектурой), т.к. синхронные fan-out вызовы 3 сервисов на каждый reports-запрос будут медленными и хрупкими.

### Модели (материализованные реплики, только для чтения)

```
EmployeeStat: employee_id, department_id, logged_hours, norm_hours, utilization_pct   # per period
ProjectStat: project_id, budget_hours, spent_hours, progress_pct
DepartmentPlan: id, department_id, year, month, planned_hours   # НОВАЯ сущность — на фронте есть "план", в бэке нигде нет источника. CRUD ниже.
```

### Эндпоинты

| Method | Path | Permission | Описание |
|---|---|---|---|
| GET | `/reports/utilization?period=YYYY-MM` | `report:read` | список сотрудников с `logged/norm/utilization_pct` |
| GET | `/reports/projects?period=YYYY-MM` | `report:read` | список проектов с `spent/budget/progress/status/deadline` |
| GET | `/reports/plan-fact?period=YYYY-MM&group_by=department` | `report:read` | `[{department, plan_hours, fact_hours}]` |
| GET | `/reports/summary?period=YYYY-MM` | `report:read` | KPI-карточки: `avg_utilization, total_logged, budget_pct, at_risk_count` |
| GET | `/reports/export?type=projects\|utilization\|plan_fact&period=&format=xlsx` | `report:read` | `StreamingResponse`, генерация через `openpyxl`, `Content-Disposition: attachment` |
| GET/POST/PATCH/DELETE | `/department-plans/` | `report:manage` (новый код, вероятно = `directory:manage`-подобный) | CRUD плановых часов по отделу/месяцу — источник для `plan-fact` |

### Схемы (пример)

```python
class UtilizationRow(BaseModel):
    employee_id: uuid.UUID
    full_name: str
    logged_hours: float
    norm_hours: float
    utilization_pct: float

class ProjectStatRow(BaseModel):
    project_id: uuid.UUID
    name: str
    client: Optional[str]
    spent_hours: float
    budget_hours: Optional[float]
    progress_pct: Optional[float]
    status: str
    deadline: Optional[date]

class PlanFactRow(BaseModel):
    department_id: uuid.UUID
    department_name: str
    plan_hours: float
    fact_hours: float

class ReportsSummary(BaseModel):
    avg_utilization_pct: float
    total_logged_hours: float
    budget_used_pct: float
    at_risk_projects_count: int

class DepartmentPlanCreate(BaseModel):
    department_id: uuid.UUID
    year: int
    month: int
    planned_hours: float
```

### Kafka (потребляет)

`employee.created/updated`, `department.created/updated/deleted`, `project.created/updated/deleted`, `assignment.*`. **Требует нового топика от timesheet_service**: `timesheet.entry_created/updated/deleted` (сейчас timesheet_service публикует только `timesheet.overtime_created` — для агрегации `spent_hours`/`logged_hours` этого недостаточно, нужно публиковать событие на каждое изменение `TimeEntry`). Это скрытая зависимость — без неё reporting_service физически не сможет посчитать `spent_hours`/`logged_hours` без синхронных вызовов в timesheet_service.

### Новые permission-коды

`report:read` (Менеджер/Администратор/HR), `report:manage` (для CRUD department-plans, Администратор).

---

## B.3 🟢 document_service (новый, порт 8007, DB `document_db` 5437)

Документооборот с маршрутом согласования/подписи + файлы. Требует объектное хранилище (S3-совместимое/MinIO) — этого сейчас нет вообще в инфраструктуре (`docker-compose.yml` не содержит minio/s3), нужно добавить как новую зависимость.

### Модели

```
DocumentType: id, code, name, color, icon, description

Document:
  id, title, type_id → DocumentType
  author_id: uuid
  project_id: uuid | null
  file_key: str        # ключ в object storage, не URL напрямую
  file_size: int
  status: DRAFT | PENDING | SIGNED | REJECTED
  comment: str | null
  created_at, updated_at

DocumentRouteStep:
  id, document_id, employee_id, step_order: int
  role: SIGNER | APPROVER
  status: PENDING | SIGNED | REJECTED
  acted_at: datetime | null
  comment: str | null

DocumentTemplate:
  id, type_id → DocumentType, title, file_key, uploaded_by, created_at
```

### Эндпоинты

| Method | Path | Permission | Описание |
|---|---|---|---|
| GET | `/documents/?filter=all\|pending\|mine\|signed&project_id=&search=` | auth | доступны документы, где caller — автор или участник маршрута, либо `document:read_any` |
| GET | `/documents/{id}` | доступ по маршруту / `document:read_any` | + `route: [DocumentRouteStep]` |
| POST | `/documents/` | auth | `multipart/form-data`: `title, type_id, project_id?, comment?, file, route: [{employee_id, role, step_order}]` |
| POST | `/documents/{id}/sign` | участник текущего шага маршрута | продвигает `step_order`, если это последний шаг — `Document.status=SIGNED` |
| POST | `/documents/{id}/reject` | то же | `comment` обязателен, `Document.status=REJECTED`, маршрут прерывается |
| GET | `/documents/{id}/file` | доступ как на GET /documents/{id} | presigned URL или проксирование стрима из object storage |
| GET | `/document-types/` | auth | справочник |
| GET | `/document-templates/` | auth | |
| POST | `/document-templates/` | `document:manage_templates` | multipart upload |
| DELETE | `/document-templates/{id}` | `document:manage_templates` | |

### Схемы

```python
class DocumentRouteStepCreate(BaseModel):
    employee_id: uuid.UUID
    role: Literal["SIGNER", "APPROVER"]
    step_order: int

class DocumentCreate(BaseModel):   # используется как Form-поля рядом с UploadFile, не чистый JSON body
    title: str
    type_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    comment: Optional[str] = None
    route: list[DocumentRouteStepCreate]

class DocumentRouteStepRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    step_order: int
    role: Literal["SIGNER", "APPROVER"]
    status: Literal["PENDING", "SIGNED", "REJECTED"]
    acted_at: Optional[datetime]
    comment: Optional[str]

    model_config = {"from_attributes": True}

class DocumentRead(BaseModel):
    id: uuid.UUID
    title: str
    document_type: "DocumentTypeRead"
    author_id: uuid.UUID
    project_id: Optional[uuid.UUID]
    file_size: int
    status: Literal["DRAFT", "PENDING", "SIGNED", "REJECTED"]
    route: list[DocumentRouteStepRead]
    created_at: datetime

    model_config = {"from_attributes": True}

class DocumentReject(BaseModel):
    comment: str
```

### Kafka

Публикует `document.route_updated` (`{document_id, current_step_employee_id, status}`) — потребитель notification_service (тип "doc" из уже существующего `NOTIF_META` на фронте).

### Новые permission-коды

`document:read_any`, `document:manage_templates`.

---

## B.4 🟡 notification_service (новый, порт 8008, DB `notification_db` 5438)

Bell-дропдаун + настройки уведомлений. Приоритет поднят при критическом ревью — колокольчик виден на каждом экране, полный мок = видимая недоделанность на 100% интерфейса. Минимальная версия (список + read-статусы, без cron) реализуема быстро; digest — отдельно.

### Модели

```
Notification:
  id, user_id: uuid
  type: APPROVAL | DOC | CHAT | DEADLINE | MENTION | PASSWORD
  title: str, text: str
  target_url: str | null    # для click-to-navigate на фронте
  is_read: bool = false
  created_at: datetime

NotificationPreference:
  user_id: uuid (PK)
  email_enabled: bool = true
  push_enabled: bool = true
  type_toggles: json    # {"APPROVAL": true, "DOC": true, "CHAT": true, "DEADLINE": true, "MENTION": true, "WEEKLY_DIGEST": false}
```

### Эндпоинты

| Method | Path | Permission | Описание |
|---|---|---|---|
| GET | `/notifications/?unread_only=&skip=&limit=` | self only | всегда только свои — без team/any вариантов, в отличие от остальных сервисов |
| POST | `/notifications/{id}/read` | self | |
| POST | `/notifications/read-all` | self | |
| GET | `/notifications/preferences` | self | |
| PATCH | `/notifications/preferences` | self | |
| WS | `/ws/notifications` | self (токен в query или первом сообщении) | опционально на первой итерации — можно обойтись поллингом `GET /notifications/?unread_only=true` раз в N секунд |

### Схемы

```python
class NotificationRead(BaseModel):
    id: uuid.UUID
    type: Literal["APPROVAL", "DOC", "CHAT", "DEADLINE", "MENTION", "PASSWORD"]
    title: str
    text: str
    target_url: Optional[str]
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class NotificationPreferenceRead(BaseModel):
    email_enabled: bool
    push_enabled: bool
    type_toggles: dict[str, bool]

class NotificationPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    type_toggles: Optional[dict[str, bool]] = None
```

### Kafka (потребляет практически всё — терминальный consumer, как profile_service)

`timesheet.period_submitted/approved/rejected`, `timesheet.overtime_created`, `document.route_updated`, `password_reset.requested`, `absence.status_changed`, (`chat.mention` — если/когда появится chat_service). **Weekly digest** — отдельный cron-джоб внутри сервиса (например APScheduler), не событийный путь; в MVP можно не делать, оставить toggle в UI неактивным до появления.

### Разрешения

Нет отдельных permission-кодов — всё строго self-scoped через JWT `sub`.

---

## B.5 🟢 chat_service (новый, порт 8009, DB `chat_db` 5439) + WebSocket

Каналы/ЛС + realtime. **Низкий приоритет** (см. критический разбор: embedded approval-карточки нельзя оставлять кликабельными без реальной интеграции — см. ниже).

### Модели

```
Channel: id, type: GROUP|DM, name: str | null, project_id: uuid | null
ChannelMember: channel_id, employee_id, joined_at, pinned: bool, muted: bool
Message:
  id, channel_id, author_id, text: str | null
  reply_to_id: uuid | null
  forwarded_from_id: uuid | null
  edited: bool = false
  related_approval_type: OVERTIME | ABSENCE | null   # см. ниже про approval-карточки
  related_approval_id: uuid | null
  created_at, updated_at
```

### Эндпоинты

| Method | Path | Описание |
|---|---|---|
| GET | `/chat/channels` | список каналов+ЛС текущего пользователя |
| GET | `/chat/channels/{id}/messages?before=&limit=` | пагинация курсором по времени |
| POST | `/chat/channels/{id}/messages` | `{text, reply_to_id?, related_approval_type?, related_approval_id?}` |
| PATCH | `/chat/messages/{id}` | автор, `{text}` |
| DELETE | `/chat/messages/{id}` | автор |
| POST | `/chat/channels/{id}/pin` \| `/mute` | текущий пользователь |
| WS | `/ws/chat` | события `message`, `typing`, `read` |

### Важно про "встроенные approval-карточки"

Из критического ревью: карточка в чате **не должна** хранить собственный статус (pending/approved/rejected) — только ссылаться на `related_approval_type` + `related_approval_id`, указывающие на настоящую запись в `overtime_approval` (timesheet_service) или `absence` (absence_service). Кнопки «Согласовать/Отклонить» в чате должны **проксировать реальный вызов** `POST /overtime-approvals/{id}/approve` или `POST /absences/{id}/approve`, а не менять локальное состояние сообщения. Если chat_service делается раньше absence_service — кнопки для отпускных карточек нужно скрывать, а не подделывать.

### Разрешения

Нет отдельных кодов, доступ к каналу — по членству (`ChannelMember`).

---

# Открытые вопросы для дизайна (не решать явочным порядком)

1. **CORS перед всем остальным** (см. критический разбор) — `management_service`, `profile_service`, `timesheet_service` не имеют `CORSMiddleware`. Прежде чем фронт сможет вызвать любой из перечисленных выше эндпоинтов (включая уже существующие), нужно добавить CORS во все 4+N сервисов. Это не входит в контракт эндпоинтов, но блокирует его использование.
2. **Outbox pattern** — все новые Kafka-топики выше по умолчанию наследуют текущий паттерн "publish после commit без retry" (см. BACKLOG.md). Для timesheet-approval и absence-approval, от которых зависят уведомления менеджеру, тихая потеря события особенно чувствительна. Решить: внедрять outbox сейчас или сознательно принять риск.
3. **`timesheet.entry_created/updated/deleted`** — новый топик, нужен reporting_service, но должен публиковаться из **уже существующего** timesheet_service. Технически это не "новый сервис", а долг в текущем.
4. **Project.budget_hours vs деньги** — уточнено по скриншоту, что колонка «бюджет» на фронте в часах, не в валюте. Если продукту в будущем нужен денежный бюджет — потребуется отдельное поле, не переиспользовать `budget_hours`.
5. **Статус проекта «Под риском»** — вычисляемый (дедлайн + отставание) или отдельное поле в `ProjectStatus`? Контракт выше **не** добавляет его в enum — решение за продуктовой стороной.
6. **Object storage для документов** — MinIO/S3-совместимое хранилище отсутствует в `docker-compose.yml`, нужно завести отдельно перед реализацией B.3.
7. **WebSocket-инфраструктура** (B.4, B.5) — ни один текущий сервис не поднимает WS/ASGI-каналы; на первой итерации можно заменить поллингом (`GET /notifications/?unread_only=true` раз в 15-30 сек) и отложить WS до появления реального чата.
8. **Reject-комментарий строже существующего прецедента.** Проверено в коде: `overtime_approval_service.py::reject()` принимает `comment: str | None` **без какой-либо валидации** — комментарий необязателен и на роутере, и в сервисе, несмотря на то что фронт в диалоге отклонения всегда его запрашивает. Новые `TimesheetPeriodReject`/`AbsenceReject` в этом контракте делают `comment` обязательным осознанно (это правильнее), а не по аналогии с существующим кодом. Стоит решить отдельно: приводить ли заодно существующий overtime reject к тому же обязательному виду, или оставить расхождение.
9. **`Absence.days_count` зависит от production calendar из timesheet_service** — не решено, реплицировать календарь в absence_service через Kafka (ещё один consumer той же сущности) или дергать timesheet_service синхронно. Заявлено как «считается на бэке» без выбора механизма.
10. **Reporting через Kafka-реплику `TimeEntry` vs синхронный агрегирующий вызов в timesheet_service** — контракт выше предполагает первое без обсуждения цены: реплика time-entry-level данных потенциально на порядок больше по объёму трафика, чем весь остальной Kafka-трафик системы (записи создаются ежедневно каждым сотрудником). Синхронный вызов дешевле по хранению, но создаёт runtime-зависимость reporting_service → timesheet_service. Не решено, какой вариант брать.
11. **Presigned URL для файлов документов (B.3) не выбран явно** — presigned URL живёт ограниченное время независимо от прав пользователя на момент открытия (файл можно переслать в этом окне); альтернатива — проксирование через сам document_service с проверкой прав на каждый запрос (медленнее, но без этой дыры). Контракт оставляет оба варианта как «или».
12. **Публичный `POST /auth/password/reset-requests` не защищён от спама заявок**, кроме rate-limit по IP — бот с ротацией IP/identifier может засыпать очередь менеджера заявками, что теперь особенно заметно, раз уведомления не должны оставаться полностью замоканными (см. приоритизацию). Нужна доп. защита (капча/лимит по identifier, не только по IP) — не специфицирована.
13. **Нет сводной таблицы роль → новые permission-коды.** Новые коды (`timesheet:approve_period(_team)`, `absence:read_any/read_team/approve/approve_team`, `report:read/manage`, `document:read_any/manage_templates`) размечены точечно в скобках по ходу текста, а не сведены в одну таблицу по аналогии с `SEED_ROLE_PERMISSIONS` в `auth_service/src/seed.py` — при реализации распределение по 5 ролям (Сотрудник/Тимлид/Менеджер/HR/Администратор) придётся угадывать, а не читать из контракта.
