// chatbot.js — TNEB Email Support Chatbot Frontend

let sessionData = {};

function getTime() {
    return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

function appendMessage(text, isUser = false) {
    const win = document.getElementById('chatWindow');
    const div = document.createElement('div');
    div.className = `chat-message ${isUser ? 'user-message' : 'bot-message'}`;

    if (isUser) {
        div.innerHTML = `
            <div class="message-bubble">
                <div class="message-text">${escapeHtml(text)}</div>
                <div class="message-time">${getTime()}</div>
            </div>
            <div class="bot-avatar" style="background:#0F8B8D">
                <i class="bi bi-person-fill"></i>
            </div>`;
    } else {
        div.innerHTML = `
            <div class="bot-avatar"><i class="bi bi-robot"></i></div>
            <div class="message-bubble">
                <div class="message-text">${text}</div>
                <div class="message-time">${getTime()}</div>
            </div>`;
    }

    win.appendChild(div);
    win.scrollTop = win.scrollHeight;
    return div;
}

function appendBotWithReplies(text, quickReplies = [], ticketCreated = null) {
    const win = document.getElementById('chatWindow');
    const div = document.createElement('div');
    div.className = 'chat-message bot-message';

    let qrHTML = '';
    if (quickReplies.length > 0) {
        qrHTML = `<div class="quick-replies mt-2">` +
            quickReplies.map(r =>
                `<button class="quick-reply-btn" onclick="sendQuick('${r.replace(/'/g, "\\'")}')">${r}</button>`
            ).join('') +
            `</div>`;
    }

    let ticketHTML = '';
    if (ticketCreated) {
        ticketHTML = `
            <div class="mt-2">
                <a href="/tickets/track?id=${ticketCreated.id}" class="btn btn-sm btn-outline-primary" target="_blank">
                    <i class="bi bi-search me-1"></i>Track ${ticketCreated.id}
                </a>
            </div>`;
    }

    div.innerHTML = `
        <div class="bot-avatar"><i class="bi bi-robot"></i></div>
        <div class="message-bubble">
            <div class="message-text">${text}</div>
            ${qrHTML}
            ${ticketHTML}
            <div class="message-time">${getTime()}</div>
        </div>`;

    win.appendChild(div);
    win.scrollTop = win.scrollHeight;

    // Disable all previous quick-reply buttons
    win.querySelectorAll('.quick-reply-btn:not(:disabled)').forEach((btn, idx, arr) => {
        if (idx < arr.length - (quickReplies.length)) {
            btn.disabled = true;
        }
    });
}

function showTyping() {
    document.getElementById('typingIndicator').style.display = 'flex';
    const win = document.getElementById('chatWindow');
    win.scrollTop = win.scrollHeight;
}

function hideTyping() {
    document.getElementById('typingIndicator').style.display = 'none';
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    appendMessage(text, true);
    showTyping();

    // Update active nav item based on common patterns
    updateNavActive(text);

    try {
        const res = await fetch('/chatbot/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, session_data: sessionData })
        });
        const data = await res.json();

        // Simulate typing delay
        const delay = Math.min(Math.max(data.text.length * 8, 600), 1800);
        setTimeout(() => {
            hideTyping();
            appendBotWithReplies(data.text, data.quick_replies || [], data.ticket_created);
            sessionData = data.session_data || {};
        }, delay);

    } catch (err) {
        hideTyping();
        appendBotWithReplies('⚠️ Connection error. Please try again.', ['Retry', 'Go to home']);
    }
}

function sendQuick(text) {
    document.getElementById('chatInput').value = text;
    sendMessage();
}

function updateNavActive(text) {
    const lower = text.toLowerCase();
    const map = {
        'search': 0, 'email': 0,
        'password': 1, 'forgot': 1,
        'not received': 2, 'inbox': 2,
        'send': 3, 'outbox': 3,
        'login': 4, 'signin': 4,
        'locked': 5, 'blocked': 5,
        'track': 6, 'ticket': 6,
    };
    const items = document.querySelectorAll('.chat-nav-item');
    for (const [key, idx] of Object.entries(map)) {
        if (lower.includes(key) && items[idx]) {
            items.forEach(i => i.classList.remove('active'));
            items[idx].classList.add('active');
            break;
        }
    }
}

// Enter key on chat input
document.addEventListener('DOMContentLoaded', () => {
    const inp = document.getElementById('chatInput');
    if (inp) {
        inp.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
});
