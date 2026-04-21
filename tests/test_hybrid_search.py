#!/usr/bin/env python3
"""
Tests for hybrid search functionality
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from keyword_search import KeywordSearchIndex, HybridSearchOptimizer
from search_fuser import SearchResultFuser, SearchQualityEvaluator


class TestKeywordSearchIndex(unittest.TestCase):
    """Test KeywordSearchIndex class"""
    
    def setUp(self):
        """Set up test environment"""
        self.index = KeywordSearchIndex()
        
        # Test documents
        self.documents = [
            {
                "chunk_id": "doc1",
                "content": "This is a test document about Python programming.",
                "metadata": {"file_path": "test.py", "language": "python"}
            },
            {
                "chunk_id": "doc2", 
                "content": "Java is another programming language for enterprise applications.",
                "metadata": {"file_path": "Test.java", "language": "java"}
            },
            {
                "chunk_id": "doc3",
                "content": "Python and Java are both popular programming languages.",
                "metadata": {"file_path": "comparison.md", "language": "markdown"}
            }
        ]
        
        # Add documents to index
        for doc in self.documents:
            self.index.add_document(
                chunk_id=doc["chunk_id"],
                content=doc["content"],
                metadata=doc["metadata"]
            )
    
    def test_tokenization(self):
        """Test tokenization of text"""
        tokens = self.index._tokenize("Python programming with camelCase and snake_case")
        # Note: 'case' appears twice in input but should be deduplicated in tokens
        expected_tokens = {"python", "programming", "camel", "snake"}
        # Check that all expected tokens are present
        for token in expected_tokens:
            self.assertIn(token, tokens)
        # Check that we don't have duplicates
        self.assertEqual(len(tokens), len(set(tokens)))
    
    def test_add_document(self):
        """Test adding documents to index"""
        self.assertEqual(self.index.get_document_count(), 3)
        self.assertGreater(self.index.get_vocabulary_size(), 0)
    
    def test_search_basic(self):
        """Test basic keyword search"""
        results = self.index.search("Python programming", n_results=2)
        
        self.assertGreater(len(results), 0)
        # doc1 or doc3 could be most relevant (both contain "Python" and "programming")
        # Check that we get results and they have scores
        for result in results:
            self.assertGreater(result.score, 0)
            self.assertIn(result.chunk_id, ["doc1", "doc2", "doc3"])
    
    def test_search_multiple_words(self):
        """Test search with multiple words"""
        results = self.index.search("Java enterprise", n_results=2)
        
        self.assertGreater(len(results), 0)
        # doc2 should be most relevant for "Java enterprise"
        self.assertEqual(results[0].chunk_id, "doc2")
    
    def test_search_no_results(self):
        """Test search with no matching results"""
        results = self.index.search("nonexistentword", n_results=5)
        self.assertEqual(len(results), 0)
    
    def test_remove_document(self):
        """Test removing documents from index"""
        self.index.remove_document("doc1")
        self.assertEqual(self.index.get_document_count(), 2)
        
        # Search should not return removed document
        results = self.index.search("Python", n_results=5)
        doc_ids = [r.chunk_id for r in results]
        self.assertNotIn("doc1", doc_ids)
    
    def test_save_load(self):
        """Test saving and loading index"""
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Save index
            self.index.save(tmp_path)
            
            # Create new index and load
            new_index = KeywordSearchIndex()
            new_index.load(tmp_path)
            
            # Verify loaded index
            self.assertEqual(new_index.get_document_count(), 3)
            
            # Test search on loaded index
            results = new_index.search("Python", n_results=2)
            self.assertGreater(len(results), 0)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_get_stats(self):
        """Test getting index statistics"""
        stats = self.index.get_stats()
        
        self.assertEqual(stats['total_documents'], 3)
        self.assertGreater(stats['vocabulary_size'], 0)
        self.assertGreater(stats['average_document_length'], 0)
        self.assertEqual(len(stats['most_common_words']), min(10, stats['vocabulary_size']))


class TestSearchResultFuser(unittest.TestCase):
    """Test SearchResultFuser class"""
    
    def setUp(self):
        """Set up test data"""
        self.semantic_results = [
            {
                "chunk_id": "doc1",
                "score": 0.9,
                "content": "Semantic result 1",
                "metadata": {"file_path": "test1.py"}
            },
            {
                "chunk_id": "doc2",
                "score": 0.7,
                "content": "Semantic result 2",
                "metadata": {"file_path": "test2.py"}
            },
            {
                "chunk_id": "doc3",
                "score": 0.5,
                "content": "Semantic result 3",
                "metadata": {"file_path": "test3.py"}
            }
        ]
        
        self.keyword_results = [
            {
                "chunk_id": "doc2",
                "score": 0.8,
                "content": "Keyword result 2",
                "metadata": {"file_path": "test2.py"}
            },
            {
                "chunk_id": "doc4",
                "score": 0.6,
                "content": "Keyword result 4",
                "metadata": {"file_path": "test4.py"}
            },
            {
                "chunk_id": "doc1",
                "score": 0.4,
                "content": "Keyword result 1",
                "metadata": {"file_path": "test1.py"}
            }
        ]
    
    def test_normalize_scores(self):
        """Test score normalization"""
        fuser = SearchResultFuser()
        
        # Create test results
        results = [
            type('Result', (), {
                'chunk_id': f'doc{i}',
                'score': i * 0.2,
                'content': f'Content {i}',
                'metadata': {},
                'search_type': 'test'
            })() for i in range(1, 6)
        ]
        
        normalized = fuser.normalize_scores(results)
        
        # Check normalization
        scores = [r.score for r in normalized]
        self.assertAlmostEqual(min(scores), 0.0, places=5)
        self.assertAlmostEqual(max(scores), 1.0, places=5)
    
    def test_weighted_fusion(self):
        """Test weighted score fusion"""
        fuser = SearchResultFuser(semantic_weight=0.6, keyword_weight=0.4)
        
        fused = fuser.fuse(
            semantic_results=self.semantic_results,
            keyword_results=self.keyword_results,
            n_results=5,
            fusion_method='weighted'
        )
        
        self.assertGreater(len(fused), 0)
        
        # Check that results are sorted by score (descending)
        scores = [r['score'] for r in fused]
        self.assertEqual(scores, sorted(scores, reverse=True))
        
        # Check that all results have required fields
        for result in fused:
            self.assertIn('chunk_id', result)
            self.assertIn('score', result)
            self.assertIn('content', result)
            self.assertIn('metadata', result)
            self.assertEqual(result['search_type'], 'hybrid')
    
    def test_rrf_fusion(self):
        """Test reciprocal rank fusion"""
        fuser = SearchResultFuser()
        
        fused = fuser.fuse(
            semantic_results=self.semantic_results,
            keyword_results=self.keyword_results,
            n_results=5,
            fusion_method='rrf'
        )
        
        self.assertGreater(len(fused), 0)
        
        # In RRF, doc2 should be top (appears in both lists with good ranks)
        top_result = fused[0]
        self.assertEqual(top_result['chunk_id'], 'doc2')
    
    def test_deduplication(self):
        """Test result deduplication"""
        fuser = SearchResultFuser()
        
        # Create results with duplicates
        semantic_with_dupes = self.semantic_results + [self.semantic_results[0]]
        keyword_with_dupes = self.keyword_results + [self.keyword_results[0]]
        
        fused = fuser.fuse(
            semantic_results=semantic_with_dupes,
            keyword_results=keyword_with_dupes,
            n_results=10,
            fusion_method='weighted',
            deduplicate=True
        )
        
        # Check that we have unique chunk_ids
        chunk_ids = [r['chunk_id'] for r in fused]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))
    
    def test_empty_results(self):
        """Test fusion with empty results"""
        fuser = SearchResultFuser()
        
        # Test with empty semantic results
        fused1 = fuser.fuse(
            semantic_results=[],
            keyword_results=self.keyword_results,
            n_results=5,
            fusion_method='weighted'
        )
        self.assertEqual(len(fused1), min(5, len(self.keyword_results)))
        
        # Test with empty keyword results
        fused2 = fuser.fuse(
            semantic_results=self.semantic_results,
            keyword_results=[],
            n_results=5,
            fusion_method='weighted'
        )
        self.assertEqual(len(fused2), min(5, len(self.semantic_results)))
        
        # Test with both empty
        fused3 = fuser.fuse(
            semantic_results=[],
            keyword_results=[],
            n_results=5,
            fusion_method='weighted'
        )
        self.assertEqual(len(fused3), 0)


class TestHybridSearchOptimizer(unittest.TestCase):
    """Test HybridSearchOptimizer class"""
    
    def test_calculate_query_complexity(self):
        """Test query complexity calculation"""
        
        # Simple query
        simple_score = HybridSearchOptimizer.calculate_query_complexity("test")
        self.assertGreaterEqual(simple_score, 0.0)
        self.assertLessEqual(simple_score, 1.0)
        
        # Complex query
        complex_score = HybridSearchOptimizer.calculate_query_complexity(
            "implement database connection pool with connection pooling and transaction management"
        )
        self.assertGreater(complex_score, simple_score)
        
        # Technical query
        tech_score = HybridSearchOptimizer.calculate_query_complexity(
            "createUserRepository with JPA annotations and @Transactional"
        )
        self.assertGreater(tech_score, simple_score)
    
    def test_suggest_weights(self):
        """Test weight suggestion based on query complexity"""
        
        # Simple query should favor keyword search
        simple_weights = HybridSearchOptimizer.suggest_weights("test function")
        self.assertLess(simple_weights[0], 0.5)  # semantic weight < 0.5
        self.assertGreater(simple_weights[1], 0.5)  # keyword weight > 0.5
        
        # Complex query should favor semantic search
        complex_weights = HybridSearchOptimizer.suggest_weights(
            "how to implement microservices architecture with service discovery"
        )
        self.assertGreater(complex_weights[0], 0.5)  # semantic weight > 0.5
        self.assertLess(complex_weights[1], 0.5)  # keyword weight < 0.5
        
        # Technical query should favor semantic search
        tech_weights = HybridSearchOptimizer.suggest_weights(
            "@Entity @Table(name='users') class UserRepository extends JpaRepository"
        )
        self.assertGreater(tech_weights[0], 0.5)  # semantic weight > 0.5
        self.assertLess(tech_weights[1], 0.5)  # keyword weight < 0.5


class TestSearchQualityEvaluator(unittest.TestCase):
    """Test SearchQualityEvaluator class"""
    
    def test_calculate_precision_at_k(self):
        """Test precision@k calculation"""
        results = [
            {"chunk_id": "doc1"},
            {"chunk_id": "doc2"},
            {"chunk_id": "doc3"},
            {"chunk_id": "doc4"},
            {"chunk_id": "doc5"}
        ]
        
        relevant_ids = {"doc1", "doc3", "doc5"}
        
        # Precision@1: only first result, should be 1.0 if doc1 is relevant
        precision_1 = SearchQualityEvaluator.calculate_precision_at_k(results, relevant_ids, 1)
        self.assertEqual(precision_1, 1.0)
        
        # Precision@3: first 3 results, 2 are relevant (doc1, doc3)
        precision_3 = SearchQualityEvaluator.calculate_precision_at_k(results, relevant_ids, 3)
        self.assertAlmostEqual(precision_3, 2.0/3.0, places=5)
        
        # Precision@5: all 5 results, 3 are relevant
        precision_5 = SearchQualityEvaluator.calculate_precision_at_k(results, relevant_ids, 5)
        self.assertAlmostEqual(precision_5, 3.0/5.0, places=5)
    
    def test_calculate_recall_at_k(self):
        """Test recall@k calculation"""
        results = [
            {"chunk_id": "doc1"},
            {"chunk_id": "doc2"},
            {"chunk_id": "doc3"},
            {"chunk_id": "doc4"},
            {"chunk_id": "doc5"}
        ]
        
        relevant_ids = {"doc1", "doc3", "doc5", "doc6", "doc7"}  # 5 relevant total
        
        # Recall@3: found 2 out of 5 relevant
        recall_3 = SearchQualityEvaluator.calculate_recall_at_k(results, relevant_ids, 3)
        self.assertAlmostEqual(recall_3, 2.0/5.0, places=5)
        
        # Recall@5: found 3 out of 5 relevant
        recall_5 = SearchQualityEvaluator.calculate_recall_at_k(results, relevant_ids, 5)
        self.assertAlmostEqual(recall_5, 3.0/5.0, places=5)
    
    def test_calculate_f1_score(self):
        """Test F1-score calculation"""
        
        # Perfect precision and recall
        f1_perfect = SearchQualityEvaluator.calculate_f1_score(1.0, 1.0)
        self.assertEqual(f1_perfect, 1.0)
        
        # Good precision, poor recall
        f1_good_precision = SearchQualityEvaluator.calculate_f1_score(0.8, 0.2)
        self.assertGreater(f1_good_precision, 0.0)
        self.assertLess(f1_good_precision, 0.5)
        
        # Poor precision, good recall
        f1_good_recall = SearchQualityEvaluator.calculate_f1_score(0.2, 0.8)
        self.assertGreater(f1_good_recall, 0.0)
        self.assertLess(f1_good_recall, 0.5)
        
        # Zero precision and recall
        f1_zero = SearchQualityEvaluator.calculate_f1_score(0.0, 0.0)
        self.assertEqual(f1_zero, 0.0)
    
    def test_evaluate_search_quality(self):
        """Test comprehensive search quality evaluation"""
        semantic_results = [
            {"chunk_id": "doc1"},
            {"chunk_id": "doc2"},
            {"chunk_id": "doc3"}
        ]
        
        keyword_results = [
            {"chunk_id": "doc2"},
            {"chunk_id": "doc4"},
            {"chunk_id": "doc5"}
        ]
        
        hybrid_results = [
            {"chunk_id": "doc1"},
            {"chunk_id": "doc2"},
            {"chunk_id": "doc3"},
            {"chunk_id": "doc4"},
            {"chunk_id": "doc5"}
        ]
        
        relevant_ids = {"doc1", "doc2", "doc3"}
        
        metrics = SearchQualityEvaluator.evaluate_search_quality(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            hybrid_results=hybrid_results,
            relevant_ids=relevant_ids,
            k_values=[1, 3, 5]
        )
        
        # Check structure
        self.assertIn('semantic', metrics)
        self.assertIn('keyword', metrics)
        self.assertIn('hybrid', metrics)
        
        # Check metrics for each search type
        for search_type in ['semantic', 'keyword', 'hybrid']:
            self.assertIn('precision@1', metrics[search_type])
            self.assertIn('precision@3', metrics[search_type])
            self.assertIn('precision@5', metrics[search_type])
            self.assertIn('recall@1', metrics[search_type])
            self.assertIn('recall@3', metrics[search_type])
            self.assertIn('recall@5', metrics[search_type])
            self.assertIn('f1@1', metrics[search_type])
            self.assertIn('f1@3', metrics[search_type])
            self.assertIn('f1@5', metrics[search_type])


if __name__ == '__main__':
    unittest.main()