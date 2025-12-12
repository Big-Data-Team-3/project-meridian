#! /bin/bash

# This script is used to setup the GCP project and other resources required for the project.

# Authenticate with GCP
gcloud auth login
echo "Authenticated with GCP"
# Get the project ID from the .env file, handling quotes and whitespace for the project ID
PROJECT_ID=$(grep "^PROJECT_ID=" .env | cut -d '=' -f 2 | tr -d '"' | tr -d "'" | tr -d '[' | tr -d ']' | xargs)

# Create a new project (you can manually create the project in the GCP console if you prefer, but please do add the env value for the project ID to the .env file)
if [ -z "$PROJECT_ID" ]; then
    echo "PROJECT_ID is not set"
    PROJECT_ID="meridian-project"
fi
# If the project already exists, skip the creation
if gcloud projects list --filter="projectId=$PROJECT_ID" --format="get(projectId)" | grep -q $PROJECT_ID; then
    echo "Project $PROJECT_ID already exists"
else
    echo "Creating project $PROJECT_ID"
    gcloud projects create $PROJECT_ID --set-as-default
fi

echo "--------------------------------"
echo "Enabling essential APIs..."
# Essential APIs
gcloud services enable compute.googleapis.com              # Compute Engine
gcloud services enable storage-component.googleapis.com     # Cloud Storage (GCS)
gcloud services enable sqladmin.googleapis.com              # Cloud SQL
gcloud services enable identitytoolkit.googleapis.com        # Identity Toolkit

# Optional but recommended
gcloud services enable run.googleapis.com                   # Cloud Run (if using)
gcloud services enable containerregistry.googleapis.com      # Container Registry
gcloud services enable cloudbuild.googleapis.com             # Cloud Build (for CI/CD)

# Optional: Monitoring and logging
gcloud services enable logging.googleapis.com                # Cloud Logging
gcloud services enable monitoring.googleapis.com            # Cloud Monitoring

echo "The following APIs are enabled:"
gcloud services list --enabled --format="get(name)"
echo "--------------------------------"
echo "Creating service accounts for the project..."

# Create Compute Engine Service Account
if gcloud iam service-accounts describe compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com &>/dev/null; then
    echo "✅ Service Account for Compute Engine already exists: compute-engine-sa"
