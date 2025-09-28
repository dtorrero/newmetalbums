# SSL Setup Guide for Metal Albums Docker Deployment

This guide covers SSL certificate setup for both **Debian-based** (Ubuntu, Debian, Armbian) and **Arch-based** (Arch Linux, Manjaro) systems.

## 🎯 **Overview**

The Metal Albums application uses Docker with nginx SSL termination to provide HTTPS access on port 5000. SSL certificates are managed on the host system and mounted into the Docker container.

**Final URL**: `https://example.com:5000`

---

## 🐧 **Debian-Based Systems (Ubuntu, Debian, Armbian)**

### **Step 1: Install Certbot**

```bash
# Update package list
sudo apt update

# Install certbot and nginx plugin
sudo apt install certbot python3-certbot-nginx

# Verify installation
certbot --version
```

### **Step 2: Stop Docker Services**

```bash
# Navigate to your project directory
cd /path/to/newmetalbums

# Stop running containers
docker-compose down
```

### **Step 3: Obtain SSL Certificate**

```bash
# Method A: Standalone mode (recommended for custom ports)
sudo certbot certonly --standalone \
    --preferred-challenges http \
    --http-01-port 80 \
    -d example.com \
    --email your-email@domain.com \
    --agree-tos \
    --no-eff-email

# Method B: Webroot mode (if you have a web server running)
sudo certbot certonly --webroot \
    -w /var/www/html \
    -d example.com \
    --email your-email@domain.com \
    --agree-tos \
    --no-eff-email
```

### **Step 4: Verify Certificate Installation**

```bash
# Check certificate files
sudo ls -la /etc/letsencrypt/live/example.com/

# Should show:
# cert.pem -> ../../archive/example.com/cert1.pem
# chain.pem -> ../../archive/example.com/chain1.pem
# fullchain.pem -> ../../archive/example.com/fullchain1.pem
# privkey.pem -> ../../archive/example.com/privkey1.pem
```

### **Step 5: Set Up Auto-Renewal**

```bash
# Test renewal process
sudo certbot renew --dry-run

# Add to crontab for automatic renewal
sudo crontab -e

# Add this line (runs at 3 AM daily):
0 3 * * * /usr/bin/certbot renew --quiet --deploy-hook "cd /path/to/newmetalbums && docker-compose restart frontend"
```

### **Step 6: Configure Firewall**

```bash
# Install and configure UFW
sudo apt install ufw

# Allow SSH (important!)
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 5000

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## 🏔️ **Arch-Based Systems (Arch Linux, Manjaro)**

### **Step 1: Install Certbot**

```bash
# Update system
sudo pacman -Syu

# Install certbot
sudo pacman -S certbot certbot-nginx

# Alternative: Install from AUR (if needed)
yay -S certbot-git

# Verify installation
certbot --version
```

### **Step 2: Stop Docker Services**

```bash
# Navigate to your project directory
cd /path/to/newmetalbums

# Stop running containers
docker-compose down
```

### **Step 3: Obtain SSL Certificate**

```bash
# Method A: Standalone mode (recommended)
sudo certbot certonly --standalone \
    --preferred-challenges http \
    --http-01-port 80 \
    -d example.com \
    --email your-email@domain.com \
    --agree-tos \
    --no-eff-email

# Method B: Manual mode (for complex setups)
sudo certbot certonly --manual \
    --preferred-challenges http \
    -d example.com \
    --email your-email@domain.com \
    --agree-tos \
    --no-eff-email
```

### **Step 4: Verify Certificate Installation**

```bash
# Check certificate files
sudo ls -la /etc/letsencrypt/live/example.com/

# Test certificate validity
sudo openssl x509 -in /etc/letsencrypt/live/example.com/cert.pem -text -noout
```

### **Step 5: Set Up Auto-Renewal with systemd**

```bash
# Enable and start certbot renewal timer
sudo systemctl enable certbot-renew.timer
sudo systemctl start certbot-renew.timer

# Check timer status
sudo systemctl status certbot-renew.timer

# Create custom renewal hook
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy

# Create deployment hook script
sudo tee /etc/letsencrypt/renewal-hooks/deploy/docker-restart.sh << 'EOF'
#!/bin/bash
cd /path/to/newmetalbums
docker-compose restart frontend
EOF

