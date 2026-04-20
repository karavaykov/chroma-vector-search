# Chroma Vector Search - Микросервисная архитектура

## Обзор

Это микросервисная реализация Chroma Vector Search, которая заменяет монолитный TCP-сервер на набор специализированных сервисов с REST API.

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway (8000)                   │
│                    FastAPI + Redis                      │
└──────────────┬────────────────┬─────────────────────────┘
               │                │
    ┌──────────▼──────┐  ┌─────▼──────────┐  ┌─────────────┐
    │ Indexing (8001) │  │ Search (8002)  │  │Metadata(8003)│
    │ FastAPI + Chroma│  │ FastAPI + Chroma│  │FastAPI + PG │
    └─────────────────┘  └────────────────┘  └─────────────┘
         │                    │                    │
    ┌────▼──────┐      ┌─────▼──────┐      ┌─────▼──────┐
    │ ChromaDB  │      │   Redis    │      │ PostgreSQL │
    │   (8004)  │      │   (6379)   │      │   (5432)   │
    └───────────┘      └────────────┘      └────────────┘
```

## Сервисы

### 1. API Gateway (порт 8000)
- Единая точка входа для клиентов
- Rate limiting и аутентификация
- Маршрутизация запросов к другим сервисам
- Health checks всех сервисов

### 2. Indexing Service (порт 8001)
- Индексация кодовой базы
- Потоковая обработка файлов
- Генерация эмбеддингов
- Управление задачами индексации

### 3. Search Service (порт 8002)
- Семантический поиск
- Кэширование запросов
- Поиск похожих фрагментов
- Фильтрация по метаданным

### 4. Metadata Service (порт 8003)
- Управление метаданными
- Статистика коллекций
- Схема метаданных
- История изменений

## Быстрый старт

### Требования
- Docker и Docker Compose
- 4GB+ свободной памяти

### Запуск
```bash
# Запустить все сервисы
./start_microservices.sh up

# Проверить статус
./start_microservices.sh status

# Остановить сервисы
./start_microservices.sh down
```

### Проверка работоспособности
```bash
# Проверить health всех сервисов
curl http://localhost:8000/api/v1/health

# Посмотреть документацию API
open http://localhost:8000/api/docs
```

## Использование

### Через REST API
```bash
# Поиск
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "database connection", "n_results": 5}'

# Индексация
curl -X POST http://localhost:8000/api/v1/index \
  -H "Content-Type: application/json" \
  -d '{"project_root": "/path/to/project", "file_patterns": ["**/*.py"]}'

# Статистика
curl http://localhost:8000/api/v1/stats

# Список файлов
curl http://localhost:8000/api/v1/files
```

### Через Python клиент
```python
from chroma_rest_client import ChromaRESTClient

client = ChromaRESTClient("http://localhost:8000")

# Поиск
results = client.search("database connection", n_results=5)

# Индексация
job = client.index("/path/to/project", ["**/*.py", "**/*.java"])

# Проверка статуса
status = client.get_index_status(job["job_id"])

# Статистика
stats = client.get_stats()
```

### Через командную строку
```bash
# Поиск
python chroma_rest_client.py --search "database connection" --results 3

# Индексация
python chroma_rest_client.py --index --project-root /path/to/project

# Статистика
python chroma_rest_client.py --stats

# Health check
python chroma_rest_client.py --health
```

## Миграция с TCP на REST

### Старый TCP клиент
```python
# TCP команды
SEARCH|query|n_results
INDEX|file_patterns
STATS
PING
```

### Новый REST API
```python
# Поиск
POST /api/v1/search
{
  "query": "database connection",
  "n_results": 5,
  "filters": {"language": "python"}
}

# Индексация
POST /api/v1/index
{
  "project_root": "/path/to/project",
  "file_patterns": ["**/*.py"],
  "max_file_size_mb": 10
}
```

## Конфигурация

### Переменные окружения
```bash
# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=chroma_metadata
POSTGRES_USER=chroma
POSTGRES_PASSWORD=chroma123
```

### Docker Compose настройки
```yaml
# Изменить порты
services:
  api-gateway:
    ports:
      - "8080:8000"  # Внешний:Внутренний
```

## Мониторинг

### Prometheus (порт 9090)
- Метрики производительности
- Health checks
- Rate limiting статистика

### Grafana (порт 3000)
- Дашборды производительности
- Мониторинг сервисов
- Анализ использования

### Доступ к мониторингу
```bash
# Prometheus
open http://localhost:9090

# Grafana
open http://localhost:3000
# Логин: admin / admin
```

## Разработка

### Локальная разработка
```bash
# Запустить сервисы в development режиме
docker-compose -f docker-compose.dev.yml up

# Запустить тесты
python -m pytest tests/

# Проверить код
python -m black services/
python -m flake8 services/
```

### Добавление нового сервиса
1. Создать директорию в `services/`
2. Добавить `Dockerfile` и `requirements.txt`
3. Реализовать FastAPI приложение
4. Добавить в `docker-compose.yml`
5. Обновить `API Gateway` для маршрутизации

## Производительность

### Оптимизации
- **Кэширование:** Redis для кэширования запросов и результатов
- **Балансировка:** Docker Compose для оркестрации сервисов
- **Масштабирование:** Каждый сервис можно масштабировать независимо
- **Мониторинг:** Prometheus + Grafana для отслеживания метрик

### Ожидаемая производительность
- Время поиска: < 2 секунд
- Индексация 50k файлов: < 10 минут
- Память на сервис: < 500MB
- Поддержка: 500k+ файлов

## Устранение неполадок

### Общие проблемы
```bash
# Проверить логи
./start_microservices.sh logs

# Перезапустить сервисы
./start_microservices.sh restart

# Очистить всё и начать заново
./start_microservices.sh clean
```

### Проблемы с подключением
1. Проверить, что все порты свободны
2. Проверить логи Docker контейнеров
3. Убедиться, что есть доступ к интернету для загрузки образов

### Проблемы с памятью
1. Увеличить лимиты памяти в Docker
2. Уменьшить batch size в Indexing Service
3. Настроить кэширование в Redis

## Лицензия

MIT License - смотрите [LICENSE](LICENSE) файл.

## Контакты

- GitHub: [karavaykov/chroma-vector-search](https://github.com/karavaykov/chroma-vector-search)
- Issues: [GitHub Issues](https://github.com/karavaykov/chroma-vector-search/issues)
- Discussions: [GitHub Discussions](https://github.com/karavaykov/chroma-vector-search/discussions)