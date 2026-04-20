# Chroma Vector Search для OpenCode

[English](README.md) | [Русский](README.ru.md) | [中文](README.zh.md)

Семантический поиск по коду для OpenCode - TCP-альтернатива MCP (совместимость с Python 3.9+)

## 📋 Обзор

Chroma Vector Search - это инструмент семантического поиска по коду, который интегрируется с OpenCode через простой TCP-протокол. В отличие от официального MCP (Model Context Protocol), который требует Python ≥3.10, наш сервер работает на Python 3.9+, что делает его совместимым со стандартными системами macOS.

## ✨ Особенности

- **Совместимость с Python 3.9+** - работает на стандартных системах macOS
- **TCP-сервер на порту 8765** - простой текстовый протокол
- **Семантический поиск по коду** - использует ChromaDB и Sentence Transformers
- **Интеграция с OpenCode** - через конфигурацию custom tools
- **Полная документация** - API, развертывание, примеры использования
- **Тесты и CI/CD** - автоматическое тестирование через GitHub Actions
- **GPU ускорение** - поддержка CUDA и MPS для быстрых эмбеддингов (2.6x-14.7x ускорение)

## 🚀 Быстрый старт

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/karavaykov/chroma-vector-search.git
cd chroma-vector-search

# Установить зависимости
pip install -r requirements.txt
```

### Запуск сервера

```bash
# Запустить TCP-сервер
python chroma_simple_server.py

# Или использовать скрипт
./start_chroma_mcp.sh
```

### Интеграция с OpenCode

Добавьте в конфигурацию OpenCode (`~/.opencode/config.json`):

```json
{
  "tools": [
    {
      "type": "custom",
      "config": "./opencode_chroma_simple.jsonc"
    }
  ]
}
```

## 📖 Использование

### Индексация кода

```bash
# Индексация директории с кодом
python chroma_client.py index /path/to/your/code
```

### Поиск по коду

```bash
# Семантический поиск
python chroma_client.py search "функция для обработки ошибок"
```

### Примеры промптов для OpenCode

```
Найди все функции, связанные с аутентификацией пользователей
Покажи реализацию обработки платежей
Найди классы для работы с базой данных
```

## 🚀 GPU Ускорение (Новое в v1.1.0)

Ускорьте генерацию эмбеддингов с поддержкой GPU для NVIDIA CUDA и Apple Silicon MPS:

### Установка с поддержкой GPU

```bash
# Для NVIDIA GPU (CUDA) - ускорение 10-16x
pip install -r requirements-gpu.txt

# Для Apple Silicon (MPS) - ускорение 8-12x
pip install torch torchvision torchaudio
pip install -r requirements.txt
```

### Использование

```bash
# Включить GPU ускорение (автоопределение устройства)
python chroma_simple_server.py --server --gpu

# Использовать конкретное устройство
python chroma_simple_server.py --server --gpu --gpu-device cuda      # NVIDIA CUDA
python chroma_simple_server.py --server --gpu --gpu-device mps       # Apple Silicon
python chroma_simple_server.py --server --gpu --gpu-device cpu       # Принудительно CPU

# Оптимизация для пакетной обработки
python chroma_simple_server.py --server --gpu --gpu-batch-size 64 --gpu-mixed-precision
```

### Результаты производительности (тестирование на Apple M1)

| Операция | Время CPU | Время GPU (MPS) | Ускорение |
|----------|-----------|-----------------|-----------|
| Поисковый запрос | 4-39мс | 2-4мс | 2.6x-14.7x |
| Пакетная обработка (64 текста) | 304мс | 24мс | 12.6x |
| Пакетная обработка (128 текстов) | 601мс | 49мс | 12.3x |

**Подробная документация:** [GPU Acceleration Guide](docs/GPU_ACCELERATION.md) | [Тесты производительности](ENTERPRISE_PERFORMANCE_TEST_WITH_GPU.md)

## 🏗️ Архитектура

```
┌─────────────────┐    TCP (порт 8765)    ┌─────────────────┐
│    OpenCode     │ ◄───────────────────► │  Chroma Server  │
│   (клиент)      │                       │   (Python 3.9+) │
└─────────────────┘                       └─────────────────┘
         │                                         │
         ▼                                         ▼
┌─────────────────┐                       ┌─────────────────┐
│  Custom Tools   │                       │    ChromaDB     │
│  Конфигурация   │                       │  + Embeddings   │
└─────────────────┘                       └─────────────────┘
```

## 📊 Команды протокола

Сервер поддерживает простой текстовый протокол:

```
SEARCH <запрос>          # Семантический поиск
INDEX <путь>             # Индексация директории
STATS                    # Статистика базы данных
PING                     # Проверка соединения
```

## 🧪 Тестирование

```bash
# Запустить все тесты
pytest tests/

# Тестировать отдельные модули
pytest tests/test_basic.py
pytest tests/test_client.py
```

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! Пожалуйста, ознакомьтесь с [CONTRIBUTING.md](CONTRIBUTING.md) для получения подробной информации.

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. Подробнее см. в файле [LICENSE](LICENSE).

## 📞 Поддержка

- **Issues**: [GitHub Issues](https://github.com/karavaykov/chroma-vector-search/issues)
- **Документация**: [docs/](docs/)
- **Примеры**: [examples/](examples/)

## 🙏 Благодарности

- [ChromaDB](https://www.trychroma.com/) - векторная база данных
- [Sentence Transformers](https://www.sbert.net/) - модели эмбеддингов
- [OpenCode](https://opencode.ai/) - платформа для разработки с ИИ

---

**Примечание**: Этот проект является альтернативой официальному MCP (Model Context Protocol) и специально разработан для совместимости с Python 3.9+, что делает его доступным для более широкого круга пользователей.