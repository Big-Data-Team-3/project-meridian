#!/bin/bash

###############################################################################
# Meridian Project - Cloud SQL Setup Script
# 
# This script creates a Cloud SQL PostgreSQL instance for the Meridian project.
# It's designed to be generic and reusable for any deployment.
#
# Usage: ./scripts/setup_cloud_sql.sh
#
# Prerequisites:
#   - .env file with PROJECT_ID, REGION, and optional Cloud SQL config
#   - gcloud CLI installed and authenticated
#   - Appropriate GCP permissions
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
        exit 1
    fi
    
    # Load variables, handling quotes and whitespace
    set -a
    source .env
    set +a
    
    # Validate required variables
    local required_vars=(
        "PROJECT_ID"
        "REGION"
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

###############################################################################
# Configuration
###############################################################################

# Cloud SQL instance configuration (with defaults)
INSTANCE_NAME=${CLOUD_SQL_INSTANCE_NAME:-"meridian-db"}
DB_NAME=${DB_NAME:-"meridian"}
DB_USER=${DB_USER:-"meridian_user"}
DB_PASS=${DB_PASS:-""}  # Will generate if not set
TIER=${CLOUD_SQL_TIER:-"db-f1-micro"}  # Free tier for development
STORAGE_SIZE=${CLOUD_SQL_STORAGE_SIZE:-"10GB"}
STORAGE_TYPE=${CLOUD_SQL_STORAGE_TYPE:-"SSD"}

###############################################################################
# Main Setup Function
###############################################################################

setup_cloud_sql() {
    print_header "Cloud SQL Instance Setup"
    
    # Set gcloud project
    print_step "Setting GCP Project"
    gcloud config set project ${PROJECT_ID} --quiet
    print_success "Project set to: ${PROJECT_ID}"
    
    # Check if instance already exists
    if gcloud sql instances describe ${INSTANCE_NAME} \
        --project=${PROJECT_ID} &>/dev/null; then
        print_info "Cloud SQL instance '${INSTANCE_NAME}' already exists"
        INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe ${INSTANCE_NAME} \
            --project=${PROJECT_ID} \
            --format='value(connectionName)')
        print_success "Using existing instance"
        print_info "Connection name: ${INSTANCE_CONNECTION_NAME}"
    else
        print_step "Creating Cloud SQL Instance"
        print_info "Instance name: ${INSTANCE_NAME}"
        print_info "Region: ${REGION}"
        print_info "Tier: ${TIER}"
        print_info "Storage: ${STORAGE_SIZE} ${STORAGE_TYPE}"
        
        # Create the instance
        gcloud sql instances create ${INSTANCE_NAME} \
            --database-version=POSTGRES_15 \
            --tier=${TIER} \
            --region=${REGION} \
            --project=${PROJECT_ID} \
            --storage-type=${STORAGE_TYPE} \
            --storage-size=${STORAGE_SIZE} \
            --backup-start-time=03:00 \
            --enable-bin-log \
            --maintenance-window-day=SUN \
            --maintenance-window-hour=4 \
            --quiet
        
        print_success "Cloud SQL instance created"
        
        # Get connection name
        INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe ${INSTANCE_NAME} \
            --project=${PROJECT_ID} \
            --format='value(connectionName)')
        
        print_success "Connection name: ${INSTANCE_CONNECTION_NAME}"
    fi
    
    # Set root password if not set
    if [ -z "${DB_PASS}" ]; then
        print_step "Generating Database Password"
        DB_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        gcloud sql users set-password postgres \
            --instance=${INSTANCE_NAME} \
            --password=${DB_PASS} \
            --project=${PROJECT_ID} \
            --quiet
        print_success "Root password set"
    else
        print_info "Using provided DB_PASS from .env"
    fi
    
    # Create database if it doesn't exist
    if gcloud sql databases describe ${DB_NAME} \
        --instance=${INSTANCE_NAME} \
        --project=${PROJECT_ID} &>/dev/null; then
        print_success "Database '${DB_NAME}' already exists"
    else
        print_step "Creating Database"
        gcloud sql databases create ${DB_NAME} \
            --instance=${INSTANCE_NAME} \
            --project=${PROJECT_ID} \
            --quiet
        print_success "Database '${DB_NAME}' created"
    fi
    
    # Create application user if it doesn't exist
    if gcloud sql users list \
        --instance=${INSTANCE_NAME} \
        --project=${PROJECT_ID} \
        --format='value(name)' | grep -q "^${DB_USER}$"; then
        print_success "Database user '${DB_USER}' already exists"
    else
        print_step "Creating Database User"
        gcloud sql users create ${DB_USER} \
            --instance=${INSTANCE_NAME} \
            --password=${DB_PASS} \
            --project=${PROJECT_ID} \
            --quiet
        print_success "Database user '${DB_USER}' created"
    fi
    
    # Summary
    print_header "Cloud SQL Setup Complete!"
    echo -e "${GREEN}✓ Cloud SQL instance ready${NC}\n"
    echo "Configuration:"
    echo "  Instance: ${INSTANCE_NAME}"
    echo "  Connection: ${INSTANCE_CONNECTION_NAME}"
    echo "  Database: ${DB_NAME}"
    echo "  User: ${DB_USER}"
    echo ""
    echo "Add these to your .env file:"
    echo "INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME}"
    echo "DB_USER=${DB_USER}"
    echo "DB_PASS=${DB_PASS}"
    echo "DB_NAME=${DB_NAME}"
    echo ""
    echo "Next steps:"
    echo "  1. Update your .env file with the above values"
    echo "  2. Run migrations: ./scripts/deploy_to_cloud_run.sh (Phase 5 will run migrations)"
    echo "  3. Or run migrations manually: python meridian-backend/database/run_migrations.py"
    echo ""
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_header "Meridian Project - Cloud SQL Setup"
    
    print_info "This script will:"
    echo "  1. Create a Cloud SQL PostgreSQL instance (if it doesn't exist)"
    echo "  2. Create the database"
    echo "  3. Create database user"
    echo "  4. Generate connection details"
    echo ""
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Setup cancelled"
        exit 0
    fi
    
    load_env
    setup_cloud_sql
}

# Run main function
main "$@"

