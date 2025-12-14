# Quick Start Guide

Get your THCA Community Platform running in 15 minutes!

## ⚡ Prerequisites Check

Before starting, make sure you have:
- [ ] Python 3.9+ installed (`python --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Git installed (`git --version`)
- [ ] Discord Bot Token (get from https://discord.com/developers)
- [ ] Discord Webhook URLs (from your server channel settings)

## 🚀 5-Step Setup

### Step 1: Get the Code (1 minute)

```bash
# Clone or download the repository
git clone <your-repo-url>
cd thca-community-platform

# Or if you have the files already:
cd thca-community-platform
```

### Step 2: Backend Setup (3 minutes)

```bash
# Navigate to backend
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy requests beautifulsoup4 discord-webhook python-dotenv

# Create database
python -c "from models import Base, engine; Base.metadata.create_all(bind=engine)"

# Start the API server
uvicorn main:app --reload
```

The API should now be running at http://localhost:8000

Test it: Open http://localhost:8000/health in your browser
You should see: `{"status":"healthy","timestamp":"..."}`

### Step 3: Frontend Setup (3 minutes)

Open a NEW terminal (keep backend running):

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend should now be running at http://localhost:5173

Open it in your browser - you should see the platform!

### Step 4: Configure Discord (2 minutes)

1. **Get your Discord Webhooks:**
   - Go to your Discord server
   - Edit each channel (#flower-drops, #live-resin-drops, etc.)
   - Go to Integrations → Webhooks → New Webhook
   - Copy the webhook URL

2. **Update the product watcher:**
   Open `scrapers/product_watcher.py` and update lines 22-30:
   ```python
   WEBHOOKS = {
       "flower": "YOUR_FLOWER_WEBHOOK_URL",
       "live_resin": "YOUR_LIVE_RESIN_WEBHOOK_URL",
       "rosin": "YOUR_ROSIN_WEBHOOK_URL",
   }
   PRICE_TRACKER_WEBHOOK = "YOUR_PRICE_TRACKER_WEBHOOK_URL"
   ```

### Step 5: Start Product Watcher (2 minutes)

Open a THIRD terminal:

```bash
cd scrapers

# Copy your existing watcher's parser functions
# They should already be compatible!

# Start the watcher
python product_watcher.py
```

You should see:
```
INFO:__main__:Starting THCA Product Watcher...
INFO:__main__:Checking Tesoro - Shop Products...
INFO:__main__:Checking Hello Mary - Flower p1...
```

## ✅ Verify Everything Works

### Test 1: Backend ✓
```bash
curl http://localhost:8000/api/products
```
Should return JSON with products (might be empty at first)

### Test 2: Frontend ✓
1. Open http://localhost:5173
2. You should see the product browser
3. Try the filters and search

### Test 3: Product Watcher ✓
1. Watch the terminal for scraping logs
2. When a new product is found, you should see:
   - Log: "New product: [name] from [vendor]"
   - Discord notification in the appropriate channel

### Test 4: Strain Scraper ✓
```bash
cd scrapers
python strain_scraper.py "Jealousy"
```
Should fetch and display strain info from Leafly/Wikileaf

## 🎯 What to Do Next

### Immediate (Day 1)
1. ✅ Verify product watcher is posting to Discord
2. ✅ Test all filters in the frontend
3. ✅ Try searching for products
4. ✅ Check the analytics page

### Short Term (Week 1)
1. Add more vendor parsers (copy existing pattern)
2. Run strain scraper on your top strains
3. Customize the frontend colors/branding
4. Set up your domain name

### Medium Term (Month 1)
1. Deploy to production (see DEPLOYMENT.md)
2. Announce on Reddit/Discord communities
3. Gather user feedback
4. Add requested features

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'X'"
**Solution:** Install the missing package
```bash
pip install <package-name>
# or for frontend:
npm install <package-name>
```

### "Port already in use"
**Backend (port 8000):**
```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9
# Or use a different port:
uvicorn main:app --port 8001
```

**Frontend (port 5173):**
```bash
# Kill the process
lsof -ti:5173 | xargs kill -9
# Or Vite will automatically use next available port
```

### Products not showing in frontend
**Check:**
1. Is the backend running? (http://localhost:8000/health)
2. Is the product watcher running and finding products?
3. Check browser console for errors (F12)
4. Check CORS settings in backend main.py

### Discord notifications not working
**Check:**
1. Are webhook URLs correct?
2. Are channels set to allow webhook messages?
3. Check scraper terminal for errors
4. Test webhook directly:
   ```bash
   curl -X POST "YOUR_WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d '{"content":"Test message"}'
   ```

### Database errors
**Solution:** Recreate the database
```bash
cd backend
rm thca_platform.db  # Delete old database
python -c "from models import Base, engine; Base.metadata.create_all(bind=engine)"
```

## 📱 Development Tips

### Hot Reload
- Backend: `uvicorn main:app --reload` (auto-restarts on code changes)
- Frontend: `npm run dev` (auto-refreshes on code changes)
- Watcher: You need to manually restart this

### Viewing Data
**Database (SQLite):**
```bash
sqlite3 backend/thca_platform.db
.tables
SELECT * FROM products LIMIT 5;
.quit
```

**API Explorer:**
Open http://localhost:8000/docs
- Interactive API documentation
- Test endpoints directly
- See all available endpoints

### Adding a New Vendor

1. **Create parser function** (in scrapers/product_watcher.py):
```python
def parse_new_vendor(site_config):
    url = site_config['url']
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    products = []
    for item in soup.select('.product-card'):  # Adjust selector
        products.append({
            'id': f"newvendor-{item['data-id']}",  # Unique ID
            'title': item.select_one('.title').text,
            'url': item.select_one('a')['href'],
            'price': float(item.select_one('.price').text.replace('$', '')),
            'in_stock': 'sold out' not in item.text.lower(),
            'image_url': item.select_one('img')['src'],
        })
    
    return products
```

2. **Add to PARSERS dict:**
```python
PARSERS = {
    'parse_new_vendor': parse_new_vendor,
    # ... existing parsers
}
```

3. **Add to SITES list:**
```python
SITES.append({
    'name': 'New Vendor',
    'url': 'https://newvendor.com/products',
    'parser': 'parse_new_vendor'
})
```

4. **Test it:**
```bash
# Restart the watcher
# Watch for: "Checking New Vendor..."
```

### Frontend Customization

**Colors (frontend/tailwind.config.js):**
```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#10b981',  // Change to your brand color
        secondary: '#6366f1',
      }
    }
  }
}
```

**Logo (frontend/src/App.tsx):**
Replace line ~16:
```tsx
<img src="/your-logo.png" className="h-8" alt="Logo" />
```

## 🎓 Learning Resources

### API Usage
- **List products:** `GET http://localhost:8000/api/products`
- **Filter products:** `GET http://localhost:8000/api/products?vendor_id=1&product_type=flower&in_stock_only=true`
- **Get product:** `GET http://localhost:8000/api/products/1`
- **Search:** `GET http://localhost:8000/api/search?q=jealousy`

