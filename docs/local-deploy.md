---
title: Deploy Locale con Hot Reload
tags: [development, deploy, docker, local]
aliases: [local-dev, hot-reload, sviluppo-locale]
---

# Deploy Locale con Hot Reload

Questa guida spiega come avviare MIO in ambiente locale con **hot reload** per lo sviluppo.

---

## 🚀 Quick Start

```bash
# 1. Copia il file di configurazione locale
cp .env.local.example .env

# 2. Modifica .env con le tue configurazioni (opzionale per iniziare)

# 3. Avvia l'ambiente di sviluppo
./deploy_local.sh
```

L'applicazione sarà disponibile su: **http://localhost:8000**

---

## 📋 Prerequisiti

- Docker e Docker Compose installati
- File `.env` creato da `.env.local.example`
- Porta 8000 libera sul sistema

---

## 🔧 Script `deploy_local.sh`

Script dedicato per il deploy in ambiente locale con supporto hot reload.

### Comandi Disponibili

#### Avvio Standard
```bash
./deploy_local.sh
```
Avvia tutti i servizi con hot reload attivo.

#### Ricostruzione Immagini
```bash
./deploy_local.sh --build
```
Utile dopo modifiche a `Dockerfile` o `requirements.txt`.

#### Reset Completo
```bash
./deploy_local.sh --reset
```
- Rimuove volumi e container
- Ricostruisce tutto da zero
- Utile per pulire lo stato locale

#### Esecuzione Migrate
```bash
./deploy_local.sh --migrate
```
Avvia i container ed esegue automaticamente `migrate`.

#### Visualizzazione Log
```bash
./deploy_local.sh --logs
```
Mostra i log in tempo reale (follow mode). Premi `Ctrl+C` per uscire.

#### Fermare i Container
```bash
./deploy_local.sh --stop       # Ferma senza rimuovere
./deploy_local.sh --down       # Ferma e rimuove
```

#### Comandi Django
```bash
# Esegui qualsiasi comando manage.py
./deploy_local.sh --manage "createsuperuser"
./deploy_local.sh --manage "shell"
./deploy_local.sh --manage "test"
```

#### Shell nel Container
```bash
./deploy_local.sh --shell
```
Apre una bash interattiva nel container `web`.

---

## 🔥 Hot Reload

L'hot reload è **automaticamente attivo** per:

| Tipo File | Comportamento |
|-----------|---------------|
| **File Python** (`.py`) | Django runserver rileva cambiamenti e ricarica automaticamente |
| **Template HTML** | Rendering immediato al refresh del browser |
| **File LESS/CSS** | Compilazione on-the-fly via `DevLessCompileMiddleware` |
| **JavaScript/Stimulus** | Ricarica browser necessaria, ma file aggiornati immediatamente |
| **Modelli** (`.py`) | Richiede riavvio del container (non hot reload) |
| **Migrazioni** | Richiede `migrate` manuale o `--migrate` |

### Configurazione Hot Reload

Il file `docker-compose.override.yml` (caricato automaticamente da Docker Compose) configura:

- **Volume mount**: `./:/app` - Monta l'intero progetto nel container
- **DJANGO_DEBUG**: `true` - Abilita modalità debug
- **LESS_DEV_MODE**: `true` - Compilazione LESS on-the-fly
- **UI_STYLE_MODE**: `DEV` - Stili in modalità sviluppo
- **Porta 8000**: Esposta direttamente per accesso locale

---

## 🐳 Docker Compose Override

Il progetto utilizza due file Compose:

1. **`docker-compose.yml`** - Configurazione di base (production-oriented)
2. **`docker-compose.override.yml`** - Override per sviluppo locale

Docker Compose carica automaticamente entrambi i file, con l'override che ha priorità.

### Differenze Chiave (Dev vs Prod)

| Aspetto | Dev (Locale) | Prod (VPS)
|---------|-------------|------------|
| **DJANGO_DEBUG** | `true` | `false` |
| **Hot Reload** | ✅ Attivo | ❌ Disabilitato |
| **Volume Sorgenti** | `./:/app` (mount) | Solo volumi dati |
| **Server** | `runserver` (auto-reload) | Gunicorn |
| **Caddy** | ❌ Disabilitato | ✅ Attivo |
| **LESS Compilation** | On-the-fly | Pre-compilato |
| **Porta Accesso** | `localhost:8000` | Via Caddy (80/443) |

---

## 🛠️ Flusso di Sviluppo Tipico

### 1. Avvio Iniziale
```bash
./deploy_local.sh
```

### 2. Modifica Codice
Apri i file nel tuo editor preferito e modifica:
- **View Django** → Cambiamento immediato (hot reload)
- **Template** → Refresh browser per vedere
- **CSS/LESS** → Compilazione automatica

### 3. Test Modifiche
- Ricarica la pagina nel browser
- Per Python: il server si riavvia automaticamente

### 4. Creazione Migrazioni
```bash
# Dopo modifiche ai modelli
./deploy_local.sh --shell
# Nel container:
python manage.py makemigrations
python manage.py migrate
exit
```

### 5. Completato
```bash
./deploy_local.sh --stop       # Ferma per pausa
# oppure
./deploy_local.sh --down       # Pulizia completa
```

---

## 🐛 Troubleshooting

### Container non si avvia
```bash
# Verifica errori
./deploy_local.sh --logs

# Reset completo
./deploy_local.sh --reset
```

### Porta 8000 occupata
```bash
# Trova processo che usa la porta
lsof -i :8000

# O cambia porta nel .env (modifica non necessaria, usa mappatura)
```

### Cambiamenti non visibili
```bash
# Verifica che il container veda i file
./deploy_local.sh --shell
ls -la /app/
```

### Problemi con dipendenze Python
```bash
# Ricostruisci immagine dopo modifiche a requirements.txt
./deploy_local.sh --build
```

---

## 📁 Struttura File Rilevanti

```
mio_master/
├── deploy_local.sh              # Script deploy locale ⭐
├── docker-compose.yml           # Config base
├── docker-compose.override.yml  # Override dev (hot reload)
├── .env.local.example           # Template configurazione locale
├── .env                         # Configurazione attiva (non committare)
└── docs/
    └── local-deploy.md          # Questo file
```

---

## 🔄 Confronto con Deploy VPS

| Azione | Locale (Dev) | VPS (Prod) |
|--------|-------------|------------|
| **Script** | `deploy_local.sh` | `deploy_vps.sh` |
| **Hot Reload** | ✅ Automatico | ❌ No |
| **Git Pull** | Manuale | Automatico (`--force-sync`) |
| **Build** | Solo quando serve (`--build`) | Sempre (`--build`) |
| **Check Post-Deploy** | Opzionali | Automatici |
| **Backup** | No | `.env` backup automatico |

---

## 📝 Note Importanti

1. **Non committare `.env`** - È nel `.gitignore` per sicurezza
2. **Database locale** - Persiste nei volumi Docker finché non fai `--reset`
3. **Media files** - Salvati in volume Docker, accessibili in dev
4. **Radicale (CalDAV)** - Disponibile su porta 5232 in locale

---

## 🔗 Vedi Anche

- [[deployment]] - Deploy produzione VPS
- [[project-identity]] - Visione progetto e architettura
- [[dependencies]] - Dipendenze tra app

---

*Ultimo aggiornamento: 2026-04-30*
