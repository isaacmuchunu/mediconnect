# 🚀 MediConnect Deployment Guide

## 📋 **PRODUCTION DEPLOYMENT CHECKLIST**

### ✅ **SYSTEM REQUIREMENTS**

#### **Server Requirements**
- **OS**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **CPU**: 4+ cores (8+ recommended for production)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 100GB+ SSD storage
- **Network**: High-speed internet with static IP

#### **Software Dependencies**
- **Python**: 3.11+
- **PostgreSQL**: 15+ with PostGIS extension
- **Redis**: 6.0+
- **Nginx**: 1.18+
- **SSL Certificate**: Let's Encrypt or commercial
- **Docker**: 20.10+ (optional but recommended)

---

## 🛠 **INSTALLATION STEPS**

### **1. System Preparation**

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql-15 postgresql-contrib postgresql-15-postgis-3 redis-server nginx git curl

# Create application user
sudo useradd -m -s /bin/bash mediconnect
sudo usermod -aG sudo mediconnect
```

### **2. Database Setup**

```bash
# Switch to postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE mediconnect_prod;
CREATE USER mediconnect WITH PASSWORD 'your_secure_password_here';
ALTER ROLE mediconnect SET client_encoding TO 'utf8';
ALTER ROLE mediconnect SET default_transaction_isolation TO 'read committed';
ALTER ROLE mediconnect SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mediconnect_prod TO mediconnect;

-- Enable PostGIS extension
\c mediconnect_prod;
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

\q
```

### **3. Application Deployment**

```bash
# Switch to application user
sudo su - mediconnect

# Clone repository
git clone https://github.com/your-org/mediconnect.git
cd mediconnect

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create production settings
cp hospital_ereferral/settings.py hospital_ereferral/settings_prod.py
```

### **4. Environment Configuration**

Create `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql://mediconnect:your_secure_password_here@localhost:5432/mediconnect_prod

# Security Settings
SECRET_KEY=your_very_long_and_secure_secret_key_here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Email Configuration
EMAIL_HOST=smtp.your-email-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password

# Twilio Configuration (for SMS)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Google Maps API
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# Security Headers
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

### **5. Database Migration**

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Load initial data (optional)
python manage.py loaddata fixtures/initial_data.json
```

---

## 🔧 **PRODUCTION CONFIGURATION**

### **1. Gunicorn Configuration**

Create `/home/mediconnect/mediconnect/gunicorn.conf.py`:

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
```

### **2. Systemd Service**

Create `/etc/systemd/system/mediconnect.service`:

```ini
[Unit]
Description=MediConnect Gunicorn daemon
After=network.target

[Service]
User=mediconnect
Group=mediconnect
WorkingDirectory=/home/mediconnect/mediconnect
Environment="PATH=/home/mediconnect/mediconnect/venv/bin"
ExecStart=/home/mediconnect/mediconnect/venv/bin/gunicorn --config gunicorn.conf.py hospital_ereferral.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

### **3. Celery Configuration**

Create `/etc/systemd/system/mediconnect-celery.service`:

```ini
[Unit]
Description=MediConnect Celery Worker
After=network.target

[Service]
Type=forking
User=mediconnect
Group=mediconnect
EnvironmentFile=/home/mediconnect/mediconnect/.env
WorkingDirectory=/home/mediconnect/mediconnect
ExecStart=/home/mediconnect/mediconnect/venv/bin/celery multi start worker1 \
    -A hospital_ereferral --pidfile=/var/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log --loglevel=INFO
ExecStop=/home/mediconnect/mediconnect/venv/bin/celery multi stopwait worker1 \
    --pidfile=/var/run/celery/%n.pid
ExecReload=/home/mediconnect/mediconnect/venv/bin/celery multi restart worker1 \
    -A hospital_ereferral --pidfile=/var/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log --loglevel=INFO

[Install]
WantedBy=multi-user.target
```

### **4. Nginx Configuration**

Create `/etc/nginx/sites-available/mediconnect`:

```nginx
upstream mediconnect {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    client_max_body_size 100M;

    location / {
        proxy_pass http://mediconnect;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static/ {
        alias /home/mediconnect/mediconnect/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /home/mediconnect/mediconnect/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://mediconnect;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🔐 **SECURITY CONFIGURATION**

### **1. SSL Certificate Setup**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

### **2. Firewall Configuration**

```bash
# Configure UFW firewall
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### **3. Database Security**

```bash
# Edit PostgreSQL configuration
sudo nano /etc/postgresql/15/main/postgresql.conf

# Set listen_addresses = 'localhost'
# Set ssl = on

sudo nano /etc/postgresql/15/main/pg_hba.conf

# Ensure only local connections are allowed
# local   all             all                                     md5
# host    all             all             127.0.0.1/32            md5
```

---

## 🚀 **DEPLOYMENT EXECUTION**

### **1. Start Services**

```bash
# Enable and start services
sudo systemctl enable mediconnect
sudo systemctl enable mediconnect-celery
sudo systemctl enable nginx
sudo systemctl enable redis-server
sudo systemctl enable postgresql

sudo systemctl start mediconnect
sudo systemctl start mediconnect-celery
sudo systemctl start nginx
sudo systemctl start redis-server
sudo systemctl start postgresql
```

### **2. Verify Deployment**

```bash
# Check service status
sudo systemctl status mediconnect
sudo systemctl status mediconnect-celery
sudo systemctl status nginx

# Check logs
sudo journalctl -u mediconnect -f
sudo journalctl -u mediconnect-celery -f

# Test application
curl -I https://your-domain.com
```

---

## 📊 **MONITORING & MAINTENANCE**

### **1. Log Management**

```bash
# Set up log rotation
sudo nano /etc/logrotate.d/mediconnect

/var/log/mediconnect/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 mediconnect mediconnect
    postrotate
        systemctl reload mediconnect
    endscript
}
```

### **2. Backup Strategy**

```bash
# Database backup script
#!/bin/bash
BACKUP_DIR="/home/mediconnect/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -h localhost -U mediconnect mediconnect_prod > $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### **3. Performance Monitoring**

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Monitor system resources
htop
iotop
nethogs

# Monitor application logs
tail -f /var/log/mediconnect/application.log
```

---

## 🔄 **UPDATE PROCEDURES**

### **1. Application Updates**

```bash
# Switch to application user
sudo su - mediconnect
cd mediconnect

# Backup current version
git tag backup-$(date +%Y%m%d)

# Pull latest changes
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart mediconnect
sudo systemctl restart mediconnect-celery
```

### **2. Database Updates**

```bash
# Create database backup before updates
pg_dump -h localhost -U mediconnect mediconnect_prod > backup_before_update.sql

# Run migrations
python manage.py migrate

# Verify application functionality
curl -I https://your-domain.com
```

---

## 🆘 **TROUBLESHOOTING**

### **Common Issues**

1. **Service won't start**: Check logs with `journalctl -u mediconnect`
2. **Database connection errors**: Verify PostgreSQL is running and credentials are correct
3. **Static files not loading**: Run `python manage.py collectstatic` and check Nginx configuration
4. **SSL certificate issues**: Verify certificate paths and run `sudo certbot renew`

### **Emergency Procedures**

1. **Rollback deployment**: Use git tags to revert to previous version
2. **Database recovery**: Restore from backup using `psql`
3. **Service restart**: `sudo systemctl restart mediconnect`

---

## 📞 **SUPPORT**

For deployment support and troubleshooting:
- **Documentation**: Check project wiki and documentation
- **Logs**: Always check application and system logs first
- **Community**: Join our support community for assistance

**🎉 Your MediConnect system is now ready for production use!**
