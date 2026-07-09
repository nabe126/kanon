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

@patch("monitor.restart_container_via_api")
def test_execute_rollback(mock_restart_api):
    """ロールバック実行時に、現在の異常コードが退避され、LKGから復元されるかをシミュレート検証します。"""
    # LKGを事前に登録
    good_snap = monitor.create_snapshot()
    monitor.save_lkg(good_snap)
    
    # 正常コードの内容を書き換え (エラー状態を模倣)
    with open(os.path.join(monitor.SRC_DIR, "discord_agent.py"), "w") as f:
        f.write("# Bad broken code\n")
        
    # Docker API 再起動呼び出しをモック
    mock_restart_api.return_value = True
    
    # ロールバック実行
    success = monitor.execute_rollback()
    assert success is True
    
    # 復元されたファイルの確認
    with open(os.path.join(monitor.SRC_DIR, "discord_agent.py"), "r") as f:
        content = f.read()
    assert content == "# Good logic code\n"  # 元の健康なコードに戻っていること

@patch("monitor.check_health")
@patch("monitor.execute_rollback")
@patch("monitor.time.sleep")
@patch("monitor.create_snapshot")
@patch("monitor.save_lkg")
def test_monitor_lifecycle(mock_save_lkg, mock_create_snapshot, mock_sleep, mock_rollback, mock_check_health):
    """monitor.py の main() ループ全体のライフサイクル（一時的失敗からの回復、および連続失敗からのロールバック）を検証します。"""
    # check_health の戻り値を順次設定
    # 起動時(True) -> ループ1(False) -> ループ2(True: 一時回復) -> ループ3(False) -> ループ4(False) -> ループ5(False: 3回失敗でロールバック)
    mock_check_health.side_effect = [
        True,   # 起動時: healthy
        False,  # ループ1: 一時的失敗 (1/3)
        True,   # ループ2: 一時的回復 (1/3 -> 0/3) -> 新規 LKG 保存
        False,  # ループ3: 再失敗 (1/3)
        False,  # ループ4: 連続失敗 (2/3)
        False,  # ループ5: 3回連続失敗 (3/3) -> ロールバック実行
    ]
    
    # execute_rollback の戻り値
    mock_rollback.return_value = True
    
    # time.sleep をモックし、呼び出しカウントを用いて無限ループを安全に脱出する
    sleep_calls = []
    def mock_sleep_func(seconds):
        sleep_calls.append(seconds)
        if len(sleep_calls) >= 5:  # 5回スリープが呼ばれたら（ループ5のロールバック後スリープ(60)時）KeyboardInterrupt でループを抜ける
            raise KeyboardInterrupt("Exit main loop for testing")
            
    mock_sleep.side_effect = mock_sleep_func
    
    # main() を実行し、意図的にスローした KeyboardInterrupt を捕捉する
    with pytest.raises(KeyboardInterrupt):
        monitor.main()
        
    # 検証項目:
    # 1. 起動時に check_health() が True だったため、初期 LKG が作成・保存されていること
    assert mock_create_snapshot.call_count >= 1
    assert mock_save_lkg.call_count >= 1
    
    # 2. ロールバックが呼び出されていること
    mock_rollback.assert_called_once()
    
    # 3. スナップショットと LKG が合計 2 回作成・保存されていること
    # - 起動時 (1回目)
    # - 一時回復時 (2回目)
    # - ロールバック後は LKG を復元しただけなので、追加の保存は走らない
    assert mock_create_snapshot.call_count == 2
    assert mock_save_lkg.call_count == 2


