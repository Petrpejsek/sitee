# SITEE - Provozní dokumentace

Kompletní provozní příručka pro správu projektu LLM Audit Engine (Sitee).

---

## 1. GitHub Repository

### Informace o repozitáři

| Položka | Hodnota |
|---------|---------|
| **URL** | https://github.com/Petrpejsek/sitee |
| **Clone HTTPS** | `https://github.com/Petrpejsek/sitee.git` |
| **Clone SSH** | `git@github.com:Petrpejsek/sitee.git` |
| **Branch** | `main` |

### Git workflow

```bash
# Stáhnout nejnovější změny
git pull origin main

# Zobrazit stav
git status

# Přidat změny
git add .

# Commit
git commit -m "Popis změny"

# Push na GitHub
git push origin main
```

### Rollback na předchozí verzi

```bash
# Zobrazit historii commitů
git log --oneline

# Vrátit se k určitému commitu (POZOR: ztratíte novější změny)
git reset --hard <commit-hash>

# Nebo vytvořit nový commit který vrátí změny
git revert <commit-hash>
```

---

## 2. Server - DigitalOcean

### Plánovaná konfigurace

| Položka | Hodnota |
|---------|---------|
| **Provider** | DigitalOcean |
| **Region** | NYC1 nebo SFO3 (USA) |
| **Droplet** | 2GB RAM / 1 vCPU ($12/měsíc) |
| **OS** | Ubuntu 22.04 LTS |
| **IP adresa** | `<DOPLNIT PO VYTVOŘENÍ>` |
| **Doména** | `<DOPLNIT>` |

### SSH připojení

```bash
# Připojení na server
ssh root@<IP_ADRESA>

# Nebo s SSH klíčem
ssh -i ~/.ssh/digitalocean_key root@<IP_ADRESA>

# Připojení jako www-data (aplikační uživatel)
ssh root@<IP_ADRESA>
sudo -u www-data bash
```

### Cesty na serveru

```
/var/www/llm-audit-engine/          # Hlavní složka aplikace
├── backend/                         # Python FastAPI backend
│   ├── venv/                       # Python virtual environment
│   ├── app/                        # Aplikační kód
│   └── .env                        # Environment variables (TAJNÉ!)
├── frontend/                        # React frontend (built)
│   └── dist/                       # Produkční build
├── reports/                         # Generované PDF reporty
└── deployment/                      # Systemd služby, nginx config
```

---

## 3. Deploy postup

### První deploy (nový server)

```bash
# 1. Připojit se na server
ssh root@<IP_ADRESA>

# 2. Aktualizovat systém
apt update && apt upgrade -y

# 3. Nainstalovat závislosti
apt install -y python3.10 python3.10-venv python3-pip postgresql nginx nodejs npm

# 4. Vytvořit aplikačního uživatele
useradd -r -m -s /bin/bash www-data
mkdir -p /var/www/llm-audit-engine
chown www-data:www-data /var/www/llm-audit-engine

# 5. Naklonovat repo
cd /var/www/llm-audit-engine
sudo -u www-data git clone https://github.com/Petrpejsek/sitee.git .

# 6. Setup backend
cd backend
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo -u www-data venv/bin/pip install gunicorn

# 7. Vytvořit .env soubor (VIZ SEKCE 4)
sudo -u www-data nano .env

# 8. Spustit migrace
sudo -u www-data venv/bin/alembic upgrade head

# 9. Setup frontend
cd ../frontend
sudo -u www-data npm install
sudo -u www-data npm run build

# 10. Nainstalovat systemd služby
cp deployment/*.service /etc/systemd/system/
cp deployment/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable llm-audit-api llm-audit-worker llm-audit-cleanup.timer
systemctl start llm-audit-api llm-audit-worker llm-audit-cleanup.timer

# 11. Nastavit nginx
cp deployment/nginx.conf /etc/nginx/sites-available/llm-audit
ln -s /etc/nginx/sites-available/llm-audit /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 12. SSL certifikát
apt install certbot python3-certbot-nginx
certbot --nginx -d <DOMENA>
```

### Aktualizace (nový deploy)

```bash
# Připojit se na server
ssh root@<IP_ADRESA>

# Stáhnout změny
cd /var/www/llm-audit-engine
sudo -u www-data git pull origin main

# Backend update
cd backend
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo -u www-data venv/bin/alembic upgrade head

# Frontend rebuild (pokud změněn)
cd ../frontend
sudo -u www-data npm install
sudo -u www-data npm run build

# Restart služeb
systemctl restart llm-audit-api llm-audit-worker
```

---

## 4. Environment Variables

### Backend `.env` soubor

Umístění: `/var/www/llm-audit-engine/backend/.env`

```bash
# Database
DATABASE_URL=postgresql+asyncpg://llm_audit_user:<HESLO>@localhost:5432/llm_audit

# OpenAI
OPENAI_API_KEY=sk-<VÁŠ_KLÍČ>
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1

# Storage
REPORTS_DIR=/var/www/llm-audit-engine/reports
REPORTS_RETENTION_DAYS=30

# URLs (změnit na vaši doménu)
BACKEND_URL=https://<DOMENA>
FRONTEND_URL=https://<DOMENA>
CORS_ORIGINS=https://<DOMENA>

# Environment
ENVIRONMENT=production

# Stripe (platby)
STRIPE_API_KEY=sk_live_<VÁŠ_KLÍČ>
STRIPE_WEBHOOK_SECRET=whsec_<VÁŠ_SECRET>
STRIPE_AUDIT_PRICE_ID=price_xxxxx

# JWT
JWT_SECRET_KEY=<NÁHODNÝ_ŘETĚZEC_MIN_32_ZNAKŮ>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=15
```

