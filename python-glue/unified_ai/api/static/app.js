// Mobile AI Assistant JavaScript

class MobileAssistant {
    constructor() {
        this.apiKey = localStorage.getItem('apiKey') || '';
        this.serverUrl = localStorage.getItem('serverUrl') || window.location.origin;
        this.conversationId = localStorage.getItem('conversationId') || null;
        this.useWebSocket = localStorage.getItem('useWebSocket') === 'true';
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadConversations();
        this.updateUI();
        
        if (this.useWebSocket && this.apiKey) {
            this.connectWebSocket();
        }
    }

    setupEventListeners() {
        // Send button
        document.getElementById('send-btn').addEventListener('click', () => this.sendMessage());
        
        // Enter key in input
        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Settings
        document.getElementById('settings-btn').addEventListener('click', () => this.togglePanel('settings'));
        document.getElementById('close-settings').addEventListener('click', () => this.togglePanel('settings'));
        document.getElementById('save-api-key').addEventListener('click', () => this.saveApiKey());
        document.getElementById('save-server-url').addEventListener('click', () => this.saveServerUrl());
        document.getElementById('use-websocket').addEventListener('change', (e) => {
            localStorage.setItem('useWebSocket', e.target.checked);
            this.useWebSocket = e.target.checked;
            if (e.target.checked && this.apiKey) {
                this.connectWebSocket();
            } else {
                this.disconnectWebSocket();
            }
        });

        // Conversations
        document.getElementById('conversations-btn').addEventListener('click', () => this.togglePanel('conversations'));
        document.getElementById('close-conversations').addEventListener('click', () => this.togglePanel('conversations'));
        document.getElementById('new-conversation-btn').addEventListener('click', () => this.newConversation());
    }

    togglePanel(panelName) {
        const panel = document.getElementById(`${panelName}-panel`);
        panel.classList.toggle('hidden');
    }

    updateUI() {
        // Update API key input
        document.getElementById('api-key-input').value = this.apiKey;
        document.getElementById('server-url-input').value = this.serverUrl;
        document.getElementById('use-websocket').checked = this.useWebSocket;
        
        // Update send button state
        const sendBtn = document.getElementById('send-btn');
        const messageInput = document.getElementById('message-input');
        
        if (!this.apiKey) {
            sendBtn.disabled = true;
            messageInput.placeholder = 'Configure API key in settings';
        } else {
            sendBtn.disabled = false;
            messageInput.placeholder = 'Ask anything...';
        }
    }

    async saveApiKey() {
        const apiKey = document.getElementById('api-key-input').value.trim();
        if (!apiKey) {
            alert('Please enter an API key');
            return;
        }
        
        this.apiKey = apiKey;
        localStorage.setItem('apiKey', apiKey);
        this.updateUI();
        
        if (this.useWebSocket) {
            this.connectWebSocket();
        }
        
        alert('API key saved!');
        this.togglePanel('settings');
    }

    async saveServerUrl() {
        const serverUrl = document.getElementById('server-url-input').value.trim();
        if (!serverUrl) {
            alert('Please enter a server URL');
            return;
        }
        
        this.serverUrl = serverUrl;
        localStorage.setItem('serverUrl', serverUrl);
        this.updateUI();
        
        if (this.useWebSocket) {
            this.disconnectWebSocket();
            this.connectWebSocket();
        }
        
        alert('Server URL saved!');
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message) return;
        if (!this.apiKey) {
            alert('Please configure API key in settings');
            return;
        }

        // Clear input
        input.value = '';
        
        // Add user message to UI
        this.addMessage('user', message);
        
        // Show typing indicator
        this.showTypingIndicator();

