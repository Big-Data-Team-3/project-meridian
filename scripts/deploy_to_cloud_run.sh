#!/bin/bash

###############################################################################
# Meridian Project - Complete GCP Cloud Run Deployment Script
# 
# This script automates the entire deployment process:
# 1. Validates prerequisites and environment
# 2. Sets up GCP infrastructure (APIs, Cloud SQL, Service Accounts)
# 3. Builds and pushes Docker images
# 4. Deploys all services to Cloud Run
# 5. Configures service-to-service communication
# 6. Runs database migrations
# 7. Tests the deployment
#
# Usage: ./scripts/deploy_to_cloud_run.sh
###############################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_step() {
    echo -e "\n${YELLOW}▶ $1${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Load environment variables from .env file
load_env() {
    if [ ! -f .env ]; then
        print_error ".env file not found!"
        print_info "Please create a .env file with required variables."
        print_info "See .env.example for reference."
        exit 1
    fi
    
    # Load variables, handling quotes and whitespace
    set -a
    source .env
    set +a
    
    # Extract GOOGLE_CLIENT_ID from NEXT_PUBLIC_GOOGLE_CLIENT_ID if needed
    if [ -n "${NEXT_PUBLIC_GOOGLE_CLIENT_ID}" ] && [ -z "${GOOGLE_CLIENT_ID}" ]; then
        export GOOGLE_CLIENT_ID="${NEXT_PUBLIC_GOOGLE_CLIENT_ID}"
        print_info "Using NEXT_PUBLIC_GOOGLE_CLIENT_ID for GOOGLE_CLIENT_ID"
    fi
    
    # Validate required variables
    local required_vars=(
        "PROJECT_ID"
        "REGION"
        "INSTANCE_CONNECTION_NAME"
        "DB_USER"
        "DB_PASS"
        "DB_NAME"
        "OPENAI_API_KEY"
        "NEXT_PUBLIC_GOOGLE_CLIENT_ID"
        "GOOGLE_CLIENT_SECRET"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
    
    print_success "Environment variables loaded"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking Prerequisites"
    
    local errors=0
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        errors=$((errors + 1))
    else
        print_success "Docker is installed: $(docker --version)"
    fi
    
    # Check gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed"
        print_info "Install from: https://cloud.google.com/sdk/docs/install"
        errors=$((errors + 1))
    else
        print_success "gcloud CLI is installed: $(gcloud --version | head -n 1)"
    fi
    
    # Check if logged in to gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not logged in to gcloud"
        print_info "Run: gcloud auth login"
        errors=$((errors + 1))
    else
        print_success "Logged in to gcloud as: $(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        errors=$((errors + 1))
    else
        print_success "Docker daemon is running"
    fi
    
    if [ $errors -ne 0 ]; then
        print_error "Please fix the above errors before continuing"
        exit 1
    fi
}

###############################################################################
# Phase 1: GCP Infrastructure Setup
###############################################################################

setup_gcp_infrastructure() {
    print_header "Phase 1: GCP Infrastructure Setup"
    
    # ========================================
    # SET PRODUCTION CONTEXT
    # ========================================
    export DEPLOYMENT_ENV="production"
    export DB_NAME="${PROD_DB_NAME:-meridian_prod}"
    
    print_info "Deployment Environment: ${DEPLOYMENT_ENV}"
    print_info "Database Name: ${DB_NAME}"
    echo ""
    
    # Set gcloud project
    print_step "Setting GCP Project"
    gcloud config set project ${PROJECT_ID} --quiet
    print_success "Project set to: ${PROJECT_ID}"
    
    # Enable APIs
    print_step "Enabling Required APIs"
    gcloud services enable \
        run.googleapis.com \
        cloudbuild.googleapis.com \
        artifactregistry.googleapis.com \
        sqladmin.googleapis.com \
        storage-component.googleapis.com \
        logging.googleapis.com \
        monitoring.googleapis.com \
        --project=${PROJECT_ID} --quiet
    
    print_success "APIs enabled"
    
    # Create Artifact Registry repository
    print_step "Creating Artifact Registry Repository"
    if gcloud artifacts repositories describe meridian \
        --location=${REGION} \
        --project=${PROJECT_ID} &>/dev/null; then
        print_success "Repository 'meridian' already exists"
    else
        gcloud artifacts repositories create meridian \
            --repository-format=docker \
            --location=${REGION} \
            --project=${PROJECT_ID} --quiet
        print_success "Repository 'meridian' created"
    fi
    
    # Configure Docker authentication
    print_step "Configuring Docker Authentication"
    gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
    print_success "Docker authentication configured"
    
    # Run GCP setup script for service accounts (idempotent)
    print_step "Setting up Service Accounts"
    if [ -f scripts/setup_gcp.sh ]; then
        bash scripts/setup_gcp.sh
        print_success "Service accounts configured"
    else
        print_error "scripts/setup_gcp.sh not found"
        exit 1
    fi
    
    # ========================================
    # ENSURE CLOUD SQL AND DATABASE SETUP
    # ========================================
    print_step "Setting up Cloud SQL and Production Database"
    
    # Check if INSTANCE_CONNECTION_NAME is set in environment
    if [ -z "${INSTANCE_CONNECTION_NAME}" ]; then
        print_error "INSTANCE_CONNECTION_NAME is not set in .env file"
        print_info "Please add Cloud SQL instance connection name to .env"
        print_info "Format: INSTANCE_CONNECTION_NAME=project:region:instance-name"
        print_info "Or just set the instance name and it will be created automatically"
        exit 1
    fi
    
    # Extract instance name from connection string (format: project:region:instance)
    INSTANCE_NAME=$(echo ${INSTANCE_CONNECTION_NAME} | cut -d ':' -f 3)
    
    # Check if the instance exists
    if gcloud sql instances describe ${INSTANCE_NAME} \
        --project=${PROJECT_ID} &>/dev/null; then
        print_success "Cloud SQL instance '${INSTANCE_NAME}' exists"
    else
        print_info "Cloud SQL instance '${INSTANCE_NAME}' not found"
        print_info "Running setup_cloud_sql.sh to create it..."
        
        if [ -f scripts/setup_cloud_sql.sh ]; then
            bash scripts/setup_cloud_sql.sh
            print_success "Cloud SQL instance created"
        else
            print_error "scripts/setup_cloud_sql.sh not found"
            print_info "Please create Cloud SQL instance manually or add setup_cloud_sql.sh"
            exit 1
        fi
    fi
    
    print_success "Using connection name: ${INSTANCE_CONNECTION_NAME}"
    
    # Check if production database exists
    if gcloud sql databases describe ${DB_NAME} \
        --instance=${INSTANCE_NAME} \
        --project=${PROJECT_ID} &>/dev/null; then
        print_success "Database '${DB_NAME}' exists"
    else
        print_info "Database '${DB_NAME}' not found. Creating..."
        gcloud sql databases create ${DB_NAME} \
            --instance=${INSTANCE_NAME} \
            --project=${PROJECT_ID} --quiet
        print_success "Database '${DB_NAME}' created"
    fi
}

###############################################################################
# Phase 2: Build and Push Docker Images
###############################################################################

build_and_push_images() {
    print_header "Phase 2: Building and Pushing Docker Images"
    
    export GCR_REGION="${REGION}-docker.pkg.dev"
    export IMAGE_PREFIX="${GCR_REGION}/${PROJECT_ID}/meridian"
    
    # Build Agents image
    print_step "Building Agents Service Image"
    # Use --platform linux/amd64 for Cloud Run compatibility (required for Apple Silicon Macs)
    docker build --platform linux/amd64 -f Dockerfile.agents \
        -t ${IMAGE_PREFIX}/meridian-agents:latest \
        -t ${IMAGE_PREFIX}/meridian-agents:$(git rev-parse --short HEAD 2>/dev/null || echo "latest") \
        . --quiet
    
    print_success "Agents image built"
    
    # Push Agents image
    print_step "Pushing Agents Service Image"
    docker push ${IMAGE_PREFIX}/meridian-agents:latest --quiet
    print_success "Agents image pushed"
    
    # Build Backend image
    print_step "Building Backend Service Image"
    # Use --platform linux/amd64 for Cloud Run compatibility (required for Apple Silicon Macs)
    docker build --platform linux/amd64 -f Dockerfile.backend \
        -t ${IMAGE_PREFIX}/meridian-backend:latest \
        -t ${IMAGE_PREFIX}/meridian-backend:$(git rev-parse --short HEAD 2>/dev/null || echo "latest") \
        . --quiet
    
    print_success "Backend image built"
    
    # Push Backend image
    print_step "Pushing Backend Service Image"
    docker push ${IMAGE_PREFIX}/meridian-backend:latest --quiet
    print_success "Backend image pushed"
    
    # Note: Frontend will be built after backend deployment when we have the backend URL
}

###############################################################################
# Phase 3: Deploy to Cloud Run
###############################################################################

deploy_to_cloud_run() {
    print_header "Phase 3: Deploying to Cloud Run"
    
    export GCR_REGION="${REGION}-docker.pkg.dev"
    export IMAGE_PREFIX="${GCR_REGION}/${PROJECT_ID}/meridian"
    export CLOUD_RUN_SA="cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Deploy Agents Service
    print_step "Deploying Agents Service"
    # Note: PORT is automatically set by Cloud Run, don't set it manually
    AGENTS_URL=$(gcloud run deploy meridian-agents \
        --image ${IMAGE_PREFIX}/meridian-agents:latest \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --service-account ${CLOUD_RUN_SA} \
        --set-env-vars "OPENAI_API_KEY=${OPENAI_API_KEY}" \
        --set-cloudsql-instances ${INSTANCE_CONNECTION_NAME} \
        --memory 2Gi \
        --cpu 2 \
        --timeout 900 \
        --max-instances 10 \
        --min-instances 0 \
        --project ${PROJECT_ID} \
        --format 'value(status.url)' --quiet)
    
    export AGENTS_URL
    print_success "Agents Service deployed: ${AGENTS_URL}"
    
    # Update .env with agents URL
    if grep -q "^AGENTS_SERVICE_URL=" .env 2>/dev/null; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^AGENTS_SERVICE_URL=.*|AGENTS_SERVICE_URL=${AGENTS_URL}|" .env
        else
            # Linux
            sed -i "s|^AGENTS_SERVICE_URL=.*|AGENTS_SERVICE_URL=${AGENTS_URL}|" .env
        fi
    else
        echo "AGENTS_SERVICE_URL=${AGENTS_URL}" >> .env
    fi
    
    # Deploy Backend Service
    print_step "Deploying Backend Service"
    BACKEND_URL=$(gcloud run deploy meridian-backend \
        --image ${IMAGE_PREFIX}/meridian-backend:latest \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --service-account ${CLOUD_RUN_SA} \
        --set-env-vars \
            "INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME},\
            DB_USER=${DB_USER},\
            DB_PASS=${DB_PASS},\
            DB_NAME=${DB_NAME},\
            OPENAI_API_KEY=${OPENAI_API_KEY},\
            GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},\
            GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET},\
            AGENTS_SERVICE_URL=${AGENTS_URL}" \
        --set-cloudsql-instances ${INSTANCE_CONNECTION_NAME} \
        --memory 1Gi \
        --cpu 1 \
        --timeout 300 \
        --max-instances 10 \
        --min-instances 0 \
        --project ${PROJECT_ID} \
        --format 'value(status.url)' --quiet)
    
    export BACKEND_URL
    print_success "Backend Service deployed: ${BACKEND_URL}"
    
    # Update .env with backend URL
    if grep -q "^BACKEND_URL=" .env 2>/dev/null; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^BACKEND_URL=.*|BACKEND_URL=${BACKEND_URL}|" .env
        else
            # Linux
            sed -i "s|^BACKEND_URL=.*|BACKEND_URL=${BACKEND_URL}|" .env
        fi
    else
        echo "BACKEND_URL=${BACKEND_URL}" >> .env
    fi
    
    # Rebuild Frontend with correct backend URL
    print_step "Rebuilding Frontend with Correct Backend URL"
    # Use --platform linux/amd64 for Cloud Run compatibility (required for Apple Silicon Macs)
    docker build --platform linux/amd64 -f Dockerfile.frontend \
        --build-arg NEXT_PUBLIC_GOOGLE_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_CLIENT_ID} \
        --build-arg NEXT_PUBLIC_API_URL=${BACKEND_URL} \
        -t ${IMAGE_PREFIX}/meridian-frontend:latest \
        . --quiet
    
    docker push ${IMAGE_PREFIX}/meridian-frontend:latest --quiet
    print_success "Frontend image rebuilt and pushed"
    
    # Deploy Frontend Service
    print_step "Deploying Frontend Service"
    FRONTEND_URL=$(gcloud run deploy meridian-frontend \
        --image ${IMAGE_PREFIX}/meridian-frontend:latest \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --memory 512Mi \
        --cpu 1 \
        --timeout 60 \
        --max-instances 10 \
        --min-instances 0 \
        --project ${PROJECT_ID} \
        --format 'value(status.url)' --quiet)
    
    export FRONTEND_URL
    print_success "Frontend Service deployed: ${FRONTEND_URL}"
}

