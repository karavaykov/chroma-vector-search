#!/usr/bin/env python3
"""
Демонстрация гибридного поиска в Chroma Vector Search
"""

import os
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from chroma_simple_server import ChromaSimpleServer, GPUConfig
from keyword_search import HybridSearchOptimizer


def create_test_files(project_root: Path):
    """Создание тестовых файлов для демонстрации"""
    
    # Python файл с функциями
    python_code = '''
def calculate_total_price(items, tax_rate=0.1):
    """Calculate total price with tax"""
    subtotal = sum(item['price'] * item['quantity'] for item in items)
    tax = subtotal * tax_rate
    return subtotal + tax

def apply_discount(price, discount_percent):
    """Apply discount to price"""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_percent / 100)

class ShoppingCart:
    """Shopping cart for e-commerce"""
    
    def __init__(self):
        self.items = []
    
    def add_item(self, product, quantity=1):
        """Add item to cart"""
        self.items.append({
            'product': product,
            'quantity': quantity,
            'price': product.price
        })
    
    def get_total(self):
        """Get total cart value"""
        return calculate_total_price(self.items)
'''
    
    # Java файл с похожей функциональностью
    java_code = '''
public class PriceCalculator {
    private double taxRate = 0.1;
    
    public double calculateTotal(List<CartItem> items) {
        double subtotal = 0.0;
        for (CartItem item : items) {
            subtotal += item.getPrice() * item.getQuantity();
        }
        double tax = subtotal * taxRate;
        return subtotal + tax;
    }
    
    public double applyDiscount(double price, double discountPercent) {
        if (discountPercent < 0 || discountPercent > 100) {
            throw new IllegalArgumentException("Discount must be between 0 and 100");
        }
        return price * (1 - discountPercent / 100);
    }
}

public class ShoppingCart {
    private List<CartItem> items = new ArrayList<>();
    
    public void addItem(Product product, int quantity) {
        items.add(new CartItem(product, quantity));
    }
    
    public double getTotal() {
        PriceCalculator calculator = new PriceCalculator();
        return calculator.calculateTotal(items);
    }
}
'''
    
    # Документация
    docs = '''
# E-commerce System Documentation

## Price Calculation Functions

### calculate_total_price(items, tax_rate)
Calculates total price including tax for a list of items.

### apply_discount(price, discount_percent)
Applies percentage discount to a price.

## Shopping Cart Classes

### ShoppingCart (Python)
Manages shopping cart items and calculates totals.

### ShoppingCart (Java)
Java implementation of shopping cart with price calculation.
'''
    
    # Создаем директории и файлы
    (project_root / "python").mkdir(exist_ok=True)
    (project_root / "java").mkdir(exist_ok=True)
    (project_root / "docs").mkdir(exist_ok=True)
    
    (project_root / "python" / "shopping.py").write_text(python_code)
    (project_root / "java" / "ShoppingCart.java").write_text(java_code)
    (project_root / "docs" / "README.md").write_text(docs)
    
    print(f"Созданы тестовые файлы в {project_root}")


