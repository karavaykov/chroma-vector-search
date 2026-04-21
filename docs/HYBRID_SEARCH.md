# Гибридный поиск в Chroma Vector Search

## Обзор

Гибридный поиск объединяет семантический (векторный) поиск с keyword (полнотекстовым) поиском для улучшения точности и релевантности результатов. Этот подход особенно полезен для поиска по коду, где точные совпадения имен функций и классов (keyword search) важны так же, как и семантическое понимание концепций.

## Архитектура

### Компоненты

1. **KeywordSearchIndex** - инвертированный индекс с TF-IDF для полнотекстового поиска
2. **SearchResultFuser** - алгоритмы комбинирования результатов (RRF, Weighted Fusion)
3. **HybridSearchOptimizer** - оптимизатор для динамического выбора весов
4. **Интеграция с ChromaSimpleServer** - единый API для всех типов поиска

### Алгоритмы комбинирования

#### 1. Weighted Score Fusion
- Взвешенная комбинация нормализованных оценок
- Настраиваемые веса: `semantic_weight` и `keyword_weight`
- Формула: `final_score = semantic_weight * semantic_score + keyword_weight * keyword_score`

#### 2. Reciprocal Rank Fusion (RRF)
- Комбинирование рангов вместо оценок
- Устойчив к разным шкалам оценок
- Формула: `RRF_score = 1/(k + semantic_rank) + 1/(k + keyword_rank)`

#### 3. Комбинированный подход (both)
- Использует оба алгоритма и усредняет результаты
- Наиболее устойчивый к разным типам запросов

## Использование

### Командная строка

```bash
# Семантический поиск (по умолчанию)
python chroma_client.py --search "database connection" --results 5

# Keyword поиск
python chroma_client.py --search "calculateSum" --search-type keyword --results 10

# Гибридный поиск с настраиваемыми весами
python chroma_client.py --search "API endpoint" --search-type hybrid \
  --semantic-weight 0.6 --keyword-weight 0.4 --fusion-method weighted

# Гибридный поиск с RRF
python chroma_client.py --search "user authentication" --search-type hybrid \
  --fusion-method rrf

# Автоматический подбор весов (рекомендуется)
python chroma_client.py --search "implement @Entity class" --search-type hybrid
```

### Python API

```python
from chroma_simple_server import ChromaSimpleServer

# Инициализация сервера
server = ChromaSimpleServer(project_root=".")

# Индексация с поддержкой keyword поиска
server.index_codebase(file_patterns=["**/*.py", "**/*.java"])

# Разные типы поиска
semantic_results = server.semantic_search("database connection", n_results=5)
keyword_results = server.keyword_search("UserRepository", n_results=10)

# Гибридный поиск
hybrid_results = server.hybrid_search(
    query="authentication middleware",
    n_results=8,
    semantic_weight=0.7,      # Вес семантического поиска
    keyword_weight=0.3,       # Вес keyword поиска
    fusion_method='weighted', # Метод комбинирования
    search_type='hybrid'      # Тип поиска: 'semantic', 'keyword', или 'hybrid'
)

# Автоматический подбор весов на основе запроса
from keyword_search import HybridSearchOptimizer
weights = HybridSearchOptimizer.suggest_weights("create REST API endpoint")
# Возвращает (semantic_weight, keyword_weight) на основе сложности запроса
```

### TCP API (для OpenCode)

```
# Семантический поиск
SEARCH|query|n_results

# Keyword поиск  
KEYWORD_SEARCH|query|n_results

# Гибридный поиск
HYBRID_SEARCH|query|n_results|semantic_weight|keyword_weight|fusion_method
```

Пример ответа:
```json
{
  "type": "search_results",
  "results": [
    {
      "rank": 1,
      "content": "def authenticate_user(username, password):",
      "file_path": "auth.py",
      "line_start": 42,
      "line_end": 55,
      "language": "python",
      "similarity_score": 0.892,
      "chunk_id": "auth.py:42",
      "search_type": "hybrid"
    }
  ]
}
```

## Конфигурация

### Настройка весов

Система автоматически подбирает оптимальные веса на основе:
- **Длины запроса**: короткие запросы → больше weight для keyword
- **Технических терминов**: наличие camelCase, аннотаций → больше weight для semantic
- **Сложности запроса**: сложные описания → больше weight для semantic

Ручная настройка:
```python
# Для точных имен функций/классов
server.hybrid_search(query="UserRepository", semantic_weight=0.3, keyword_weight=0.7)

# Для концептуальных запросов  
server.hybrid_search(query="how to implement caching", semantic_weight=0.8, keyword_weight=0.2)

# Для смешанных запросов
server.hybrid_search(query="create UserRepository with @Entity", semantic_weight=0.6, keyword_weight=0.4)
```

### Методы комбинирования

| Метод | Лучше всего подходит для | Производительность |
|-------|--------------------------|-------------------|
| `weighted` | Общего назначения, настраиваемые веса | Высокая |
| `rrf` | Запросов с разными типами результатов | Высокая |
| `both` | Максимальной точности, критичных систем | Средняя |

## Примеры использования

### Пример 1: Поиск точных имен

```bash
# Keyword-heavy для точных имен функций
python chroma_client.py --search "calculateTotalPrice" --search-type hybrid \
  --semantic-weight 0.3 --keyword-weight 0.7

# Результаты будут включать точные совпадения имен
```

