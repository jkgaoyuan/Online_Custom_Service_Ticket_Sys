#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="ticket-system"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

echo "===================================="
echo "  Ticket System Production Deploy"
echo "===================================="

# 检查环境文件
if [ ! -f "${SCRIPT_DIR}/${ENV_FILE}" ]; then
    echo "❌ Error: ${ENV_FILE} not found."
    echo "   Please copy .env.production and configure it first."
    exit 1
fi

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed."
    exit 1
fi

if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed."
    exit 1
fi

# 使用正确的 compose 命令
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

cd "${SCRIPT_DIR}"

# 检查密钥是否已修改
SECRET_KEY=$(grep "^SECRET_KEY=" "${ENV_FILE}" | cut -d '=' -f2)
if [ "$SECRET_KEY" = "change-me-to-a-32-char-random-string" ]; then
    echo "⚠️  Warning: SECRET_KEY is still using default value."
    echo "   Please update it in ${ENV_FILE} before deploying."
    read -p "Continue anyway? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo ""
echo "📦 Building and starting services..."
${COMPOSE_CMD} -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --build

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# 检查服务状态
echo ""
echo "🔍 Service status:"
${COMPOSE_CMD} -f "${COMPOSE_FILE}" ps

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Access URLs:"
echo "   Frontend: http://localhost"
echo "   API Docs: http://localhost/api/docs (DEBUG=True only)"
echo "   Health:   http://localhost/api/health"
echo ""
echo "📊 View logs:"
echo "   ${COMPOSE_CMD} -f ${COMPOSE_FILE} logs -f"
echo ""
echo "🛑 Stop services:"
echo "   ${COMPOSE_CMD} -f ${COMPOSE_FILE} down"
