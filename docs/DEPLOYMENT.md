# Deployment Guide

This guide covers deployment options for Chroma Vector Search in various environments.

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/chroma-vector-search.git
cd chroma-vector-search

# Install dependencies
pip install -r requirements.txt

# Index codebase
python chroma_simple_server.py --index

# Start server
python chroma_simple_server.py --server
```

### Development Script

Use the provided start script:

```bash
# Make script executable
chmod +x start_chroma_mcp.sh

# Start server with script
./start_chroma_mcp.sh
```

## Production Deployment

### System Requirements

- **Python**: 3.9 or higher
- **Memory**: 512 MB minimum, 1 GB recommended
- **Storage**: 100 MB for dependencies + index storage
- **CPU**: 2 cores minimum, 4 cores recommended

### Installation

#### Option 1: pip install

```bash
# Install from local source
pip install .

# Or install directly
pip install git+https://github.com/yourusername/chroma-vector-search.git
```

#### Option 2: System-wide installation

```bash
# Clone repository
git clone https://github.com/yourusername/chroma-vector-search.git
cd chroma-vector-search

# Install system-wide
sudo python setup.py install

# Create systemd service
sudo cp systemd/chroma-vector-search.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable chroma-vector-search
sudo systemctl start chroma-vector-search
```

### Configuration

#### Environment Variables

```bash
# Server configuration
export CHROMA_PORT=8765
export CHROMA_PROJECT_ROOT=/path/to/project
export CHROMA_CHUNK_SIZE=15
export CHROMA_OVERLAP=3
export CHROMA_MODEL=all-MiniLM-L6-v2

# Performance tuning
export OMP_NUM_THREADS=4  # Limit CPU threads
export TF_CPP_MIN_LOG_LEVEL=3  # Reduce TensorFlow logging
```

#### Configuration File

Create `config.yaml`:

```yaml
server:
  port: 8765
  host: localhost
  project_root: /path/to/project
  
indexing:
  chunk_size: 15
  overlap: 3
  file_patterns:
    - "**/*.java"
    - "**/*.py"
    - "**/*.js"
    - "**/*.ts"
  
model:
  name: all-MiniLM-L6-v2
  device: cpu  # or cuda, mps
  
storage:
  chroma_path: .chroma_db
  max_documents: 100000
  
logging:
  level: INFO
  file: /var/log/chroma-vector-search.log
```

### Process Management

#### Systemd Service

Create `/etc/systemd/system/chroma-vector-search.service`:

```ini
[Unit]
Description=Chroma Vector Search Server
After=network.target

[Service]
Type=simple
User=chroma
Group=chroma
WorkingDirectory=/opt/chroma-vector-search
Environment="PATH=/opt/chroma-vector-search/venv/bin"
ExecStart=/opt/chroma-vector-search/venv/bin/python chroma_simple_server.py --server --port 8765
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=chroma-vector-search

[Install]
WantedBy=multi-user.target
```

#### Supervisor

Create `/etc/supervisor/conf.d/chroma-vector-search.conf`:

```ini
[program:chroma-vector-search]
command=/opt/chroma-vector-search/venv/bin/python chroma_simple_server.py --server --port 8765
directory=/opt/chroma-vector-search
user=chroma
autostart=true
autorestart=true
stderr_logfile=/var/log/chroma-vector-search.err.log
stdout_logfile=/var/log/chroma-vector-search.out.log
environment=PYTHONUNBUFFERED="1"
```

### Docker Deployment

#### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 chroma
USER chroma

# Expose port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python chroma_client.py --ping --port 8765 || exit 1

# Start server
CMD ["python", "chroma_simple_server.py", "--server", "--port", "8765"]
```

#### Docker Compose

