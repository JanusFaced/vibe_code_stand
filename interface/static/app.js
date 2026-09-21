const chat = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const status = document.getElementById('status');

let ws = null;
let reconnectTimer = null;

// Состояние группировки
let lastGroup = null;   // DOM-элемент последней группы агента
let lastRole = null;    // роль последнего сообщения


// ============================================================
// WebSocket
// ============================================================

function connect() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${protocol}://${location.host}/ws`);
    
    ws.onopen = () => {
        status.textContent = 'Подключено';
        status.className = 'connected';
        sendBtn.disabled = false;
    };
    
    ws.onclose = () => {
        status.textContent = 'Отключено';
        status.className = 'disconnected';
        sendBtn.disabled = true;
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(connect, 2000);
    };
    
    ws.onerror = () => {
        status.textContent = 'Ошибка';
        status.className = 'disconnected';
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };
}


// ============================================================
// Обработка сообщений
// ============================================================

function handleMessage(data) {
    switch (data.type) {
        case 'history':
            data.messages.forEach(m => addMessage(m.role, m.content, false));
            scrollToBottom();
            break;
        case 'user_ack':
            break;
        case 'output':
            addAgentOutput(data.text);
            break;
        case 'status':
            addMessage('system', data.text);
            break;
        case 'status_report':
            addMessage('system', `Запущено: ${data.running.join(', ') || 'ничего'}`);
            break;
        case 'error':
            addMessage('error', data.text);
            break;
        case 'done':
            addMessage('system', `Процесс ${data.target} завершён (код ${data.code})`);
            break;
        case 'heartbeat':
            // игнорируем
            break;
    }
}


// ============================================================
// Группировка output агента
// ============================================================

function addAgentOutput(text) {
    // Если предыдущее было от агента и есть группа — добавляем в неё
    if (lastRole === 'agent' && lastGroup) {
        const content = lastGroup.querySelector('.content');
        const line = document.createElement('div');
        line.className = getLineClass(text);
        line.textContent = text;
        content.appendChild(line);
    } else {
        // Создаём новую группу (без имени роли)
        const div = document.createElement('div');
        div.className = 'msg agent grouped';
        
        const content = document.createElement('div');
        content.className = 'content';
        
        const line = document.createElement('div');
        line.className = getLineClass(text);
        line.textContent = text;
        content.appendChild(line);
        
        div.appendChild(content);
        chat.appendChild(div);
        
        lastGroup = div;
    }
    
    lastRole = 'agent';
    scrollToBottom();
}


function getLineClass(text) {
    if (!text) return '';
    const lower = text.toLowerCase();
    
    if (text.includes('❌') || lower.includes('error') || lower.includes('traceback')) {
        return 'line-error';
    }
    if (text.includes('✅')) {
        return 'line-success';
    }
    if (text.includes('⚠️')) {
        return 'line-warn';
    }
    return '';
}


// ============================================================
// Обычные сообщения (с именем роли)
// ============================================================

function addMessage(role, content, scroll = true) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    
    const roleLabels = {
        user: 'Вы',
        agent: 'Агент',
        system: 'Система',
        error: 'Ошибка'
    };
    
    const roleDiv = document.createElement('div');
    roleDiv.className = 'role';
    roleDiv.textContent = roleLabels[role] || role;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    contentDiv.textContent = content;
    
    div.appendChild(roleDiv);
    div.appendChild(contentDiv);
    chat.appendChild(div);
    
    // Сбрасываем группировку — следующее output создаст новую группу
    lastGroup = null;
    lastRole = role;
    
    if (scroll) scrollToBottom();
}


// ============================================================
// Скролл
// ============================================================

function isNearBottom() {
    return chat.scrollHeight - chat.scrollTop - chat.clientHeight < 100;
}

function scrollToBottom() {
    // Автоскролл только если пользователь уже внизу
    if (isNearBottom()) {
        chat.scrollTop = chat.scrollHeight;
    }
}


// ============================================================
// Отправка
// ============================================================

function sendMessage() {
    const text = input.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    
    addMessage('user', text);
    input.value = '';
    
    ws.send(JSON.stringify({ text }));
}

sendBtn.onclick = sendMessage;
input.onkeydown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
};

connect();