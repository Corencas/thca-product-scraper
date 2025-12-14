# Deployment Guide - THCA Community Platform

Complete guide for deploying the THCA Community Platform to production.

## 🎯 Deployment Options

### Option 1: All-in-One (Recommended for Start)
- **Railway.app** - Easiest, handles backend + database
- **Vercel** - Frontend
- **Your Server** - Product watcher (needs to run 24/7)

### Option 2: Traditional VPS
- **DigitalOcean/Linode/Vultr** - Single droplet for everything
- More control, requires more setup

### Option 3: Fully Managed
- **Railway** - Backend + DB
- **Vercel** - Frontend
- **Railway** - Product watcher (separate service)

## 🚀 Quick Deploy (Railway + Vercel)

### 1. Database Setup (Railway)

1. Create Railway account at railway.app
2. New Project → Deploy PostgreSQL
3. Note your database credentials:
   ```
   DATABASE_URL=postgresql://user:pass@host:port/dbname
   ```

### 2. Backend Deployment (Railway)

1. **Prepare your repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Create railway.json** in project root:
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "NIXPACKS",
       "buildCommand": "pip install -r backend/requirements.txt"
     },
     "deploy": {
       "startCommand": "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT",
       "healthcheckPath": "/health",
       "healthcheckTimeout": 100
     }
   }
   ```

3. **Deploy to Railway**
   - New Project → Deploy from GitHub
   - Select your repository
   - Add environment variables:
     ```
     DATABASE_URL=postgresql://...
     DISCORD_BOT_TOKEN=...
     WEBHOOK_FLOWER=...
     WEBHOOK_LIVE_RESIN=...
     WEBHOOK_ROSIN=...
     PRICE_TRACKER_WEBHOOK=...
     ```

4. **Get your API URL**
   - Railway will give you a URL like: `https://your-app.railway.app`

### 3. Frontend Deployment (Vercel)

1. **Update frontend/.env.production**
   ```env
   VITE_API_URL=https://your-app.railway.app
   VITE_DISCORD_INVITE=https://discord.gg/your-invite
   ```

2. **Deploy to Vercel**
   ```bash
   cd frontend
   npm install -g vercel
   vercel --prod
   ```

3. **Configure Vercel**
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`
   - Root Directory: `frontend`

### 4. Product Watcher Deployment

**Option A: Separate Railway Service**
1. Create new Railway service
2. Set start command: `cd scrapers && python product_watcher.py`
3. Add same environment variables as backend

**Option B: Your Own Server (Recommended)**
```bash
# On your server
git clone your-repo
cd thca-community-platform/scrapers

# Install dependencies
pip install -r ../backend/requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/thca-watcher.service
```

Content of service file:
```ini
[Unit]
Description=THCA Product Watcher
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/thca-community-platform/scrapers
Environment="DATABASE_URL=postgresql://..."
Environment="DISCORD_BOT_TOKEN=..."
ExecStart=/usr/bin/python3 product_watcher.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable thca-watcher
sudo systemctl start thca-watcher
sudo systemctl status thca-watcher
```

## 🔧 Production Configurations

### Backend (main.py)

Add production middleware:
```python
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Update CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app",
        "https://your-custom-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Database Migrations (Alembic)

1. **Initialize Alembic**
   ```bash
   cd backend
   alembic init alembic
   ```

2. **Configure alembic.ini**
   ```ini
   sqlalchemy.url = ${DATABASE_URL}
   ```

3. **Create migration**
   ```bash
   alembic revision --autogenerate -m "Initial tables"
   alembic upgrade head
   ```

### Environment Variables

