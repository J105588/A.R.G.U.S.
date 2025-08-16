document.addEventListener('DOMContentLoaded', function() {
    const socket = io();

    // どのページにいるか判定
    const path = window.location.pathname;

    if (path.includes('/dashboard')) {
        setupDashboard(socket);
    }

    if (path.includes('/settings')) {
        setupSettings(socket);
    }
    
    // 全ページ共通のステータス更新
    socket.on('status_update', function(data) {
        if (document.getElementById('filtering-status')) {
            document.getElementById('filtering-status').textContent = data.filtering_enabled ? '有効' : '無効';
        }
        if (document.getElementById('filtering-enabled-toggle')) {
            document.getElementById('filtering-enabled-toggle').checked = data.filtering_enabled;
        }
         if (document.getElementById('filtering-status-text')) {
            document.getElementById('filtering-status-text').textContent = data.filtering_enabled ? '有効' : '無効';
        }
    });
});

function setupDashboard(socket) {
    socket.on('dashboard_update', function(data) {
        updateDashboard(data);
    });

    // 定期的に更新をリクエスト
    setInterval(() => {
        fetch('/api/stats/dashboard')
            .then(response => response.json())
            .then(data => updateDashboard(data));
    }, 5000); // 5秒ごとに更新
    
    // 初期データ取得
    fetch('/api/stats/dashboard')
        .then(response => response.json())
        .then(data => updateDashboard(data));
}

function updateDashboard(data) {
    document.getElementById('total-requests').textContent = data.total_requests ?? 'N/A';
    document.getElementById('blocked-requests').textContent = data.blocked_requests ?? 'N/A';
    document.getElementById('total-traffic').textContent = data.total_traffic_mb ?? 'N/A';

    const logBody = document.getElementById('blocked-log-body');
    if (logBody && data.recent_blocked) {
        logBody.innerHTML = ''; // Clear previous logs
        data.recent_blocked.forEach(log => {
            const row = document.createElement('tr');
            const timestamp = new Date(log.timestamp).toLocaleString();
            row.innerHTML = `
                <td>${timestamp}</td>
                <td>${log.client_ip}</td>
                <td>${escapeHtml(log.url)}</td>
                <td>${escapeHtml(log.reason)}</td>
            `;
            logBody.appendChild(row);
        });
    }
}


function setupSettings(socket) {
    const toggle = document.getElementById('filtering-enabled-toggle');
    const statusText = document.getElementById('filtering-status-text');

    toggle.addEventListener('change', function() {
        const isEnabled = this.checked;
        fetch('/api/settings/filtering', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: isEnabled })
        });
    });
    
    // 初期データ読み込み
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            toggle.checked = data.filtering_enabled;
            statusText.textContent = data.filtering_enabled ? '有効' : '無効';
        });

    loadRules('domains');
    loadRules('keywords');
}

function loadRules(ruleType) {
    fetch(`/api/rules/${ruleType}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById(`blocked-${ruleType}`).value = data.join('\n');
        });
}

function saveRules(ruleType) {
    const textarea = document.getElementById(`blocked-${ruleType}`);
    const rules = textarea.value.split('\n').filter(r => r.trim() !== '');
    
    fetch(`/api/rules/${ruleType}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules: rules })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`${ruleType.charAt(0).toUpperCase() + ruleType.slice(1)} のルールが保存されました。`);
        } else {
            alert('ルールの保存に失敗しました。');
        }
    });
}

function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}