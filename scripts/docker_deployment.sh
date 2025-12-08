#!/bin/bash

# Meridian Project - Local Docker Deployment Script
# This script rebuilds all Docker images and starts containers

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
if docker build -f Dockerfile.frontend -t ${FRONTEND_IMAGE} .; then
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
if docker run -d \
    -p ${BACKEND_PORT}:${BACKEND_PORT} \
    --name ${BACKEND_CONTAINER} \
    -e AGENTS_SERVICE_URL=http://host.docker.internal:${AGENTS_PORT} \
    ${BACKEND_IMAGE}; then
    echo -e "${GREEN}✓ ${BACKEND_CONTAINER} started${NC}\n"
else
    echo -e "${RED}✗ Failed to start ${BACKEND_CONTAINER}${NC}"
    exit 1
fi

# Run Frontend Service
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
echo -e "  View logs:     ${GREEN}docker logs -f ${CONTAINER_NAME}${NC}"
echo -e "  Stop all:      ${GREEN}docker stop ${FRONTEND_CONTAINER} ${BACKEND_CONTAINER} ${AGENTS_CONTAINER}${NC}"
echo -e "  Remove all:    ${GREEN}docker rm ${FRONTEND_CONTAINER} ${BACKEND_CONTAINER} ${AGENTS_CONTAINER}${NC}"

echo -e "\n${GREEN}All services are running!${NC}\n"
