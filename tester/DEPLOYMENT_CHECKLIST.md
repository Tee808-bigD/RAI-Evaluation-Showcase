# RAI Evaluation Showcase — Production Deployment Checklist

Use this checklist to prepare the application for production deployment.

## Pre-Deployment Security Review

### Environment & Secrets

- [ ] **Generate strong JWT secret**
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
  Add to `.env.production` as `JWT_SECRET`

- [ ] **Add production NVIDIA API key**
  - Obtain from https://build.nvidia.com/settings/api-keys
  - Add to `.env.production` as `NVIDIA_API_KEY`
  - Verify it's NOT in git history: `git log --all -p -- .env`

- [ ] **Configure CORS origins for your domain**
  ```
  ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://api.yourdomain.com
  ```

- [ ] **Ensure .env.production is in .gitignore**
  ```bash
  grep ".env" .gitignore
  ```

- [ ] **Review all environment variables**
  ```bash
  cat .env.production | grep -v "^#"
  ```

### Code Security

- [ ] **No hardcoded secrets in code**
  ```bash
  # Check for common patterns
  grep -r "nvapi-" backend/ frontend/ --exclude-dir=node_modules --exclude-dir=.git
  grep -r "SECRET=" backend/ frontend/ --exclude-dir=node_modules --exclude-dir=.git
  grep -r "password" backend/ frontend/ --exclude-dir=node_modules --exclude-dir=.git
  ```

- [ ] **Review authentication flow**
  - [ ] `/token` endpoint only accepts valid API keys
  - [ ] Tokens have expiry (< 1 hour)
  - [ ] All endpoints verify token before processing

- [ ] **Check input validation**
  - [ ] Pydantic models validate all user inputs
  - [ ] No direct database queries with user input
  - [ ] File uploads blocked (if applicable)

- [ ] **Verify error handling**
  - [ ] No stack traces in responses
  - [ ] No sensitive data in error messages
  - [ ] Generic 500 errors logged but not shown to client

### Backend Configuration

- [ ] **Set ENVIRONMENT=production**
  ```bash
  grep "ENVIRONMENT=production" .env.production
  ```

- [ ] **Disable debug mode**
  - [ ] Remove `--reload` from uvicorn command
  - [ ] Disable `/docs` and `/redoc` endpoints (done in code for prod)

- [ ] **Verify rate limiting is enabled**
  ```bash
  grep "@limiter.limit" backend/main_secure.py | wc -l
  # Should show 8+ decorators
  ```

- [ ] **Review logging configuration**
  - [ ] `LOG_LEVEL=INFO` or higher
  - [ ] No API keys or secrets in logs
  - [ ] Centralized log collection ready (ELK, Datadog, etc.)

### Frontend Configuration

- [ ] **Set REACT_APP_API_URL to HTTPS endpoint**
  ```bash
  grep "REACT_APP_API_URL" .env.production
  # Should be https://, not http://
  ```

- [ ] **Set REACT_APP_WS_URL to WSS endpoint**
  ```bash
  grep "REACT_APP_WS_URL" .env.production
  # Should be wss://, not ws://
  ```

- [ ] **Build production bundle**
  ```bash
  cd frontend && npm run build
  # Check build/ directory exists and contains static assets
  ```

- [ ] **Enable authentication if needed**
  ```bash
  grep "REACT_APP_REQUIRE_AUTH=true" .env.production
  # Set to true if using internal API key auth
  ```

## Infrastructure Preparation

### HTTPS / TLS

- [ ] **Obtain SSL certificate**
  - [ ] From Let's Encrypt (free)
  - [ ] Or from certificate authority
  - [ ] Wildcard certificate for subdomains? (*.yourdomain.com)

- [ ] **Configure reverse proxy (Nginx recommended)**
  ```nginx
  server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/your-cert.crt;
    ssl_certificate_key /etc/ssl/private/your-key.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Redirect HTTP to HTTPS
    if ($scheme != "https") {
      return 301 https://$server_name$request_uri;
    }
    
    location / {
      proxy_pass http://backend:8000;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support
    location /ws/ {
      proxy_pass http://backend:8000;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
    }
  }
  ```

- [ ] **Test SSL certificate**
  ```bash
  openssl s_client -connect yourdomain.com:443
  # Should show valid certificate
  ```

### Database (if using persistence)

- [ ] **Create PostgreSQL database**
  ```bash
  createdb rai_evaluation
  ```

- [ ] **Run migrations**
  ```bash
  python backend/migrations.py upgrade
  ```

- [ ] **Backup strategy configured**
  - [ ] Daily backups
  - [ ] Tested restore process
  - [ ] Off-site backup storage

- [ ] **User table created with hashed API keys**
  ```sql
  CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    api_key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
  );
  ```

### Monitoring & Logging

- [ ] **Set up centralized logging**
  - [ ] ELK Stack (Elasticsearch, Logstash, Kibana)
  - [ ] Datadog / New Relic
  - [ ] CloudWatch (if AWS)
  - [ ] Configure log shipping from Docker containers

- [ ] **Enable application monitoring**
  - [ ] APM tool (DataDog APM, New Relic, etc.)
  - [ ] Capture response times
  - [ ] Track error rates
  - [ ] Monitor database query performance

- [ ] **Set up alerting**
  - [ ] High error rate (> 5%)
  - [ ] Response time > 5 seconds
  - [ ] Rate limit abuse detected
  - [ ] Database connection issues
  - [ ] SSL certificate expiring soon

- [ ] **Health check endpoint monitored**
  ```bash
  # Set up uptime monitoring (UptimeRobot, Pingdom, etc.)
  # Monitor: GET https://api.yourdomain.com/health
  # Expected: 200 OK, {"status": "ok"}
  ```