###############################################################################
# Phase 4: Configure Service Communication
###############################################################################

configure_service_communication() {
    print_header "Phase 4: Configuring Service Communication"
    
    # Allow Backend to invoke Agents service
    print_step "Configuring Service-to-Service Authentication"
    gcloud run services add-iam-policy-binding meridian-agents \
        --region ${REGION} \
        --member="serviceAccount:cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/run.invoker" \
        --project ${PROJECT_ID} --quiet
    
    print_success "Backend can now invoke Agents service"
}

###############################################################################
# Phase 5: Run Database Migrations
###############################################################################

run_migrations() {
    print_header "Phase 5: Running Database Migrations"
    
    print_step "Creating Migration Job"
    
    export GCR_REGION="${REGION}-docker.pkg.dev"
    export IMAGE_PREFIX="${GCR_REGION}/${PROJECT_ID}/meridian"
    export CLOUD_RUN_SA="cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Create a Cloud Run Job for migrations
    if gcloud run jobs describe meridian-migrations \
        --region ${REGION} \
        --project ${PROJECT_ID} &>/dev/null; then
        print_info "Migration job already exists, updating..."
        gcloud run jobs update meridian-migrations \
            --image ${IMAGE_PREFIX}/meridian-backend:latest \
            --region ${REGION} \
            --service-account ${CLOUD_RUN_SA} \
            --set-env-vars \
                "INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME},\
                DB_USER=${DB_USER},\
                DB_PASS=${DB_PASS},\
                DB_NAME=${DB_NAME}" \
            --set-cloudsql-instances ${INSTANCE_CONNECTION_NAME} \
            --project ${PROJECT_ID} --quiet
    else
        gcloud run jobs create meridian-migrations \
            --image ${IMAGE_PREFIX}/meridian-backend:latest \
            --region ${REGION} \
            --service-account ${CLOUD_RUN_SA} \
            --set-env-vars \
                "INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME},\
                DB_USER=${DB_USER},\
                DB_PASS=${DB_PASS},\
                DB_NAME=${DB_NAME}" \
            --set-cloudsql-instances ${INSTANCE_CONNECTION_NAME} \
            --command sh \
            --args "-c,cd /app && PYTHONPATH=/app/meridian-backend:/app python meridian-backend/database/run_migrations.py" \
            --project ${PROJECT_ID} --quiet
    fi
    
    print_step "Executing Migration Job"
    gcloud run jobs execute meridian-migrations \
        --region ${REGION} \
        --project ${PROJECT_ID} --wait --quiet
    
    print_success "Database migrations completed"
}