else
    echo "Creating Service Account for Compute Engine..."
    if gcloud iam service-accounts create compute-engine-sa \
        --display-name="Compute Engine Service Account" \
        --description="Service account for Compute Engine VMs running Airflow, Chroma, FastAPI" \
        --project=$PROJECT_ID; then
        echo "✅ Service Account for Compute Engine created: compute-engine-sa"
    else
        echo "❌ ERROR: Failed to create Compute Engine service account"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Add IAM policy binding for Compute Engine Service Account to Cloud Storage (GCS) - Read/Write access
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Compute Engine Service Account to Cloud Storage (GCS) - Read/Write access already exists"
else
    echo "Adding IAM policy binding for Compute Engine Service Account to Cloud Storage (GCS) - Read/Write access..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
    then
        echo "✅ IAM policy binding for Compute Engine Service Account to Cloud Storage (GCS) - Read/Write access added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Compute Engine Service Account to Cloud Storage (GCS) - Read/Write access"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Create Cloud SQL Service Account (if it doesn't exist)
if gcloud iam service-accounts describe cloud-sql-sa@$PROJECT_ID.iam.gserviceaccount.com --project=$PROJECT_ID &>/dev/null; then
    echo "✅ Service Account for Cloud SQL already exists: cloud-sql-sa"
else
    echo "Creating Service Account for Cloud SQL..."
    if gcloud iam service-accounts create cloud-sql-sa \
        --display-name="Cloud SQL Service Account" \
        --description="Service account for Cloud SQL client connections" \
        --project=$PROJECT_ID; then
        echo "✅ Service Account for Cloud SQL created: cloud-sql-sa"
    else
        echo "❌ ERROR: Failed to create Cloud SQL service account"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Wait for all service accounts to be fully propagated in GCP before adding IAM bindings
echo ""
echo "⏳ Waiting 5 seconds for all service accounts to be fully propagated in GCP..."
sleep 5
echo "✅ Service account propagation wait complete"
echo ""

# Add IAM policy binding for Cloud SQL Service Account to Cloud SQL Client Role (roles/cloudsql.client) (for PostgreSQL)
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "cloud-sql-sa@$PROJECT_ID.iam.gserviceaccount.com.*roles/cloudsql.client"; then
    echo "✅ IAM policy binding for Cloud SQL Service Account to Cloud SQL Client Role (roles/cloudsql.client) (for PostgreSQL) already exists"
else
    echo "Adding IAM policy binding for Cloud SQL Service Account to Cloud SQL Client Role (roles/cloudsql.client) (for PostgreSQL)..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-sql-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"
    then
        echo "✅ IAM policy binding for Cloud SQL Service Account to Cloud SQL Client Role (roles/cloudsql.client) (for PostgreSQL) added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud SQL Service Account to Cloud SQL Client Role (roles/cloudsql.client) (for PostgreSQL)"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi


# Add IAM policy binding for Compute Engine Service Account to Cloud SQL - Viewer access (for PostgreSQL)
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Compute Engine Service Account to Cloud SQL - Viewer access (for PostgreSQL) already exists"
else
    echo "Adding IAM policy binding for Compute Engine Service Account to Cloud SQL - Viewer access (for PostgreSQL)..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.viewer"
    then
        echo "✅ IAM policy binding for Compute Engine Service Account to Cloud SQL - Viewer access (for PostgreSQL) added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Compute Engine Service Account to Cloud SQL - Viewer access (for PostgreSQL)"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Add IAM policy binding for Compute Engine Service Account to Logging - Write logs
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Compute Engine Service Account to Logging - Write logs already exists"
else
    echo "Adding IAM policy binding for Compute Engine Service Account to Logging - Write logs..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"
    then
        echo "✅ IAM policy binding for Compute Engine Service Account to Logging - Write logs added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Compute Engine Service Account to Logging - Write logs"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Add IAM policy binding for Compute Engine Service Account to Monitoring - Write metrics
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Compute Engine Service Account to Monitoring - Write metrics already exists"
else
    echo "Adding IAM policy binding for Compute Engine Service Account to Monitoring - Write metrics..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.metricWriter"
    then
        echo "✅ IAM policy binding for Compute Engine Service Account to Monitoring - Write metrics added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Compute Engine Service Account to Monitoring - Write metrics"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Create Cloud Run Service Account
CLOUD_RUN_SA_EMAIL="cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $CLOUD_RUN_SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    echo "✅ Service Account for Cloud Run already exists: cloud-run-sa"
else
    echo "Creating Service Account for Cloud Run..."
    if ! gcloud iam service-accounts create cloud-run-sa \
        --display-name="Cloud Run Service Account" \
        --description="Service account for Cloud Run services" \
        --project=$PROJECT_ID 2>&1; then
        echo "❌ ERROR: Failed to create Cloud Run service account"
        echo "   Please check your permissions and try again"
        exit 1
    fi
    echo "✅ Service Account for Cloud Run created: cloud-run-sa"
fi

# Verify service account exists before adding IAM bindings
if ! gcloud iam service-accounts describe $CLOUD_RUN_SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    echo "❌ ERROR: Cloud Run service account does not exist. Cannot add IAM bindings."
    exit 1
fi

# Cloud Storage (GCS) - Read/Write access
echo "Adding IAM policy binding for Cloud Run Service Account to Cloud Storage (GCS) - Read/Write access..."
if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUD_RUN_SA_EMAIL" \
    --role="roles/storage.objectAdmin" &>/dev/null; then
    echo "✅ IAM policy binding for Cloud Run Service Account to Cloud Storage (GCS) - Read/Write access added"
else
    # Check if binding already exists
    if gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:serviceAccount:$CLOUD_RUN_SA_EMAIL AND bindings.role:roles/storage.objectAdmin" --format="get(bindings.role)" &>/dev/null | grep -q "roles/storage.objectAdmin"; then
        echo "✅ IAM policy binding for Cloud Run Service Account to Cloud Storage (GCS) - Read/Write access already exists"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud Run Service Account to Cloud Storage (GCS) - Read/Write access"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Cloud SQL - Admin access
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Cloud Run Service Account to Cloud SQL - Admin access (for PostgreSQL) already exists"
else
    echo "Adding IAM policy binding for Cloud Run Service Account to Cloud SQL - Admin access (for PostgreSQL)..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.admin"
    then
        echo "✅ IAM policy binding for Cloud Run Service Account to Cloud SQL - Admin access (for PostgreSQL) added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud Run Service Account to Cloud SQL - Admin access (for PostgreSQL)"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

echo "Cloud SQL - Admin access added to the service account"

# Logging
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Cloud Run Service Account to Logging - Write logs already exists"
else
    echo "Adding IAM policy binding for Cloud Run Service Account to Logging - Write logs..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"
    then
        echo "✅ IAM policy binding for Cloud Run Service Account to Logging - Write logs added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud Run Service Account to Logging - Write logs"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Monitoring
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Cloud Run Service Account to Monitoring - Write metrics already exists"
else
    echo "Adding IAM policy binding for Cloud Run Service Account to Monitoring - Write metrics..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.metricWriter"
    then
        echo "✅ IAM policy binding for Cloud Run Service Account to Monitoring - Write metrics added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud Run Service Account to Monitoring - Write metrics"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

echo "Monitoring - Write metrics added to the service account"

# Get project number
echo "Getting project number..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
if [ -z "$PROJECT_NUMBER" ]; then
    echo "❌ ERROR: Failed to get project number for $PROJECT_ID"
    echo "   Please verify the project exists and you have access"
    exit 1
fi
echo "✅ Project number: $PROJECT_NUMBER"
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Cloud Run Service Account to Container Registry - Push images already exists"
else
    echo "Adding IAM policy binding for Cloud Run Service Account to Container Registry - Push images..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
    --role="roles/storage.admin"
    then
        echo "✅ IAM policy binding for Cloud Run Service Account to Container Registry - Push images added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud Run Service Account to Container Registry - Push images"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Cloud Run - Deploy (if deploying to Cloud Run)
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Cloud Run Service Account to Cloud Run - Deploy already exists"
else
    echo "Adding IAM policy binding for Cloud Run Service Account to Cloud Run - Deploy..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
    --role="roles/run.admin"
    then
        echo "✅ IAM policy binding for Cloud Run Service Account to Cloud Run - Deploy added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud Run Service Account to Cloud Run - Deploy"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Compute Engine - Admin access (full compute control)
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Cloud Build Service Account to Compute Engine - Admin access already exists"
else
    echo "Adding IAM policy binding for Cloud Build Service Account to Compute Engine - Admin access..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
    --role="roles/compute.admin"
    then
        echo "✅ IAM policy binding for Cloud Build Service Account to Compute Engine - Admin access added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud Build Service Account to Compute Engine - Admin access"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

echo "Compute Engine - Admin access added to the service account"

# Airflow Service Account
if gcloud iam service-accounts describe airflow-sa@$PROJECT_ID.iam.gserviceaccount.com &>/dev/null; then
    echo "✅ Airflow Service Account already exists: airflow-sa"
else
    echo "Creating Airflow Service Account..."
    if gcloud iam service-accounts create airflow-sa \
        --display-name="Airflow Service Account" \
        --description="Service account for Airflow DAGs" \
        --project=$PROJECT_ID; then
        echo "✅ Airflow Service Account created: airflow-sa"
    else
        echo "❌ ERROR: Failed to create Airflow service account"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

# Wait for all service accounts to be fully propagated in GCP before proceeding
echo ""
echo "⏳ Waiting 10 seconds for all service accounts to be fully propagated in GCP..."
sleep 10
echo "✅ Service account propagation wait complete"
echo ""

# Function to delete all existing keys for a service account
delete_all_service_account_keys() {
    local sa_name=$1
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if service account exists
    if ! gcloud iam service-accounts describe "$sa_email" --project=$PROJECT_ID &>/dev/null; then
        echo "⚠️  Service account $sa_name does not exist. Skipping key deletion."
        return 0
    fi
    
    # Get all key IDs (excluding the managed key which can't be deleted)
    local key_ids=$(gcloud iam service-accounts keys list --iam-account="$sa_email" --project=$PROJECT_ID --format="value(name)" --filter="keyType=USER_MANAGED" 2>/dev/null)
    
    if [ -z "$key_ids" ]; then
        echo "ℹ️  No existing keys found for $sa_name"
        return 0
    fi
    
    local key_count=$(echo "$key_ids" | wc -l | tr -d ' ')
    echo "Found $key_count existing key(s) for $sa_name. Deleting..."
    
    # Delete each key
    local deleted=0
    local failed=0
    while IFS= read -r key_id; do
        if [ -n "$key_id" ]; then
            if gcloud iam service-accounts keys delete "$key_id" --iam-account="$sa_email" --project=$PROJECT_ID --quiet 2>/dev/null; then
                deleted=$((deleted + 1))
            else
                failed=$((failed + 1))
                echo "   ⚠️  Failed to delete key: $key_id"
            fi
        fi
    done <<< "$key_ids"
    
    if [ $deleted -gt 0 ]; then
        echo "✅ Deleted $deleted key(s) for $sa_name"
    fi
    if [ $failed -gt 0 ]; then
        echo "⚠️  Failed to delete $failed key(s) for $sa_name"
    fi
    
    return 0
}

# Function to create or update service account key
create_service_account_key() {
    local sa_name=$1
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
    local key_file="config/${sa_name}.json"
    
    # Check if service account exists
    if ! gcloud iam service-accounts describe "$sa_email" --project=$PROJECT_ID &>/dev/null; then
        echo "❌ ERROR: Service account $sa_name does not exist. Skipping key creation."
        return 1
    fi
    
    # Remove existing key file if it exists
    if [ -f "$key_file" ]; then
        echo "Removing existing key file: $key_file"
        rm -f "$key_file"
    fi
    
    # Create the key
    echo "Creating service account key for $sa_name..."
    if gcloud iam service-accounts keys create "$key_file" \
        --iam-account="$sa_email" \
        --project=$PROJECT_ID 2>&1; then
        echo "✅ Service account key created: $key_file"
        return 0
    else
        local exit_code=$?
        echo "❌ ERROR: Failed to create service account key for $sa_name (exit code: $exit_code)"
        echo "   This might be due to:"
        echo "   - Service account not fully propagated (wait a few minutes and retry)"
        echo "   - Maximum key limit reached (10 keys per service account)"
        echo "   - Insufficient permissions"
        echo "   - Service account doesn't exist"
        return 1
    fi
}

# Download all service account keys (JSON) and save them in a folder called "config"
echo "--------------------------------"
echo "Managing service account keys..."
echo "--------------------------------"
mkdir -p config

# Delete all existing keys for each service account
echo ""
echo "Step 1: Deleting all existing service account keys..."
echo "---------------------------------------------------"
delete_all_service_account_keys "airflow-sa"
delete_all_service_account_keys "cloud-run-sa"
delete_all_service_account_keys "compute-engine-sa"
delete_all_service_account_keys "cloud-sql-sa"

# Wait a moment for deletions to propagate
echo ""
echo "⏳ Waiting 3 seconds for key deletions to propagate..."
sleep 3

# Create new keys for each service account
echo ""
echo "Step 2: Creating new service account keys..."
echo "--------------------------------------------"
create_service_account_key "airflow-sa"
create_service_account_key "cloud-run-sa"
create_service_account_key "compute-engine-sa"
create_service_account_key "cloud-sql-sa"

echo ""
echo "✅ Service account key management complete"
echo "   New keys are saved in the config/ folder"

echo "--------------------------------"
echo "Authenticating with GCP application default..."
gcloud auth application-default login
echo "Authenticated with GCP application default"
echo "--------------------------------"
echo "Done setting up the project"