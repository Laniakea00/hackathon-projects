Render deployment (Backend)

Environment variables:
- DATABASE_URL: e.g. postgresql+asyncpg://user:pass@host:5432/db
- DATABASE_URL_SYNC: e.g. postgresql://user:pass@host:5432/db
- REDIS_URL: e.g. rediss://:pass@host:6379/0
- SECRET_KEY: random string
- ALLOWED_ORIGINS: https://your-frontend.onrender.com
- OPENAI_API_KEY: your key
- OPENAI_MODEL: gpt-4.1

Build command:
- pip install -r requirements.txt

Start command:
- uvicorn app.main:app --host 0.0.0.0 --port $PORT

# SmartBot HR Platform - Backend

Полнофункциональный backend для MVP платформы HR-чатбота с автоматическим скринингом кандидатов.

## 🚀 Возможности

- ✅ Регистрация и аутентификация работодателей (JWT)
- ✅ CRUD операции для вакансий
- ✅ Создание профилей кандидатов
- ✅ Система откликов на вакансии
- ✅ WebSocket чат с ботом для собеседования
- ✅ Автоматическая оценка релевантности кандидатов
- ✅ Асинхронная архитектура (FastAPI + SQLAlchemy async)
- ✅ PostgreSQL + Redis
- ✅ Docker-ready

## 🛠 Технологический стек

- **Python 3.11+**
- **FastAPI** - современный веб-фреймворк
- **SQLAlchemy 2.0** - ORM с async поддержкой
- **Alembic** - миграции базы данных
- **PostgreSQL** - основная БД
- **Redis** - кэширование и сессии
- **JWT** - аутентификация
- **WebSockets** - real-time чат
- **Docker & Docker Compose** - контейнеризация

## 📂 Структура проекта

```
smartbot-backend/
├── app/
│   ├── api/                 # API endpoints
│   │   ├── auth.py         # Аутентификация
│   │   ├── employers.py    # Работодатели
│   │   ├── vacancies.py    # Вакансии
│   │   ├── candidates.py   # Кандидаты
│   │   ├── responses.py    # Отклики
│   │   └── chat.py         # WebSocket чат
│   ├── models/             # SQLAlchemy модели
│   ├── schemas/            # Pydantic схемы
│   ├── services/           # Бизнес-логика
│   ├── db/                 # База данных
│   ├── utils/              # Утилиты (auth, etc)
│   ├── config.py           # Конфигурация
│   └── main.py             # FastAPI приложение
├── alembic/                # Миграции
├── requirements.txt        # Зависимости
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🗄 Модель данных

### Основные сущности:

1. **Employer** - работодатель
2. **Vacancy** - вакансия
3. **Candidate** - кандидат
4. **CandidateResponse** - отклик кандидата
5. **ChatSession** - сессия чата
6. **ChatMessage** - сообщение в чате

### Связи:
- Employer → Vacancy (1:N)
- Vacancy → CandidateResponse (1:N)
- Candidate → CandidateResponse (1:N)
- CandidateResponse → ChatSession (1:1)
- ChatSession → ChatMessage (1:N)

## 🚀 Быстрый старт

### Вариант 1: Docker Compose (рекомендуется)

1. **Клонируйте репозиторий:**
```bash
cd smartbot-backend
```

2. **Создайте .env файл:**
```bash
cp .env.example .env
```

3. **Запустите сервисы:**
```bash
docker-compose up -d
```

4. **Выполните миграции:**
```bash
docker-compose exec app alembic upgrade head
```

5. **API доступен по адресу:**
- http://localhost:8000
- Документация: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Вариант 2: Локальная установка

1. **Установите зависимости:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Настройте PostgreSQL и Redis:**
```bash
# Установите PostgreSQL и Redis локально
# Или используйте Docker:
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine
```

3. **Создайте .env файл:**
```bash
cp .env.example .env
# Отредактируйте .env с вашими настройками
```

4. **Создайте базу данных:**
```bash
createdb smartbot_db
```

5. **Выполните миграции:**
```bash
alembic upgrade head
```

6. **Запустите сервер:**
```bash
uvicorn app.main:app --reload
```

## 📡 API Endpoints

### Аутентификация

```http
POST /employers/register
POST /auth/login
```

### Вакансии

```http
POST   /vacancies              # Создать вакансию (требует JWT)
GET    /vacancies              # Список вакансий
GET    /vacancies/{id}         # Получить вакансию
PUT    /vacancies/{id}         # Обновить вакансию (требует JWT)
DELETE /vacancies/{id}         # Удалить вакансию (требует JWT)
```

### Кандидаты

```http
POST /candidates               # Создать профиль кандидата
GET  /candidates               # Список кандидатов
GET  /candidates/{id}          # Получить кандидата
```

### Отклики

```http
POST /responses                # Создать отклик
GET  /responses                # Список откликов (требует JWT)
GET  /responses/{id}           # Получить отклик
```

### WebSocket чат

```
WS /ws/chat/{response_id}      # Подключиться к чату
```

## 🔐 Аутентификация

API использует JWT токены для аутентификации работодателей.

### Пример регистрации:

```bash
curl -X POST http://localhost:8000/employers/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Tech Corp",
    "email": "hr@techcorp.com",
    "password": "securepass123"
  }'
