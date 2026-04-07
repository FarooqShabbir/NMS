# NMS Quick Start Guide

## Prerequisites
- Docker Desktop (Windows/Mac) or Docker + Docker Compose (Linux)
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

## Installation (5 minutes)

### Step 1: Start Services
```bash
cd nms
docker-compose up -d
```

### Step 2: Verify Services
```bash
docker-compose ps
```
All services should show "healthy" or "running".

### Step 3: Access Application
- **Frontend**: http://localhost
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

### Step 4: Login
```
Username: admin
Password: admin123
```

## First Steps

### 1. Add Your First Device
1. Go to **Devices** page
2. Click **Add Device**
3. Enter device details:
   - Name: `Core-Router-01`
   - IP: `192.168.1.1`
   - Type: `Router`
   - SNMP Community: `public` (or your community string)
4. Click **Add Device**

### 2. Verify SNMP Connectivity
1. Click the **Test Connection** button on the device
2. Should show "Connected: Cisco IOS..." or similar

### 3. View Polling Results
1. Wait 60 seconds (default polling interval)
2. Refresh the device list
3. Status should change from "unknown" to "up" or "down"

### 4. Trigger Immediate Backup
1. Go to **Backups** page
2. Click **Backup All Devices**
3. Wait for backup to complete
4. Download backup file to verify

## Default Polling Intervals

| Metric | Interval |
|--------|----------|
| Device Health (CPU/Memory) | 60 seconds |
| Interface Stats | 60 seconds |
| Routing Protocols | 5 minutes |
| VPN Status | 5 minutes |

Edit `backend/.env` to change intervals.

## Troubleshooting

### Frontend not loading
```bash
docker-compose logs frontend
docker-compose restart frontend
```

### Backend errors
```bash
docker-compose logs backend
docker-compose restart backend
```

### Database issues
```bash
docker-compose logs postgres
docker-compose restart postgres
```

### Celery not processing tasks
```bash
docker-compose logs celery_worker
docker-compose logs celery_beat
docker-compose restart celery_worker celery_beat
```

### Reset Everything (data loss!)
```bash
docker-compose down -v
docker-compose up -d
```

## Next Steps

1. **Configure Alert Notifications**
   - Edit `backend/.env`
   - Add SMTP/Slack/Telegram settings

2. **Add More Devices**
   - Use bulk import (CSV) for multiple devices

3. **Set Up Backup Schedules**
   - Go to Backups > Schedules
   - Create daily/weekly backup schedules

4. **Create Alert Rules**
   - Go to Alerts > Rules
   - Set custom thresholds

## Vercel + Supabase Quick Deploy

1. Create a Supabase project and copy the pooled PostgreSQL connection string.
2. Deploy backend as a Vercel project with root directory `backend`.
3. Set backend env vars:
   - `DATABASE_URL` (Supabase string with `sslmode=require`)
   - `SECRET_KEY`
   - `FRONTEND_URL` and `CORS_ORIGINS`
   - `DB_USE_NULL_POOL=true`
   - `AUTO_CREATE_TABLES=false`
   - `SEED_DEFAULT_ADMIN=false`
   - `ENABLE_CELERY=false`
   - `INFLUXDB_ENABLED=false` (unless managed InfluxDB is configured)
4. Run migrations: `alembic upgrade head`.
5. Deploy frontend as a second Vercel project with root directory `frontend`.
6. Set frontend env var:
   - `VITE_API_BASE_URL=https://your-backend-project.vercel.app/api`

## Support

- API Documentation: http://localhost:8000/docs
- Logs: `docker-compose logs -f`