        if (this.useWebSocket && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.sendWebSocketMessage(message);
        } else {
            this.sendRESTMessage(message);
        }
    }

    async sendRESTMessage(message) {
        try {
            const url = `${this.serverUrl}/api/v1/chat`;
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey,
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId,
                }),
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Invalid API key. Please check your settings.');
                }
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            this.hideTypingIndicator();
            this.addMessage('assistant', data.content);
            
            // Update conversation ID if new
            if (data.conversation_id && !this.conversationId) {
                this.conversationId = data.conversation_id;
                localStorage.setItem('conversationId', this.conversationId);
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('error', `Error: ${error.message}`);
        }
    }

    connectWebSocket() {
        if (!this.apiKey) return;
        
        const wsUrl = this.serverUrl.replace('http://', 'ws://').replace('https://', 'wss://');
        const wsEndpoint = `${wsUrl}/api/v1/ws/chat`;
        
        try {
            this.ws = new WebSocket(wsEndpoint);
            
            this.ws.onopen = () => {
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected', 'Connected');
                // Send API key as first message
                this.ws.send(JSON.stringify({
                    type: 'auth',
                    api_key: this.apiKey,
                }));
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'chunk') {
                    this.appendToLastMessage(data.content);
                } else if (data.type === 'start') {
                    this.hideTypingIndicator();
                    this.addMessage('assistant', '');
                } else if (data.type === 'end') {
                    // Message complete
                } else if (data.type === 'error') {
                    this.hideTypingIndicator();
                    this.addMessage('error', data.message);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus('disconnected', 'Connection error');
            };
            
            this.ws.onclose = () => {
                this.updateConnectionStatus('disconnected', 'Disconnected');
                // Attempt to reconnect
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    setTimeout(() => this.connectWebSocket(), 2000 * this.reconnectAttempts);
                }
            };
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.updateConnectionStatus('disconnected', 'WebSocket unavailable');
        }
    }

    disconnectWebSocket() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    sendWebSocketMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'chat',
                message: message,
                conversation_id: this.conversationId,
            }));
        } else {
            // Fallback to REST
            this.sendRESTMessage(message);
        }
    }

    addMessage(role, content) {
        const messagesContainer = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.dataset.role = role;
        
        const contentDiv = document.createElement('div');
        contentDiv.textContent = content;
        messageDiv.appendChild(contentDiv);
        
        const timestamp = document.createElement('div');
        timestamp.className = 'timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();
        messageDiv.appendChild(timestamp);
        
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    appendToLastMessage(content) {
        const messages = document.querySelectorAll('.message.assistant');
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            const contentDiv = lastMessage.querySelector('div:first-child');
            if (contentDiv) {
                contentDiv.textContent += content;
                this.scrollToBottom();
            }
        }
    }

    showTypingIndicator() {
        document.getElementById('typing-indicator').classList.remove('hidden');
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        document.getElementById('typing-indicator').classList.add('hidden');
    }

    scrollToBottom() {
        const container = document.querySelector('.chat-container');
        container.scrollTop = container.scrollHeight;
    }

    updateConnectionStatus(status, message) {
        const statusEl = document.getElementById('connection-status');
        statusEl.className = `connection-status ${status}`;
        statusEl.textContent = message;
        statusEl.classList.remove('hidden');
        
        if (status === 'connected') {
            setTimeout(() => statusEl.classList.add('hidden'), 2000);
        }
    }

    newConversation() {
        this.conversationId = null;
        localStorage.removeItem('conversationId');
        document.getElementById('chat-messages').innerHTML = '';
        this.togglePanel('conversations');
    }

    async loadConversations() {
        // TODO: Implement conversation loading from API
        // For now, just show current conversation
        const list = document.getElementById('conversations-list');
        if (this.conversationId) {
            const item = document.createElement('div');
            item.className = 'conversation-item active';
            item.innerHTML = `
                <h3>Current Conversation</h3>
                <p>ID: ${this.conversationId.substring(0, 8)}...</p>
            `;
            list.appendChild(item);
        }
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new MobileAssistant();
    });
} else {
    new MobileAssistant();
}
