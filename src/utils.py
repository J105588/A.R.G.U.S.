import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def initialize_database(db_path: Path):
    """
    データベースを初期化し、必要なテーブルを作成します。
    """
    try:
        db_path.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # requestsテーブル: 全ての通信リクエストを記録
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                method TEXT NOT NULL,
                host TEXT NOT NULL,
                path TEXT,
                status_code INTEGER,
                response_size INTEGER,
                user_agent TEXT,
                blocked INTEGER DEFAULT 0
            )
        ''')

        # blocked_contentテーブル: ブロックされた通信の詳細を記録
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                url TEXT NOT NULL,
                reason TEXT NOT NULL
            )
        ''')

        # settingsテーブル: システム設定を保存
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()
        logger.info(f"データベース '{db_path}' が正常に初期化されました。")
    except sqlite3.Error as e:
        logger.error(f"データベースの初期化に失敗しました: {e}")
        raise

def get_db_connection(db_path: Path):
    """
    データベース接続を取得します。
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"データベース接続の取得に失敗しました: {e}")
        return None