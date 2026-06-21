# Security Policy for ProcessNovaCore

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |

## Reporting a Vulnerability

Please report security vulnerabilities to security@processnova.mx. You can expect a response within 48 hours and a fix within 7 days.

## Security Measures

This project follows industry best practices for security, including:

### 1. Application Layer
- **Django Security**: Uses Django's built-in security features
- **XSS Protection**: Automatic escaping and `SECURE_BROWSER_XSS_FILTER` enabled
- **Clickjacking Protection**: `X_FRAME_OPTIONS = 'DENY'`
- **Content Type Sniffing**: `SECURE_CONTENT_TYPE_NOSNIFF = True`
- **CSRF Protection**: Enabled and uses `CSRF_COOKIE_HTTPONLY` and `CSRF_COOKIE_SAMESITE`
- **Rate Limiting**: Uses `django-ratelimit` to prevent API abuse
- **CSP (Content Security Policy)**: Strict policy with `django-csp`
- **Referrer Policy**: `strict-origin-when-cross-origin`

### 2. Session Management
- **Session Expiration**: Sessions expire after 30 minutes of inactivity
- **Browser Close**: Sessions expire when the browser closes
- **Secure Cookies**: All cookies are marked as Secure, HTTPOnly, and SameSite=Strict
- **Session Timeout**: `SESSION_COOKIE_AGE = 1800` (30 minutes)

### 3. Password Security
- **Validation**: Passwords must be at least 10 characters long, not similar to user attributes, not common, and not entirely numeric
- **Hashing**: Uses Django's PBKDF2 password hasher
- **MFA Recommendation**: Multi-factor authentication is recommended for production use

### 4. Database Security
- **Secure Defaults**: All database connections use TLS/SSL
- **Tenant Isolation**: Multi-tenant architecture with strict organization-based filtering
- **No Raw Queries**: Uses Django ORM exclusively to prevent SQL injection
- **Audit Log**: `django-auditlog` tracks all model changes with user attribution

### 5. HTTPS & SSL
- **SSL Redirect**: Enforced in production
- **HSTS (HTTP Strict Transport Security)**: Enabled with 1 year duration (`max-age=31536000`)
- **HSTS Preload**: Preload list enabled
- **HSTS Include Subdomains**: Applies to all subdomains
- **Secure Proxy**: Uses `SECURE_PROXY_SSL_HEADER` for proxy servers like Render

### 6. API Security
- **Authentication**: Requires login for all endpoints
- **Tenant Isolation**: All API endpoints are tenant-aware using `@tenant_required`
- **Permission Checks**: All tools require appropriate user roles
- **Rate Limits**: 
  - AI Chat: 30 requests per minute
  - Analysis APIs: 20 requests per minute
  - All rate limits use user or IP for identification

### 7. Static Files & Media
- **WhiteNoise**: Serves static files with compression and caching
- **Secure Delivery**: All static files served over HTTPS

### 8. Logging & Monitoring
- **Audit Logs**: Track all model changes
- **Security Logs**: Monitor all security-related events
- **Error Logging**: Captures and logs all exceptions
- **No Secrets in Logs**: Never logs sensitive information

### 9. Third-Party Dependencies
- **Dependency Management**: Uses `requirements.txt` with version constraints
- **Regular Updates**: All dependencies kept up-to-date
- **Security Scanning**: Recommended: Use tools like pip-audit or safety for dependency scanning

## Production Deployment Checklist

Before deploying to production, verify:
- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` is set as an environment variable
- [ ] `ALLOWED_HOSTS` is configured properly
- [ ] `CSRF_TRUSTED_ORIGINS` is configured with your production domains
- [ ] All security middleware is enabled
- [ ] Database uses SSL/TLS connection
- [ ] Static files served with HTTPS
- [ ] Email configuration uses secure protocols
- [ ] Backup strategy is in place and tested
- [ ] Rate limiting is active
- [ ] CSP is configured and enforced
- [ ] HSTS is enabled
- [ ] Secure cookies are set
- [ ] Audit log is active
- [ ] Monitoring and alerting is set up
- [ ] Regular security scanning is scheduled

## Data Privacy

This application:
- Follows principle of least privilege
- Does not expose sensitive data in logs
- Encrypts data in transit
- Isolates tenant data strictly
- Tracks access to sensitive information

## Contact

For security issues or questions: security@processnova.mx
