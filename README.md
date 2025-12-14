# THCA Community Platform

A comprehensive, community-driven platform for tracking THCA products, strains, vendors, and deals. Built with modern web technologies and designed for the cannabis community.

## 🌟 Features

### Product Tracking
- **Real-time Monitoring**: Continuous scraping of vendor websites for new products
- **Advanced Filtering**: Filter by vendor, product type, price, strain, potency
- **Price History**: Track price changes over time with interactive charts
- **Stock Alerts**: Get notified when products come back in stock
- **Best Deals**: Automatically identifies best price per gram deals

### Strain Database
- **Comprehensive Info**: Lineage, effects, terpenes, flavor profiles
- **Auto-Scraping**: Pulls data from Leafly, Wikileaf, and AllBud
- **Lineage Trees**: Interactive family tree visualization
- **Effects & Terpenes**: Detailed cannabinoid and terpene profiles

### Vendor Directory
- **Vendor Profiles**: Reviews, ratings, typical drop schedules
- **Promo Codes**: Community-submitted and verified discount codes
- **Shipping Info**: States served, payment methods, minimums
- **Drop Calendar**: Scheduled drops with multi-day reminders

### Community Features
- **Discord Integration**: Real-time notifications in dedicated channels
- **User Accounts**: Save favorites, set price alerts
- **Reviews & Ratings**: Rate products and vendors
- **Analytics**: Market trends, popular strains, price analytics

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL (or SQLite for development)
- Discord Bot Token (for notifications)

### Backend Setup

1. **Install Python Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Initialize Database**
```bash
python -c "from models import Base, engine; Base.metadata.create_all(bind=engine)"
```

4. **Run the API Server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. **Install Node Dependencies**
```bash
cd frontend
npm install
```

2. **Configure Environment**
```bash
cp .env.example .env
# Set VITE_API_URL to your backend URL
```

3. **Run Development Server**
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Product Watcher Setup

1. **Configure Vendor Scrapers**
```bash
cd scrapers
# Edit product_watcher.py to add/configure vendors
```

2. **Start the Watcher**
```bash
python product_watcher.py
```

The watcher will:
- Scrape vendor sites every 4 seconds
- Post new drops to Discord
- Update the database
- Track price changes

### Strain Scraper

Build comprehensive strain database:
```bash
cd scrapers
python strain_scraper.py "Strain Name"
python strain_scraper.py "Jealousy" --build-tree
```

## 📁 Project Structure

```
thca-community-platform/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy database models
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment template
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main app component
│   │   ├── pages/           # Page components
│   │   │   ├── ProductBrowser.tsx
│   │   │   ├── StrainDatabase.tsx
│   │   │   ├── VendorList.tsx
│   │   │   └── Analytics.tsx
│   │   └── components/      # Reusable components
│   │       ├── ProductCard.tsx
│   │       ├── FilterPanel.tsx
│   │       └── StrainTree.tsx
│   ├── package.json
│   └── .env.example
├── scrapers/
│   ├── product_watcher.py   # Enhanced product scraper
│   ├── strain_scraper.py    # Multi-source strain scraper
│   └── vendor_scrapers/     # Individual vendor parsers
├── discord_bot/
│   ├── bot.py               # Discord bot with commands
│   └── notifications.py     # Notification system
└── docs/
    ├── API.md               # API documentation
    ├── DEPLOYMENT.md        # Deployment guide
    └── CONTRIBUTING.md      # Contribution guidelines
```

## 🔧 Configuration

### Database (Backend .env)
```env
DATABASE_URL=postgresql://user:password@localhost/thca_db
# Or for SQLite:
# DATABASE_URL=sqlite:///./thca_platform.db
```

### Discord Bot
```env
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_server_id

# Channel Webhooks
WEBHOOK_FLOWER=https://discord.com/api/webhooks/...
WEBHOOK_LIVE_RESIN=https://discord.com/api/webhooks/...
WEBHOOK_ROSIN=https://discord.com/api/webhooks/...
WEBHOOK_PRICE_TRACKER=https://discord.com/api/webhooks/...
WEBHOOK_DROP_CALENDAR=https://discord.com/api/webhooks/...
```

### Frontend
```env
VITE_API_URL=http://localhost:8000
VITE_DISCORD_INVITE=https://discord.gg/your-invite
```

## 📊 API Endpoints

