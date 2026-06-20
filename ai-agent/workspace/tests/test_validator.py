import os
import pytest
from src.utils.validator import check_syntax, check_import, apply_candidate_code

def test_check_syntax_success(tmp_path) -> None:
    """正常な文法のファイルを正しくPass判定できるかテストします。"""
    test_file = tmp_path / "valid_syntax.py"
    test_file.write_text("def hello():\n    return 'world'\n")
    
    success, err = check_syntax(str(test_file))
    assert success is True
    assert err is None

def test_check_syntax_fail(tmp_path) -> None:
    """文法エラー（SyntaxError）を検知してエラーを返却できるかテストします。"""
    test_file = tmp_path / "invalid_syntax.py"
    test_file.write_text("def hello(\n")  # 閉じ括弧エラー
    
    success, err = check_syntax(str(test_file))
    assert success is False
    assert err is not None

def test_check_import_success(tmp_path) -> None:
    """正常なインポートが記述されたモジュールをロードテストします。"""
    test_file = tmp_path / "valid_import.py"
    test_file.write_text("import os\nimport sys\n")
    
    success, err = check_import(str(test_file))
    assert success is True
    assert err is None

def test_check_import_fail(tmp_path) -> None:
    """存在しないライブラリ（ImportError）の検出ができるかテストします。"""
    test_file = tmp_path / "invalid_import.py"
    test_file.write_text("import non_existent_package_for_pytest_validation\n")
    
    success, err = check_import(str(test_file))
    assert success is False
    assert err is not None
    assert "non_existent_package" in err

def test_apply_candidate_code_success(tmp_path) -> None:
    """候補コードの検証・適用が成功し、バックアップが作成されるテスト"""
    candidate = tmp_path / "candidate.py"
    target = tmp_path / "target.py"
    backup_dir = tmp_path / "backups"
    
    candidate.write_text("def run():\n    return 42\n")
    target.write_text("def run():\n    return 0\n")
    
    success, err = apply_candidate_code(str(candidate), str(target), str(backup_dir))
    assert success is True
    assert err is None
    
    # 適用されたか確認
    assert target.read_text() == "def run():\n    return 42\n"
    
    # バックアップが作成されたか確認
    backup_file = backup_dir / "target.py.bk"
    assert backup_file.exists()
    assert backup_file.read_text() == "def run():\n    return 0\n"

def test_apply_candidate_code_fail_syntax(tmp_path) -> None:
    """構文エラー時に適用が拒否され、既存コードが維持されるテスト"""
    candidate = tmp_path / "candidate.py"
    target = tmp_path / "target.py"
    backup_dir = tmp_path / "backups"
    
    candidate.write_text("def run(\n") # 構文エラー
    target.write_text("def run():\n    return 0\n")
    
    success, err = apply_candidate_code(str(candidate), str(target), str(backup_dir))
    assert success is False
    assert "Syntax verification failed" in err
    
    # 既存コードが維持されているか確認
    assert target.read_text() == "def run():\n    return 0\n"
    assert not (backup_dir / "target.py.bk").exists()

def test_apply_candidate_code_fail_import(tmp_path) -> None:
    """インポートエラー時に適用が拒否され、既存コードが維持されるテスト"""
    candidate = tmp_path / "candidate.py"
    target = tmp_path / "target.py"
    backup_dir = tmp_path / "backups"
    
    candidate.write_text("import non_existent_pkg_name\n") # インポートエラー
    target.write_text("def run():\n    return 0\n")
    
    success, err = apply_candidate_code(str(candidate), str(target), str(backup_dir))
    assert success is False
    assert "Import verification failed" in err
    
    # 既存コードが維持されているか確認
    assert target.read_text() == "def run():\n    return 0\n"
    assert not (backup_dir / "target.py.bk").exists()