###############################################################################
# Phase 6: Test Deployment
###############################################################################

test_deployment() {
    print_header "Phase 6: Testing Deployment"
    
    print_step "Testing Health Endpoints"
    
    # Test Agents
    if curl -s -f ${AGENTS_URL}/health > /dev/null 2>&1; then
        print_success "Agents service health check passed"
    else
        print_error "Agents service health check failed"
        print_info "URL: ${AGENTS_URL}/health"
    fi
    
    # Test Backend
    if curl -s -f ${BACKEND_URL}/health > /dev/null 2>&1; then
        print_success "Backend service health check passed"
    else
        print_error "Backend service health check failed"
        print_info "URL: ${BACKEND_URL}/health"
    fi
    
    # Test Frontend
    if curl -s -f ${FRONTEND_URL} > /dev/null 2>&1; then
        print_success "Frontend service is accessible"
    else
        print_error "Frontend service is not accessible"
        print_info "URL: ${FRONTEND_URL}"
    fi
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_header "Meridian Project - GCP Cloud Run Deployment"
    
    print_info "This script will:"
    echo "  1. Validate prerequisites"
    echo "  2. Set up GCP infrastructure"
    echo "  3. Build and push Docker images"
    echo "  4. Deploy services to Cloud Run"
    echo "  5. Configure service communication"
    echo "  6. Run database migrations"
    echo "  7. Test the deployment"
    echo ""
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deployment cancelled"
        exit 0
    fi
    
    # Execute phases
    load_env
    check_prerequisites
    setup_gcp_infrastructure
    build_and_push_images
    deploy_to_cloud_run
    configure_service_communication
    run_migrations
    test_deployment
    
    # Final summary
    print_header "Deployment Complete!"
    echo -e "${GREEN}✓ All services deployed successfully${NC}\n"
    echo "Service URLs:"
    echo "  Frontend: ${FRONTEND_URL}"
    echo "  Backend:  ${BACKEND_URL}"
    echo "  Agents:   ${AGENTS_URL}"
    echo ""
    echo "Next steps:"
    echo "  1. Open ${FRONTEND_URL} in your browser"
    echo "  2. Test the application with a sample query"
    echo "  3. Monitor logs: gcloud logging read 'resource.type=cloud_run_revision' --limit 50"
    echo ""
}

# Run main function
main "$@"

