# SITEE - Deployment Checklist

Kompletní checklist pro deployment do produkce. Postupujte krok za krokem.

---

## PRE-DEPLOYMENT (Před deploymentem)

### 1. Lokální příprava

- [ ] Všechny změny commitnuty do `dev` větve
- [ ] Dev větev otestována lokálně (`./dev.sh`)
- [ ] Všechny testy prošly (pokud máte)
- [ ] Linter errory vyřešeny
- [ ] Dev merged do `main` větve
- [ ] Main větev pushnutá na GitHub

```bash
git checkout dev
git status  # Žádné uncommitted změny
git checkout main
git merge dev
git push origin main
```

### 2. Produkční příprava

- [ ] Backend `.env.production.template` zkopírován a vyplněn na serveru
- [ ] Frontend `.env.production.example` zkopírován a domain nastavena
- [ ] Database na serveru vytvořena a připravena
- [ ] OpenAI API klíč aktivní a funkční
- [ ] Stripe účet nastaven (alespoň test mode)
- [ ] Domain připravena a nasměrována na server IP

### 3. Server setup

- [ ] DigitalOcean Droplet vytvořen (Ubuntu 22.04)
- [ ] SSH klíč přidán pro bezpečný přístup
- [ ] Firewall nakonfigurován (UFW: 22, 80, 443)
- [ ] System dependencies nainstalované (Python, Node, PostgreSQL, Nginx)

```bash
ssh root@YOUR_SERVER_IP
apt update && apt upgrade -y
```

---

## DEPLOYMENT (První deploy na nový server)

### 4. Instalace aplikace

Postupujte podle [`PRODUCTION_DEPLOYMENT.md`](PRODUCTION_DEPLOYMENT.md) sekce "První deploy".

- [ ] PostgreSQL database vytvořena
- [ ] App user `www-data` vytvořen
- [ ] Git repository naklonován do `/var/www/llm-audit-engine`
- [ ] Backend venv vytvořen a dependencies nainstalovány
- [ ] Backend `.env` soubor vytvořen a vyplněn
- [ ] Alembic migrace spuštěny (`alembic upgrade head`)
- [ ] Frontend build vytvořen (`npm run build`)
- [ ] Reports directory vytvořen s správnými oprávněními

### 5. Systemd služby

- [ ] Service files zkopírovány do `/etc/systemd/system/`
- [ ] Services enabled: `llm-audit-api`, `llm-audit-worker`, `llm-audit-cleanup.timer`
- [ ] Services spuštěny a běží
- [ ] Log directory vytvořen: `/var/log/llm-audit`

```bash
systemctl status llm-audit-api
systemctl status llm-audit-worker
systemctl list-timers llm-audit-cleanup.timer
```

### 6. Nginx konfigurace

- [ ] Nginx config zkopírován do `/etc/nginx/sites-available/`
- [ ] Domain name změněna v config souboru
- [ ] Symlink vytvořen v `/etc/nginx/sites-enabled/`
- [ ] Default site odstraněn
- [ ] Nginx config tested (`nginx -t`)
- [ ] Nginx reloaded

### 7. SSL certifikát

- [ ] Certbot nainstalován
- [ ] SSL certifikát získán (`certbot --nginx -d YOUR_DOMAIN`)
- [ ] Auto-renewal test prošel (`certbot renew --dry-run`)

---

## POST-DEPLOYMENT (Po deploym

entu)

### 8. Verifikace

- [ ] **Health check endpoint:** `curl https://YOUR_DOMAIN/health`
  - Očekáváno: `{"status": "healthy"}`
- [ ] **Frontend načítání:** Otevřít `https://YOUR_DOMAIN` v prohlížeči
- [ ] **API response:** Test na audit endpoint
- [ ] **Database connection:** Ověřit že API může přistupovat k DB
- [ ] **Logs jsou čisté:** Žádné critical errory v logs

```bash
# Check all services
systemctl status llm-audit-api llm-audit-worker

# Check logs
journalctl -u llm-audit-api -n 50
journalctl -u llm-audit-worker -n 50

# Check disk space
df -h
```

### 9. Funkční testy

- [ ] **Landing page:** Zobrazuje se správně
- [ ] **Email gate:** Zadání emailu funguje
- [ ] **Audit creation:** Lze vytvořit nový audit
- [ ] **Audit processing:** Worker zpracovává audity
- [ ] **PDF generation:** PDF se generuje a zobrazuje
- [ ] **Payment flow:** Stripe redirect funguje (test mode OK)

### 10. Monitoring setup

- [ ] **Health check cron:** Nastavit monitoring (volitelné)
- [ ] **Backup cron:** Automatické denní backupy DB
- [ ] **Log rotation:** Nastavit logrotate
- [ ] **Disk space monitoring:** Alert při 80% využití

