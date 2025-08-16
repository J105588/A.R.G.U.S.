import os
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from mitmproxy import certs

logger = logging.getLogger(__name__)

def create_web_app(filter_manager):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config['SECRET_KEY'] = 'secret_key_for_network_monitor'
    socketio = SocketIO(app)

    @app.route('/')
    def index():
        return render_template('index.html')
        
    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/settings')
    def settings():
        return render_template('settings.html')

    @app.route('/certificate')
    def certificate_page():
        # このページは証明書ダウンロード用のリンクを動的に表示します
        mitmproxy_cert_dir = Path.home() / '.mitmproxy'
        cert_files = {
            'pem': 'mitmproxy-ca-cert.pem',
            'p12': 'mitmproxy-ca-cert.p12',
            'cer': 'mitmproxy-ca-cert.cer' # Windows用の一般的な拡張子
        }
        available_certs = {name: file for name, file in cert_files.items() 
                           if (mitmproxy_cert_dir / file).exists()}
        return render_template('certificate.html', certs=available_certs)

    @app.route('/download_cert/<filename>')
    def download_cert(filename):
        # 証明書ファイルをダウンロードさせるためのエンドポイント
        mitmproxy_cert_dir = Path.home() / '.mitmproxy'
        return send_from_directory(mitmproxy_cert_dir, filename, as_attachment=True)

    # --- API Endpoints ---

    @app.route('/api/status', methods=['GET'])
    def get_status():
        return jsonify(filter_manager.get_status())

    @app.route('/api/cert_status', methods=['GET'])
    def get_cert_status_api():
        """
        Mitmproxyの証明書の存在を、公式のcertsモジュールを使って確認します。
        これにより、OSやユーザー名に依存しない、より堅牢なチェックが可能になります。
        """
        try:
            # certs.default_ca() は証明書ストアのデフォルトCAオブジェクトを返します
            store = certs.default_ca() 
            # .get_cert_path() で証明書ファイルへのフルパスを取得します
            cert_path = store.get_cert_path(certs.types.PEM) # .pem形式の証明書パスを取得
            
            if os.path.exists(cert_path):
                # 証明書が存在する場合
                return jsonify({"installed": True, "path": cert_path})
            else:
                # パスは取得できたが、ファイルが存在しない場合 (通常はありえません)
                return jsonify({"installed": False, "path": None})
        except Exception as e:
            # .mitmproxyフォルダが存在しない、などの理由でエラーになった場合
            logger.error(f"Certificate status check failed: {e}")
            return jsonify({"installed": False, "path": None})

    @app.route('/api/settings/filtering', methods=['POST'])
    def set_filtering_status():
        data = request.json
        if 'enabled' in data and isinstance(data['enabled'], bool):
            filter_manager.filtering_enabled = data['enabled']
            socketio.emit('status_update', {'filtering_enabled': filter_manager.filtering_enabled})
            logger.info(f"フィルタリング状態が {'有効' if data['enabled'] else '無効'} に変更されました。")
            return jsonify({"success": True, "enabled": filter_manager.filtering_enabled})
        return jsonify({"success": False, "error": "Invalid request"}), 400

    @app.route('/api/rules/<rule_type>', methods=['GET', 'POST'])
    def manage_rules(rule_type):
        if rule_type not in ['domains', 'keywords']:
            return jsonify({"success": False, "error": "Invalid rule type"}), 404

        path = filter_manager.blocked_domains_path if rule_type == 'domains' else filter_manager.blocked_keywords_path
        target_set = filter_manager.blocked_domains if rule_type == 'domains' else filter_manager.blocked_keywords
        
        if request.method == 'GET':
            return jsonify(sorted(list(target_set)))
        
        if request.method == 'POST':
            data = request.json
            if 'rules' in data and isinstance(data['rules'], list):
                with filter_manager.lock:
                    target_set.clear()
                    target_set.update([r.strip().lower() for r in data['rules'] if r.strip()])
                    filter_manager.save_rules_to_file(path, target_set)
                logger.info(f"ブロック対象の{rule_type}が更新されました。")
                socketio.emit('rules_updated', {'type': rule_type})
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "Invalid data format"}), 400

    @app.route('/api/stats/dashboard', methods=['GET'])
    def get_dashboard_stats():
        stats = filter_manager.get_dashboard_stats()
        return jsonify(stats)

    # --- SocketIO Events ---
    
    @socketio.on('connect')
    def handle_connect():
        logger.info('Web管理画面にクライアントが接続しました。')
        emit_initial_data()

    def emit_initial_data():
        """接続時に初期データをクライアントに送信します。"""
        socketio.emit('status_update', filter_manager.get_status())
        socketio.emit('dashboard_update', filter_manager.get_dashboard_stats())

    # 定期的にダッシュボードデータを更新するための外部からのトリガー用
    app.config['socketio'] = socketio
    app.config['filter_manager'] = filter_manager

    return app