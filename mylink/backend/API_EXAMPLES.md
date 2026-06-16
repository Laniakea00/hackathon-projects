# SmartBot API - Примеры использования

Полное руководство по использованию API SmartBot HR Platform.

## 📋 Содержание

1. [Аутентификация](#аутентификация)
2. [Работодатели](#работодатели)
3. [Вакансии](#вакансии)
4. [Кандидаты](#кандидаты)
5. [Отклики](#отклики)
6. [WebSocket чат](#websocket-чат)

---

## Аутентификация

### 1. Регистрация работодателя

**Endpoint:** `POST /employers/register`

**Request:**
```bash
curl -X POST http://localhost:8000/employers/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Tech Solutions Inc",
    "email": "hr@techsolutions.com",
    "password": "securePassword123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Вход работодателя

**Endpoint:** `POST /auth/login`

**Request:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "hr@techsolutions.com",
    "password": "securePassword123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**💡 Сохраните токен для дальнейших запросов!**

---

## Работодатели

### 3. Получить информацию о текущем работодателе

**Endpoint:** `GET /employers/me`

**Request:**
```bash
curl -X GET http://localhost:8000/employers/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "company_name": "Tech Solutions Inc",
  "email": "hr@techsolutions.com",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

## Вакансии

### 4. Создать вакансию

**Endpoint:** `POST /vacancies`

**Request:**
```bash
curl -X POST http://localhost:8000/vacancies \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Python Developer",
    "description": "We are looking for an experienced Python developer to join our team. You will work on building scalable backend services using FastAPI and PostgreSQL.",
    "requirements": {
      "experience": "3+ years",
      "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
      "education": "Bachelor degree in Computer Science or related field"
    },
    "location": "Moscow",
    "salary_min": 150000,
    "salary_max": 250000
  }'
```

**Response:**
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "employer_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Senior Python Developer",
  "description": "We are looking for an experienced Python developer...",
  "requirements": {
    "experience": "3+ years",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "education": "Bachelor degree in Computer Science or related field"
  },
  "location": "Moscow",
  "salary_min": 150000,
  "salary_max": 250000,
  "created_at": "2024-01-15T11:00:00Z"
}
```

### 5. Получить список всех вакансий

**Endpoint:** `GET /vacancies`

**Request:**
```bash
curl -X GET http://localhost:8000/vacancies
```

**Response:**
```json
[
  {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "employer_id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Senior Python Developer",
    "description": "We are looking for...",
    "requirements": {...},
    "location": "Moscow",
    "salary_min": 150000,
    "salary_max": 250000,
    "created_at": "2024-01-15T11:00:00Z"
  }
]
```

### 6. Получить вакансию по ID

**Endpoint:** `GET /vacancies/{vacancy_id}`

**Request:**
```bash
curl -X GET http://localhost:8000/vacancies/456e7890-e89b-12d3-a456-426614174001
```

### 7. Обновить вакансию

**Endpoint:** `PUT /vacancies/{vacancy_id}`

**Request:**
```bash
curl -X PUT http://localhost:8000/vacancies/456e7890-e89b-12d3-a456-426614174001 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "salary_min": 180000,
    "salary_max": 280000
  }'
```

### 8. Удалить вакансию

**Endpoint:** `DELETE /vacancies/{vacancy_id}`

**Request:**
```bash
curl -X DELETE http://localhost:8000/vacancies/456e7890-e89b-12d3-a456-426614174001 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Кандидаты

### 9. Создать профиль кандидата

**Endpoint:** `POST /candidates`

**Request:**
```bash
curl -X POST http://localhost:8000/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ivan Petrov",
    "email": "ivan.petrov@example.com",
    "phone": "+79991234567",
    "city": "Moscow",
    "resume_text": "Experienced Python developer with 5 years of experience in building web applications. Proficient in FastAPI, Django, PostgreSQL, and Docker. Strong understanding of software design patterns and best practices."
  }'
```

**Response:**
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174002",
  "full_name": "Ivan Petrov",
  "email": "ivan.petrov@example.com",
  "phone": "+79991234567",
  "city": "Moscow",
  "resume_text": "Experienced Python developer...",
  "created_at": "2024-01-15T12:00:00Z"
}
```

### 10. Получить список кандидатов

**Endpoint:** `GET /candidates`

**Request:**
```bash
curl -X GET http://localhost:8000/candidates
```

### 11. Получить кандидата по ID

**Endpoint:** `GET /candidates/{candidate_id}`

**Request:**
```bash
curl -X GET http://localhost:8000/candidates/789e0123-e89b-12d3-a456-426614174002
```

---

## Отклики

### 12. Создать отклик на вакансию

**Endpoint:** `POST /responses`

**Request:**
```bash
curl -X POST http://localhost:8000/responses \
  -H "Content-Type: application/json" \
  -d '{
    "vacancy_id": "456e7890-e89b-12d3-a456-426614174001",
    "candidate_id": "789e0123-e89b-12d3-a456-426614174002"
  }'
```

**Response:**
```json
{
  "id": "abc12345-e89b-12d3-a456-426614174003",
  "vacancy_id": "456e7890-e89b-12d3-a456-426614174001",
  "candidate_id": "789e0123-e89b-12d3-a456-426614174002",
  "status": "new",
  "relevance_score": null,
  "rejection_reasons": null,
  "created_at": "2024-01-15T13:00:00Z"
}
```

**💡 После создания отклика используйте `response_id` для подключения к WebSocket чату!**

### 13. Получить список откликов (для работодателя)

**Endpoint:** `GET /responses`

**Request:**
```bash
curl -X GET http://localhost:8000/responses \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Response:**
```json
[
  {
    "id": "abc12345-e89b-12d3-a456-426614174003",
    "vacancy_id": "456e7890-e89b-12d3-a456-426614174001",
    "candidate_id": "789e0123-e89b-12d3-a456-426614174002",
    "status": "approved",
    "relevance_score": 1.0,
    "rejection_reasons": null,
    "created_at": "2024-01-15T13:00:00Z",
    "candidate_name": "Ivan Petrov",
    "candidate_email": "ivan.petrov@example.com",
    "candidate_city": "Moscow"
  }
]
```

### 14. Получить отклики по конкретной вакансии

**Endpoint:** `GET /responses?vacancy_id={vacancy_id}`

**Request:**
```bash
curl -X GET "http://localhost:8000/responses?vacancy_id=456e7890-e89b-12d3-a456-426614174001" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 15. Получить отклик по ID

**Endpoint:** `GET /responses/{response_id}`

**Request:**
```bash
curl -X GET http://localhost:8000/responses/abc12345-e89b-12d3-a456-426614174003
```

---

## WebSocket чат

### 16. Подключение к чату

**Endpoint:** `WS /ws/chat/{response_id}`

**JavaScript пример:**

```javascript
// Подключение к WebSocket
const responseId = 'abc12345-e89b-12d3-a456-426614174003';
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${responseId}`);

// Обработка открытия соединения
ws.onopen = () => {
  console.log('✅ Connected to chat');
};

// Обработка входящих сообщений
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'bot_message':
      console.log('🤖 Bot:', data.message);
      console.log('Question index:', data.question_index);
      // Отобразить сообщение бота в UI
      break;
      
    case 'chat_ended':
      console.log('🏁 Chat ended');
      console.log('Approved:', data.approved);
      console.log('Reason:', data.reason);
      // Показать результат
      break;
      
    case 'error':
      console.error('❌ Error:', data.message);
      break;
  }
};

// Обработка ошибок
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

// Обработка закрытия соединения
ws.onclose = () => {
  console.log('Connection closed');
};

// Отправка сообщения
function sendMessage(message) {
  ws.send(JSON.stringify({
    message: message
  }));
}

// Пример использования
setTimeout(() => {
  sendMessage('Moscow'); // Ответ на первый вопрос
}, 2000);

setTimeout(() => {
  sendMessage('5 years'); // Ответ на второй вопрос
}, 5000);

setTimeout(() => {
  sendMessage('Yes'); // Ответ на третий вопрос
}, 8000);
```

**Python пример (с использованием websockets):**

```python
import asyncio
import websockets
import json

async def chat_with_bot():
    response_id = 'abc12345-e89b-12d3-a456-426614174003'
    uri = f"ws://localhost:8000/ws/chat/{response_id}"
    
    async with websockets.connect(uri) as websocket:
        print("✅ Connected to chat")
        
        # Получить первое сообщение от бота
        message = await websocket.recv()
        data = json.loads(message)
        print(f"🤖 Bot: {data['message']}")
        
        # Отправить ответ
        await websocket.send(json.dumps({"message": "Moscow"}))
        
        # Продолжить диалог
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data['type'] == 'bot_message':
                print(f"🤖 Bot: {data['message']}")
                
                # Ответить на вопросы
                if 'опыт' in data['message'].lower():
                    await websocket.send(json.dumps({"message": "5 years"}))
                elif 'удаленн' in data['message'].lower():
                    await websocket.send(json.dumps({"message": "Yes"}))
                    
            elif data['type'] == 'chat_ended':
                print(f"🏁 Chat ended. Approved: {data['approved']}")
                break

asyncio.run(chat_with_bot())
```

### Поток сообщений в чате

1. **Подключение** → Бот отправляет приветствие и первый вопрос
2. **Кандидат отвечает** → Бот анализирует ответ
3. **Бот задает следующий вопрос** или завершает чат
4. **Завершение** → Бот отправляет финальное сообщение и результат

### Типы сообщений от бота

```typescript
// Сообщение от бота
{
  "type": "bot_message",
  "message": "Здравствуйте! Подтвердите, пожалуйста, ваш город проживания?",
  "question_index": 0
}

// Завершение чата
{
  "type": "chat_ended",
  "approved": true,
  "reason": "Все вопросы пройдены"
}

// Ошибка
{
  "type": "error",
  "message": "Response not found"
}
```

---

## 🔄 Полный пример workflow

### Шаг 1: Регистрация работодателя

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/employers/register \
  -H "Content-Type: application/json" \
  -d '{"company_name": "My Company", "email": "hr@company.com", "password": "pass123"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
```

### Шаг 2: Создание вакансии

```bash
VACANCY_ID=$(curl -s -X POST http://localhost:8000/vacancies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Developer",
    "description": "Great opportunity",
    "location": "Moscow",
    "salary_min": 100000,
    "salary_max": 200000
  }' | jq -r '.id')

echo "Vacancy ID: $VACANCY_ID"
```

### Шаг 3: Создание кандидата

```bash
CANDIDATE_ID=$(curl -s -X POST http://localhost:8000/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "city": "Moscow",
    "phone": "+79991234567"
  }' | jq -r '.id')

echo "Candidate ID: $CANDIDATE_ID"
```

### Шаг 4: Создание отклика

```bash
RESPONSE_ID=$(curl -s -X POST http://localhost:8000/responses \
  -H "Content-Type: application/json" \
  -d "{
    \"vacancy_id\": \"$VACANCY_ID\",
    \"candidate_id\": \"$CANDIDATE_ID\"
  }" | jq -r '.id')

echo "Response ID: $RESPONSE_ID"
echo "WebSocket URL: ws://localhost:8000/ws/chat/$RESPONSE_ID"
```

### Шаг 5: Подключение к чату (используйте WebSocket клиент)

### Шаг 6: Просмотр откликов

```bash
curl -X GET "http://localhost:8000/responses?vacancy_id=$VACANCY_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 🧪 Тестирование с Postman

1. Импортируйте коллекцию (создайте новую коллекцию в Postman)
2. Добавьте переменную окружения `base_url` = `http://localhost:8000`
3. Добавьте переменную `token` для хранения JWT
4. Используйте примеры выше для создания запросов

---

## 📊 Статусы откликов

- `new` - Новый отклик, чат не начат
- `in_chat` - Кандидат в процессе чата с ботом
- `approved` - Кандидат одобрен
- `rejected` - Кандидат отклонен

---

## ⚠️ Обработка ошибок

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```
**Решение:** Проверьте JWT токен

### 404 Not Found
```json
{
  "detail": "Vacancy not found"
}
```
**Решение:** Проверьте ID ресурса

### 400 Bad Request
```json
{
  "detail": "Email already registered"
}
```
**Решение:** Используйте другой email или войдите

---

**Готово! Используйте эти примеры для интеграции с фронтендом. 🚀**

