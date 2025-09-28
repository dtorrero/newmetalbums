# 🚀 SSL Quick Start Guide

## **Option 1: Interactive Configuration (Recommended)**

```bash
# Step 1: Configure your domain and settings
./configure-ssl.sh

# Step 2: The script will optionally run SSL setup automatically
# Or run manually: ./setup-ssl.sh
```

## **Option 2: Manual Configuration**

```bash
# Step 1: Copy environment template
cp .env.example .env

# Step 2: Edit .env file with your settings
nano .env

# Step 3: Run SSL setup
./setup-ssl.sh
```

## **Option 3: One-Command Setup**

```bash
# Set your domain and run setup in one command
DOMAIN=yourdomain.com LETSENCRYPT_EMAIL=you@domain.com ./setup-ssl.sh
```

---

## **Environment Variables**

Create a `.env` file with:

```bash
# Required
DOMAIN=yourdomain.com
LETSENCRYPT_EMAIL=your-email@domain.com

# Optional
SSL_PORT=5000
ENVIRONMENT=production
```

---

## **How It Works**

1. **nginx-ssl.template** - Template file with `${NGINX_HOST}` and `${NGINX_PORT}` variables
2. **Docker Compose** - Automatically substitutes environment variables into nginx config
3. **No hardcoding** - Domain and port are configurable via `.env` file

---

## **Final URL**

Your site will be available at: `https://yourdomain.com:5000`

---

## **Troubleshooting**

- **Missing .env file**: Run `./configure-ssl.sh` to create it interactively
- **Wrong domain**: Edit `.env` file and restart: `docker-compose restart frontend`
- **Certificate issues**: Check SSL_SETUP_GUIDE.md for detailed troubleshooting
