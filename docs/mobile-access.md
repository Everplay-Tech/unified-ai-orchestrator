# Mobile Remote Access Guide

This guide explains how to set up and use the mobile web interface to access your AI assistant from anywhere.

## Overview

The mobile interface allows you to chat with your AI assistant running on your home computer using any mobile device's web browser. It features:

- Responsive mobile-optimized UI
- API key authentication for security
- WebSocket support for real-time streaming responses
- Progressive Web App (PWA) support for home screen installation
- Conversation history management
- Offline support (view cached conversations)

## Prerequisites

- AI assistant server running on your home computer
- Mobile device with modern web browser (iOS Safari, Chrome, Firefox, etc.)
- Network access to your home computer (same WiFi or port forwarding configured)

## Setup Instructions

### Step 1: Generate Mobile API Key

On your home computer, generate a secure API key:

```bash
uai mobile-key --generate
```

This will:
- Generate a cryptographically secure API key
- Store it securely in your system keyring
- Display the key for you to save

**Important**: Save this API key securely. You'll need it to access the mobile interface.

You can view your current API key anytime with:
```bash
uai mobile-key --show
```

### Step 2: Start the Server

Start the API server on your home computer:

```bash
python -m unified_ai.api.server
```

Or if installed via pip:
```bash
uai server  # If this command exists, or use the Python module directly
```

The server will start on `http://0.0.0.0:8000` by default.

### Step 3: Configure Network Access

#### Option A: Same WiFi Network (Local Access)

If your mobile device is on the same WiFi network:

1. Find your computer's local IP address:
   - **macOS/Linux**: `ifconfig | grep "inet "` or `ip addr show`
   - **Windows**: `ipconfig`
2. Access from mobile browser: `http://YOUR_COMPUTER_IP:8000`

#### Option B: Remote Access (Port Forwarding)

To access from outside your home network:

1. **Configure Router Port Forwarding**:
   - Log into your router's admin panel (usually `192.168.1.1` or `192.168.0.1`)
   - Set up port forwarding:
     - External Port: `8000` (or any available port)
     - Internal IP: Your computer's local IP
     - Internal Port: `8000`
     - Protocol: TCP
   - Save and apply changes

2. **Find Your Public IP**:
   - Visit `https://whatismyipaddress.com` from your home computer
   - Note your public IP address

3. **Access from Mobile**:
   - Use `http://YOUR_PUBLIC_IP:8000` (or your forwarded port)
   - **Security Note**: For production use, set up HTTPS with a reverse proxy (see Security section)

### Step 4: Configure Mobile Browser

1. Open your mobile browser and navigate to the server URL
2. You'll see the mobile chat interface
3. Tap the settings icon (⚙️) in the top right
4. Enter your API key (from Step 1)
5. Optionally configure the server URL if different from current page
6. Save settings

### Step 5: Start Chatting

- Type your message in the input field
- Tap "Send" or press Enter
- Responses will appear in real-time
- Enable WebSocket in settings for streaming responses

## Progressive Web App (PWA) Installation

The mobile interface can be installed as a PWA on your device's home screen:

### iOS (Safari)

1. Open the mobile interface in Safari
2. Tap the Share button (square with arrow)
3. Scroll down and tap "Add to Home Screen"
4. Customize the name if desired
5. Tap "Add"

### Android (Chrome)

1. Open the mobile interface in Chrome
2. Tap the menu (three dots)
3. Tap "Add to Home screen" or "Install app"
4. Confirm installation

### Benefits of PWA Installation

- Quick access from home screen
- App-like experience (standalone window)
- Offline support (view cached conversations)
- Better performance

## Configuration

### Server Configuration

Edit `~/.uai/config.toml` or `config/default.toml`:

```toml
[api]
enable_mobile = true
allowed_origins = ["*"]  # Or specific domains for production
rate_limit_per_minute = 60
```

### Environment Variables

You can also set the mobile API key via environment variable:

```bash
export MOBILE_API_KEY=your-api-key-here
```

