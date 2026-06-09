# 🕵️ Prospect Finder

Discover businesses worldwide with enriched contact data. Finds email, LinkedIn, Instagram, Facebook, and phone for any business type in any city.

## Features

- 🔍 **Discover** businesses via Google Places API (official, reliable, free tier)
- 📧 **Enrich** with email, LinkedIn, Instagram, Facebook, phone
- 🌍 **Global** — works in US, UK, Australia, Singapore, India, and 200+ countries
- 🧠 **Smart dedup** — fuzzy matching against your existing prospect list
- 🔥 **Hot leads** — automatically flags businesses without websites (easiest to convert)
- 📥 **Export** — simple CSV + import-ready format for your prospect list

## How It Works

```
Phase 1: Google Places API → finds businesses by type + location
Phase 2: Enrichment → DuckDuckGo + Facebook + Instagram + website scrape
Output: CSV with email, LinkedIn, Instagram, Facebook, phone, website status
```

## Setup Guide (3 minutes)

### 1. Get a Google API Key

1. Go to **[Google Cloud Console](https://console.cloud.google.com)**
2. Click **Create Project** (or select an existing one)
3. Go to **APIs & Services → Library**
4. Search for **Places API** and click **Enable**
5. Go to **Credentials → Create Credentials → API Key**
6. Copy the key (looks like `AIzaSy...`)

> **Cost:** Google gives $200/month free credit. Each scan costs ~$0.50-$1.00. You can run 200-400 scans per month for free.

### 2. Deploy on Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to **[Streamlit Cloud](https://streamlit.io/cloud)** → Sign in with GitHub
3. Click **New App** → select your repo → set **Main file** to `app.py`
4. Go to **Settings → Secrets** and add:

```toml
password = "your-team-password"
google_api_key = "AIzaSy..."
```

5. Click **Deploy** → your app is live at `https://yourapp.streamlit.app`

### 3. Local Development

```bash
pip install -r requirements.txt

# Create .streamlit/secrets.toml:
# password = "your-password"
# google_api_key = "AIzaSy..."

streamlit run app.py
```

## Usage

1. Enter business types (e.g., `med spa`, `cosmetic dentist`, `dermatologist`)
2. Enter locations (one per line: `City, State` or `City, Country`)
3. Optionally upload your existing prospect CSV to avoid duplicates
4. Click **Start Scan**
5. Wait 2-5 minutes for results
6. Download CSV

## Supported Countries

| Country | Code | Local Directories |
|---------|------|-------------------|
| United States | US | Yelp, BBB, RealSelf |
| United Kingdom | UK | DuckDuckGo + social |
| Australia | AU | DuckDuckGo + social |
| Singapore | SG | DuckDuckGo + social |
| India | IN | DuckDuckGo + social |
| Canada | CA | DuckDuckGo + social |
| 200+ more | — | Google Places + DuckDuckGo + social |

## Output Fields

| Field | Description |
|-------|-------------|
| Business Name | Name from Google Places |
| Category | Your input category |
| City / State / Country | Location |
| Email | Found via search + social scraping |
| Phone | From Google Places or enrichment |
| Website | Empty = no website (🔥 hot lead) |
| LinkedIn | From search |
| Instagram | From search + bio scrape |
| Facebook | From search + page scrape |
| Rating / Reviews | From Google Places |
| Lead Priority | Hot (email + no site) / Warm |
| Email Source | Where the email was found |

## File Structure

```
prospect-finder/
├── app.py                   ← Streamlit UI
├── scraper.py               ← Scan orchestrator
├── requirements.txt         ← Dependencies
├── secrets.toml.example     ← API key template
├── providers/
│   ├── google_places.py     ← Google Places API (discovery + pagination)
│   ├── duckduckgo_provider.py  ← DuckDuckGo search (email extraction)
│   ├── social_scraper.py    ← Facebook + Instagram bio scraping
│   └── website_scraper.py   ← Website contact page scraping
├── utils/
│   ├── dedup.py             ← Fuzzy matching against existing CSV
│   └── phone_format.py      ← Phone number formatting
└── README.md
```

## Cost Breakdown

| Component | Cost per scan (10 cities, 2 types) |
|-----------|-------------------------------------|
| Google Places API | ~$0.60 |
| DuckDuckGo | Free |
| Facebook/Instagram scrape | Free |
| Website scrape | Free |
| **Total** | **~$0.60** |
| **Free monthly credit** | **$200** |
| **Scans per month** | **~300** |

## FAQ

### Why use Google Places API instead of scraping Google Maps?
Official API is reliable, doesn't break, returns structured data, and is within ToS. The $200/month free credit covers ~28,000 API calls — enough for ~300 full scans.

### How accurate are the emails?
~50-60% of businesses will have a findable email. Sources include DuckDuckGo snippets, Facebook About sections, Instagram bios, and website contact pages. No email verification is performed — you should verify before sending.

### Can I add more countries?
Yes — the tool auto-detects country from the city/state you enter. For any country, Google Places + DuckDuckGo + social scraping will work. Country-specific directories are included for US only.

### What does "Hot" mean?
🔥 Hot = business has no website AND we found an email or LinkedIn. These are your easiest conversions — they clearly need web presence services.

### Is this legal?
Yes — the tool uses official Google Places API and scrapes only publicly available information (same as a manual search). No login, no bypassing paywalls, no personal data collection.
