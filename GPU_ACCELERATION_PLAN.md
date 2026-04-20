# План реализации GPU ускорения для Chroma Vector Search

## Текущая ситуация

Проект использует:
- `sentence-transformers` версия 5.1.2
- Модель `all-MiniLM-L6-v2` для генерации эмбеддингов
- PyTorch 2.8.0 (без CUDA на текущей системе)

## Возможности GPU ускорения

### 1. Поддержка CUDA в sentence-transformers
- `sentence-transformers` автоматически использует GPU если доступен CUDA
- Для активации нужно установить PyTorch с поддержкой CUDA
- Модель автоматически перемещается на GPU при вызове `.to('cuda')`

### 2. Варианты установки PyTorch с CUDA

**Для Linux с NVIDIA GPU:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Для Windows с NVIDIA GPU:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Для macOS (Metal Performance Shaders):**
```bash
pip install torch torchvision torchaudio
```

### 3. Оптимизации для GPU

1. **Batch processing** - обработка текстов батчами для лучшей утилизации GPU
2. **Model warm-up** - предварительная загрузка модели на GPU
3. **Mixed precision** - использование float16 для ускорения вычислений
4. **Caching** - кэширование эмбеддингов для повторяющихся текстов

## План реализации

### Этап 1: Обновление зависимостей
1. Добавить опциональные зависимости для GPU в `pyproject.toml`
2. Создать отдельные requirements файлы:
   - `requirements.txt` - базовые зависимости
   - `requirements-gpu.txt` - зависимости с CUDA поддержкой

### Этап 2: Модификация кода
1. Добавить конфигурацию для GPU в `ChromaSimpleServer`
2. Реализовать автоматическое определение доступности CUDA
3. Добавить методы для работы с GPU:
   - `_init_embedding_model_gpu()`
   - `encode_with_gpu()`
   - `move_model_to_device()`

### Этап 3: Оптимизации производительности
1. Реализовать batch processing для GPU
2. Добавить поддержку mixed precision (float16)
3. Реализовать model warm-up при старте сервера
4. Улучшить кэширование эмбеддингов

### Этап 4: Тестирование и документация
1. Написать тесты для GPU функциональности
2. Создать бенчмарки для сравнения CPU/GPU производительности
3. Обновить документацию с инструкциями по установке
4. Добавить примеры использования GPU

## Технические детали реализации

### 1. Конфигурация GPU

```python
@dataclass
class GPUConfig:
    enabled: bool = False
    device: str = "auto"  # "auto", "cuda", "cpu", "mps"
    batch_size: int = 32
    use_mixed_precision: bool = True
    cache_size: int = 1000
```

### 2. Инициализация модели с GPU

```python
def _init_embedding_model_gpu(self):
    """Initialize model with GPU support"""
    import torch
    
    # Determine device
    if self.gpu_config.device == "auto":
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    else:
        device = self.gpu_config.device
    
    # Load model
    self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Move to device
    self.embedding_model.to(device)
    self.device = device
    
    # Enable mixed precision if requested
    if self.gpu_config.use_mixed_precision and device != "cpu":
        self.embedding_model.half()
    
    # Warm up model
    self._warm_up_model()
```

### 3. Batch processing для GPU

```python
def encode_batch_gpu(self, texts: List[str]) -> List[List[float]]:
    """Encode batch of texts using GPU with optimization"""
    if not texts:
        return []
    
    # Split into batches
    batches = [texts[i:i + self.gpu_config.batch_size] 
               for i in range(0, len(texts), self.gpu_config.batch_size)]
    
    embeddings = []
    for batch in batches:
        # Encode batch on GPU
        batch_embeddings = self.embedding_model.encode(
            batch,
            convert_to_tensor=True,
            show_progress_bar=False
        )
        
        # Move to CPU and convert to list
        if self.device != "cpu":
            batch_embeddings = batch_embeddings.cpu()
        
        embeddings.extend(batch_embeddings.tolist())
    
    return embeddings
```

## Ожидаемые улучшения производительности

### Для NVIDIA GPU (CUDA):
- **Small batches (1-10 текстов)**: 2-5x ускорение
- **Large batches (100+ текстов)**: 10-50x ускорение
- **Memory usage**: увеличение на 1-2GB для модели

### Для Apple Silicon (MPS):
- **Small batches**: 1.5-3x ускорение
- **Large batches**: 5-10x ускорение

### Для CPU (без изменений):
- Текущая производительность сохраняется

## Следующие шаги

1. ✅ Изучить текущую архитектуру
2. 🔄 Исследовать возможности GPU ускорения
3. Проанализировать зависимости проекта
4. Реализовать поддержку CUDA
5. Добавить конфигурацию
6. Написать тесты
7. Обновить документацию

## Риски и ограничения

1. **Зависимость от оборудования** - требуется NVIDIA GPU для CUDA
2. **Увеличение памяти** - модель занимает место в VRAM
3. **Сложность установки** - нужны драйверы CUDA
4. **Совместимость** - разные версии PyTorch/CUDA

## Альтернативы

1. **ONNX Runtime** - кроссплатформенное ускорение
2. **TensorRT** - оптимизация для NVIDIA
3. **OpenVINO** - оптимизация для Intel
4. **Core ML** - оптимизация для Apple