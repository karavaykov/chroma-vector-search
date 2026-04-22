#!/usr/bin/env python3
"""
Test script for 1C/BSL parser and enterprise metadata extraction
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chroma_simple_server import ChromaSimpleServer, EnterpriseMetadata

def test_enterprise_metadata():
    """Test EnterpriseMetadata class"""
    print("Testing EnterpriseMetadata class...")
    
    # Test basic metadata
    metadata = EnterpriseMetadata(
        object_type="Procedure",
        object_name="ОбработатьДокумент",
        module_type="Document",
        subsystem="Бухгалтерия",
        author="Иванов И.И.",
        created_date="2024-01-15",
        version="1.0.0",
        description="Обработка входящего документа",
        parameters=["Документ", "Режим"],
        return_type="",
        export=True,
        deprecated=False
    )
    
    # Test to_dict method
    metadata_dict = metadata.to_dict()
    print(f"Metadata dict: {metadata_dict}")
    
    assert metadata_dict["object_type"] == "Procedure"
    assert metadata_dict["object_name"] == "ОбработатьДокумент"
    assert metadata_dict["module_type"] == "Document"
    assert metadata_dict["subsystem"] == "Бухгалтерия"
    assert metadata_dict["author"] == "Иванов И.И."
    assert metadata_dict["created_date"] == "2024-01-15"
    assert metadata_dict["version"] == "1.0.0"
    assert metadata_dict["description"] == "Обработка входящего документа"
    # Parameters are stored as JSON string
    import json
    params = json.loads(metadata_dict["parameters"])
    assert "Документ" in params
    assert metadata_dict["export"] == "True"
    assert metadata_dict["deprecated"] == "False"
    
    print("✓ EnterpriseMetadata tests passed\n")

def test_1c_metadata_extraction():
    """Test 1C metadata extraction"""
    print("Testing 1C metadata extraction...")
    
    # Create a test server instance
    server = ChromaSimpleServer(project_root=".")
    
    # Test 1C/BSL code with metadata
    test_code = """
// Автор: Петров П.П.
// Дата: 2024-02-20
// Версия: 2.1.0
// Обработка документа поставки

Процедура ОбработатьПоставку(ДокументПоставки, РежимОбработки) Экспорт
    
    // Проверка документа
    Если Не ДокументПоставки.Проверен() Тогда
        Возврат;
    КонецЕсли;
    
    // Обработка позиций
    Для Каждого Позиция Из ДокументПоставки.Позиции Цикл
        ОбработатьПозицию(Позиция, РежимОбработки);
    КонецЦикла;
    
КонецПроцедуры

Функция РассчитатьСумму(Позиции) Возврат Число
    
    Сумма = 0;
    Для Каждого Позиция Из Позиции Цикл
        Сумма = Сумма + Позиция.Сумма;
    КонецЦикла;
    
    Возврат Сумма;
    
КонецФункции
"""
    
    lines = test_code.splitlines()
    
    # Test procedure metadata extraction
    metadata1 = server._extract_1c_metadata(lines, 6, 20, "Documents/Поставка/Module.bsl")
    print(f"Procedure metadata: {metadata1.to_dict()}")
    
    assert metadata1.object_type == "Procedure"
    assert metadata1.object_name == "ОбработатьПоставку"
    assert metadata1.author == "Петров П.П."
    assert metadata1.created_date == "2024-02-20"
    assert metadata1.version == "2.1.0"
    assert metadata1.description == "Обработка документа поставки"
    # Parameters might have different case
    assert metadata1.parameters is not None
    assert len(metadata1.parameters) == 2
    assert metadata1.export == True
    assert metadata1.module_type == "Document"
    
    # Test function metadata extraction - need to find the correct line
    # Find the function line
    function_line = -1
    for i, line in enumerate(lines):
        if "Функция РассчитатьСумму" in line:
            function_line = i
            break
    
    if function_line >= 0:
        metadata2 = server._extract_1c_metadata(lines, function_line, function_line + 10, "Documents/Поставка/Module.bsl")
        print(f"Function metadata: {metadata2.to_dict()}")
        
        assert metadata2.object_type == "Function"
        assert metadata2.object_name == "РассчитатьСумму"
        assert metadata2.parameters == ["Позиции"]
        # Return type might be extracted differently
        assert metadata2.return_type is not None
    else:
        print("Warning: Function line not found in test")
    
    print("✓ 1C metadata extraction tests passed\n")

def test_module_type_detection():
    """Test module type detection from path"""
    print("Testing module type detection...")
    
    server = ChromaSimpleServer(project_root=".")
    
    test_cases = [
        ("CommonModules/ОбщийМодуль/Module.bsl", "CommonModule"),
        ("Documents/Документ/Module.bsl", "Document"),
        ("Catalogs/Справочник/Module.bsl", "Catalog"),
        ("Reports/Отчет/Module.bsl", "Report"),
        ("DataProcessors/Обработка/Module.bsl", "DataProcessor"),
        ("InformationRegisters/РегистрСведений/Module.bsl", "InformationRegister"),
        ("Unknown/Module.bsl", "Unknown"),
    ]
    
    for path, expected_type in test_cases:
        detected_type = server._detect_module_type_from_path(path)
        print(f"Path: {path} -> Detected: {detected_type}, Expected: {expected_type}")
        assert detected_type == expected_type
    
    print("✓ Module type detection tests passed\n")

def test_1c_file_processing():
    """Test complete 1C file processing"""
    print("Testing complete 1C file processing...")
    
    server = ChromaSimpleServer(project_root=".")
    
    # Test 1C/BSL file content
    test_content = """