# Make script executable
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/docker-restart.sh
```

### **Step 6: Configure Firewall**

```bash
# Install and configure firewalld
sudo pacman -S firewalld
sudo systemctl enable firewalld
sudo systemctl start firewalld

# Allow necessary ports
sudo firewall-cmd --permanent --add-port=22/tcp    # SSH
sudo firewall-cmd --permanent --add-port=80/tcp    # HTTP
sudo firewall-cmd --permanent --add-port=443/tcp   # HTTPS
sudo firewall-cmd --permanent --add-port=5000/tcp  # Custom SSL port

# Reload firewall
sudo firewall-cmd --reload

# Check status
sudo firewall-cmd --list-all
```

---

## 🚀 **Final Deployment Steps (Both Systems)**

### **Step 1: Update Domain in Configuration**

```bash
# Edit the nginx SSL configuration
nano frontend/nginx-ssl.conf

# Replace 'example.com' with your actual domain name
sed -i 's/example.com/yourdomain.com/g' frontend/nginx-ssl.conf
```

### **Step 2: Start Docker Services**

```bash
# Start containers with SSL configuration
docker-compose up -d

# Check container status
docker-compose ps

# View logs
docker-compose logs frontend
```

### **Step 3: Test SSL Configuration**

```bash
# Test SSL certificate
openssl s_client -connect yourdomain.com:5000 -servername yourdomain.com

# Test HTTP to HTTPS redirect
curl -I http://yourdomain.com

# Test HTTPS response
curl -I https://yourdomain.com:5000
```

### **Step 4: Validate SSL Security**

Visit these online tools to test your SSL configuration:

- **SSL Labs Test**: https://www.ssllabs.com/ssltest/
- **Security Headers**: https://securityheaders.com/
- **SSL Checker**: https://www.sslshopper.com/ssl-checker.html

---

## 🔧 **Troubleshooting**

### **Common Issues**

**1. Certificate Permission Errors**
```bash
# Fix certificate permissions
sudo chmod 755 /etc/letsencrypt/live/
sudo chmod 755 /etc/letsencrypt/archive/
```

**2. Docker Container Can't Access Certificates**
```bash
# Check if certificates exist
sudo ls -la /etc/letsencrypt/live/yourdomain.com/

# Restart container with proper volume mounts
docker-compose down && docker-compose up -d
```

**3. Port 80 Already in Use**
```bash
# Check what's using port 80
sudo netstat -tlnp | grep :80

# Stop conflicting services
sudo systemctl stop apache2  # or nginx
```

**4. Firewall Blocking Connections**
```bash
# Debian/Ubuntu
sudo ufw status
sudo ufw allow 5000

# Arch Linux
sudo firewall-cmd --list-all
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### **Certificate Renewal Issues**

```bash
# Test renewal manually
sudo certbot renew --dry-run

# Force renewal (if needed)
sudo certbot renew --force-renewal

# Check renewal logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### **Docker-Specific Issues**

```bash
# Check container logs
docker-compose logs frontend

# Restart specific service
docker-compose restart frontend

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

---

## 📋 **Security Checklist**

- ✅ SSL certificate installed and valid
- ✅ HTTP redirects to HTTPS
- ✅ Strong SSL ciphers configured
- ✅ Security headers enabled
- ✅ Firewall configured properly
- ✅ Auto-renewal set up
- ✅ SSL Labs grade A or A+
- ✅ HSTS enabled
- ✅ OCSP stapling configured

---

## 🔄 **Maintenance**

### **Monthly Tasks**
- Check SSL certificate expiration: `sudo certbot certificates`
- Review SSL Labs test results
- Update Docker images: `docker-compose pull && docker-compose up -d`

### **Quarterly Tasks**
- Review and update SSL configuration
- Check for nginx security updates
- Audit firewall rules

---

## 📞 **Support**

If you encounter issues:

1. **Check logs**: `docker-compose logs frontend`
2. **Verify certificates**: `sudo certbot certificates`
3. **Test connectivity**: `curl -I https://yourdomain.com:5000`
4. **Review firewall**: `sudo ufw status` or `sudo firewall-cmd --list-all`

**Final URL**: `https://yourdomain.com:5000`