```yaml
version: '3.8'

services:
  chroma-vector-search:
    build: .
    ports:
      - "8765:8765"
    volumes:
      - ./data:/app/.chroma_db
      - ./projects:/projects
    environment:
      - CHROMA_PROJECT_ROOT=/projects
      - CHROMA_PORT=8765
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "chroma_client.py", "--ping", "--port", "8765"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Kubernetes Deployment

#### Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chroma-vector-search
spec:
  replicas: 1
  selector:
    matchLabels:
      app: chroma-vector-search
  template:
    metadata:
      labels:
        app: chroma-vector-search
    spec:
      containers:
      - name: chroma-vector-search
        image: yourregistry/chroma-vector-search:latest
        ports:
        - containerPort: 8765
        env:
        - name: CHROMA_PROJECT_ROOT
          value: "/projects"
        - name: CHROMA_PORT
          value: "8765"
        volumeMounts:
        - name: project-data
          mountPath: /projects
        - name: chroma-data
          mountPath: /app/.chroma_db
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - python
            - chroma_client.py
            - --ping
            - --port
            - "8765"
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - python
            - chroma_client.py
            - --ping
            - --port
            - "8765"
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: project-data
        persistentVolumeClaim:
          claimName: project-pvc
      - name: chroma-data
        persistentVolumeClaim:
          claimName: chroma-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: chroma-vector-search
spec:
  selector:
    app: chroma-vector-search
  ports:
  - port: 8765
    targetPort: 8765
  type: ClusterIP
```

## Monitoring

### Logging

Configure logging in `chroma_simple_server.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/chroma-vector-search.log'),
        logging.StreamHandler()
    ]
)
```

### Metrics

Add Prometheus metrics:

```python
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics
SEARCH_REQUESTS = Counter('chroma_search_requests_total', 'Total search requests')
SEARCH_DURATION = Histogram('chroma_search_duration_seconds', 'Search request duration')
INDEXED_DOCUMENTS = Counter('chroma_indexed_documents_total', 'Total indexed documents')

# Start metrics server
start_http_server(8000)
```

### Health Checks

```bash
# Basic health check
python chroma_client.py --ping

# Detailed health check
python chroma_client.py --stats

# Custom health check script
#!/bin/bash
RESPONSE=$(python chroma_client.py --ping --port 8765 2>/dev/null)
if echo "$RESPONSE" | grep -q '"status": "alive"'; then
    exit 0
else
    exit 1
fi
```

## Backup and Recovery

### Backup Strategy

```bash
#!/bin/bash
# backup-chroma.sh

BACKUP_DIR="/backups/chroma-vector-search"
DATE=$(date +%Y%m%d_%H%M%S)

# Stop server
systemctl stop chroma-vector-search

# Backup index
tar -czf "$BACKUP_DIR/chroma-index-$DATE.tar.gz" .chroma_db/

# Backup configuration
cp config.yaml "$BACKUP_DIR/config-$DATE.yaml"

# Start server
systemctl start chroma-vector-search

# Keep only last 7 backups
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
```

### Recovery

```bash
#!/bin/bash
# restore-chroma.sh

BACKUP_FILE="$1"

# Stop server
systemctl stop chroma-vector-search

# Restore index
rm -rf .chroma_db
tar -xzf "$BACKUP_FILE"

# Start server
systemctl start chroma-vector-search
```

## Scaling

### Horizontal Scaling

For multiple projects or teams:

```bash
# Project 1
python chroma_simple_server.py --server --port 8765 --project-root /projects/team1

# Project 2  
python chroma_simple_server.py --server --port 8766 --project-root /projects/team2

# Project 3
python chroma_simple_server.py --server --port 8767 --project-root /projects/team3
```

### Load Balancing

Use Nginx as load balancer:

```nginx
upstream chroma_servers {
    server 127.0.0.1:8765;
    server 127.0.0.1:8766;
    server 127.0.0.1:8767;
}

server {
    listen 80;
    server_name chroma.example.com;
    
    location / {
        proxy_pass http://chroma_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Security

### Firewall Configuration

```bash
# Allow only local connections
sudo ufw allow from 127.0.0.1 to any port 8765

