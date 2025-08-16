from mitmproxy import http
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class NetworkMonitorAddon:
    def __init__(self, filter_manager):
        self.filter_manager = filter_manager
        
    def request(self, flow: http.HTTPFlow):
        """Called when an HTTP request is received."""
        # Do nothing if filtering is disabled
        if not self.filter_manager.filtering_enabled:
            return
            
        # Check if the request should be blocked
        should_block, reason = self._should_block(flow.request)
        
        if should_block:
            # Log the block event
            client_ip = flow.client_conn.address[0] if flow.client_conn.address else "unknown"
            self.filter_manager.log_blocked_request(client_ip, flow.request.pretty_url, reason)
            
            # Create a custom HTML response for the blocked page
            flow.response = http.HTTPResponse.make(
                403,  # Forbidden
                self._create_block_page_html(flow.request, reason),
                {"Content-Type": "text/html; charset=utf-8"}
            )
            logger.info(f"Blocked request from {client_ip} to {flow.request.pretty_url} due to: {reason}")
    
    def response(self, flow: http.HTTPFlow):
        """Called when an HTTP response is received."""
        # Log all traffic (if not already blocked)
        client_ip = flow.client_conn.address[0] if flow.client_conn.address else "unknown"
        is_blocked = flow.response.status_code == 403
        self.filter_manager.log_request(flow, client_ip, is_blocked)

    def _should_block(self, request: http.Request):
        """Determines if a request should be blocked based on current rules."""
        host = request.pretty_host.lower()
        url = request.pretty_url.lower()

        # Check against blocked domains
        for domain in self.filter_manager.blocked_domains:
            if domain in host:
                return True, f"Blocked Domain: {domain}"
        
        # Check against blocked keywords
        for keyword in self.filter_manager.blocked_keywords:
            if keyword in url:
                return True, f"Blocked Keyword: '{keyword}'"
        
        return False, None
    
    def _create_block_page_html(self, request, reason: str):
        """Generates the HTML content for the block page."""
        escaped_url = request.pretty_url.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>Access Blocked</title>
    <style>
        body {{ font-family: sans-serif; background-color: #f0f2f5; color: #333; text-align: center; padding: 50px; }}
        .container {{ background-color: white; padding: 40px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); display: inline-block; max-width: 600px; }}
        h1 {{ color: #d9534f; }}
        .url-display {{ background-color: #eee; padding: 10px; border-radius: 5px; word-wrap: break-word; text-align: left; margin: 20px 0; }}
        .reason {{ color: #d9534f; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>&#9940; Access Blocked</h1>
        <p>Your request to the following URL was blocked by the network filter:</p>
        <div class="url-display">{escaped_url}</div>
        <p><strong>Reason:</strong> <span class="reason">{reason}</span></p>
        <p><small>Blocked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
    </div>
</body>
</html>
"""