### Database Schema
See `backend/models.py` for all tables and relationships

### Adding Features
1. **Backend:** Add endpoint in `main.py`
2. **Frontend:** Create component in `src/components/`
3. **Page:** Add route in `App.tsx`

## 💬 Getting Help

1. **Check the logs**
   - Backend: Terminal running uvicorn
   - Frontend: Browser console (F12)
   - Watcher: Terminal running product_watcher.py

2. **Read the docs**
   - README.md - Overview
   - FEATURES.md - Complete feature list
   - DEPLOYMENT.md - Production setup
   - API docs: http://localhost:8000/docs

3. **Common issues**
   - Most issues are import errors or wrong file paths
   - Make sure you're in the right directory
   - Check Python/Node versions

4. **Still stuck?**
   - Open an issue on GitHub
   - Ask in Discord
   - Check existing issues

## 🎉 You're Ready!

Your THCA Community Platform is now running locally. Here's what you have:

✅ Backend API with database
✅ Modern React frontend
✅ Product watcher posting to Discord
✅ Strain scraper for lineage data
✅ Analytics dashboard
✅ Advanced filtering
✅ Price history tracking

**Next Steps:**
1. Let it run for a few hours to gather products
2. Try all the features
3. Customize the branding
4. Prepare for production deployment

**When ready to launch:**
- See DEPLOYMENT.md for production setup
- See FEATURES.md for full capabilities
- Announce in THCA communities

---

**Happy tracking! 🌿**