## Security Best Practices

### For Local Network Use

- API key authentication is sufficient
- Keep your API key secure
- Don't share your API key

### For Remote/Internet Access

**Strongly Recommended**:

1. **Use HTTPS**: Set up a reverse proxy (nginx/caddy) with SSL certificates
2. **VPN**: Consider using a VPN instead of direct port forwarding
3. **Restrict Origins**: Set `allowed_origins` in config to specific domains
4. **Firewall Rules**: Only allow connections from trusted IPs
5. **Regular Key Rotation**: Regenerate API keys periodically

### Reverse Proxy Setup (nginx example)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Troubleshooting

### Cannot Connect to Server

1. **Check Server Status**:
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy"}`

2. **Check Firewall**: Ensure port 8000 is not blocked
   - **macOS**: System Preferences → Security → Firewall
   - **Linux**: `sudo ufw allow 8000`
   - **Windows**: Windows Defender Firewall settings

3. **Check IP Address**: Verify you're using the correct IP address

4. **Check Router**: Ensure port forwarding is configured correctly

### API Key Authentication Fails

1. Verify API key is correct (no extra spaces)
2. Check API key is stored: `uai mobile-key --show`
3. Ensure server has access to keyring:
   - **macOS**: Keychain access permissions
   - **Linux**: Secret Service (GNOME Keyring) running

### WebSocket Connection Fails

1. Check if WebSocket is enabled in mobile settings
2. Verify server supports WebSocket (FastAPI with WebSocket support)
3. Check firewall allows WebSocket connections (upgrade requests)
4. For reverse proxy, ensure WebSocket upgrade headers are forwarded

### Mobile UI Not Loading

1. Clear browser cache
2. Check browser console for errors (mobile browser dev tools)
3. Verify static files are being served: `curl http://YOUR_IP:8000/static/mobile.html`
4. Check server logs for errors

### Rate Limiting Issues

If you see "Rate limit exceeded":

1. Default limit is 60 requests per minute per API key
2. Adjust in config: `rate_limit_per_minute = 120`
3. Restart server after config changes

## Features

### Conversation Management

- **New Conversation**: Tap conversations icon (💬) → "New Conversation"
- **View History**: Conversations panel shows recent chats
- **Switch Conversations**: Tap a conversation to switch context

### Settings

- **API Key**: Configure authentication key
- **Server URL**: Set custom server address
- **WebSocket**: Enable/disable streaming responses

### WebSocket Streaming

When enabled:
- Real-time response streaming
- Typing indicators
- Connection status indicator
- Auto-reconnect on disconnect

## API Endpoints

The mobile interface uses these API endpoints:

- `POST /api/v1/chat` - Send chat message (REST)
- `GET /api/v1/conversations/{id}` - Get conversation history
- `GET /api/v1/tools` - List available AI tools
- `WS /api/v1/ws/chat` - WebSocket chat endpoint (streaming)

All endpoints require API key authentication via:
- Header: `X-API-Key: your-key`
- Header: `Authorization: Bearer your-key`
- Query: `?api_key=your-key` (less secure)

## Advanced Usage

### Custom Server URL

If running on a custom port or domain:

1. Open mobile settings
2. Enter full URL: `http://your-domain.com:8080`
3. Save

### Multiple Devices

You can use the same API key on multiple devices. Rate limiting applies per API key, so all devices share the same limit.

### Offline Mode

The PWA caches the interface for offline viewing. While offline:
- View cached conversations
- Cannot send new messages
- Messages will queue when connection is restored (future feature)

## Support

For issues or questions:

1. Check server logs: `python -m unified_ai.api.server` (verbose output)
2. Check mobile browser console for client-side errors
3. Verify configuration: `uai mobile-key --show`
4. Test API directly: `curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/v1/tools`

## Future Enhancements

Planned features:
- Voice input/output
- Push notifications for responses
- Offline message queue
- Multi-user support with separate API keys
- Biometric authentication
- End-to-end encryption