### Пример 2: Поиск концепций

```bash
# Semantic-heavy для концептуальных запросов
python chroma_client.py --search "how to handle database transactions" \
  --search-type hybrid --semantic-weight 0.8 --keyword-weight 0.2

# Результаты будут включать семантически похожий код
```

### Пример 3: Смешанный поиск

```bash
# Сбалансированный поиск для смешанных запросов
python chroma_client.py --search "implement UserService with @Transactional" \
  --search-type hybrid --semantic-weight 0.6 --keyword-weight 0.4

# Сочетает точные совпадения (@Transactional) с семантикой (UserService)
```

## Производительность

### Временные характеристики

| Тип поиска | Среднее время | Память | Рекомендации |
|------------|---------------|--------|--------------|
| Semantic | ~1-2 сек | ~50-100MB | Для концептуальных запросов |
| Keyword | ~0.01-0.1 сек | ~10-50MB | Для точных имен |
| Hybrid | ~1-3 сек | ~60-150MB | Для смешанных запросов |

### Оптимизация

1. **Кэширование**: Keyword индекс кэшируется в памяти
2. **Потоковая обработка**: Индексация выполняется батчами
3. **Автоматическая настройка**: Веса подбираются на основе запроса

## Мониторинг и отладка

### Статистика

```python
stats = server.get_stats()
print(f"Semantic documents: {stats['document_count']}")
print(f"Keyword documents: {stats.get('keyword_document_count', 0)}")
print(f"Vocabulary size: {stats.get('keyword_vocabulary_size', 0)}")
```

### Оценка качества

```python
from search_fuser import SearchQualityEvaluator

# Оценка качества поиска
metrics = SearchQualityEvaluator.evaluate_search_quality(
    semantic_results=semantic_results,
    keyword_results=keyword_results, 
    hybrid_results=hybrid_results,
    relevant_ids={"chunk1", "chunk2", "chunk3"},
    k_values=[1, 3, 5, 10]
)

print(f"Precision@5: {metrics['hybrid']['precision@5']:.3f}")
print(f"Recall@5: {metrics['hybrid']['recall@5']:.3f}")
print(f"F1@5: {metrics['hybrid']['f1@5']:.3f}")
```

## Интеграция с OpenCode

### Конфигурация OpenCode

Добавьте в `opencode_chroma_simple.jsonc`:

```json
{
  "chroma_hybrid_search": {
    "description": "Гибридный поиск (семантический + keyword)",
    "command": ["python", "chroma_client.py", "--hybrid", 
                "--query", "{query}", 
                "--semantic-weight", "{semantic_weight}",
                "--keyword-weight", "{keyword_weight}",
                "--results", "{n_results}"],
    "parameters": {
      "query": {"type": "string", "description": "Поисковый запрос"},
      "semantic_weight": {"type": "number", "default": 0.7},
      "keyword_weight": {"type": "number", "default": 0.3},
      "n_results": {"type": "integer", "default": 5}
    }
  }
}
```

### Использование агентами

- **Scout**: Использует гибридный поиск для исследовательских задач
- **Smith**: Использует keyword поиск для точных имен функций
- **Architect**: Использует semantic поиск для архитектурных паттернов

## Расширенное использование

### Кастомные стоп-слова

```python
from keyword_search import KeywordSearchIndex

# Создание индекса с кастомными стоп-словами
custom_stop_words = {"var", "let", "const", "function", "class"}
index = KeywordSearchIndex(stop_words=custom_stop_words)
```

### Сохранение и загрузка индекса

```python
# Сохранение keyword индекса
server.keyword_index.save("keyword_index.pkl")

# Загрузка при инициализации
server = ChromaSimpleServer(project_root=".")
if os.path.exists(".keyword_index.pkl"):
    server.keyword_index.load(".keyword_index.pkl")
```

### Пакетный поиск

```python
# Поиск по нескольким запросам одновременно
queries = ["authentication", "authorization", "user management"]
results = server.keyword_index.batch_search(queries, n_results=3)
```

## Устранение неполадок

### Проблема: Keyword поиск не возвращает результаты

**Решение:**
1. Проверьте, что индексация выполнена: `server.get_stats()`
2. Убедитесь, что keyword индекс доступен: `stats['keyword_index_available']`
3. Проверьте токенизацию: `index._tokenize("your query")`

### Проблема: Гибридный поиск медленный

**Решение:**
1. Уменьшите `n_results` для keyword поиска
2. Используйте `fusion_method='rrf'` для лучшей производительности
3. Проверьте размер keyword индекса

### Проблема: Неправильные веса для запроса

**Решение:**
1. Используйте `HybridSearchOptimizer.suggest_weights(query)` для автоматического подбора
2. Ручная настройка на основе типа запроса
3. Мониторинг качества с помощью `SearchQualityEvaluator`

## Будущие улучшения

1. **BM25 алгоритм**: Замена TF-IDF на BM25 для лучшего keyword поиска
2. **Обучение на feedback**: Автоматическая настройка весов на основе пользовательских кликов
3. **Контекстный поиск**: Учет окружающего кода при поиске
4. **Многоязычная поддержка**: Улучшенная токенизация для разных языков

## Заключение

Гибридный поиск значительно улучшает точность поиска по коду, сочетая сильные стороны семантического и keyword поиска. Система автоматически адаптируется к типу запроса и предоставляет гибкие возможности настройки для различных сценариев использования.