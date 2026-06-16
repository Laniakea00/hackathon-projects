# 🏗️ SmartBot Backend - Архитектура системы

## 📐 Общая архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Browser    │  │  Mobile App  │  │   Frontend   │          │
│  │  (WebSocket) │  │   (HTTP)     │  │    (React)   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          │ WebSocket        │ HTTP/REST        │ HTTP/REST
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼─────────────────┐
│                      FASTAPI APPLICATION                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    API LAYER (Routers)                     │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ │ │
│  │  │ Auth │ │Employ│ │Vacan │ │Candid│ │Respon│ │  Chat  │ │ │
│  │  │      │ │ ers  │ │ cies │ │ ates │ │ ses  │ │   WS   │ │ │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └───┬────┘ │ │
│  └─────┼────────┼────────┼────────┼────────┼─────────┼──────┘ │
│        │        │        │        │        │         │         │
│  ┌─────▼────────▼────────▼────────▼────────▼─────────▼──────┐ │
│  │                   BUSINESS LOGIC LAYER                    │ │
│  │  ┌─────────────────┐        ┌────────────────────┐       │ │
│  │  │  Chat Service   │        │ Relevance Service  │       │ │
│  │  │  - Questions    │        │ - Score calculation│       │ │
│  │  │  - Answers      │        │ - Mock logic       │       │ │
│  │  │  - Sessions     │        │                    │       │ │
│  │  └─────────────────┘        └────────────────────┘       │ │
│  └───────────────────────────────────────────────────────────┘ │
│        │                                              │         │
│  ┌─────▼──────────────────────────────────────────────▼──────┐ │
│  │                   DATA ACCESS LAYER                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │  SQLAlchemy  │  │   Pydantic   │  │    Redis     │   │ │
│  │  │   (Async)    │  │   Schemas    │  │   Client     │   │ │
│  │  └──────┬───────┘  └──────────────┘  └──────┬───────┘   │ │
│  └─────────┼─────────────────────────────────────┼──────────┘ │
└────────────┼─────────────────────────────────────┼────────────┘
             │                                     │
┌────────────▼─────────────────────────────────────▼────────────┐
│                     PERSISTENCE LAYER                          │
│  ┌──────────────────────────┐    ┌─────────────────────────┐ │
│  │      PostgreSQL          │    │        Redis            │ │
│  │  ┌────────────────────┐  │    │  ┌──────────────────┐  │ │
│  │  │ • employers        │  │    │  │ • sessions       │  │ │
│  │  │ • vacancies        │  │    │  │ • cache          │  │ │
│  │  │ • candidates       │  │    │  │ • websocket data │  │ │
│  │  │ • responses        │  │    │  └──────────────────┘  │ │
│  │  │ • chat_sessions    │  │    └─────────────────────────┘ │
│  │  │ • chat_messages    │  │                                │
│  │  └────────────────────┘  │                                │
│  └──────────────────────────┘                                │
└───────────────────────────────────────────────────────────────┘
```

---

## 🔄 Поток данных

### 1. Аутентификация работодателя

```
┌─────────┐                  ┌─────────┐                  ┌──────────┐
│ Client  │                  │   API   │                  │    DB    │
└────┬────┘                  └────┬────┘                  └────┬─────┘
     │                            │                            │
     │ POST /employers/register   │                            │
     ├───────────────────────────>│                            │
     │                            │ Hash password              │
     │                            │ Create Employer            │
     │                            ├───────────────────────────>│
     │                            │                            │
     │                            │<───────────────────────────┤
     │                            │ Generate JWT               │
     │<───────────────────────────┤                            │
     │ {access_token}             │                            │
     │                            │                            │
```

### 2. Создание вакансии

```
┌─────────┐                  ┌─────────┐                  ┌──────────┐
│ Client  │                  │   API   │                  │    DB    │
└────┬────┘                  └────┬────┘                  └────┬─────┘
     │                            │                            │
     │ POST /vacancies            │                            │
     │ Authorization: Bearer JWT  │                            │
     ├───────────────────────────>│                            │
     │                            │ Verify JWT                 │
     │                            │ Get employer_id            │
     │                            │                            │
     │                            │ Create Vacancy             │
     │                            ├───────────────────────────>│
     │                            │                            │
     │                            │<───────────────────────────┤
     │<───────────────────────────┤                            │
     │ {vacancy}                  │                            │
     │                            │                            │