### Products
- `GET /api/products` - List products with filters
- `GET /api/products/{id}` - Get product details
- `GET /api/products/{id}/price-history` - Price history

### Strains
- `GET /api/strains` - List all strains
- `GET /api/strains/{id}` - Get strain details
- `GET /api/strains/{id}/lineage` - Get lineage tree

### Vendors
- `GET /api/vendors` - List all vendors
- `GET /api/vendors/{id}` - Get vendor details

### Analytics
- `GET /api/analytics/popular-strains` - Top strains
- `GET /api/analytics/price-trends` - Price trends over time
- `GET /api/analytics/deals` - Best deals by price/gram

### Search
- `GET /api/search?q={query}` - Universal search

See [API.md](docs/API.md) for complete documentation.

## 🎨 Frontend Features

### Product Browser
- **Multi-criteria Filtering**: Vendor, type, price, strain, stock status
- **Smart Sorting**: By date, price, price per gram
- **Quick Filters**: One-click filters for new drops, deals, in stock
- **Product Type Tabs**: Flower, Live Resin, Rosin, Shatter, etc.
- **Real-time Updates**: Auto-refresh when new products detected

### Strain Database
- **Comprehensive Profiles**: Genetics, effects, terpenes, flavors
- **Interactive Lineage Trees**: Visual family tree navigation
- **Product Availability**: See which vendors have each strain in stock
- **Price Comparison**: Compare prices across vendors for same strain

### Vendor Profiles
- **Detailed Info**: Shipping, payment, drop schedules
- **Active Promo Codes**: Community-verified discount codes
- **Ratings & Reviews**: Community feedback
- **Product Catalog**: All products from vendor with filtering

### Analytics Dashboard
- **Market Trends**: Price trends over time by product type
- **Popular Strains**: Most available strains across vendors
- **Best Deals**: Current best price per gram by category
- **Vendor Stats**: Product counts, average prices

## 🤖 Discord Integration

### Notification Channels
- `#flower-drops` - New flower products
- `#live-resin-drops` - Live resin concentrates
- `#rosin-drops` - Rosin products
- `#price-tracker` - Price changes and restocks
- `#drop-calendar` - Scheduled drops with reminders

### Bot Commands
- `/search [product]` - Search for products
- `/strain [name]` - Get strain info and lineage
- `/deals [type]` - Show best current deals
- `/vendor [name]` - Get vendor info and promo codes
- `/alert add [strain] [max price]` - Set price alert
- `/favorites add [product]` - Add to favorites

## 📱 Mobile Optimized

The platform is fully responsive and optimized for mobile devices:
- Touch-friendly interface
- Mobile navigation
- Optimized images and loading
- Swipe gestures for filtering

## 🛡️ Security & Privacy

- No user tracking or analytics
- Secure password hashing (bcrypt)
- Rate limiting on API endpoints
- CORS properly configured
- SQL injection protection via ORM
- XSS protection in frontend

## 🚀 Deployment

### Production Deployment

#### Backend (Railway/Render/DigitalOcean)
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://..."
export DISCORD_BOT_TOKEN="..."

# Run with gunicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Frontend (Vercel/Netlify)
```bash
npm run build
# Deploy dist/ folder
```

#### Database (PostgreSQL)
Use managed PostgreSQL from:
- Railway
- Render
- DigitalOcean
- Supabase

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

### Adding New Vendors
1. Create parser in `scrapers/vendor_scrapers/`
2. Add to `SITES` list in `product_watcher.py`
3. Test scraper thoroughly
4. Submit pull request

### Adding Features
1. Open an issue to discuss
2. Fork the repository
3. Create feature branch
4. Submit pull request

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built for the THCA community
- Inspired by franklist.info
- Uses data from Leafly, Wikileaf, and AllBud for strain info
- Community-driven promo codes and reviews

## 📞 Support

- Discord: [Join our server](https://discord.gg/your-invite)
- GitHub Issues: [Report bugs](https://github.com/yourusername/thca-platform/issues)
- Email: support@thcacommunity.com

## 🔮 Roadmap

- [ ] Mobile apps (iOS/Android)
- [ ] Email notifications
- [ ] Advanced analytics (ML price predictions)
- [ ] Vendor API integrations
- [ ] Live chat support
- [ ] Rewards/points system
- [ ] Affiliate program
- [ ] Lab result verification
- [ ] Multi-language support
- [ ] Dark/light theme toggle

---

**Built with ❤️ for the THCA community**
