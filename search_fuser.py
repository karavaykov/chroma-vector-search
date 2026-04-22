#!/usr/bin/env python3
"""
Search Result Fuser для гибридного поиска
Реализует алгоритмы комбинирования результатов семантического и keyword поиска
"""

import math
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Унифицированный результат поиска"""
    chunk_id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    search_type: str  # 'semantic', 'keyword', или 'hybrid'
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь"""
        return {
            "chunk_id": self.chunk_id,
            "similarity_score": self.score,  # Используем similarity_score для совместимости
            "score": self.score,
            "content": self.content,
            "metadata": self.metadata,
            "search_type": self.search_type
        }

class SearchResultFuser:
    """Класс для комбинирования результатов разных типов поиска"""
    
    def __init__(self, semantic_weight: float = 0.7, keyword_weight: float = 0.3):
        """
        Инициализация fuser'а
        
        Args:
            semantic_weight: Вес семантического поиска (0.0-1.0)
            keyword_weight: Вес keyword поиска (0.0-1.0)
        """
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        
        # Проверка корректности весов
        total_weight = semantic_weight + keyword_weight
        if abs(total_weight - 1.0) > 0.001:
            logger.warning(f"Сумма весов не равна 1.0: {total_weight}. Нормализую...")
            self.semantic_weight = semantic_weight / total_weight
            self.keyword_weight = keyword_weight / total_weight
    
    @staticmethod
    def normalize_scores(results: List[SearchResult]) -> List[SearchResult]:
        """
        Нормализовать оценки результатов (Min-Max нормализация)
        
        Args:
            results: Список результатов поиска
            
        Returns:
            Список результатов с нормализованными оценками
        """
        if not results:
            return results
        
        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        # Если все оценки одинаковые, возвращаем как есть
        if max_score - min_score < 0.0001:
            return results
        
        normalized_results = []
        for result in results:
            normalized_score = (result.score - min_score) / (max_score - min_score)
            normalized_results.append(SearchResult(
                chunk_id=result.chunk_id,
                score=normalized_score,
                content=result.content,
                metadata=result.metadata,
                search_type=result.search_type
            ))
        
        return normalized_results
    
    @staticmethod
    def reciprocal_rank_fusion(
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        k: int = 60
    ) -> List[SearchResult]:
        """
        Reciprocal Rank Fusion (RRF) алгоритм
        
        Args:
            semantic_results: Результаты семантического поиска
            keyword_results: Результаты keyword поиска
            k: Константа для сглаживания (обычно 60)
            
        Returns:
            Объединенные результаты, отсортированные по RRF score
        """
        # Создание словарей для быстрого доступа по chunk_id
        semantic_ranks = {}
        keyword_ranks = {}
        
        for rank, result in enumerate(semantic_results, 1):
            semantic_ranks[result.chunk_id] = rank
        
        for rank, result in enumerate(keyword_results, 1):
            keyword_ranks[result.chunk_id] = rank
        
        # Вычисление RRF score для каждого уникального chunk_id
        all_chunk_ids = set(semantic_ranks.keys()) | set(keyword_ranks.keys())
        rrf_scores = {}
        
        for chunk_id in all_chunk_ids:
            semantic_rank = semantic_ranks.get(chunk_id, k + 1)
            keyword_rank = keyword_ranks.get(chunk_id, k + 1)
            
            # Формула RRF
            rrf_score = (1.0 / (k + semantic_rank)) + (1.0 / (k + keyword_rank))
            rrf_scores[chunk_id] = rrf_score
        
        # Сбор информации о результатах
        result_map = {}
        for result in semantic_results + keyword_results:
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result
        
        # Создание финальных результатов
        fused_results = []
        for chunk_id, rrf_score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
            if chunk_id in result_map:
                original_result = result_map[chunk_id]
                fused_results.append(SearchResult(
                    chunk_id=chunk_id,
                    score=rrf_score,
                    content=original_result.content,
                    metadata=original_result.metadata,
                    search_type='hybrid'
                ))
        
        return fused_results
    
    def weighted_score_fusion(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Weighted Score Fusion алгоритм
        
        Args:
            semantic_results: Результаты семантического поиска (нормализованные)
            keyword_results: Результаты keyword поиска (нормализованные)
            
        Returns:
            Объединенные результаты, отсортированные по взвешенной оценке
        """
        # Нормализация оценок
        norm_semantic = self.normalize_scores(semantic_results)
        norm_keyword = self.normalize_scores(keyword_results)
        
        # Создание словарей для быстрого доступа
        semantic_scores = {r.chunk_id: r.score for r in norm_semantic}
        keyword_scores = {r.chunk_id: r.score for r in norm_keyword}
        
        # Сбор информации о результатах
        result_map = {}
        for result in norm_semantic + norm_keyword:
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result
        
        # Вычисление взвешенных оценок
        weighted_scores = {}
        all_chunk_ids = set(semantic_scores.keys()) | set(keyword_scores.keys())
        
        for chunk_id in all_chunk_ids:
            semantic_score = semantic_scores.get(chunk_id, 0.0)
            keyword_score = keyword_scores.get(chunk_id, 0.0)
            
            # Взвешенная комбинация
            weighted_score = (
                self.semantic_weight * semantic_score +
                self.keyword_weight * keyword_score
            )
            weighted_scores[chunk_id] = weighted_score
        
        # Создание финальных результатов
        fused_results = []
        for chunk_id, weighted_score in sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True):
            if chunk_id in result_map:
                original_result = result_map[chunk_id]
                fused_results.append(SearchResult(
                    chunk_id=chunk_id,
                    score=weighted_score,
                    content=original_result.content,
                    metadata=original_result.metadata,
                    search_type='hybrid'
                ))
        
        return fused_results
    
    def hybrid_fusion(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        fusion_method: str = 'weighted'
    ) -> List[SearchResult]:
        """
        Гибридное комбинирование результатов
        
        Args:
            semantic_results: Результаты семантического поиска
            keyword_results: Результаты keyword поиска
            fusion_method: Метод комбинирования ('rrf', 'weighted', или 'both')
            
        Returns:
            Объединенные результаты
        """
        if not semantic_results and not keyword_results:
            return []
        
        if not semantic_results:
            # Только keyword результаты
            for result in keyword_results:
                result.search_type = 'hybrid'
            return self.normalize_scores(keyword_results)
        
        if not keyword_results:
            # Только семантические результаты
            for result in semantic_results:
                result.search_type = 'hybrid'
            return self.normalize_scores(semantic_results)
        
        # Применение выбранного метода комбинирования
        if fusion_method == 'rrf':
            fused_results = self.reciprocal_rank_fusion(semantic_results, keyword_results)
        elif fusion_method == 'weighted':
            fused_results = self.weighted_score_fusion(semantic_results, keyword_results)
        elif fusion_method == 'both':
            # Комбинация обоих методов
            rrf_results = self.reciprocal_rank_fusion(semantic_results, keyword_results)
            weighted_results = self.weighted_score_fusion(semantic_results, keyword_results)
            
            # Объединение рангов из обоих методов
            combined_scores = defaultdict(float)
            result_map = {}
            
            # Сбор результатов
            for result in rrf_results + weighted_results:
                if result.chunk_id not in result_map:
                    result_map[result.chunk_id] = result
                combined_scores[result.chunk_id] += result.score
            
            # Создание финальных результатов
            fused_results = []
            for chunk_id, combined_score in sorted(combined_scores.items(), key=lambda x: x[1], reverse=True):
                original_result = result_map[chunk_id]
                fused_results.append(SearchResult(
                    chunk_id=chunk_id,
                    score=combined_score / 2.0,  # Среднее значение
                    content=original_result.content,
                    metadata=original_result.metadata,
                    search_type='hybrid'
                ))
        else:
            raise ValueError(f"Неизвестный метод комбинирования: {fusion_method}")
        
        # Дополнительная нормализация
        fused_results = self.normalize_scores(fused_results)
        
        logger.debug(f"Гибридное комбинирование: {len(semantic_results)} semantic + "
                    f"{len(keyword_results)} keyword → {len(fused_results)} fused")
        
        return fused_results
    
    @staticmethod
    def deduplicate_results(
        results: List[SearchResult],
        similarity_threshold: float = 0.9
    ) -> List[SearchResult]:
        """
        Удаление дубликатов из результатов поиска
        
        Args:
            results: Список результатов
            similarity_threshold: Порог схожести для удаления дубликатов
            
        Returns:
            Список результатов без дубликатов
        """
        if not results:
            return results
        
        # Простая дедупликация по chunk_id
        seen_ids = set()
        deduplicated = []
        
        for result in results:
            if result.chunk_id not in seen_ids:
                seen_ids.add(result.chunk_id)
                deduplicated.append(result)
        
        # Если нужно более сложное семантическое дедупликации,
        # можно добавить здесь сравнение эмбеддингов контента
        
        if len(deduplicated) < len(results):
            logger.debug(f"Дедупликация: {len(results)} → {len(deduplicated)} результатов")
        
        return deduplicated
    
    def fuse(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        n_results: int = 10,
        fusion_method: str = 'weighted',
        deduplicate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Основной метод для комбинирования результатов
        
        Args:
            semantic_results: Результаты семантического поиска в формате словаря
            keyword_results: Результаты keyword поиска в формате словаря
            n_results: Количество возвращаемых результатов
            fusion_method: Метод комбинирования
            deduplicate: Удалять ли дубликаты
            
        Returns:
            Объединенные результаты в формате словаря
        """
        # Преобразование в объекты SearchResult
        semantic_objects = [
            SearchResult(
                chunk_id=r.get('chunk_id', ''),
                score=r.get('similarity_score', r.get('score', 0.0)),  # Поддержка обоих полей
                content=r.get('content', ''),
                metadata=r.get('metadata', {}),
                search_type='semantic'
            )
            for r in semantic_results
        ]
        
        keyword_objects = [
            SearchResult(
                chunk_id=r.get('chunk_id', ''),
                score=r.get('similarity_score', r.get('score', 0.0)),  # Поддержка обоих полей
                content=r.get('content', ''),
                metadata=r.get('metadata', {}),
                search_type='keyword'
            )
            for r in keyword_results
        ]
        
        # Комбинирование результатов
        fused_objects = self.hybrid_fusion(semantic_objects, keyword_objects, fusion_method)
        
        # Дедупликация
        if deduplicate:
            fused_objects = self.deduplicate_results(fused_objects)
        
        # Ограничение количества результатов
        fused_objects = fused_objects[:n_results]
        
        # Преобразование обратно в словари
        fused_dicts = [r.to_dict() for r in fused_objects]
        
        return fused_dicts


class SearchQualityEvaluator:
    """Оценщик качества поиска"""
    
    @staticmethod
    def calculate_precision_at_k(results: List[Dict[str, Any]], relevant_ids: Set[str], k: int = 5) -> float:
        """
        Вычислить Precision@k
        
        Args:
            results: Результаты поиска
            relevant_ids: Множество релевантных chunk_id
            k: Количество рассматриваемых результатов
            
        Returns:
            Precision@k значение
        """
        if not results or k <= 0:
            return 0.0
        
        top_k = results[:k]
        relevant_count = sum(1 for r in top_k if r.get('chunk_id') in relevant_ids)
        
        return relevant_count / k
    
    @staticmethod
    def calculate_recall_at_k(results: List[Dict[str, Any]], relevant_ids: Set[str], k: int = 5) -> float:
        """
        Вычислить Recall@k
        
        Args:
            results: Результаты поиска
            relevant_ids: Множество релевантных chunk_id
            k: Количество рассматриваемых результатов
            
        Returns:
            Recall@k значение
        """
        if not relevant_ids or k <= 0:
            return 0.0
        
        top_k = results[:k]
        relevant_found = sum(1 for r in top_k if r.get('chunk_id') in relevant_ids)
        
        return relevant_found / len(relevant_ids)
    
    @staticmethod
    def calculate_f1_score(precision: float, recall: float) -> float:
        """
        Вычислить F1-score
        
        Args:
            precision: Precision значение
            recall: Recall значение
            
        Returns:
            F1-score значение
        """
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    @staticmethod
    def evaluate_search_quality(
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        hybrid_results: List[Dict[str, Any]],
        relevant_ids: Set[str],
        k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict[str, Any]:
        """
        Оценить качество разных типов поиска
        
        Returns:
            Словарь с метриками качества
        """
        metrics = {
            'semantic': {},
            'keyword': {},
            'hybrid': {}
        }
        
        for k in k_values:
            # Precision@k
            metrics['semantic'][f'precision@{k}'] = SearchQualityEvaluator.calculate_precision_at_k(
                semantic_results, relevant_ids, k
            )
            metrics['keyword'][f'precision@{k}'] = SearchQualityEvaluator.calculate_precision_at_k(
                keyword_results, relevant_ids, k
            )
            metrics['hybrid'][f'precision@{k}'] = SearchQualityEvaluator.calculate_precision_at_k(
                hybrid_results, relevant_ids, k
            )
            
            # Recall@k
            metrics['semantic'][f'recall@{k}'] = SearchQualityEvaluator.calculate_recall_at_k(
                semantic_results, relevant_ids, k
            )
            metrics['keyword'][f'recall@{k}'] = SearchQualityEvaluator.calculate_recall_at_k(
                keyword_results, relevant_ids, k
            )
            metrics['hybrid'][f'recall@{k}'] = SearchQualityEvaluator.calculate_recall_at_k(
                hybrid_results, relevant_ids, k
            )
            
            # F1@k
            for search_type in ['semantic', 'keyword', 'hybrid']:
                precision = metrics[search_type][f'precision@{k}']
                recall = metrics[search_type][f'recall@{k}']
                metrics[search_type][f'f1@{k}'] = SearchQualityEvaluator.calculate_f1_score(precision, recall)
        
        return metrics