```

Ответ:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Использование токена:

```bash
curl -X POST http://localhost:8000/vacancies \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Developer",
    "description": "We are looking for...",
    "location": "Moscow",
    "salary_min": 100000,
    "salary_max": 200000
  }'
```

## 💬 WebSocket чат - пример использования

### JavaScript клиент:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/RESPONSE_ID');

ws.onopen = () => {
  console.log('Connected to chat');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'bot_message') {
    console.log('Bot:', data.message);
  } else if (data.type === 'chat_ended') {
    console.log('Chat ended. Approved:', data.approved);
  }
};

// Отправить сообщение
ws.send(JSON.stringify({
  message: 'Москва'
}));
```

## 🧪 Тестирование

### Создание тестового работодателя и вакансии:

```bash
# 1. Регистрация работодателя
curl -X POST http://localhost:8000/employers/register \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Test Corp", "email": "test@test.com", "password": "test123"}'

# Сохраните токен из ответа

# 2. Создание вакансии
curl -X POST http://localhost:8000/vacancies \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Backend Developer",
    "description": "Python/FastAPI developer needed",
    "location": "Moscow",
    "salary_min": 150000,
    "salary_max": 250000
  }'

# 3. Создание кандидата
curl -X POST http://localhost:8000/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ivan Ivanov",
    "email": "ivan@example.com",
    "phone": "+79991234567",
    "city": "Moscow",
    "resume_text": "Experienced Python developer..."
  }'

# 4. Создание отклика
curl -X POST http://localhost:8000/responses \
  -H "Content-Type: application/json" \
  -d '{
    "vacancy_id": "VACANCY_UUID",
    "candidate_id": "CANDIDATE_UUID"
  }'

# 5. Подключиться к WebSocket чату с response_id
```

## 🔧 Миграции базы данных

### Создать новую миграцию:

```bash
alembic revision --autogenerate -m "Description"
```

### Применить миграции:

```bash
alembic upgrade head
```

### Откатить миграцию:

```bash
alembic downgrade -1
```

## 🐳 Docker команды

```bash
# Запустить все сервисы
docker-compose up -d

# Остановить сервисы
docker-compose down

# Просмотр логов
docker-compose logs -f app

# Перезапустить приложение
docker-compose restart app

# Выполнить команду внутри контейнера
docker-compose exec app bash

# Пересобрать образ
docker-compose build --no-cache
```

## 📊 Мониторинг

### Health check:

```bash
curl http://localhost:8000/health
```

### Логи:

```bash
# Docker
docker-compose logs -f app

# Локально
# Логи выводятся в консоль
```

## 🧠 Логика чат-бота (Mock для MVP)

Текущая реализация использует простую mock-логику:

1. Бот задает 3 вопроса:
   - Город проживания
   - Опыт работы
   - Готовность к удаленной работе

2. Проверка релевантности:
   - Если город кандидата ≠ город вакансии → отклонение
   - Если все вопросы пройдены → одобрение

3. После завершения чата:
   - Статус отклика обновляется
   - Рассчитывается `relevance_score` (0.0 или 1.0)
   - Сохраняются причины отклонения (если есть)

**Для production:** Замените mock-логику на интеграцию с LLM (OpenAI, Anthropic, etc.)

## 🔒 Безопасность

- ✅ Пароли хешируются с bcrypt
- ✅ JWT токены с истечением срока действия
- ✅ CORS настроен для фронтенда
- ✅ SQL injection защита через SQLAlchemy
- ⚠️ Для production: используйте HTTPS
- ⚠️ Для production: измените SECRET_KEY в .env

## 🌐 CORS настройка

По умолчанию разрешены запросы с:
- http://localhost:3000 (React)
- http://localhost:5173 (Vite)

Измените в `.env`:
```
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

## 📈 Масштабирование

Для production рекомендуется:

1. **Использовать Gunicorn + Uvicorn workers:**
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

2. **Настроить Redis для кэширования**
3. **Использовать Nginx как reverse proxy**
4. **Настроить мониторинг (Prometheus, Grafana)**
5. **Добавить rate limiting**

## 🐛 Troubleshooting

### Проблема: "Connection refused" при подключении к БД

```bash
# Проверьте, что PostgreSQL запущен
docker-compose ps

# Проверьте логи
docker-compose logs db
```

### Проблема: Миграции не применяются

```bash
# Убедитесь, что БД создана
docker-compose exec db psql -U postgres -c "CREATE DATABASE smartbot_db;"

# Выполните миграции вручную
docker-compose exec app alembic upgrade head
```

### Проблема: WebSocket не подключается

- Проверьте, что используете `ws://` (не `wss://` для локальной разработки)
- Убедитесь, что response_id существует в БД

## 📝 Лицензия

MIT License

## 👥 Контакты

Для вопросов и предложений создайте issue в репозитории.

---

**Готово к разработке! 🚀**

