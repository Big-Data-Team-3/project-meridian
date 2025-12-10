#!/bin/bash

# Meridian Project - Local Docker Deployment Script
# This script rebuilds all Docker images and starts containers

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo -e "${YELLOW}Loading environment variables from .env file...${NC}"
    export $(cat .env | grep -v '^#' | xargs)
    echo -e "${GREEN}✓ Environment variables loaded${NC}\n"
fi

# Try to load Google Client ID and Secret from config file if not set
if [ -z "$GOOGLE_CLIENT_ID" ] && [ -f "config/client_secret_apps.googleusercontent.com.json" ]; then
    echo -e "${YELLOW}Extracting Google credentials from config file...${NC}"
    GOOGLE_CLIENT_ID=$(grep -o '"client_id": "[^"]*' config/client_secret_apps.googleusercontent.com.json | cut -d'"' -f4)
    GOOGLE_CLIENT_SECRET=$(grep -o '"client_secret": "[^"]*' config/client_secret_apps.googleusercontent.com.json | cut -d'"' -f4)
    export GOOGLE_CLIENT_ID
    export GOOGLE_CLIENT_SECRET
    if [ -n "$GOOGLE_CLIENT_ID" ]; then
        echo -e "${GREEN}✓ Found GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}${NC}"
    fi
    if [ -n "$GOOGLE_CLIENT_SECRET" ]; then
        echo -e "${GREEN}✓ Found GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET:0:10}...${NC}\n"
    fi
fi

# Check if required variables are set
if [ -z "$GOOGLE_CLIENT_ID" ]; then
    echo -e "${YELLOW}⚠️  Warning: GOOGLE_CLIENT_ID is not set${NC}"
    echo -e "${YELLOW}   Google Sign-In will not work. Set it in .env file or export it.${NC}\n"
fi

# Display database configuration status
if [ -z "$INSTANCE_CONNECTION_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASS" ] || [ -z "$DB_NAME" ]; then
    echo -e "${YELLOW}⚠️  Warning: Database environment variables not set${NC}"
    echo -e "${YELLOW}   Required: INSTANCE_CONNECTION_NAME, DB_USER, DB_PASS, DB_NAME${NC}"
    echo -e "${YELLOW}   Set them in .env file or export them${NC}\n"
else
    echo -e "${GREEN}✓ Database configuration found${NC}\n"
fi

# Display OpenAI configuration status
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  Warning: OPENAI_API_KEY is not set${NC}"
    echo -e "${YELLOW}   Chat functionality will not work. Set it in .env file or export it.${NC}\n"
else
    echo -e "${GREEN}✓ OpenAI API key found${NC}\n"
fi

# Display GCP credentials status
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo -e "${YELLOW}⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS is not set${NC}"
    echo -e "${YELLOW}   Cloud SQL connection will fail. Set it in .env file or export it.${NC}"
    echo -e "${YELLOW}   Example: GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json${NC}\n"