### CI/CD Pipeline

- [ ] **GitHub Actions / GitLab CI configured**
  - [ ] Run tests on every push
  - [ ] Build Docker images
  - [ ] Push to registry
  - [ ] Deploy to staging first
  - [ ] Only deploy to production on tag

- [ ] **Secrets management**
  - [ ] Use GitHub Secrets / GitLab CI Variables
  - [ ] Never commit `.env.production`
  - [ ] Rotate secrets regularly

## Pre-Launch Testing

### Security Testing

- [ ] **Penetration test**
  ```bash
  # Try SQL injection
  curl "http://api/evaluate?scenario_id='; DROP TABLE--"
  # Should fail validation, not crash
  
  # Try XSS
  curl "http://api/evaluate?scenario_id=<script>"
  # Should fail validation
  
  # Try auth bypass
  curl "http://api/scenarios" 
  # Should require auth (if REQUIRE_AUTH=true)
  
  # Try rate limit bypass
  for i in {1..100}; do curl http://api/token; done
  # Should see 429 after limit
  ```

- [ ] **SSL/TLS security scan**
  ```bash
  # Use SSL Labs: https://www.ssllabs.com/ssltest/
  # Expected: A+ rating
  ```

### Performance Testing

- [ ] **Load test the API**
  ```bash
  # Using locust
  locust -f tests/load/locustfile.py --host=https://api.yourdomain.com
  # Expected: < 5% error rate at 100 concurrent users
  ```

- [ ] **Database performance**
  - [ ] Slow query log enabled
  - [ ] Indexes created on frequently queried columns
  - [ ] Connection pool configured

- [ ] **Frontend performance**
  ```bash
  # Lighthouse score > 90
  npm run build
  # Check bundle size < 500KB
  du -sh frontend/build/
  ```

### Functionality Testing

- [ ] **End-to-end workflow**
  1. [ ] User logs in (or gets token)
  2. [ ] Fetches scenarios
  3. [ ] Runs evaluation
  4. [ ] Receives results with metrics
  5. [ ] WebSocket streaming works

- [ ] **All endpoints tested**
  ```bash
  # GET /health
  curl https://api.yourdomain.com/health
  
  # POST /token
  curl -X POST https://api.yourdomain.com/token \
    -H "Content-Type: application/json" \
    -d '{"api_key":"..."}'
  
  # GET /scenarios (with token)
  curl -H "Authorization: Bearer $TOKEN" \
    https://api.yourdomain.com/scenarios
  
  # POST /evaluate
  curl -H "Authorization: Bearer $TOKEN" \
    -X POST https://api.yourdomain.com/evaluate \
    -H "Content-Type: application/json" \
    -d '{"scenario_id":"product_description"}'
  ```

- [ ] **Error cases tested**
  - [ ] Invalid API key
  - [ ] Expired token
  - [ ] Missing required fields
  - [ ] Invalid scenario_id
  - [ ] Rate limit exceeded

## Launch Preparation

### Final Checklist

- [ ] All environment variables set in production
- [ ] Secrets not in git history: `git log --all -p | grep -i "secret\|key" | wc -l`
- [ ] SSL certificate installed and valid
- [ ] Database backups working
- [ ] Monitoring and alerting active
- [ ] Support email configured for issues
- [ ] Incident response plan documented
- [ ] Team trained on deployment process
- [ ] Rollback procedure tested

### Deployment Command

```bash
# For Docker on production server:
docker pull rai-api:latest
docker pull rai-web:latest

docker stop rai-api rai-web
docker rm rai-api rai-web

docker run -d \
  --name rai-api \
  --restart always \
  -p 8000:8000 \
  --env-file .env.production \
  rai-api:latest

docker run -d \
  --name rai-web \
  --restart always \
  -p 3000:3000 \
  --env-file .env.production \
  rai-web:latest

# Verify health
sleep 5
curl https://api.yourdomain.com/health
```

## Post-Launch

### Day 1 Monitoring

- [ ] Check error logs for issues
- [ ] Verify no auth failures
- [ ] Monitor response times
- [ ] Test user workflow end-to-end
- [ ] Review alert notifications

### Week 1 Review

- [ ] Analyze usage patterns
- [ ] Check for performance bottlenecks
- [ ] Review security logs
- [ ] Update incident response playbook based on learnings

### Monthly Review

- [ ] Review rate limiting effectiveness
- [ ] Check SSL certificate expiry (should be > 30 days)
- [ ] Rotate secrets if needed
- [ ] Review backup integrity
- [ ] Update dependencies for security patches

## Troubleshooting Deployment Issues

### Backend won't start
```bash
# Check environment variables
docker exec rai-api env | grep NVIDIA

# Check logs
docker logs rai-api

# Verify JWT secret is set
echo $JWT_SECRET
```

### CORS errors
```bash
# Verify ALLOWED_ORIGINS
docker exec rai-api env | grep ALLOWED_ORIGINS

# Test with curl
curl -H "Origin: https://yourdomain.com" \
  -H "Access-Control-Request-Method: POST" \
  -X OPTIONS https://api.yourdomain.com/evaluate
```

### WebSocket not connecting
```bash
# Test WS connection
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Origin: https://yourdomain.com" \
  https://api.yourdomain.com/ws/eval
```

### Rate limiting too aggressive
```bash
# Check rate limit decorators in code
grep "@limiter.limit" backend/main_secure.py

# Adjust limits if needed (in code, redeploy)
# For example: change 10/minute to 20/minute
```

## Sign-Off

- **Deployment Date**: _______________
- **Deployed By**: _______________
- **Reviewed By**: _______________
- **Issues Found**: _______________
- **Resolved**: _______________

---

✅ **Deployment checklist complete!** Your application is ready for production.
