(function () {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get('session');
  if (!sessionId) {
    alert('缺少会话 ID');
    window.location.href = '/';
    return;
  }

  const messagesEl = document.getElementById('messages');
  const inputEl = document.getElementById('msg-input');
  const sendBtn = document.getElementById('send-btn');
  const endBtn = document.getElementById('end-btn');
  const personaNameEl = document.getElementById('persona-name');
  const personaMetaEl = document.getElementById('persona-meta');
  const sessionAvatarEl = document.getElementById('session-avatar');
  const statTurnsEl = document.getElementById('stat-turns');
  const statDifficultyEl = document.getElementById('stat-difficulty');

  const DIFFICULTY_LABEL = { easy: '简单', medium: '中等', hard: '困难' };

  let sending = false;
  let turnCount = 0;

  function avatarChar(name) {
    if (!name) return '·';
    const trimmed = String(name).trim();
    const stripped = trimmed.replace(/^(张|王|李|赵|刘|陈|杨|黄|周|吴|徐|孙|马|朱|胡|郭|何|林|高|罗)/, '');
    return (stripped || trimmed).slice(0, 1).toUpperCase();
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
  }

  function addBubble(role, text, opts) {
    opts = opts || {};
    const row = document.createElement('div');
    row.className = 'chat-row ' + role;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar ' + role;
    avatar.textContent = role === 'user' ? '我' : '客';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble ' + role + (opts.error ? ' error' : '');
    if (opts.html) {
      bubble.innerHTML = opts.html;
    } else {
      bubble.textContent = text;
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return row;
  }

  function setLoading(show) {
    if (show) {
      const row = addBubble('assistant', '', {
        html: '<span class="typing"><span></span><span></span><span></span></span>',
      });
      row.id = 'loading-bubble';
    } else {
      const el = document.getElementById('loading-bubble');
      if (el) el.remove();
    }
  }

  async function loadSession() {
    try {
      const resp = await fetch('/api/sessions/' + sessionId);
      if (!resp.ok) {
        personaNameEl.textContent = '会话异常';
        personaMetaEl.textContent = '请返回首页重新创建';
        return;
      }
      const data = await resp.json();
      personaNameEl.textContent = data.persona_name || '客户';
      sessionAvatarEl.textContent = avatarChar(data.persona_name);
      personaMetaEl.textContent =
        '难度：' + (DIFFICULTY_LABEL[data.difficulty] || data.difficulty) +
        ' · 会话 ID: ' + (data.session_id || '').slice(0, 8);
      statDifficultyEl.textContent = DIFFICULTY_LABEL[data.difficulty] || '—';
      turnCount = data.turn_count || 0;
      statTurnsEl.textContent = turnCount;
    } catch (e) {
      personaNameEl.textContent = '加载失败';
      personaMetaEl.textContent = e.message;
    }
  }

  function dismissEmptyState() {
    const empty = document.getElementById('empty-state');
    if (empty) empty.remove();
  }

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text || sending) return;
    sending = true;
    sendBtn.disabled = true;
    inputEl.value = '';
    dismissEmptyState();
    addBubble('user', text);
    setLoading(true);

    try {
      const resp = await fetch('/api/sessions/' + sessionId + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      setLoading(false);
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        addBubble('assistant', '[错误] ' + (err.detail || resp.statusText), { error: true });
        return;
      }
      const data = await resp.json();
      addBubble('assistant', data.response);
      if (typeof data.turn_count === 'number') {
        turnCount = data.turn_count;
        statTurnsEl.textContent = turnCount;
      }
    } catch (e) {
      setLoading(false);
      addBubble('assistant', '[网络错误] ' + e.message, { error: true });
    } finally {
      sending = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  sendBtn.addEventListener('click', sendMessage);
  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  endBtn.addEventListener('click', function () {
    if (turnCount === 0) {
      if (!confirm('你还没发起任何对话，确定要直接结束并查看报告吗？')) return;
    }
    window.location.href = '/report.html?session=' + sessionId;
  });

  loadSession();
  inputEl.focus();
})();
