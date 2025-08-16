import threading
import json
from pathlib import Path
import logging
from datetime import datetime, timedelta

from .utils import initialize_database, get_db_connection

logger = logging.getLogger(__name__)

class NetworkFilterManager:
    def __init__(self, config_dir='config', data_dir='data'):
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / 'network_stats.db'

        self.config_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        initialize_database(self.db_path)

        self.lock = threading.Lock()
        
        self.blocked_domains_path = self.config_dir / 'blocked_domains.txt'
        self.blocked_keywords_path = self.config_dir / 'blocked_keywords.txt'
        
        self.blocked_domains = set()
        self.blocked_keywords = set()
        self.allowed_ips = set()
        
        self.filtering_enabled = True
        
        self.load_all_rules()

    def load_all_rules(self):
        """すべてのフィルタリングルールと設定を読み込みます。"""
        with self.lock:
            self._load_rules_from_file(self.blocked_domains_path, self.blocked_domains)
            self._load_rules_from_file(self.blocked_keywords_path, self.blocked_keywords)
            # 必要であれば、許可IPリストなどもここに追加
    
    def _load_rules_from_file(self, file_path, target_set):
        """指定されたファイルからルールを読み込み、セットを更新します。"""
        target_set.clear()
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        target_set.add(line.lower())
        logger.info(f"'{file_path}' から {len(target_set)} 件のルールを読み込みました。")

    def save_rules_to_file(self, file_path, source_set):
        """指定されたセットの内容をファイルに保存します。"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for item in sorted(list(source_set)):
                    f.write(f"{item}\n")
            logger.info(f"'{file_path}' にルールを保存しました。")
            return True
        except IOError as e:
            logger.error(f"ファイル '{file_path}' の保存に失敗しました: {e}")
            return False

    def get_status(self):
        """現在のフィルタリングステータスと統計情報を返します。"""
        with self.lock:
            return {
                "filtering_enabled": self.filtering_enabled,
                "blocked_domains_count": len(self.blocked_domains),
                "blocked_keywords_count": len(self.blocked_keywords),
                "allowed_ips_count": len(self.allowed_ips)
            }
            
    def get_dashboard_stats(self):
        """ダッシュボード用の統計情報をデータベースから取得します。"""
        conn = get_db_connection(self.db_path)
        if not conn:
            return {}

        try:
            cursor = conn.cursor()
            
            # 過去24時間の統計
            time_threshold = (datetime.now() - timedelta(hours=24)).isoformat()
            
            # 総リクエスト数
            total_requests = cursor.execute(
                "SELECT COUNT(id) FROM requests WHERE timestamp >= ?", (time_threshold,)
            ).fetchone()[0]

            # ブロックされたリクエスト数
            blocked_requests = cursor.execute(
                "SELECT COUNT(id) FROM blocked_content WHERE timestamp >= ?", (time_threshold,)
            ).fetchone()[0]

            # 通信量
            total_traffic = cursor.execute(
                "SELECT SUM(response_size) FROM requests WHERE timestamp >= ?", (time_threshold,)
            ).fetchone()[0] or 0

            # 最近のブロックイベント
            recent_blocked = cursor.execute(
                "SELECT timestamp, client_ip, url, reason FROM blocked_content ORDER BY timestamp DESC LIMIT 10"
            ).fetchall()

            conn.close()

            return {
                "total_requests": total_requests,
                "blocked_requests": blocked_requests,
                "total_traffic_mb": round(total_traffic / (1024 * 1024), 2),
                "recent_blocked": [dict(row) for row in recent_blocked]
            }
        except Exception as e:
            logger.error(f"ダッシュボード統計の取得に失敗: {e}")
            if conn:
                conn.close()
            return {}