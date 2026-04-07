# Network Monitoring System (NMS)

A comprehensive network monitoring solution with SNMP backend, supporting routing protocols (BGP, OSPF, EIGRP), VPN/DMVPN monitoring, and automated device backups.

## Features

### Device Management
- Add/Edit/Delete network devices (routers, switches, firewalls, servers)
- Auto-discovery via SNMP
- Device grouping by location/department
- Real-time status monitoring (Up/Down/Warning)

### SNMP Support
- SNMP v1, v2c, v3 with authentication and encryption
- Community string management
- Custom OID configuration
- MIB browser support

### Routing Protocol Monitoring
| Protocol | Metrics |
|----------|---------|
| **BGP** | Neighbor state, Prefixes, AS info, Uptime, Flap count |
| **OSPF** | Neighbor state, Area ID, Router ID, LSDB info |
| **EIGRP** | Neighbor table, Successor count, K-values, AS number |

### VPN & DMVPN Monitoring
- IPSec tunnel status (Phase 1/2, SA count, encryption stats)
- GRE tunnel monitoring
- DMVPN NHRP cache entries
- Hub-and-spoke topology visualization

### Device Backup
- Automated scheduled backups (SSH/SCP/TFTP)
- Git integration for versioned backups
- Configuration diff viewer
- Rollback capabilities
- Cloud sync (S3, Azure, GCS)

### Alerting
- Threshold-based alerts (CPU, Memory, Bandwidth)
- Status change alerts (Device/Interface/Routing/VPN down)
- Multiple notification channels (Email, Slack, Telegram, Webhook)
- Maintenance windows for alert suppression
- Alert escalation

### User Management
- Role-based access control (Admin, Operator, Viewer, Backup Admin)
- JWT authentication
- TOTP 2FA support
- Audit logging

---

## Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: Supabase PostgreSQL (primary), InfluxDB (optional metrics)
- **Cache/Queue**: Redis + Celery
- **SNMP**: pysnmp
- **SSH**: paramiko

### Frontend
- **Framework**: React 18 + TypeScript
- **UI**: Mantine UI
- **Charts**: Recharts / Chart.js
- **State**: Zustand
- **HTTP**: Axios

### Infrastructure
- Docker + Docker Compose
- Nginx (reverse proxy)
- Vercel (frontend + backend deployments)

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git (optional, for backup versioning)

### Installation

1. **Clone the repository**
```bash
cd nms
```

2. **Configure environment variables**
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your settings
```

3. **Start all services**
```bash
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Default Credentials
```
Username: admin
Password: admin123
```

**Change these immediately after first login!**

---

## Supabase + Vercel Deployment (Recommended)

Supabase is the best fit for this codebase because the backend already uses SQLAlchemy models and PostgreSQL-compatible migrations. This avoids a major rewrite that Firebase would require for relational querying and joins.

### 1. Create Supabase project
- Create a new Supabase project.
- Get the pooled connection string from Supabase.
- Ensure it includes SSL, for example: `?sslmode=require`.

### 2. Deploy backend to Vercel (Project A)
Set Vercel project Root Directory to `backend` and configure these environment variables:

```env
DATABASE_URL=postgresql://postgres.your-project:[PASSWORD]@aws-0-region.pooler.supabase.com:6543/postgres?sslmode=require
SECRET_KEY=replace-with-a-long-random-secret
FRONTEND_URL=https://your-frontend-project.vercel.app
CORS_ORIGINS=https://your-frontend-project.vercel.app
DB_USE_NULL_POOL=true
AUTO_CREATE_TABLES=false
SEED_DEFAULT_ADMIN=false
ENABLE_CELERY=false
INFLUXDB_ENABLED=false
```

Important notes:
- `AUTO_CREATE_TABLES=false` is recommended on Vercel. Run Alembic migrations explicitly.
- `ENABLE_CELERY=false` avoids Redis dependency on serverless runtime.
- `INFLUXDB_ENABLED=false` unless you have a managed InfluxDB endpoint.

### 3. Run migrations against Supabase
From the backend directory:

```bash
alembic upgrade head
```

### 4. Deploy frontend to Vercel (Project B)
Set Vercel project Root Directory to `frontend` and configure:

```env
VITE_API_BASE_URL=https://your-backend-project.vercel.app/api
```

The frontend is now configured to call this base URL.

### 5. Verify deployment
- Frontend login page loads on Vercel.
- Backend health endpoint returns OK: `/api/health`.
- Auth and device endpoints can read/write data in Supabase.

---

## Project Structure