```

### 3. Отклик и чат (WebSocket)

```
┌──────────┐     ┌─────────┐     ┌────────────┐     ┌──────┐
│Candidate │     │   API   │     │   Service  │     │  DB  │
└────┬─────┘     └────┬────┘     └─────┬──────┘     └──┬───┘
     │                │                 │                │
     │ POST /responses│                 │                │
     ├───────────────>│                 │                │
     │                │ Create Response │                │
     │                ├─────────────────┼───────────────>│
     │                │                 │                │
     │<───────────────┤                 │                │
     │ {response_id}  │                 │                │
     │                │                 │                │
     │ WS /ws/chat/   │                 │                │
     │   {response_id}│                 │                │
     ├───────────────>│                 │                │
     │                │ Create Session  │                │
     │                ├────────────────>│                │
     │                │                 │ Save Session   │
     │                │                 ├───────────────>│
     │                │                 │                │
     │<───────────────┤                 │                │
     │ Bot: Question 1│                 │                │
     │                │                 │                │
     │ Answer: "Moscow"                 │                │
     ├───────────────>│                 │                │
     │                │ Process Answer  │                │
     │                ├────────────────>│                │
     │                │                 │ Check logic    │
     │                │                 │ Save message   │
     │                │                 ├───────────────>│
     │                │                 │                │
     │<───────────────┤                 │                │
     │ Bot: Question 2│                 │                │
     │                │                 │                │
     │ ... (repeat)   │                 │                │
     │                │                 │                │
     │<───────────────┤                 │                │
     │ Chat ended     │                 │                │
     │ Approved: true │                 │                │
     │                │                 │ Update status  │
     │                │                 │ Set score      │
     │                │                 ├───────────────>│
     │                │                 │                │
```

### 4. Просмотр откликов работодателем

```
┌──────────┐                  ┌─────────┐                  ┌──────────┐
│Employer  │                  │   API   │                  │    DB    │
└────┬─────┘                  └────┬────┘                  └────┬─────┘
     │                            │                            │
     │ GET /responses             │                            │
     │ ?vacancy_id=...            │                            │
     │ Authorization: Bearer JWT  │                            │
     ├───────────────────────────>│                            │
     │                            │ Verify JWT                 │
     │                            │ Check ownership            │
     │                            │                            │
     │                            │ Query responses            │
     │                            │ JOIN candidates            │
     │                            ├───────────────────────────>│
     │                            │                            │
     │                            │<───────────────────────────┤
     │<───────────────────────────┤                            │
     │ [{response, candidate}]    │                            │
     │                            │                            │
```

---

## 🗄️ Модель данных (ER диаграмма)

```
┌─────────────────────┐
│     Employer        │
├─────────────────────┤
│ id (PK)             │
│ company_name        │
│ email (unique)      │
│ password_hash       │
│ created_at          │
│ updated_at          │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────┐
│      Vacancy        │
├─────────────────────┤
│ id (PK)             │
│ employer_id (FK)    │
│ title               │
│ description         │
│ requirements (JSON) │
│ location            │
│ salary_min          │
│ salary_max          │
│ created_at          │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────────────┐         ┌─────────────────────┐
│   CandidateResponse         │         │     Candidate       │
├─────────────────────────────┤         ├─────────────────────┤
│ id (PK)                     │   N:1   │ id (PK)             │
│ vacancy_id (FK)             │◄────────┤ full_name           │
│ candidate_id (FK)           │         │ email               │
│ status (enum)               │         │ phone               │
│ relevance_score             │         │ city                │
│ rejection_reasons (JSON)    │         │ resume_text         │
│ created_at                  │         │ created_at          │
└──────────┬──────────────────┘         └─────────────────────┘
           │
           │ 1:1
           │
┌──────────▼──────────┐
│    ChatSession      │
├─────────────────────┤
│ id (PK)             │
│ response_id (FK)    │
│ started_at          │
│ ended_at            │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────┐
│    ChatMessage      │
├─────────────────────┤
│ id (PK)             │
│ session_id (FK)     │
│ sender_type (enum)  │
│ message_text        │
│ created_at          │
└─────────────────────┘
```

---

## 🔐 Безопасность

### Аутентификация

```
┌─────────────────────────────────────────────────────────┐
│                  JWT Authentication                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. User registers/logs in                              │
│     ↓                                                    │
│  2. Password hashed with bcrypt                         │
│     ↓                                                    │
│  3. JWT token created (HS256)                           │
│     Payload: {sub: user_id, email: email, exp: ...}    │
│     ↓                                                    │
│  4. Token returned to client                            │
│     ↓                                                    │
│  5. Client includes in Authorization header             │
│     Authorization: Bearer <token>                       │
│     ↓                                                    │
│  6. Server verifies token signature                     │
│     ↓                                                    │
│  7. Extract user_id from payload                        │
│     ↓                                                    │
│  8. Fetch user from database                            │
│     ↓                                                    │
│  9. Inject user into endpoint dependency                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Авторизация