### Vygenerovat JWT secret

```bash
openssl rand -hex 32
```

### Frontend environment

Frontend používá `VITE_API_URL` v build time. Nastavit v `frontend/.env.production`:

```bash
VITE_API_URL=https://<DOMENA>
```

---

## 5. Správa služeb

### Systemd příkazy

```bash
# Status všech služeb
systemctl status llm-audit-api llm-audit-worker

# Restart služeb
systemctl restart llm-audit-api
systemctl restart llm-audit-worker

# Stop/Start
systemctl stop llm-audit-api
systemctl start llm-audit-api

# Zobrazit logy (real-time)
journalctl -u llm-audit-api -f
journalctl -u llm-audit-worker -f

# Logy za poslední hodinu
journalctl -u llm-audit-api --since "1 hour ago"
```

### Nginx

```bash
# Test konfigurace
nginx -t

# Reload (bez výpadku)
systemctl reload nginx

# Restart
systemctl restart nginx

# Logy
tail -f /var/log/nginx/llm-audit-access.log
tail -f /var/log/nginx/llm-audit-error.log
```

### PostgreSQL

```bash
# Status
systemctl status postgresql

# Připojení do DB
sudo -u postgres psql llm_audit

# Základní příkazy v psql
\dt                    # Seznam tabulek
\d audit_requests      # Struktura tabulky
SELECT COUNT(*) FROM audit_requests;
\q                     # Ukončit
```

---

## 6. Monitoring a Health Checks

### Endpoints

| Endpoint | Popis |
|----------|-------|
| `https://<DOMENA>/health` | API health check |
| `https://<DOMENA>/api/audits` | Seznam auditů |

### Kontrola stavu

```bash
# API health check
curl https://<DOMENA>/health

# Očekávaná odpověď
{"status": "healthy"}

# Test z příkazové řádky serveru
curl http://localhost:8000/health
```

### Disk space

```bash
# Celkové využití disku
df -h

# Velikost reports složky
du -sh /var/www/llm-audit-engine/reports/

# Počet reportů
ls /var/www/llm-audit-engine/reports/ | wc -l
```

---

## 7. Backup

### Databáze

```bash
# Backup
sudo -u postgres pg_dump llm_audit > /backup/llm-audit-$(date +%Y%m%d).sql

# Restore
sudo -u postgres psql llm_audit < /backup/llm-audit-20241215.sql
```

### Reporty

```bash
# Backup reportů
tar -czf /backup/reports-$(date +%Y%m%d).tar.gz /var/www/llm-audit-engine/reports/
```

### Automatický backup (cron)

```bash
# Editovat crontab
crontab -e

# Přidat (denní backup v 2:00)
0 2 * * * sudo -u postgres pg_dump llm_audit > /backup/llm-audit-$(date +\%Y\%m\%d).sql
```

---

## 8. Troubleshooting

### API neodpovídá

```bash
# 1. Zkontrolovat status služby
systemctl status llm-audit-api

# 2. Zobrazit logy
journalctl -u llm-audit-api -n 50

# 3. Restart
systemctl restart llm-audit-api

# 4. Zkontrolovat port
netstat -tlnp | grep 8000
```

### Worker nezpracovává audity

```bash
# 1. Status
systemctl status llm-audit-worker

# 2. Logy
journalctl -u llm-audit-worker -f

# 3. Zkontrolovat frontu v DB
sudo -u postgres psql llm_audit -c "SELECT id, status FROM audit_requests WHERE status = 'pending';"

# 4. Restart
systemctl restart llm-audit-worker
```

### Databáze nedostupná

```bash
# 1. Status PostgreSQL
systemctl status postgresql

# 2. Restart
systemctl restart postgresql

# 3. Zkontrolovat připojení
sudo -u postgres psql -c "SELECT 1;"
```

### Plný disk

```bash
# 1. Zjistit co zabírá místo
du -sh /* | sort -h

# 2. Vyčistit staré reporty
cd /var/www/llm-audit-engine/backend
sudo -u www-data venv/bin/python -m app.cleanup

# 3. Vyčistit logy
journalctl --vacuum-time=7d
```

### SSL certifikát expiruje

```bash
# Zkontrolovat expiraci
certbot certificates

# Obnovit manuálně
certbot renew

# Automatická obnova (už by měla být nastavena)
systemctl status certbot.timer
```

---

## 9. Užitečné příkazy - Quick Reference

```bash
# === PŘIPOJENÍ ===
ssh root@<IP>                              # SSH na server

# === GIT ===
git pull origin main                       # Stáhnout změny
git status                                 # Stav
git log --oneline -10                      # Posledních 10 commitů

# === SLUŽBY ===
systemctl restart llm-audit-api            # Restart API
systemctl restart llm-audit-worker         # Restart worker
journalctl -u llm-audit-api -f             # Live logy API

# === DATABÁZE ===
sudo -u postgres psql llm_audit            # Připojení do DB

# === MONITORING ===
curl https://<DOMENA>/health               # Health check
df -h                                      # Disk space
htop                                       # Systémové prostředky

# === DEPLOY ===
cd /var/www/llm-audit-engine && sudo -u www-data git pull && systemctl restart llm-audit-api llm-audit-worker
```

---

## 10. Kontakty a odkazy

| Položka | Odkaz |
|---------|-------|
| **GitHub repo** | https://github.com/Petrpejsek/sitee |
| **DigitalOcean** | https://cloud.digitalocean.com |
| **OpenAI API** | https://platform.openai.com |
| **Stripe Dashboard** | https://dashboard.stripe.com |

---

*Poslední aktualizace: Prosinec 2024*