elif [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo -e "${YELLOW}⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS file not found: ${GOOGLE_APPLICATION_CREDENTIALS}${NC}"
    echo -e "${YELLOW}   Cloud SQL connection will fail. Check the file path.${NC}\n"
else
    echo -e "${GREEN}✓ GCP credentials file found: ${GOOGLE_APPLICATION_CREDENTIALS}${NC}\n"
fi

# Configuration
FRONTEND_IMAGE="meridian-frontend:latest"
BACKEND_IMAGE="meridian-backend:latest"
AGENTS_IMAGE="meridian-agents:latest"

FRONTEND_CONTAINER="meridian-frontend"
BACKEND_CONTAINER="meridian-backend"
AGENTS_CONTAINER="meridian-agents"

FRONTEND_PORT=3000
BACKEND_PORT=8000
AGENTS_PORT=8001

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Meridian Project - Docker Deployment${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Function to stop and remove container
stop_and_remove() {
    local container=$1
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${YELLOW}Stopping and removing ${container}...${NC}"
        docker stop ${container} 2>/dev/null || true
        docker rm ${container} 2>/dev/null || true
        echo -e "${GREEN}✓ ${container} removed${NC}\n"
    else
        echo -e "${GREEN}✓ ${container} does not exist, skipping${NC}\n"
    fi
}

# Step 1: Stop and remove existing containers
echo -e "${YELLOW}Step 1: Cleaning up existing containers...${NC}"
stop_and_remove ${FRONTEND_CONTAINER}
stop_and_remove ${BACKEND_CONTAINER}
stop_and_remove ${AGENTS_CONTAINER}

# Step 2: Build Docker images
echo -e "${YELLOW}Step 2: Building Docker images...${NC}\n"

# Build Frontend
echo -e "${YELLOW}Building ${FRONTEND_IMAGE}...${NC}"
if docker build -f Dockerfile.frontend \
    --build-arg NEXT_PUBLIC_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID} \
    --build-arg NEXT_PUBLIC_API_URL=${API_URL:-http://localhost:8000} \
    -t ${FRONTEND_IMAGE} .; then
    echo -e "${GREEN}✓ ${FRONTEND_IMAGE} built successfully${NC}\n"
else
    echo -e "${RED}✗ Failed to build ${FRONTEND_IMAGE}${NC}"
    exit 1
fi

# Build Backend
echo -e "${YELLOW}Building ${BACKEND_IMAGE}...${NC}"
if docker build -f Dockerfile.backend -t ${BACKEND_IMAGE} .; then
    echo -e "${GREEN}✓ ${BACKEND_IMAGE} built successfully${NC}\n"
else
    echo -e "${RED}✗ Failed to build ${BACKEND_IMAGE}${NC}"
    exit 1
fi

# Build Agents
echo -e "${YELLOW}Building ${AGENTS_IMAGE}...${NC}"
if docker build -f Dockerfile.agents -t ${AGENTS_IMAGE} .; then
    echo -e "${GREEN}✓ ${AGENTS_IMAGE} built successfully${NC}\n"
else
    echo -e "${RED}✗ Failed to build ${AGENTS_IMAGE}${NC}"
    exit 1
fi

# Step 3: Run containers
echo -e "${YELLOW}Step 3: Starting containers...${NC}\n"

# Run Agents Service (start first as backend depends on it)
echo -e "${YELLOW}Starting ${AGENTS_CONTAINER} on port ${AGENTS_PORT}...${NC}"
if docker run -d \
    -p ${AGENTS_PORT}:${AGENTS_PORT} \
    --name ${AGENTS_CONTAINER} \
    -e OPENAI_API_KEY=${OPENAI_API_KEY} \
    ${AGENTS_IMAGE}; then
    echo -e "${GREEN}✓ ${AGENTS_CONTAINER} started${NC}\n"
else
    echo -e "${RED}✗ Failed to start ${AGENTS_CONTAINER}${NC}"
    exit 1
fi

# Wait a bit for agents to initialize
echo -e "${YELLOW}Waiting for agents service to initialize...${NC}"
sleep 5

# Run Backend Service
echo -e "${YELLOW}Starting ${BACKEND_CONTAINER} on port ${BACKEND_PORT}...${NC}"

# Check for required environment variables
if [ -z "$INSTANCE_CONNECTION_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASS" ] || [ -z "$DB_NAME" ]; then
    echo -e "${RED}✗ Missing required database environment variables${NC}"
    echo -e "${YELLOW}   Required: INSTANCE_CONNECTION_NAME, DB_USER, DB_PASS, DB_NAME${NC}"
    echo -e "${YELLOW}   Set them in .env file or export them${NC}"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}✗ Missing required OPENAI_API_KEY environment variable${NC}"
    echo -e "${YELLOW}   Set it in .env file or export it${NC}"
    exit 1
fi

# Build docker run command with environment variables
BACKEND_RUN_CMD="docker run -d \
    -p ${BACKEND_PORT}:${BACKEND_PORT} \
    --name ${BACKEND_CONTAINER} \
    -e AGENTS_SERVICE_URL=http://host.docker.internal:${AGENTS_PORT} \
    -e INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME} \
    -e DB_USER=${DB_USER} \
    -e DB_PASS=${DB_PASS} \
    -e DB_NAME=${DB_NAME} \
    -e DB_TYPE=${DB_TYPE:-postgresql} \
    -e OPENAI_API_KEY=${OPENAI_API_KEY} \
    -e OPENAI_MODEL=${OPENAI_MODEL:-gpt-4}"

# Add GCP credentials volume if provided (REQUIRED for Cloud SQL)
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo -e "${RED}✗ Missing required GOOGLE_APPLICATION_CREDENTIALS environment variable${NC}"
    echo -e "${YELLOW}   Cloud SQL connection requires GCP service account credentials.${NC}"
    echo -e "${YELLOW}   Set GOOGLE_APPLICATION_CREDENTIALS in .env file pointing to your service account JSON file.${NC}"
    echo -e "${YELLOW}   Example: GOOGLE_APPLICATION_CREDENTIALS=/path/to/config/cloud-run-sa.json${NC}"
    exit 1
elif [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo -e "${RED}✗ GCP credentials file not found: ${GOOGLE_APPLICATION_CREDENTIALS}${NC}"
    echo -e "${YELLOW}   Please check the file path and ensure the file exists.${NC}"
    exit 1
else
    # Mount credentials file and set environment variable
    BACKEND_RUN_CMD="${BACKEND_RUN_CMD} \
    -v ${GOOGLE_APPLICATION_CREDENTIALS}:/app/gcp-credentials.json:ro \
    -e GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json"
    echo -e "${GREEN}✓ GCP credentials file will be mounted: ${GOOGLE_APPLICATION_CREDENTIALS}${NC}"
fi

# Add optional environment variables
if [ -n "$PORT" ]; then
    BACKEND_RUN_CMD="${BACKEND_RUN_CMD} -e PORT=${PORT}"
fi
if [ -n "$LOG_LEVEL" ]; then
    BACKEND_RUN_CMD="${BACKEND_RUN_CMD} -e LOG_LEVEL=${LOG_LEVEL}"
fi
if [ -n "$ENVIRONMENT" ]; then
    BACKEND_RUN_CMD="${BACKEND_RUN_CMD} -e ENVIRONMENT=${ENVIRONMENT}"
fi
if [ -n "$MAX_CONVERSATION_HISTORY" ]; then
    BACKEND_RUN_CMD="${BACKEND_RUN_CMD} -e MAX_CONVERSATION_HISTORY=${MAX_CONVERSATION_HISTORY}"
fi

BACKEND_RUN_CMD="${BACKEND_RUN_CMD} ${BACKEND_IMAGE}"

# Execute the command
if eval ${BACKEND_RUN_CMD}; then
    echo -e "${GREEN}✓ ${BACKEND_CONTAINER} started${NC}\n"
else
    echo -e "${RED}✗ Failed to start ${BACKEND_CONTAINER}${NC}"
    exit 1
fi

# Run Frontend Service
# Note: NEXT_PUBLIC_* vars are baked in at build time, but we can still pass them for runtime overrides
echo -e "${YELLOW}Starting ${FRONTEND_CONTAINER} on port ${FRONTEND_PORT}...${NC}"
if docker run -d \
    -p ${FRONTEND_PORT}:${FRONTEND_PORT} \
    --name ${FRONTEND_CONTAINER} \
    ${FRONTEND_IMAGE}; then
    echo -e "${GREEN}✓ ${FRONTEND_CONTAINER} started${NC}\n"
else
    echo -e "${RED}✗ Failed to start ${FRONTEND_CONTAINER}${NC}"
    exit 1
fi

# Step 4: Health checks
echo -e "${YELLOW}Step 4: Running health checks...${NC}\n"

# Wait a bit for services to be ready
sleep 3

check_health() {
    local service=$1
    local url=$2
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f ${url} > /dev/null 2>&1; then
            echo -e "${GREEN}✓ ${service} is healthy${NC}"
            return 0
        fi
        echo -e "${YELLOW}  Attempt ${attempt}/${max_attempts}: ${service} not ready yet...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ ${service} health check failed${NC}"
    return 1
}

check_health "Agents Service" "http://localhost:${AGENTS_PORT}/health"
check_health "Backend Service" "http://localhost:${BACKEND_PORT}/health"
check_health "Frontend Service" "http://localhost:${FRONTEND_PORT}"

# Step 5: Display status
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Container Status:${NC}"
docker ps --filter "name=meridian-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n${YELLOW}Service URLs:${NC}"
echo -e "  Frontend:  ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "  Backend:   ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
echo -e "  Agents:    ${GREEN}http://localhost:${AGENTS_PORT}${NC}"

echo -e "\n${YELLOW}Useful Commands:${NC}"
echo -e "  View backend logs:  ${GREEN}docker logs -f ${BACKEND_CONTAINER}${NC}"
echo -e "  View frontend logs: ${GREEN}docker logs -f ${FRONTEND_CONTAINER}${NC}"
echo -e "  View agents logs:   ${GREEN}docker logs -f ${AGENTS_CONTAINER}${NC}"
echo -e "  Stop all:           ${GREEN}docker stop ${FRONTEND_CONTAINER} ${BACKEND_CONTAINER} ${AGENTS_CONTAINER}${NC}"
echo -e "  Remove all:          ${GREEN}docker rm ${FRONTEND_CONTAINER} ${BACKEND_CONTAINER} ${AGENTS_CONTAINER}${NC}"

echo -e "\n${YELLOW}Important Notes:${NC}"
echo -e "  • Database migrations run automatically on backend startup${NC}"
echo -e "  • Ensure Cloud SQL credentials are properly configured${NC}"
echo -e "  • Check logs if services fail to start: ${GREEN}docker logs ${BACKEND_CONTAINER}${NC}"

echo -e "\n${GREEN}All services are running!${NC}\n"