def demo_hybrid_search():
    """Демонстрация гибридного поиска"""
    
    # Создаем временную директорию
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="chroma_demo_")
    project_root = Path(temp_dir)
    
    try:
        print("=" * 80)
        print("ДЕМОНСТРАЦИЯ ГИБРИДНОГО ПОИСКА В CHROMA VECTOR SEARCH")
        print("=" * 80)
        
        # Создаем тестовые файлы
        create_test_files(project_root)
        
        # Инициализируем сервер
        print("\n1. Инициализация сервера...")
        server = ChromaSimpleServer(
            project_root=str(project_root),
            port=8770,  # Используем другой порт для демо
            gpu_config=GPUConfig(enabled=False)
        )
        
        # Индексируем файлы
        print("\n2. Индексация файлов...")
        count = server.index_codebase(
            file_patterns=["**/*.py", "**/*.java", "**/*.md"],
            max_file_size_mb=1
        )
        print(f"   Проиндексировано чанков: {count}")
        
        # Получаем статистику
        stats = server.get_stats()
        print(f"   Всего документов: {stats['document_count']}")
        if stats.get('keyword_index_available'):
            print(f"   Документов в keyword индексе: {stats.get('keyword_document_count', 0)}")
        
        print("\n" + "=" * 80)
        print("3. ТЕСТИРОВАНИЕ РАЗНЫХ ТИПОВ ПОИСКА")
        print("=" * 80)
        
        # Тест 1: Семантический поиск (концептуальный запрос)
        print("\n📚 ТЕСТ 1: Семантический поиск")
        print("   Запрос: 'how to calculate total price with tax'")
        semantic_results = server.semantic_search(
            "how to calculate total price with tax", 
            n_results=3
        )
        print(f"   Найдено результатов: {len(semantic_results)}")
        for i, result in enumerate(semantic_results[:2], 1):
            print(f"   {i}. {result.get('file_path', 'unknown')} (score: {result['similarity_score']:.3f})")
        
        # Тест 2: Keyword поиск (точное имя)
        print("\n🔍 ТЕСТ 2: Keyword поиск")
        print("   Запрос: 'calculateTotal'")
        if stats.get('keyword_index_available'):
            keyword_results = server.keyword_search("calculateTotal", n_results=3)
            print(f"   Найдено результатов: {len(keyword_results)}")
            for i, result in enumerate(keyword_results[:2], 1):
                print(f"   {i}. {result.get('file_path', 'unknown')} (score: {result['similarity_score']:.3f})")
        else:
            print("   Keyword поиск недоступен")
        
        # Тест 3: Гибридный поиск с автоматическим подбором весов
        print("\n🤖 ТЕСТ 3: Гибридный поиск (автоматические веса)")
        print("   Запрос: 'calculate total price function'")
        
        # Автоматический подбор весов
        weights = HybridSearchOptimizer.suggest_weights("calculate total price function")
        print(f"   Предложенные веса: semantic={weights[0]:.2f}, keyword={weights[1]:.2f}")
        
        hybrid_results = server.hybrid_search(
            query="calculate total price function",
            n_results=5,
            semantic_weight=weights[0],
            keyword_weight=weights[1],
            fusion_method='weighted'
        )
        print(f"   Найдено результатов: {len(hybrid_results)}")
        for i, result in enumerate(hybrid_results[:3], 1):
            source = result.get('file_path', result.get('metadata', {}).get('file_path', 'unknown'))
            print(f"   {i}. {source} (score: {result['similarity_score']:.3f}, type: {result.get('search_type', 'unknown')})")
        
        # Тест 4: Гибридный поиск с разными весами
        print("\n⚖️ ТЕСТ 4: Гибридный поиск с разными весами")
        
        test_cases = [
            ("Keyword-heavy (70% keyword)", "ShoppingCart", 0.3, 0.7),
            ("Balanced (50/50)", "apply discount to price", 0.5, 0.5),
            ("Semantic-heavy (80% semantic)", "how to implement shopping cart functionality", 0.8, 0.2),
        ]
        
        for description, query, semantic_weight, keyword_weight in test_cases:
            print(f"\n   {description}")
            print(f"   Запрос: '{query}'")
            print(f"   Веса: semantic={semantic_weight}, keyword={keyword_weight}")
            
            results = server.hybrid_search(
                query=query,
                n_results=3,
                semantic_weight=semantic_weight,
                keyword_weight=keyword_weight,
                fusion_method='weighted'
            )
            
            if results:
                top_result = results[0]
                source = top_result.get('file_path', top_result.get('metadata', {}).get('file_path', 'unknown'))
                print(f"   Лучший результат: {source} (score: {top_result['similarity_score']:.3f})")
            else:
                print("   Результатов не найдено")
        
        # Тест 5: Сравнение методов комбинирования
        print("\n🔄 ТЕСТ 5: Сравнение методов комбинирования")
        print("   Запрос: 'price calculation with tax'")
        
        fusion_methods = ['weighted', 'rrf', 'both']
        
        for method in fusion_methods:
            results = server.hybrid_search(
                query="price calculation with tax",
                n_results=3,
                semantic_weight=0.6,
                keyword_weight=0.4,
                fusion_method=method
            )
            print(f"\n   Метод: {method}")
            if results:
                scores = [r['similarity_score'] for r in results[:3]]
                print(f"   Топ-3 scores: {[f'{s:.3f}' for s in scores]}")
        
        print("\n" + "=" * 80)
        print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
        print("=" * 80)
        
        # Показываем итоговую статистику
        print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        final_stats = server.get_stats()
        print(f"   • Всего документов: {final_stats['document_count']}")
        if final_stats.get('keyword_index_available'):
            print(f"   • Документов в keyword индексе: {final_stats['keyword_document_count']}")
            print(f"   • Уникальных слов: {final_stats['keyword_vocabulary_size']}")
        print(f"   • Гибридный поиск доступен: {final_stats['hybrid_search_available']}")
        
    finally:
        # Очистка временной директории
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\n🗑️ Временная директория очищена: {temp_dir}")


if __name__ == "__main__":
    demo_hybrid_search()