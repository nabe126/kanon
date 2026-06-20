import os
import pytest
from src.utils.validator import check_syntax, check_import

def test_check_syntax_success(tmp_path):
    """正常な文法のファイルを正しくPass判定できるかテストします。"""
    test_file = tmp_path / "valid_syntax.py"
    test_file.write_text("def hello():\n    return 'world'\n")
    
    success, err = check_syntax(str(test_file))
    assert success is True
    assert err is None

def test_check_syntax_fail(tmp_path):
    """文法エラー（SyntaxError）を検知してエラーを返却できるかテストします。"""
    test_file = tmp_path / "invalid_syntax.py"
    test_file.write_text("def hello(\n")  # 閉じ括弧エラー
    
    success, err = check_syntax(str(test_file))
    assert success is False
    assert err is not None

def test_check_import_success(tmp_path):
    """正常なインポートが記述されたモジュールをロードテストします。"""
    test_file = tmp_path / "valid_import.py"
    test_file.write_text("import os\nimport sys\n")
    
    success, err = check_import(str(test_file))
    assert success is True
    assert err is None

def test_check_import_fail(tmp_path):
    """存在しないライブラリ（ImportError）の検出ができるかテストします。"""
    test_file = tmp_path / "invalid_import.py"
    test_file.write_text("import non_existent_package_for_pytest_validation\n")
    
    success, err = check_import(str(test_file))
    assert success is False
    assert err is not None
    assert "non_existent_package" in err
