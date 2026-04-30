#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Uso: ./deploy_local.sh [opzioni]

Deploy locale di MIO con hot reload per sviluppo.

Opzioni:
  --build           Ricostruisce le immagini (utile dopo cambiamenti a Dockerfile/requirements)
  --reset           Reset completo: rimuove volumi e ricostruisce da zero
  --migrate         Esegue migrate dopo l'avvio
  --logs            Mostra i log in tempo reale (follow)
  --stop            Ferma tutti i container senza rimuoverli
  --down            Ferma e rimuove container e network
  --shell           Apre una shell nel container web
  --manage <cmd>    Esegue un comando manage.py (es: --manage "createsuperuser")
  -h, --help        Mostra questo aiuto

Esempi:
  ./deploy_local.sh                 # Avvio standard con hot reload
  ./deploy_local.sh --build         # Ricostruisce immagini e avvia
  ./deploy_local.sh --reset         # Pulizia completa e rebuild
  ./deploy_local.sh --manage migrate
  ./deploy_local.sh --shell
EOF
}

BUILD=0
RESET=0
MIGRATE=0
LOGS=0
STOP=0
DOWN=0
SHELL=0
MANAGE_CMD=""

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --build)
      BUILD=1
      ;;
    --reset)
      RESET=1
      ;;
    --migrate)
      MIGRATE=1
      ;;
    --logs)
      LOGS=1
      ;;
    --stop)
      STOP=1
      ;;
    --down)
      DOWN=1
      ;;
    --shell)
      SHELL=1
      ;;
    --manage)
      shift
      if [[ "${1:-}" == "" ]]; then
        echo "Errore: --manage richiede un comando."
        exit 1
      fi
      MANAGE_CMD="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Opzione non valida: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
  echo -e "${BLUE}==>${NC} $1"
}

log_success() {
  echo -e "${GREEN}==>${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}==>${NC} $1"
}

log_error() {
  echo -e "${RED}==>${NC} $1"
}

# Verifica prerequisiti
if ! command -v docker >/dev/null 2>&1; then
  log_error "docker non trovato nel PATH."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  log_error "docker compose non disponibile."
  exit 1
fi

# Verifica file .env
if [[ ! -f ".env" ]]; then
  if [[ -f ".env.local.example" ]]; then
    log_warn "File .env non trovato. Creo da .env.local.example..."
    cp .env.local.example .env
    log_info "Modifica .env con le tue configurazioni prima di continuare."
    exit 1
  else
    log_error "File .env non trovato e nessun .env.local.example disponibile."
    exit 1
  fi
fi

# Controlla se è in esecuzione
is_running() {
  docker compose ps --format json 2>/dev/null | grep -q '"State": "running"'
}

# Gestione comandi semplici
if [[ "$STOP" -eq 1 ]]; then
  log_info "Fermazione container..."
  docker compose stop
  log_success "Container fermati."
  exit 0
fi

if [[ "$DOWN" -eq 1 ]]; then
  log_info "Rimozione container..."
  docker compose down
  log_success "Container rimossi."
  exit 0
fi

if [[ -n "$MANAGE_CMD" ]]; then
  if ! is_running; then
    log_error "I container non sono in esecuzione. Avvia prima con ./deploy_local.sh"
    exit 1
  fi
  log_info "Esecuzione: python manage.py $MANAGE_CMD"
  docker compose exec web python manage.py $MANAGE_CMD
  exit 0
fi

if [[ "$SHELL" -eq 1 ]]; then
  if ! is_running; then
    log_error "I container non sono in esecuzione. Avvia prima con ./deploy_local.sh"
    exit 1
  fi
  log_info "Apertura shell nel container web..."
  docker compose exec web bash
  exit 0
fi

# Reset completo
if [[ "$RESET" -eq 1 ]]; then
  log_warn "RESET COMPLETO: rimuovo volumi, container e ricostruisco tutto..."
  docker compose down -v --remove-orphans
  docker compose rm -f
  BUILD=1
fi

log_info "Deploy locale MIO (hot reload)"
log_info "Directory: ${PROJECT_DIR}"

# Verifica che sia impostato per dev mode
if grep -q "DEBUG=false" .env 2>/dev/null || grep -q "DJANGO_DEBUG=false" .env 2>/dev/null; then
  log_warn "Attenzione: DEBUG sembra disabilitato in .env"
  log_warn "Per hot reload, assicurati che DJANGO_DEBUG=true"
fi

# Build se necessario
if [[ "$BUILD" -eq 1 ]] || [[ "$RESET" -eq 1 ]]; then
  log_info "Build immagini..."
  docker compose build --no-cache
fi

# Avvio container
log_info "Avvio container..."
if [[ "$LOGS" -eq 1 ]]; then
  docker compose up -d --remove-orphans
  log_success "Container avviati. Mostro log (Ctrl+C per uscire)..."
  docker compose logs -f
else
  docker compose up -d --remove-orphans
  
  # Attesa per i servizi
  log_info "Attesa avvio servizi..."
  sleep 3
  
  # Verifica stato
  if docker compose ps | grep -q "healthy\|running"; then
    log_success "Servizi avviati correttamente!"
    
    # Mostra URL
    echo ""
    echo -e "${GREEN}====================================${NC}"
    echo -e "${GREEN}  MIO disponibile su:${NC}"
    echo -e "${GREEN}  http://localhost:8000${NC}"
    echo -e "${GREEN}====================================${NC}"
    echo ""
    
    # Esegui migrate se richiesto
    if [[ "$MIGRATE" -eq 1 ]]; then
      log_info "Esecuzione migrate..."
      docker compose exec -T web python manage.py migrate --noinput || true
    fi
    
    log_info "Stato container:"
    docker compose ps
    
    echo ""
    log_info "Comandi utili:"
    echo "  ./deploy_local.sh --logs       # Mostra log"
    echo "  ./deploy_local.sh --shell      # Shell nel container"
    echo "  ./deploy_local.sh --manage migrate"
    echo "  ./deploy_local.sh --stop       # Ferma container"
    echo ""
    log_info "Hot reload attivo:"
    echo "  - Modifiche ai file .py sono rilevate automaticamente"
    echo "  - Modifiche ai template sono immediate"
    echo "  - LESS viene compilato on-the-fly"
    
  else
    log_error "Problema nell'avvio dei servizi:"
    docker compose ps
    echo ""
    log_info "Log errori:"
    docker compose logs --tail=50
    exit 1
  fi
fi
