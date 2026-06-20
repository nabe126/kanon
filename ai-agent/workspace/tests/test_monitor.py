import os
import sys
import shutil
import time
import pytest
from unittest.mock import patch, MagicMock

# controller/monitor.py のインポート用パス解決
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../controller")))
import monitor

@pytest.fixture(autouse=True)
def setup_test_directories(tmp_path):
    """テスト用に monitor のパス設定を一時ディレクトリへリマッピングします。"""
    # 退避
    old_workspace = monitor.WORKSPACE_DIR
    old_src = monitor.SRC_DIR
    old_backup = monitor.BACKUP_DIR
    old_lkg = monitor.LKG_INFO_PATH
    
    # 一時フォルダの設定
    monitor.WORKSPACE_DIR = str(tmp_path)
    monitor.SRC_DIR = os.path.join(str(tmp_path), "src")
    monitor.BACKUP_DIR = os.path.join(str(tmp_path), "backups")
    monitor.LKG_INFO_PATH = os.path.join(monitor.BACKUP_DIR, "LKG.json")
    
    # ダミーの src/ ディレクトリと初期ファイルを作成
    os.makedirs(monitor.SRC_DIR, exist_ok=True)
    with open(os.path.join(monitor.SRC_DIR, "discord_agent.py"), "w") as f:
        f.write("# Good logic code\n")
        
    yield
    
    # 復元
    monitor.WORKSPACE_DIR = old_workspace
    monitor.SRC_DIR = old_src
    monitor.BACKUP_DIR = old_backup
    monitor.LKG_INFO_PATH = old_lkg

def test_create_snapshot_and_rotation():
    """スナップショットの作成と、最大世代数（5）によるローテーション制限を検証します。"""
    # 6回連続でスナップショット作成を要求 (タイムスタンプ衝突防止のため時間を少し進める)
    for i in range(6):
        # 内部時間文字列を上書き変更するためのモックを使用するか、微小スリープ
        time.sleep(1.05)
        monitor.create_snapshot()
        
    snapshots = [
        d for d in os.listdir(monitor.BACKUP_DIR) 
        if d.startswith("snapshot_") and os.path.isdir(os.path.join(monitor.BACKUP_DIR, d))
    ]
    
    # 世代数上限である5つに抑えられていることを検証
    assert len(snapshots) == 5

def test_save_and_get_lkg():
    """LKG.json の保存と読み込みによるスナップショットパスの追跡を検証します。"""
    snapshot_path = monitor.create_snapshot()
    monitor.save_lkg(snapshot_path)
    
    assert os.path.exists(monitor.LKG_INFO_PATH)
    
    lkg_path = monitor.get_lkg_path()
    assert os.path.basename(lkg_path) == os.path.basename(snapshot_path)

@patch("urllib.request.urlopen")
def test_check_health_healthy(mock_urlopen):
    """ヘルスチェック応答が healthy/warning 時の検知をテストします。"""
    # 200 Healthy
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"status": "healthy"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response
    assert monitor.check_health() is True
    
    # 200 Warning (これも正常扱い)
    mock_response.read.return_value = b'{"status": "warning"}'
    assert monitor.check_health() is True

@patch("urllib.request.urlopen")
def test_check_health_failed(mock_urlopen):
    """ヘルスチェック応答が critical または例外発生時の検知をテストします。"""
    # 200 Critical
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"status": "critical"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response
    assert monitor.check_health() is False
    
    # 例外エラー発生
    mock_urlopen.side_effect = Exception("Connection Refused")
    assert monitor.check_health() is False

@patch("subprocess.run")
def test_execute_rollback(mock_run):
    """ロールバック実行時に、現在の異常コードが退避され、LKGから復元されるかをシミュレート検証します。"""
    # LKGを事前に登録
    good_snap = monitor.create_snapshot()
    monitor.save_lkg(good_snap)
    
    # 正常コードの内容を書き換え (エラー状態を模倣)
    with open(os.path.join(monitor.SRC_DIR, "discord_agent.py"), "w") as f:
        f.write("# Bad broken code\n")
        
    # サブプロセスの戻り値をモック
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run.return_value = mock_res
    
    # ロールバック実行
    success = monitor.execute_rollback()
    assert success is True
    
    # 復元されたファイルの確認
    with open(os.path.join(monitor.SRC_DIR, "discord_agent.py"), "r") as f:
        content = f.read()
    assert content == "# Good logic code\n"  # 元の健康なコードに戻っていること