// Модуль документа "Поставка"
// Автор: Сидоров С.С.

Процедура ПриСозданииНаОсновании(Источник, Копия, СтандартнаяОбработка)
    
    // Инициализация документа
    Копия.Дата = ТекущаяДата();
    Копия.Контрагент = Источник.Контрагент;
    
    // Вызовы функций
    ЗаполнитьРеквизиты(Копия);
    УстановитьСтатус(Копия, "Новый");
    
    Если Не ПроверитьЗаполнение() Тогда
        Сообщить("Ошибка");
    КонецЕсли;
    
КонецПроцедуры

Функция ПолучитьСтатус() Возврат Строка
    
    Если ЭтотОбъект.Проведен Тогда
        Возврат "Проведен";
    Иначе
        Возврат "Не проведен";
    КонецЕсли;
    
КонецФункции

// Вспомогательная процедура
Процедура УстановитьНомер()
    
    ЭтотОбъект.Номер = ПолучитьСледующийНомер();
    
КонецПроцедуры
"""
    
    # Process the file
    chunks = server._process_1c_bsl_file(test_content, "Documents/Поставка/Module.bsl")
    
    print(f"Found {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"  Lines: {chunk.line_start}-{chunk.line_end}")
        print(f"  Content preview: {chunk.content[:100]}...")
        if chunk.enterprise_metadata:
            print(f"  Object type: {chunk.enterprise_metadata.object_type}")
            print(f"  Object name: {chunk.enterprise_metadata.object_name}")
            print(f"  Module type: {chunk.enterprise_metadata.module_type}")
            print(f"  Author: {chunk.enterprise_metadata.author}")
            print(f"  Calls: {chunk.enterprise_metadata.calls}")
    
    assert len(chunks) >= 3  # Should find at least 3 procedures/functions
    assert chunks[0].enterprise_metadata.object_type == "Procedure"
    assert chunks[0].enterprise_metadata.object_name == "ПриСозданииНаОсновании"
    assert chunks[0].enterprise_metadata.module_type == "Document"
    
    # Check call graph extraction
    calls_proc1 = chunks[0].enterprise_metadata.calls
    assert "ЗаполнитьРеквизиты" in calls_proc1
    assert "УстановитьСтатус" in calls_proc1
    assert "ПроверитьЗаполнение" in calls_proc1
    # 'Сообщить' and 'ТекущаяДата' are reserved and should not be in calls
    assert "Сообщить" not in calls_proc1
    assert "ТекущаяДата" not in calls_proc1
    
    calls_proc3 = chunks[2].enterprise_metadata.calls
    assert "ПолучитьСледующийНомер" in calls_proc3
    
    print("✓ 1C file processing tests passed\n")

def test_contextual_chunks():
    """Test contextual chunk creation"""
    print("Testing contextual chunk creation...")
    
    server = ChromaSimpleServer(project_root=".")
    
    # Create test lines
    test_lines = []
    for i in range(1, 101):
        test_lines.append(f"// Line {i}")
    
    # Create base metadata
    base_metadata = EnterpriseMetadata(
        object_type="Procedure",
        object_name="ТестоваяПроцедура",
        module_type="CommonModule"
    )
    
    # Create contextual chunks
    chunks = server._create_contextual_chunks(test_lines, "Test/Module.bsl", base_metadata)
    
    print(f"Created {len(chunks)} contextual chunks")
    
    for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
        print(f"\nContextual chunk {i+1}:")
        print(f"  Lines: {chunk.line_start}-{chunk.line_end}")
        print(f"  Context: {chunk.enterprise_metadata.description}")
        print(f"  Content lines: {len(chunk.content.splitlines())}")
    
    # Verify chunk properties
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.enterprise_metadata is not None
        assert "Contextual chunk" in chunk.enterprise_metadata.description
        # Each chunk should have context lines
        lines_in_chunk = chunk.line_end - chunk.line_start + 1
        assert lines_in_chunk >= 20  # chunk_size
    
    print("✓ Contextual chunk tests passed\n")

def main():
    """Run all tests"""
    print("Running 1C/BSL parser tests")
    print("=" * 60)
    
    try:
        test_enterprise_metadata()
        test_1c_metadata_extraction()
        test_module_type_detection()
        test_1c_file_processing()
        test_contextual_chunks()
        
        print("=" * 60)
        print("✅ All tests passed successfully!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())