# Or allow specific IP ranges
sudo ufw allow from 192.168.1.0/24 to any port 8765
```

### Authentication

Add basic authentication:

```python
import base64

def authenticate(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False
    
    try:
        auth_type, credentials = auth_header.split(' ', 1)
        if auth_type.lower() != 'basic':
            return False
        
        decoded = base64.b64decode(credentials).decode('utf-8')
        username, password = decoded.split(':', 1)
        
        # Check credentials
        return username == 'admin' and password == 'secret'
    except:
        return False
```

### SSL/TLS

Use Nginx as SSL termination:

```nginx
server {
    listen 443 ssl;
    server_name chroma.example.com;
    
    ssl_certificate /etc/ssl/certs/chroma.example.com.crt;
    ssl_certificate_key /etc/ssl/private/chroma.example.com.key;
    
    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Performance Tuning

### Memory Optimization

```python
# Reduce chunk size for memory-constrained environments
CHUNK_SIZE = 10
OVERLAP = 2

# Use smaller model
MODEL = 'paraphrase-MiniLM-L3-v2'
```

### CPU Optimization

```bash
# Set CPU affinity
taskset -c 0,1 python chroma_simple_server.py --server

# Limit CPU usage with cpulimit
cpulimit -l 50 -p $(pgrep -f chroma_simple_server)
```

### Disk Optimization

```bash
# Use faster storage
ln -sf /mnt/ssd/.chroma_db .chroma_db

# Optimize SQLite
PRAGMA synchronous = NORMAL;
PRAGMA journal_mode = WAL;
PRAGMA cache_size = -2000;
```

## Troubleshooting Production Issues

### Common Issues

1. **Server crashes on startup**
   ```bash
   # Check logs
   journalctl -u chroma-vector-search -n 50
   
   # Check dependencies
   pip list | grep -E "chromadb|sentence-transformers"
   
   # Check disk space
   df -h .
   ```

2. **High memory usage**
   ```bash
   # Monitor memory
   top -p $(pgrep -f chroma_simple_server)
   
   # Reduce chunk size
   export CHROMA_CHUNK_SIZE=10
   ```

3. **Slow search performance**
   ```bash
   # Check CPU usage
   htop
   
   # Check disk I/O
   iotop
   
   # Rebuild index
   python chroma_simple_server.py --index
   ```

### Debug Mode

```bash
# Run with debug logging
python chroma_simple_server.py --server --verbose

# Or enable debug in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Maintenance

### Regular Tasks

1. **Daily**
   - Check server status
   - Review logs for errors
   - Monitor disk space

2. **Weekly**
   - Backup index
   - Update dependencies
   - Clean old logs

3. **Monthly**
   - Performance review
   - Security updates
   - Capacity planning

### Update Procedure

```bash
# 1. Backup current installation
./backup-chroma.sh

# 2. Stop server
systemctl stop chroma-vector-search

# 3. Update code
git pull origin main

# 4. Update dependencies
pip install -r requirements.txt --upgrade

# 5. Restart server
systemctl start chroma-vector-search

# 6. Verify
python chroma_client.py --ping
```

## Support

### Getting Help

1. **Documentation**: Check [README.md](README.md) and [API.md](docs/API.md)
2. **Issues**: Report bugs on GitHub
3. **Community**: Join discussions

### Emergency Procedures

1. **Server down**
   ```bash
   # Restart service
   systemctl restart chroma-vector-search
   
   # Check logs
   journalctl -u chroma-vector-search --since "5 minutes ago"
   ```

2. **Data corruption**
   ```bash
   # Restore from backup
   ./restore-chroma.sh /backups/chroma-index-latest.tar.gz
   ```

3. **Security incident**
   ```bash
   # Stop server immediately
   systemctl stop chroma-vector-search
   
   # Isolate server
   ufw deny 8765
   
   # Investigate logs
   grep -i "error\|fail\|unauth" /var/log/chroma-vector-search.log
   ```