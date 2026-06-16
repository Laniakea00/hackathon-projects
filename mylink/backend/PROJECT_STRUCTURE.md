# 📁 SmartBot Backend - Структура проекта

## Обзор архитектуры

```
smartbot-backend/
│
├── 📄 Конфигурация и документация
│   ├── .env.example              # Пример переменных окружения
│   ├── .gitignore                # Git ignore правила
│   ├── .dockerignore             # Docker ignore правила
│   ├── requirements.txt          # Python зависимости
│   ├── alembic.ini               # Конфигурация Alembic
│   ├── Dockerfile                # Docker образ приложения
│   ├── docker-compose.yml        # Docker Compose конфигурация
│   ├── Makefile                  # Команды для разработки
│   ├── README.md                 # Основная документация
│   ├── QUICKSTART.md             # Быстрый старт
│   ├── API_EXAMPLES.md           # Примеры использования API
│   ├── PROJECT_STRUCTURE.md      # Этот файл
│   ├── run.sh                    # Скрипт запуска (Linux/Mac)
│   └── run.bat                   # Скрипт запуска (Windows)
│
├── 🗄️ Миграции базы данных
│   └── alembic/
│       ├── env.py                # Конфигурация окружения Alembic
│       ├── script.py.mako        # Шаблон миграций
│       ├── README                # Описание
│       └── versions/             # Файлы миграций
│
├── 🛠️ Утилиты и скрипты
│   └── scripts/
│       ├── init_db.py            # Инициализация БД
│       └── create_test_data.py   # Создание тестовых данных
│
└── 📦 Основное приложение
    └── app/
        ├── main.py               # Точка входа FastAPI
        ├── config.py             # Настройки приложения
        │
        ├── 🌐 API endpoints
        │   └── api/
        │       ├── auth.py       # Аутентификация (login)
        │       ├── employers.py  # Работодатели (register, me)
        │       ├── vacancies.py  # Вакансии (CRUD)
        │       ├── candidates.py # Кандидаты (CRUD)
        │       ├── responses.py  # Отклики (CRUD)
        │       └── chat.py       # WebSocket чат
        │
        ├── 🗃️ Модели данных
        │   └── models/
        │       ├── employer.py   # Модель работодателя
        │       ├── vacancy.py    # Модель вакансии
        │       ├── candidate.py  # Модель кандидата
        │       ├── response.py   # Модель отклика
        │       └── chat.py       # Модели чата (Session, Message)
        │
        ├── 📋 Pydantic схемы
        │   └── schemas/
        │       ├── auth.py       # Схемы токенов
        │       ├── employer.py   # Схемы работодателя
        │       ├── vacancy.py    # Схемы вакансии
        │       ├── candidate.py  # Схемы кандидата
        │       ├── response.py   # Схемы отклика
        │       └── chat.py       # Схемы чата
        │
        ├── 🧠 Бизнес-логика
        │   └── services/
        │       ├── chat_service.py      # Логика чата
        │       └── relevance_service.py # Расчет релевантности
        │
        ├── 🔌 База данных
        │   └── db/
        │       ├── base.py       # Base класс SQLAlchemy
        │       ├── session.py    # Async сессии
        │       └── redis.py      # Redis подключение
        │
        └── 🔧 Утилиты
            └── utils/
                └── auth.py       # JWT, bcrypt, dependencies
```

---

## 🔍 Детальное описание компонентов

### 1. Точка входа (`app/main.py`)

- Создание FastAPI приложения
- Настройка CORS middleware
- Подключение роутеров
- Lifespan события (startup/shutdown)
- Health check endpoints

### 2. Конфигурация (`app/config.py`)

- Pydantic Settings для переменных окружения
- DATABASE_URL, REDIS_URL
- JWT настройки (SECRET_KEY, ALGORITHM)
- CORS origins
- Debug режим

### 3. API Endpoints (`app/api/`)

#### `auth.py`
- `POST /auth/login` - Вход работодателя

#### `employers.py`
- `POST /employers/register` - Регистрация работодателя
- `GET /employers/me` - Информация о текущем работодателе

#### `vacancies.py`
- `POST /vacancies` - Создать вакансию
- `GET /vacancies` - Список вакансий
- `GET /vacancies/{id}` - Получить вакансию
- `PUT /vacancies/{id}` - Обновить вакансию
- `DELETE /vacancies/{id}` - Удалить вакансию

#### `candidates.py`
- `POST /candidates` - Создать кандидата
- `GET /candidates` - Список кандидатов
- `GET /candidates/{id}` - Получить кандидата

#### `responses.py`
- `POST /responses` - Создать отклик
- `GET /responses` - Список откликов (с фильтром по vacancy_id)
- `GET /responses/{id}` - Получить отклик

#### `chat.py`
- `WS /ws/chat/{response_id}` - WebSocket чат с ботом

### 4. Модели данных (`app/models/`)

#### `employer.py` - Employer
```python
- id: UUID
- company_name: str
- email: str (unique)
- password_hash: str
- created_at: datetime
- updated_at: datetime
- vacancies: relationship
```

#### `vacancy.py` - Vacancy
```python
- id: UUID
- employer_id: UUID (FK)
- title: str
- description: text
- requirements: JSON
- location: str
- salary_min: int
- salary_max: int
- created_at: datetime
- employer: relationship
- responses: relationship
```

