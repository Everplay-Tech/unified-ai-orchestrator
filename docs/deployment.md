# Deployment Guide

## Production Deployment

### Environment Variables

Required:
- `JWT_SECRET_KEY` - Secret for JWT tokens
- `ENCRYPTION_KEY` - Encryption key for secrets

Optional:
- `DATABASE_PATH` - Path to SQLite database
- `LOG_LEVEL` - Logging level (info, debug, etc.)
- `API_HOST` - API host (default: 0.0.0.0)
- `API_PORT` - API port (default: 8000)

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Copy and build
COPY . .
RUN pip install -e .
RUN cd rust-core && cargo build --release

# Run
CMD ["python", "-m", "unified_ai.api.server"]
```

### Systemd Service

Create `/etc/systemd/system/uai.service`:

```ini
[Unit]
Description=Unified AI Orchestrator
After=network.target

[Service]
Type=simple
User=uai
WorkingDirectory=/opt/uai
Environment="JWT_SECRET_KEY=your-secret-key"
ExecStart=/usr/bin/python3 -m unified_ai.api.server
Restart=always

[Install]
WantedBy=multi-user.target
```

### Security Checklist

- [ ] Set strong `JWT_SECRET_KEY`
- [ ] Set `ENCRYPTION_KEY`
- [ ] Configure CORS origins
- [ ] Enable HTTPS
- [ ] Set up firewall rules
- [ ] Configure rate limiting
- [ ] Set up monitoring
- [ ] Enable audit logging

### Monitoring

- Prometheus metrics: `GET /metrics`
- Health check: `GET /health`
- Logs: Structured JSON logs

## Mobile Access

The system includes a mobile web interface for remote access. See [Mobile Access Guide](mobile-access.md) for detailed setup instructions.

### Quick Setup

1. Generate mobile API key:
   ```bash
   uai mobile-key --generate
   ```

2. Start server:
   ```bash
   python -m unified_ai.api.server
   ```

3. Configure network access (port forwarding for remote access)

4. Access from mobile browser at `http://YOUR_IP:8000`

### Mobile Access Security

For production mobile access:

- **Use HTTPS**: Set up reverse proxy with SSL certificates
- **Restrict Origins**: Configure `allowed_origins` in config file
- **API Key Authentication**: Required for all mobile requests
- **Rate Limiting**: Configured per API key (default: 60 req/min)
- **VPN Recommended**: Use VPN instead of direct port forwarding for better security

### Configuration

Mobile access settings in `~/.uai/config.toml`:

```toml
[api]
enable_mobile = true
api_key = "stored-in-keyring"  # Generated via uai mobile-key --generate
allowed_origins = ["*"]  # Restrict in production
rate_limit_per_minute = 60
```

See [mobile-access.md](mobile-access.md) for complete setup guide.
