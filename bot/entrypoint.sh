#!/bin/bash
#!/bin/bash
set -euo pipefail

# Функция для чтения секретов и проверки их существования
read_secret() {
  local secret_path="$1"
  if [ ! -f "$secret_path" ]; then
    echo "[entrypoint] ERROR: Secret file $secret_path not found!" >&2
    exit 1
  fi
  cat "$secret_path"
}

export BOT_TOKEN=$(cat /run/secrets/bot_token)
export POSTGRES_USER=$(cat /run/secrets/postgres_user)
export POSTGRES_PASSWORD=$(cat /run/secrets/postgres_password)
export POSTGRES_DB=$(cat /run/secrets/postgres_db)
export UKASSA_TOKEN=$(cat /run/secrets/ukassa_token)

export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db_meow:5434/${POSTGRES_DB}"





# Ждём доступности Postgres
echo "[entrypoint] Waiting for postgres..."
until pg_isready -h db_meow -p 5434 -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
  >&2 echo "[entrypoint] Postgres is unavailable - sleeping"
  sleep 1
done
echo "[entrypoint] Postgres is ready"

# Логика запуска
case "${1:-}" in
  bot)
    echo "[entrypoint] Starting FastAPI on port 8000..."
    uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload &

    echo "[entrypoint] Starting Telegram bot..."
    exec python /bot/main.py
    ;;
  alembic)
    shift
    exec alembic "$@"
    ;;
  *)
    exec "$@"
    ;;
esac