#### `candidate.py` - Candidate
```python
- id: UUID
- full_name: str
- email: str
- phone: str
- city: str
- resume_text: text
- created_at: datetime
- responses: relationship
```

#### `response.py` - CandidateResponse
```python
- id: UUID
- vacancy_id: UUID (FK)
- candidate_id: UUID (FK)
- status: enum (new, in_chat, approved, rejected)
- relevance_score: float
- rejection_reasons: JSON
- created_at: datetime
- vacancy: relationship
- candidate: relationship
- chat_session: relationship
```

#### `chat.py` - ChatSession, ChatMessage
```python
ChatSession:
- id: UUID
- response_id: UUID (FK, unique)
- started_at: datetime
- ended_at: datetime | null
- response: relationship
- messages: relationship

ChatMessage:
- id: UUID
- session_id: UUID (FK)
- sender_type: enum (bot, candidate)
- message_text: text
- created_at: datetime
- session: relationship
```

### 5. Схемы (`app/schemas/`)

Pydantic модели для валидации запросов и ответов:
- `*Create` - для создания (POST)
- `*Response` - для ответов (GET)
- `*Update` - для обновления (PUT)

### 6. Сервисы (`app/services/`)

#### `chat_service.py` - ChatService
- `create_session()` - Создать чат сессию
- `add_message()` - Добавить сообщение
- `get_session_messages()` - Получить историю
- `end_session()` - Завершить сессию
- `get_bot_questions()` - Получить вопросы бота
- `process_candidate_answer()` - Обработать ответ (mock логика)
- `finalize_response()` - Финализировать отклик

#### `relevance_service.py` - RelevanceService
- `calculate_relevance()` - Расчет релевантности (mock)

### 7. База данных (`app/db/`)

#### `base.py`
- SQLAlchemy Base класс

#### `session.py`
- Async engine
- AsyncSessionLocal
- `get_db()` dependency

#### `redis.py`
- Redis клиент
- `get_redis()` функция
- `close_redis()` функция

### 8. Утилиты (`app/utils/`)

#### `auth.py`
- `verify_password()` - Проверка пароля
- `get_password_hash()` - Хеширование пароля
- `create_access_token()` - Создание JWT
- `get_current_employer()` - Dependency для получения текущего работодателя

---

## 🔄 Поток данных

### 1. Регистрация и создание вакансии
```
Client → POST /employers/register
       → Employer создан
       → JWT токен возвращен
       
Client → POST /vacancies (с JWT)
       → Vacancy создана
```

### 2. Отклик и чат
```
Client → POST /candidates
       → Candidate создан
       
Client → POST /responses
       → CandidateResponse создан (status: new)
       
Client → WS /ws/chat/{response_id}
       → ChatSession создан
       → Status → in_chat
       → Бот задает вопросы
       → Кандидат отвечает
       → ChatMessage сохраняются
       → Логика оценки (mock)
       → Status → approved/rejected
       → relevance_score установлен
       → ChatSession завершен
```

### 3. Просмотр откликов
```
Employer → GET /responses?vacancy_id=...
         → Список откликов с candidate info
         → relevance_score, status
```

---

## 🔐 Безопасность

### Аутентификация
- JWT токены (HS256)
- Bearer схема
- Пароли хешируются с bcrypt

### Авторизация
- Работодатель может управлять только своими вакансиями
- Dependency `get_current_employer` проверяет JWT

### База данных
- Async SQLAlchemy предотвращает SQL injection
- Cascading deletes настроены
- Foreign key constraints

---

## 🚀 Масштабирование

### Текущая архитектура поддерживает:
1. **Горизонтальное масштабирование** - несколько инстансов приложения
2. **Redis для кэширования** - готово к использованию
3. **Async операции** - высокая производительность
4. **WebSocket** - real-time коммуникация

### Для production:
1. Добавить Nginx как reverse proxy
2. Использовать Gunicorn с Uvicorn workers
3. Настроить Redis для session storage
4. Добавить мониторинг (Prometheus, Grafana)
5. Настроить rate limiting
6. Добавить логирование в ELK/Loki

---

## 🧪 Тестирование

### Структура для тестов (добавить):
```
tests/
├── conftest.py           # Fixtures
├── test_auth.py          # Тесты аутентификации
├── test_vacancies.py     # Тесты вакансий
├── test_candidates.py    # Тесты кандидатов
├── test_responses.py     # Тесты откликов
└── test_chat.py          # Тесты WebSocket
```

### Запуск тестов:
```bash
pytest
pytest --cov=app tests/
```

---

## 📊 Мониторинг и логирование

### Текущее логирование:
- Консольный вывод (stdout)
- Уровень: INFO (DEBUG в dev режиме)

### Рекомендации для production:
1. Структурированное логирование (JSON)
2. Centralized logging (ELK, Loki)
3. Metrics (Prometheus)
4. Tracing (Jaeger, Zipkin)
5. Error tracking (Sentry)

---

## 🔧 Разработка

### Добавление нового endpoint:

1. Создать схему в `app/schemas/`
2. Создать endpoint в `app/api/`
3. Добавить роутер в `app/main.py`
4. (Опционально) Добавить сервис в `app/services/`

### Добавление новой модели:

1. Создать модель в `app/models/`
2. Импортировать в `app/models/__init__.py`
3. Создать миграцию: `alembic revision --autogenerate -m "Add model"`
4. Применить: `alembic upgrade head`

---

**Структура готова к разработке и расширению! 🎉**

