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

#### Authentication & Authorization
- [ ] Set strong `JWT_SECRET_KEY` (minimum 32 characters, random)
- [ ] Set `ENCRYPTION_KEY` (32 bytes for AES-256)
- [ ] Configure API key authentication (`MOBILE_API_KEY`)
- [ ] Set `api_key_required = true` in production config
- [ ] Review and configure user roles and permissions

#### Network Security
- [ ] Configure CORS origins (remove wildcard `*` in production)
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Set up reverse proxy (nginx/traefik) for SSL termination
- [ ] Configure firewall rules (only allow necessary ports)
- [ ] Use VPN or private network for internal access

#### Rate Limiting & Input Validation
- [ ] Configure rate limits per user/API key
- [ ] Enable input validation (`enable_sql_injection_protection = true`)
- [ ] Set appropriate `max_input_length` limits
- [ ] Test rate limiting under load

#### Security Headers & CSRF
- [ ] Enable security headers (`enable_security_headers = true`)
- [ ] Enable CSRF protection (`enable_csrf_protection = true`)
- [ ] Configure HSTS for HTTPS (`enable_hsts = true`)
- [ ] Review Content Security Policy settings

#### Audit & Monitoring
- [ ] Enable audit logging (`audit_logging_enabled = true`)
- [ ] Configure audit log retention (`audit_retention_days`)
- [ ] Set up log monitoring and alerting
- [ ] Monitor for suspicious activity patterns
- [ ] Set up Prometheus metrics collection

#### Database Security
- [ ] Use strong database passwords (PostgreSQL)
- [ ] Encrypt database at rest
- [ ] Restrict database network access
- [ ] Regular database backups
- [ ] Review database migration security

#### Secrets Management
- [ ] Store API keys in secure keyring (not config files)
- [ ] Use environment variables for sensitive config
- [ ] Rotate API keys regularly
- [ ] Never commit secrets to version control
- [ ] Use secrets management service in production (AWS Secrets Manager, HashiCorp Vault)

#### Production Hardening
- [ ] Run service as non-root user
- [ ] Set appropriate file permissions
- [ ] Disable unnecessary features
- [ ] Keep dependencies updated
- [ ] Regular security audits
- [ ] Penetration testing

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
- **Restrict Origins**: Configure `allowed_origins` in config file (remove `*`)
- **API Key Authentication**: Required for all mobile requests
- **Rate Limiting**: Configure per-API-key rate limits
- **Input Validation**: All inputs are validated and sanitized
- **Audit Logging**: All mobile access is logged

### Security Best Practices

#### API Key Management
1. Generate strong API keys (minimum 32 characters)
2. Store keys securely (use keyring, not config files)
3. Rotate keys regularly (every 90 days)
4. Use different keys for different environments
5. Revoke compromised keys immediately

#### JWT Token Security
1. Use strong secret keys (minimum 32 characters)
2. Set appropriate token expiration times
3. Implement token refresh mechanism
4. Validate tokens on every request
5. Store tokens securely on client side

#### Input Validation
- All user inputs are validated and sanitized
- SQL injection protection enabled by default
- XSS protection via HTML sanitization
- Path traversal prevention for file operations
- Maximum length limits enforced

#### Rate Limiting
- Per-API-key rate limiting
- Per-IP rate limiting (fallback)
- Configurable limits per endpoint
- Rate limit headers in responses
- Graceful degradation on limit exceeded

#### Audit Logging
- All authentication events logged
- All resource access logged
- Failed authentication attempts logged
- Suspicious activity patterns detected
- Log retention configurable (default 90 days)
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
