import os
import logging
from logging.handlers import RotatingFileHandler

def get_logger(name: str) -> logging.Logger:
    """エージェント用の構造化ログおよびファイルローテーションを設定したロガーを返却します。"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # ログ保存先ディレクトリ（コンテナ内 /workspace/state）の確認
        log_dir = "/workspace/state"
        if not os.path.exists(log_dir):
            # ローカル開発環境での動作も考慮し代替パスを確認
            log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../state"))
            
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "agent.log")
        
        # 最大1MB、バックアップ5世代のファイルローテーション設定
        handler = RotatingFileHandler(
            log_file, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8"
        )
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # コンテナ標準出力（stdout）にもログを流す
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
        
    return logger