```
Endpoint: DELETE /vacancies/{vacancy_id}

┌──────────────────────────────────────┐
│ 1. Verify JWT token                  │
│    ↓                                  │
│ 2. Get current_employer from token   │
│    ↓                                  │
│ 3. Fetch vacancy from DB             │
│    ↓                                  │
│ 4. Check: vacancy.employer_id ==     │
│           current_employer.id        │
│    ↓                                  │
│ 5. If match: allow deletion          │
│    If not: return 404 Not Found      │
└──────────────────────────────────────┘
```

---

## 🚀 Масштабирование

### Горизонтальное масштабирование

```
                    ┌──────────────┐
                    │ Load Balancer│
                    │   (Nginx)    │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌─────▼────┐      ┌─────▼────┐
   │  App 1  │       │  App 2   │      │  App 3   │
   │ (FastAPI│       │ (FastAPI)│      │ (FastAPI)│
   └────┬────┘       └─────┬────┘      └─────┬────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌─────▼────┐      ┌─────▼────┐
   │PostgreSQL│      │  Redis   │      │  Redis   │
   │ (Primary)│      │ (Master) │      │ (Replica)│
   └─────────┘       └──────────┘      └──────────┘
```

### WebSocket масштабирование

```
Для масштабирования WebSocket:

1. Использовать Redis Pub/Sub для broadcast
2. Sticky sessions на load balancer
3. Или использовать отдельный WebSocket сервер

┌─────────┐     ┌─────────┐     ┌─────────┐
│ Client 1│────>│ App 1   │     │ App 2   │
└─────────┘     └────┬────┘     └────┬────┘
                     │               │
                     └───────┬───────┘
                             │
                      ┌──────▼──────┐
                      │ Redis Pub/Sub│
                      └─────────────┘
```

---

## 📊 Производительность

### Async архитектура

```
Traditional (Sync):
Request 1 ──────────────────> [████████████] (blocking)
Request 2                      ──────────────────> [████████████]
Request 3                                          ──────────────────> [████████████]

Async (FastAPI):
Request 1 ──> [██] (I/O wait) [██] (I/O wait) [██] (done)
Request 2 ────> [██] (I/O wait) [██] (I/O wait) [██] (done)
Request 3 ──────> [██] (I/O wait) [██] (I/O wait) [██] (done)

Result: 3x faster throughput
```

### Database connection pooling

```
┌──────────────────────────────────────┐
│        SQLAlchemy Async Pool         │
├──────────────────────────────────────┤
│  [Conn 1] [Conn 2] [Conn 3] ...     │
│     ▲        ▲        ▲              │
│     │        │        │              │
│  [Req 1]  [Req 2]  [Req 3]          │
└──────────────────────────────────────┘

Benefits:
- Reuse connections
- Limit concurrent connections
- Better performance
```

---

## 🔄 Жизненный цикл запроса

```
1. HTTP Request arrives
   ↓
2. CORS Middleware
   ↓
3. Route matching
   ↓
4. Authentication (if required)
   ├─> Verify JWT
   ├─> Get user from DB
   └─> Inject into endpoint
   ↓
5. Request validation (Pydantic)
   ↓
6. Endpoint handler
   ├─> Business logic
   ├─> Database queries (async)
   └─> Service calls
   ↓
7. Response serialization (Pydantic)
   ↓
8. HTTP Response
```

---

## 🧩 Расширяемость

### Добавление нового функционала

```
Пример: Добавить систему уведомлений

1. Создать модель:
   app/models/notification.py

2. Создать схему:
   app/schemas/notification.py

3. Создать сервис:
   app/services/notification_service.py

4. Создать endpoint:
   app/api/notifications.py

5. Подключить роутер:
   app/main.py

6. Создать миграцию:
   alembic revision --autogenerate

7. Применить:
   alembic upgrade head
```

---

## 📦 Зависимости

```
┌─────────────────────────────────────────┐
│           Application Layer             │
│  ┌───────────────────────────────────┐  │
│  │         FastAPI                   │  │
│  └───────────┬───────────────────────┘  │
│              │                           │
│  ┌───────────▼───────────────────────┐  │
│  │  Pydantic │ SQLAlchemy │ Redis    │  │
│  └───────────┴───────────┴───────────┘  │
│              │                           │
│  ┌───────────▼───────────────────────┐  │
│  │  asyncpg  │  alembic  │  jose     │  │
│  └───────────┴───────────┴───────────┘  │
└─────────────────────────────────────────┘
```

---

**Архитектура готова к масштабированию и расширению! 🚀**

