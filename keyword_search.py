#!/usr/bin/env python3
"""
Keyword Search Index для гибридного поиска
Реализует полнотекстовый поиск с TF-IDF для комбинации с семантическим поиском
"""

import re
import math
import json
import pickle
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class KeywordSearchResult:
    """Результат keyword поиска"""
    chunk_id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь"""
        return {
            "chunk_id": self.chunk_id,
            "score": self.score,
            "content": self.content,
            "metadata": self.metadata
        }

class KeywordSearchIndex:
    """Инвертированный индекс для полнотекстового поиска с TF-IDF"""
    
    def __init__(self, stop_words: Optional[Set[str]] = None):
        """
        Инициализация keyword индекса
        
        Args:
            stop_words: Множество стоп-слов для исключения из индекса
        """
        self.index: Dict[str, Dict[str, float]] = {}  # word -> {chunk_id: tf_idf}
        self.documents: Dict[str, Dict[str, Any]] = {}  # chunk_id -> {content, metadata, length}
        self.doc_freq: Dict[str, int] = {}  # word -> количество документов, содержащих слово
        self.total_docs = 0
        self.stop_words = stop_words or self._get_default_stop_words()
        
        # Регулярные выражения для токенизации
        self.token_pattern = re.compile(r'\b\w{2,}\b', re.IGNORECASE)  # Слова от 2 символов
        self.camel_case_pattern = re.compile(r'([A-Z][a-z]+|[a-z]+|[A-Z]+(?=[A-Z]|$))')
        
    def _get_default_stop_words(self) -> Set[str]:
        """Получить стандартный набор стоп-слов для программирования"""
        programming_stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'can', 'could', 'may', 'might', 'must', 'shall', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its',
            'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
            'self', 'selves', 'what', 'which', 'who', 'whom', 'whose',
            'where', 'when', 'why', 'how', 'all', 'any', 'both', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            's', 't', 'can', 'will', 'just', 'don', 'should', 'now',
            # Программистские стоп-слова
            'var', 'let', 'const', 'function', 'class', 'interface', 'type',
            'return', 'if', 'else', 'for', 'while', 'do', 'switch', 'case',
            'try', 'catch', 'finally', 'throw', 'new', 'delete', 'void',
            'null', 'undefined', 'true', 'false', 'bool', 'int', 'float',
            'string', 'array', 'object', 'list', 'map', 'set', 'get', 'set'
        }
        return programming_stop_words
    
    def _tokenize(self, text: str) -> List[str]:
        """Токенизация текста с учетом camelCase и snake_case"""
        tokens = []
        
        # Разделение camelCase
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Разделение snake_case и kebab-case
        text = re.sub(r'[_-]', ' ', text)
        
        # Извлечение слов
        words = self.token_pattern.findall(text.lower())
        
        # Фильтрация стоп-слов и коротких токенов
        for word in words:
            if word not in self.stop_words and len(word) >= 2:
                tokens.append(word)
                
        return tokens
    
    def _calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Вычислить Term Frequency (TF) для списка токенов"""
        if not tokens:
            return {}
        
        token_count = Counter(tokens)
        max_count = max(token_count.values())
        
        tf = {}
        for token, count in token_count.items():
            # Нормализованная частота термина
            tf[token] = 0.5 + 0.5 * (count / max_count)
            
        return tf
    
    def _calculate_idf(self, word: str) -> float:
        """Вычислить Inverse Document Frequency (IDF) для слова"""
        if word not in self.doc_freq or self.doc_freq[word] == 0:
            return 0
        
        # Стандартная формула IDF с smoothing
        return math.log((self.total_docs + 1) / (self.doc_freq[word] + 1)) + 1
    
    def add_document(self, chunk_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """
        Добавить документ в индекс
        
        Args:
            chunk_id: Уникальный идентификатор чанка
            content: Текст чанка
            metadata: Метаданные чанка
        """
        if chunk_id in self.documents:
            # Обновление существующего документа
            self.remove_document(chunk_id)
        
        # Токенизация контента
        tokens = self._tokenize(content)
        if not tokens:
            return
        
        # Вычисление TF
        tf = self._calculate_tf(tokens)
        
        # Обновление частоты документов для слов
        for word in tf.keys():
            if word not in self.doc_freq:
                self.doc_freq[word] = 0
            self.doc_freq[word] += 1
        
        # Сохранение документа
        self.documents[chunk_id] = {
            'content': content,
            'metadata': metadata,
            'length': len(tokens),
            'tf': tf
        }
        
        # Обновление общего количества документов
        self.total_docs += 1
        
        # Вычисление и сохранение TF-IDF для каждого слова
        for word, tf_score in tf.items():
            idf_score = self._calculate_idf(word)
            tf_idf_score = tf_score * idf_score
            
            if word not in self.index:
                self.index[word] = {}
            self.index[word][chunk_id] = tf_idf_score
        
        logger.debug(f"Добавлен документ {chunk_id} с {len(tokens)} токенами")
    
    def remove_document(self, chunk_id: str) -> None:
        """Удалить документ из индекса"""
        if chunk_id not in self.documents:
            return
        
        # Удаление из индекса
        for word, docs in list(self.index.items()):
            if chunk_id in docs:
                del docs[chunk_id]
                # Уменьшение частоты документа для слова
                self.doc_freq[word] -= 1
                if self.doc_freq[word] <= 0:
                    del self.doc_freq[word]
            
            # Удаление пустых записей
            if not docs:
                del self.index[word]
        
        # Удаление документа
        del self.documents[chunk_id]
        self.total_docs -= 1
        
        logger.debug(f"Удален документ {chunk_id}")
    
    def search(self, query: str, n_results: int = 10) -> List[KeywordSearchResult]:
        """
        Выполнить keyword поиск
        
        Args:
            query: Поисковый запрос
            n_results: Количество возвращаемых результатов
            
        Returns:
            Список результатов поиска
        """
        if not query or not self.documents:
            return []
        
        # Токенизация запроса
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        # Счетчик релевантности для каждого документа
        doc_scores = defaultdict(float)
        
        # Поиск по каждому токену запроса
        for token in query_tokens:
            if token in self.index:
                for chunk_id, tf_idf_score in self.index[token].items():
                    # Увеличение веса для точных совпадений
                    doc_scores[chunk_id] += tf_idf_score
        
        # Сортировка результатов по убыванию релевантности
        sorted_results = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_results]
        
        # Формирование результатов
        results = []
        for chunk_id, score in sorted_results:
            if chunk_id in self.documents:
                doc = self.documents[chunk_id]
                result = KeywordSearchResult(
                    chunk_id=chunk_id,
                    score=score,
                    content=doc['content'],
                    metadata=doc['metadata']
                )
                results.append(result)
        
        logger.debug(f"Keyword поиск по запросу '{query}' вернул {len(results)} результатов")
        return results
    
    def batch_search(self, queries: List[str], n_results: int = 5) -> Dict[str, List[KeywordSearchResult]]:
        """Пакетный поиск по нескольким запросам"""
        results = {}
        for query in queries:
            results[query] = self.search(query, n_results)
        return results
    
    def get_document_count(self) -> int:
        """Получить количество документов в индексе"""
        return self.total_docs
    
    def get_vocabulary_size(self) -> int:
        """Получить размер словаря (уникальных слов)"""
        return len(self.index)
    
    def clear(self) -> None:
        """Очистить индекс"""
        self.index.clear()
        self.documents.clear()
        self.doc_freq.clear()
        self.total_docs = 0
        logger.info("Keyword индекс очищен")
    
    def save(self, filepath: str) -> None:
        """Сохранить индекс в файл"""
        data = {
            'index': self.index,
            'documents': self.documents,
            'doc_freq': self.doc_freq,
            'total_docs': self.total_docs,
            'stop_words': list(self.stop_words)
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Keyword индекс сохранен в {filepath}")
    
    def load(self, filepath: str) -> None:
        """Загрузить индекс из файла"""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            self.index = data['index']
            self.documents = data['documents']
            self.doc_freq = data['doc_freq']
            self.total_docs = data['total_docs']
            self.stop_words = set(data.get('stop_words', self._get_default_stop_words()))
            
            logger.info(f"Keyword индекс загружен из {filepath}, документов: {self.total_docs}")
        except Exception as e:
            logger.error(f"Ошибка загрузки keyword индекса: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику индекса"""
        return {
            'total_documents': self.total_docs,
            'vocabulary_size': self.get_vocabulary_size(),
            'average_document_length': sum(doc['length'] for doc in self.documents.values()) / max(1, self.total_docs),
            'most_common_words': sorted(
                self.doc_freq.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }


class HybridSearchOptimizer:
    """Оптимизатор для гибридного поиска"""
    
    @staticmethod
    def calculate_query_complexity(query: str) -> float:
        """
        Вычислить сложность запроса для динамического взвешивания
        
        Returns:
            Значение от 0.0 (простой запрос) до 1.0 (сложный запрос)
        """
        # Количество слов
        words = query.split()
        word_count = len(words)
        
        # Наличие технических терминов (предполагаем, что они в camelCase или содержат специальные символы)
        tech_terms = sum(1 for word in words if re.search(r'[A-Z][a-z]|[A-Z]{2,}|[._-]', word))
        
        # Длина запроса
        query_length = len(query)
        
        # Комбинированная оценка сложности
        complexity = (
            0.4 * min(word_count / 10, 1.0) +  # Нормализованное количество слов
            0.4 * min(tech_terms / max(1, word_count), 1.0) +  # Доля технических терминов
            0.2 * min(query_length / 100, 1.0)  # Нормализованная длина
        )
        
        return min(complexity, 1.0)
    
    @staticmethod
    def suggest_weights(query: str) -> Tuple[float, float]:
        """
        Предложить веса для гибридного поиска на основе запроса
        
        Returns:
            Кортеж (semantic_weight, keyword_weight)
        """
        complexity = HybridSearchOptimizer.calculate_query_complexity(query)
        
        # Простые запросы (короткие, без технических терминов) → больше weight для keyword
        # Сложные запросы (длинные, с техническими терминами) → больше weight для semantic
        if complexity < 0.3:
            # Простой запрос
            return (0.4, 0.6)  # 40% semantic, 60% keyword
        elif complexity < 0.7:
            # Средний запрос
            return (0.6, 0.4)  # 60% semantic, 40% keyword
        else:
            # Сложный запрос
            return (0.8, 0.2)  # 80% semantic, 20% keyword