```
nms/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   │   ├── router_devices.py
│   │   │   ├── router_routing.py
│   │   │   ├── router_vpn.py
│   │   │   ├── router_backup.py
│   │   │   ├── router_alerts.py
│   │   │   └── router_auth.py
│   │   ├── core/             # Config, security, database
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   │   ├── snmp_service.py
│   │   │   ├── routing_service.py
│   │   │   ├── vpn_service.py
│   │   │   ├── backup_service.py
│   │   │   └── alert_service.py
│   │   ├── tasks/            # Celery tasks
│   │   └── utils/            # Helpers, OID mappings
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── store/
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login (OAuth2) |
| POST | `/api/auth/refresh` | Refresh token |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Current user |

### Devices
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/devices` | List devices |
| POST | `/api/devices` | Add device |
| GET | `/api/devices/{id}` | Get device |
| PUT | `/api/devices/{id}` | Update device |
| DELETE | `/api/devices/{id}` | Delete device |
| POST | `/api/devices/{id}/poll` | Trigger poll |
| POST | `/api/devices/{id}/backup` | Trigger backup |

### Routing
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/routing/bgp/neighbors` | List BGP neighbors |
| GET | `/api/routing/ospf/neighbors` | List OSPF neighbors |
| GET | `/api/routing/eigrp/neighbors` | List EIGRP neighbors |
| GET | `/api/routing/summary/{id}` | Routing summary |

### VPN
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vpn/tunnels` | List VPN tunnels |
| GET | `/api/vpn/dmvpn/nhrp-cache` | NHRP cache |
| GET | `/api/vpn/summary` | VPN summary |

### Backups
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/backups` | List backups |
| POST | `/api/backups/trigger` | Trigger backup |
| POST | `/api/backups/trigger-all` | Backup all |
| GET | `/api/backups/{id}/download` | Download backup |
| DELETE | `/api/backups/{id}` | Delete backup |

### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts` | List alerts |
| PUT | `/api/alerts/{id}/acknowledge` | Acknowledge |
| PUT | `/api/alerts/{id}/resolve` | Resolve |
| GET | `/api/alerts/summary` | Alert summary |

---

## Configuration

### SNMP Settings
Edit `backend/.env`:
```env
SNMP_TIMEOUT=5
SNMP_RETRIES=2
POLLING_INTERVAL_HEALTH=60
POLLING_INTERVAL_INTERFACE=60
POLLING_INTERVAL_ROUTING=300
POLLING_INTERVAL_VPN=300
```

### Alert Notifications

**Email (SMTP)**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_ENABLED=true
```

**Slack**
```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK
ALERT_SLACK_ENABLED=true
```

**Telegram**
```env
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
ALERT_TELEGRAM_ENABLED=true
```

### Backup Settings
```env
BACKUP_DIR=/app/backups
BACKUP_RETENTION_DAYS=90
BACKUP_GIT_ENABLED=false
BACKUP_GIT_REPO=/app/git-backups
```

---

## Supported Vendors

| Vendor | Device Health | Routing | VPN | Backup |
|--------|---------------|---------|-----|--------|
| Cisco IOS/IOS-XE | ✅ | ✅ | ✅ | ✅ |
| Cisco NX-OS | ✅ | ✅ | ✅ | ✅ |
| Juniper JunOS | ✅ | ✅ | ⚠️ | ✅ |
| Arista EOS | ✅ | ✅ | ⚠️ | ✅ |
| HP/Aruba | ✅ | ⚠️ | ❌ | ✅ |
| Fortinet | ✅ | ❌ | ✅ | ✅ |
| Palo Alto | ✅ | ⚠️ | ✅ | ✅ |

✅ = Full support, ⚠️ = Partial support, ❌ = Not tested

---

## Troubleshooting

### Device shows "Unknown" status
1. Verify SNMP is enabled on the device
2. Check community string / SNMPv3 credentials
3. Ensure firewall allows SNMP (UDP 161)
4. Test connectivity: `snmpwalk -v2c -c public <device-ip>`

### Backups failing
1. Verify SSH credentials are correct
2. Check SSH key permissions (if using keys)
3. Ensure device supports the CLI commands
4. Check backup storage space

### Celery worker not processing tasks
1. Check Redis connectivity: `docker-compose logs redis`
2. Verify Celery worker is running: `docker-compose ps`
3. Check worker logs: `docker-compose logs celery_worker`

### Database errors
1. Check PostgreSQL is healthy: `docker-compose ps postgres`
2. View DB logs: `docker-compose logs postgres`
3. Reset DB (data loss!): `docker-compose down -v && docker-compose up -d`

### Vercel + Supabase database errors
1. Verify `DATABASE_URL` is set in Vercel backend project settings.
2. Ensure `?sslmode=require` is present in the Supabase connection string.
3. Run `alembic upgrade head` against Supabase.
4. Confirm `CORS_ORIGINS` includes your frontend Vercel URL.

---

## Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend tests
pytest backend/

# Frontend tests
npm run test
```

---

## License

MIT License - See LICENSE file for details.

---

## Support

For issues and feature requests, please open a GitHub issue.

**Version**: 1.0.0  
**Build Date**: 2026
