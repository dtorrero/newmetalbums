# Manual SSL Configuration Guide

**Purpose**: Step-by-step manual SSL setup for Docker deployments  
**For**: Generic SSL configuration with Let's Encrypt certificates  

---

## 🎯 **Overview**

This guide documents the manual SSL configuration process for applications running in Docker containers. The approach involves:

1. **Host Server**: Install certbot and obtain SSL certificates
2. **Docker Container**: Configure nginx for SSL termination
3. **Integration**: Mount certificates and configure ports

---

## 📋 **Prerequisites**

- Docker containers running
- Domain name pointing to your server
- Root/sudo access on host server
- Currently inside frontend Docker container

---

## 🔧 **Step 1: Exit Container and Prepare Host Server**

```bash
# Exit the Docker container first
exit

# Verify you're on the host server
hostname
pwd
```

## 🔧 **Step 2: Install Certbot on Host Server (Odroid/Armbian)**

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install certbot and dependencies
sudo apt install -y certbot python3-certbot-nginx

# Verify installation
certbot --version
which certbot
```

## 🔧 **Step 3: Stop Docker Services for Certificate Generation**

```bash
# Navigate to your project directory
cd /path/to/your-project

# Stop containers to free port 80
docker-compose down

# Verify port 80 is free
sudo netstat -tlnp | grep :80
```

## 🔧 **Step 4: Obtain SSL Certificate**

```bash
# Replace with your actual domain and email
DOMAIN="yourdomain.com"
EMAIL="your-email@example.com"

# Generate SSL certificate using standalone mode
sudo certbot certonly \
    --standalone \
    --preferred-challenges http \
    --http-01-port 80 \
    -d $DOMAIN \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --non-interactive

# Verify certificate files were created
sudo ls -la /etc/letsencrypt/live/$DOMAIN/
```

**Expected output:**
```
cert.pem -> ../../archive/yourdomain.com/cert1.pem
chain.pem -> ../../archive/yourdomain.com/chain1.pem
fullchain.pem -> ../../archive/yourdomain.com/fullchain1.pem
privkey.pem -> ../../archive/yourdomain.com/privkey1.pem
```

## 🔧 **Step 5: Configure Docker for SSL**

### **5.1: Update docker-compose.yml**

```bash
# Backup original docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup

# Edit docker-compose.yml
nano docker-compose.yml
```

**Add these changes to the frontend service:**

```yaml
  frontend:
    image: ghcr.io/dtorrero/newmetalbums-frontend:latest
    container_name: newmetalbums-frontend
    ports:
      - "80:80"
      - "443:443"      # Add HTTPS port
   
    volumes:
      # Mount SSL certificates (read-only)
      - /etc/letsencrypt:/etc/letsencrypt:ro
    # ... rest of configuration
```

### **5.2: Start Container for Configuration**

```bash
# Start containers with SSL certificate access
docker-compose up -d

# Access the frontend container
docker exec -it newmetalbums-frontend sh
```

## 🔧 **Step 6: Configure Nginx Inside Container**

**Now you're back inside the container. Follow these steps:**

### **6.1: Backup Original Configuration**

```bash
# Inside container
cp /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.backup

# View current configuration
cat /etc/nginx/conf.d/default.conf
```

### **6.2: Create SSL-Enabled Configuration**

```bash
# Create new SSL configuration
cat > /etc/nginx/conf.d/default.conf << 'EOF'
# HTTP Server - Redirect to HTTPS
server {
    listen 80;
    server_name yourdomain.com;  # Replace with your domain
    return 301 https://$server_name$request_uri;
}

# HTTPS Server on port 443
server {
    listen 443 ssl;
    http2 on;
    server_name yourdomain.com;  # Replace with your domain
    root /usr/share/nginx/html;
    index index.html;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Modern SSL Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Covers proxy to backend
    location /covers/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Port 443;
    }

    # API proxy to backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Port 443;
    }

    # Static assets caching
    location ~* ^/(?!covers/).*\.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # React Router handling
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;
}

EOF
```

### **6.3: Replace Domain Placeholder**

```bash
# Replace 'yourdomain.com' with your actual domain
DOMAIN="yourdomain.com"  # Set your domain here
sed -i "s/yourdomain.com/$DOMAIN/g" /etc/nginx/conf.d/default.conf

# Verify the configuration
cat /etc/nginx/conf.d/default.conf
```

### **6.4: Test and Reload Nginx**

```bash
# Test nginx configuration
nginx -t

# If test passes, reload nginx
nginx -s reload

# Check nginx is running
ps aux | grep nginx

# Check what ports are listening
netstat -tlnp
```

## 🔧 **Step 7: Exit Container and Test**

```bash
# Exit the container
exit

# Test SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Test HTTP redirect
curl -I http://yourdomain.com

# Test HTTPS access
curl -I https://yourdomain.com
```

## 🔧 **Step 8: Configure Firewall**

```bash
# Allow necessary ports
sudo ufw allow 80
sudo ufw allow 443

# Check firewall status
sudo ufw status
```

## 🔧 **Step 9: Set Up Certificate Auto-Renewal**

```bash
# Test renewal process
sudo certbot renew --dry-run

# Add renewal to crontab
sudo crontab -e

# Add this line (runs daily at 3 AM):
0 3 * * * /usr/bin/certbot renew --quiet --deploy-hook "cd /path/to/your-project && docker-compose restart your-frontend-service"
```

---

## 🧪 **Testing Checklist**

- [ ] HTTP redirects to HTTPS: `curl -I http://yourdomain.com`
- [ ] HTTPS works on port 443: `curl -I https://yourdomain.com`
- [ ] Admin button visibility works correctly
- [ ] API calls work over HTTPS
- [ ] Album covers load properly
- [ ] SSL certificate is valid: Check with browser or SSL Labs
- [ ] Auto-renewal is configured

---

## 🔧 **Troubleshooting**

### **Certificate Permission Issues**
```bash
# Fix certificate permissions
sudo chmod 755 /etc/letsencrypt/live/
sudo chmod 755 /etc/letsencrypt/archive/
```

### **Nginx Configuration Errors**
```bash
# Check nginx logs in container
docker exec your-frontend-container tail -f /var/log/nginx/error.log

# Test configuration
docker exec your-frontend-container nginx -t
```

### **Port Issues**
```bash
# Check what's using ports
sudo netstat -tlnp | grep -E ':(80|443)'

# Restart containers
docker-compose restart your-frontend-service
```

### **Certificate Not Found**
```bash
# Verify certificate exists
sudo ls -la /etc/letsencrypt/live/yourdomain.com/

# Check container can access certificates
docker exec your-frontend-container ls -la /etc/letsencrypt/live/yourdomain.com/
```

---

## 📋 **Configuration Files Created/Modified**

1. **docker-compose.yml** - Added SSL ports and certificate volume mount
2. **/etc/nginx/conf.d/default.conf** (in container) - SSL-enabled nginx configuration
3. **Crontab** - Certificate auto-renewal

---

## 🚀 **Final URLs**

- **HTTP**: `http://yourdomain.com` → Redirects to HTTPS
- **HTTPS**: `https://yourdomain.com` → Main application

---

## 📝 **Notes for Future Automation**

1. **Certificate generation** can be automated with certbot standalone mode
2. **Nginx configuration** can be templated with domain variables
3. **Docker volume mounts** are essential for certificate access
4. **Port configuration** needs to match nginx listen directives
5. **Auto-renewal** requires deploy hooks to restart containers

This manual process provides the foundation for creating automated SSL setup scripts in the future.
