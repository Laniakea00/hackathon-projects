# 🚀 SmartBot Backend - Быстрый старт

## Вариант 1: Docker (Рекомендуется) ⭐

```bash
# 1. Запустить все сервисы
docker-compose up -d

# 2. Применить миграции
docker-compose exec app alembic upgrade head

# 3. (Опционально) Создать тестовые данные
docker-compose exec app python scripts/create_test_data.py

# 4. Открыть документацию API
# http://localhost:8000/docs
```

**Готово! API работает на http://localhost:8000** ✅

---

## Вариант 2: Локальная установка

### Windows:

```bash
# 1. Запустить PostgreSQL и Redis (через Docker или локально)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

# 2. Установить зависимости и запустить
run.bat
```

### Linux/Mac:

```bash
# 1. Запустить PostgreSQL и Redis
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

# 2. Установить зависимости и запустить
chmod +x run.sh
./run.sh
```

### Или с Makefile:

```bash
# Установить зависимости
make install

# Применить миграции
make migrate

# Запустить сервер
make run
```

---

## 🧪 Быстрый тест

### 1. Зарегистрировать работодателя:

```bash
curl -X POST http://localhost:8000/employers/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "email": "test@test.com",
    "password": "test123"
  }'
```

Сохраните `access_token` из ответа.

### 2. Создать вакансию:

```bash
curl -X POST http://localhost:8000/vacancies \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Developer",
    "description": "Looking for Python dev",
    "location": "Moscow",
    "salary_min": 100000,
    "salary_max": 200000
  }'
```

### 3. Открыть документацию:

http://localhost:8000/docs

---

## 📚 Полезные ссылки

- **API документация:** http://localhost:8000/docs
- **Примеры API:** См. `API_EXAMPLES.md`
- **Полная документация:** См. `README.md`

---

## 🛠 Команды разработки

```bash
# Docker
docker-compose up -d          # Запустить
docker-compose down           # Остановить
docker-compose logs -f app    # Логи

# Миграции
alembic upgrade head          # Применить
alembic revision --autogenerate -m "msg"  # Создать

# Тестовые данные
python scripts/create_test_data.py
```

---

## ⚡ Проблемы?

### Порт 8000 занят:
```bash
# Измените порт в docker-compose.yml или при запуске
uvicorn app.main:app --port 8001
```

### База данных не подключается:
```bash
# Проверьте, что PostgreSQL запущен
docker-compose ps
```

### Ошибка миграций:
```bash
# Пересоздайте БД
docker-compose down -v
docker-compose up -d
docker-compose exec app alembic upgrade head
```

---

**Готово! Начинайте разработку! 🎉**