```bash
# Setup daily backup cron
crontab -e
# Add: 0 2 * * * sudo -u postgres pg_dump llm_audit > /backup/llm-audit-$(date +\%Y\%m\%d).sql
```

---

## DEPLOYMENT UPDATES (Aktualizace existující produkce)

Pro update již běžící produkce:

### Automatický deploy (doporučeno)

```bash
ssh root@YOUR_SERVER_IP
cd /var/www/llm-audit-engine
sudo ./scripts/deploy.sh
```

Deploy script automaticky:
1. ✅ Backupuje databázi
2. ✅ Pulluje z GitHubu
3. ✅ Updatuje dependencies
4. ✅ Spouští migrace
5. ✅ Rebuilduje frontend
6. ✅ Restartuje služby
7. ✅ Ověří health check
8. ✅ Rollback při chybě

### Manuální deploy

- [ ] SSH na server
- [ ] Backup databáze: `pg_dump llm_audit > backup.sql`
- [ ] Pull změn: `git pull origin main`
- [ ] Update dependencies: `pip install -r requirements.txt`
- [ ] Run migrations: `alembic upgrade head`
- [ ] Rebuild frontend: `npm run build`
- [ ] Restart services: `systemctl restart llm-audit-api llm-audit-worker`
- [ ] Health check: `curl http://localhost:8000/health`

---

## ROLLBACK (V případě problémů)

### Automatický rollback

```bash
ssh root@YOUR_SERVER_IP
cd /var/www/llm-audit-engine
sudo ./scripts/rollback.sh
```

### Manuální rollback

- [ ] Stop služby: `systemctl stop llm-audit-api llm-audit-worker`
- [ ] Git rollback: `git reset --hard <PREVIOUS_COMMIT>`
- [ ] Restore DB: `psql llm_audit < backup.sql`
- [ ] Restart služby: `systemctl start llm-audit-api llm-audit-worker`
- [ ] Verify: `curl http://localhost:8000/health`

---

## EMERGENCY CONTACTS & RESOURCES

### Důležité cesty

```
/var/www/llm-audit-engine/          # Aplikace
/var/log/llm-audit/                 # Logy
/var/backups/llm-audit/             # Backupy
/etc/nginx/sites-available/         # Nginx config
/etc/systemd/system/                # Systemd services
```

### Užitečné příkazy

```bash
# View all audit services
systemctl status 'llm-audit-*'

# Tail all logs
journalctl -u llm-audit-api -u llm-audit-worker -f

# Check disk usage
df -h && du -sh /var/www/llm-audit-engine/reports/

# Restart everything
systemctl restart llm-audit-api llm-audit-worker nginx

# Manual cleanup
cd /var/www/llm-audit-engine/backend && sudo -u www-data venv/bin/python -m app.cleanup
```

### Dokumentace

- [OPERATIONS.md](OPERATIONS.md) - Kompletní provozní příručka
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Detailní deploy guide
- [README.md](README.md) - Základní info o projektu

### Externe zdroje

- OpenAI Dashboard: https://platform.openai.com
- Stripe Dashboard: https://dashboard.stripe.com
- DigitalOcean Console: https://cloud.digitalocean.com
- GitHub Repository: https://github.com/Petrpejsek/sitee

---

## SECURITY CHECKLIST

- [ ] SSL certificate aktivní a platný
- [ ] Firewall nakonfigurován (pouze 22, 80, 443)
- [ ] PostgreSQL není accessible zvenčí
- [ ] `.env` soubor má permissions 600
- [ ] Strong passwords použity (DB, admin)
- [ ] OpenAI API key ma rate limits nastavené
- [ ] Stripe webhook secret ověřen
- [ ] Regular security updates (`apt upgrade`)
- [ ] Backup strategie funguje
- [ ] Log rotation nastavena

---

## NOTES

### První deploy timeline

| Krok | Čas |
|------|-----|
| Server setup | 15-30 min |
| App installation | 20-30 min |
| SSL & config | 10-15 min |
| Testing | 15-20 min |
| **Total** | **~60-90 min** |

### Update deploy timeline

| Krok | Čas |
|------|-----|
| Automated deploy script | 3-5 min |
| Manual deploy | 10-15 min |

### Common issues

1. **503 Error:** Služby neběží → `systemctl start llm-audit-api`
2. **502 Error:** Nginx config problém → `nginx -t`
3. **Database error:** Connection string špatný → Check `.env`
4. **PDF generation fails:** WeasyPrint dependencies → `apt install python3-cffi python3-brotli libpango-1.0-0`

---

*Last updated: December 2024*