**Backend (.env)**
```env
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Security
SECRET_KEY=your-secret-key-generate-with-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Discord
DISCORD_BOT_TOKEN=your-bot-token
WEBHOOK_FLOWER=https://discord.com/api/webhooks/...
WEBHOOK_LIVE_RESIN=https://discord.com/api/webhooks/...
WEBHOOK_ROSIN=https://discord.com/api/webhooks/...
PRICE_TRACKER_WEBHOOK=https://discord.com/api/webhooks/...
DROP_CALENDAR_WEBHOOK=https://discord.com/api/webhooks/...

# API Config
API_RATE_LIMIT=100/hour
CORS_ORIGINS=https://your-frontend.vercel.app,https://your-domain.com

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Frontend (.env.production)**
```env
VITE_API_URL=https://your-backend.railway.app
VITE_DISCORD_INVITE=https://discord.gg/your-invite
VITE_ENABLE_ANALYTICS=true
```

## 📊 Monitoring & Logging

### Backend Logging (Add to main.py)

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/app.log',
            maxBytes=10485760,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### Health Checks

Already implemented at `/health` endpoint. Monitor with:
- UptimeRobot (free)
- Better Uptime
- Railway's built-in monitoring

### Error Tracking

**Option 1: Sentry** (Recommended)
```bash
pip install sentry-sdk[fastapi]
```

```python
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0,
)
```

**Option 2: LogRocket** for frontend

## 🔒 Security Checklist

- [ ] Change all default passwords and tokens
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS (automatic on Vercel/Railway)
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Regular database backups
- [ ] Keep dependencies updated
- [ ] Set up monitoring/alerts
- [ ] Use strong SECRET_KEY for JWT
- [ ] Validate all user inputs
- [ ] Sanitize database queries (using ORM helps)

## 📈 Performance Optimization

### Database

1. **Add indexes**
   ```sql
   CREATE INDEX idx_products_vendor ON products(vendor_id);
   CREATE INDEX idx_products_strain ON products(strain_id);
   CREATE INDEX idx_products_type ON products(product_type);
   CREATE INDEX idx_products_price ON products(current_price);
   CREATE INDEX idx_products_stock ON products(in_stock);
   CREATE INDEX idx_price_history_product ON price_history(product_id);
   ```

2. **Connection pooling** (already configured in SQLAlchemy)

3. **Regular vacuuming** (PostgreSQL)
   ```sql
   VACUUM ANALYZE;
   ```

### Frontend

1. **Image optimization**
   - Use CDN for images (Cloudinary, ImageKit)
   - Lazy loading implemented
   - WebP format when possible

2. **Code splitting** (Vite does this automatically)

3. **Caching**
   ```typescript
   // Add to API calls
   const response = await axios.get(url, {
     headers: { 'Cache-Control': 'max-age=300' }
   });
   ```

### API

1. **Response caching**
   ```python
   from fastapi_cache import FastAPICache
   from fastapi_cache.backends.redis import RedisBackend
   from redis import asyncio as aioredis

   @app.on_event("startup")
   async def startup():
       redis = aioredis.from_url("redis://localhost")
       FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
   ```

2. **Pagination** (already implemented)

3. **Query optimization** (use SQLAlchemy eager loading)

## 🔄 Continuous Deployment

### GitHub Actions (Automatic Deploy)

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Railway
        run: |
          # Railway deploys automatically on git push
          echo "Backend deploying to Railway"

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend
```

## 🆘 Troubleshooting

### Common Issues

**Backend won't start**
- Check DATABASE_URL format
- Verify all environment variables are set
- Check logs: `railway logs` or `journalctl -u thca-watcher -f`

**Frontend can't connect to API**
- Verify VITE_API_URL is correct
- Check CORS settings in backend
- Test API directly: `curl https://your-backend/health`

**Product watcher not working**
- Check Discord webhooks are valid
- Verify DATABASE_URL is accessible
- Check logs for scraping errors
- Test parsers individually

**Database connection errors**
- Check connection string format
- Verify database is running
- Check firewall rules
- Test connection: `psql $DATABASE_URL`

## 📞 Support Resources

- [Railway Docs](https://docs.railway.app/)
- [Vercel Docs](https://vercel.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL on Railway](https://docs.railway.app/databases/postgresql)

## ✅ Post-Deployment Checklist

- [ ] Backend API accessible and returns 200 from /health
- [ ] Frontend loads and displays products
- [ ] Discord notifications working
- [ ] Product watcher running and posting to Discord
- [ ] Database backups configured
- [ ] Monitoring/alerts set up
- [ ] Domain configured (if using custom domain)
- [ ] SSL certificate active (automatic on Railway/Vercel)
- [ ] Test all main features:
  - [ ] Product browsing with filters
  - [ ] Strain search
  - [ ] Vendor pages
  - [ ] Promo codes display
  - [ ] Analytics charts
- [ ] Performance testing (page load < 2s)

---

**You're live! 🎉**

Share your platform:
- Reddit: r/hempflowers, r/cultofthefranklin
- Discord: THCA community servers
- Twitter: Cannabis tech community
