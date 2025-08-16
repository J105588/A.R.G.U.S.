import logging
from datetime import datetime
from urllib.parse import unquote

from mitmproxy import http
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)

class NetworkMonitorAddon:
    """
    mitmproxyのアドオンとして動作し、リクエストのフィルタリングとロギングを行うクラス。
    """
    def __init__(self, filter_manager):
        """
        アドオンを初期化し、FilterManagerとJinja2テンプレート環境を設定します。
        """
        self.filter_manager = filter_manager
        
        # --- ここからが今回の修正の主要部分 ---
        try:
            # Jinja2のテンプレート環境をセットアップ
            # 'templates'ディレクトリをテンプレートの置き場所として指定
            self.jinja_env = Environment(
                loader=FileSystemLoader('templates/'),
                autoescape=True  # XSS対策としてautoescapeを有効化
            )
            # ブロックページのテンプレートを読み込む
            self.block_template = self.jinja_env.get_template('blocked_page.html')
            logger.info("ブロックページテンプレート 'templates/blocked_page.html' を正常に読み込みました。")
        except TemplateNotFound:
            logger.critical("重大: ブロックページテンプレート 'templates/blocked_page.html' が見つかりません。")
            self.block_template = None
        except Exception as e:
            logger.error(f"Jinja2環境の初期化中に予期せぬエラーが発生しました: {e}")
            self.block_template = None
        # --- 修正ここまで ---

    def request(self, flow: http.HTTPFlow):
        """HTTPリクエスト受信時に呼び出されます。"""
        if not self.filter_manager.filtering_enabled:
            return
            
        # リクエストをブロックすべきか判定
        should_block, reason, blocked_value = self._should_block(flow.request)
        
        if should_block:
            client_ip = flow.client_conn.address[0] if flow.client_conn.address else "unknown"
            # データベースにブロックイベントを記録
            self.filter_manager.log_blocked_request(client_ip, flow.request.pretty_url, reason)
            
            # ブロックページを生成してレスポンスとして返す
            flow.response = http.HTTPResponse.make(
                200,  # ブロックページ自体は正常に表示されるため200 OKが一般的
                self._create_block_page_html(reason, blocked_value),
                {"Content-Type": "text/html; charset=utf-8"}
            )
            logger.info(f"BLOCK: {client_ip} -> {flow.request.pretty_url} | Reason: {reason}")
    
    def response(self, flow: http.HTTPFlow):
        """HTTPレスポンス受信時に呼び出されます。"""
        # (このメソッドは今回の修正範囲外ですが、一貫性のために残します)
        client_ip = flow.client_conn.address[0] if flow.client_conn.address else "unknown"
        # リクエストがブロックされた場合、flow.responseはここで設定したブロックページになる
        is_blocked = flow.response.headers.get("X-Blocked-By") == "A.R.G.U.S."
        self.filter_manager.log_request(flow, client_ip, is_blocked)

    def _should_block(self, request: http.Request) -> tuple[bool, str | None, str | None]:
        """
        現在のルールに基づき、リクエストをブロックすべきかどうかを判断します。
        
        Returns:
            (ブロックすべきか, ブロック理由, ブロックされた値) のタプル。
        """
        host = request.pretty_host.lower()
        # URLデコードしたパス/クエリをチェック対象とする
        path_and_query = unquote(request.path).lower()

        # ドメインブロックのチェック
        for domain in self.filter_manager.blocked_domains:
            if domain in host:
                return True, "ブロック対象ドメイン", domain
        
        # キーワードブロックのチェック
        for keyword in self.filter_manager.blocked_keywords:
            # URL全体ではなく、パスとクエリパラメータ部分のみをチェックするのが一般的
            if keyword in path_and_query:
                return True, "ブロック対象キーワード", keyword
        
        return False, None, None
    
    def _create_block_page_html(self, reason: str, blocked_value: str) -> bytes:
        """
        Jinja2テンプレートを使用して、ブロックページのHTMLコンテンツを生成します。
        
        Returns:
            bytes: UTF-8でエンコードされたHTMLコンテンツ。
        """
        # --- ここからが今回の修正の主要部分 ---
        if self.block_template:
            try:
                # テンプレートに変数を渡してHTMLをレンダリング
                html_content = self.block_template.render(
                    reason=reason,
                    blocked_value=blocked_value
                )
                return html_content.encode('utf-8')
            except Exception as e:
                logger.error(f"ブロックページのレンダリングに失敗しました: {e}")
                # レンダリング失敗時のフォールバックHTML
                fallback_html = f"<h1>Access Blocked</h1><p>Reason: {reason}</p><p>Error: Block page could not be rendered.</p>"
                return fallback_html.encode('utf-8')
        else:
            # テンプレート自体が読み込めていない場合の最終フォールバック
            logger.critical("テンプレートが利用できないため、最小限のブロックページを返します。")
            fallback_html = f"<h1>Access Blocked</h1><p>Reason: {reason}</p><p>System Error: Block page template is missing.</p>"
            return fallback_html.encode('utf-8')
        # --- 修正ここまで ---
