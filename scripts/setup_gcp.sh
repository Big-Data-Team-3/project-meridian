#! /bin/bash

# This script is used to setup the GCP project and other resources required for the project.

# Authenticate with GCP
gcloud auth login

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

# Add IAM policy binding for Compute Engine Service Account to Cloud SQL - Client access (for PostgreSQL)
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Compute Engine Service Account to Cloud SQL - Client access (for PostgreSQL) already exists"
else
    echo "Adding IAM policy binding for Compute Engine Service Account to Cloud SQL - Client access (for PostgreSQL)..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"
    then
        echo "✅ IAM policy binding for Compute Engine Service Account to Cloud SQL - Client access (for PostgreSQL) added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Compute Engine Service Account to Cloud SQL - Client access (for PostgreSQL)"
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

# Cloud SQL - Client access
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Cloud Run Service Account to Cloud SQL - Client access (for PostgreSQL) already exists"
else
    echo "Adding IAM policy binding for Cloud Run Service Account to Cloud SQL - Client access (for PostgreSQL)..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"
    then
        echo "✅ IAM policy binding for Cloud Run Service Account to Cloud SQL - Client access (for PostgreSQL) added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud Run Service Account to Cloud SQL - Client access (for PostgreSQL)"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

echo "Cloud SQL - Client access added to the service account"

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
if gcloud projects describe $PROJECT_ID --format="value(projectNumber)" | grep -q $PROJECT_NUMBER; then
    echo "✅ Project number already exists"
else
    echo "Getting project number..."
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    echo "✅ Project number: $PROJECT_NUMBER"
fi
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

# Compute Engine - Create/update VMs (if deploying to Compute Engine)
if gcloud projects get-iam-policy $PROJECT_ID --format=yaml | grep -q "cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com"; then
    echo "✅ IAM policy binding for Cloud Run Service Account to Compute Engine - Create/update VMs already exists"
else
    echo "Adding IAM policy binding for Cloud Run Service Account to Compute Engine - Create/update VMs..."
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
    --role="roles/compute.instanceAdmin.v1"
    then
        echo "✅ IAM policy binding for Cloud Run Service Account to Compute Engine - Create/update VMs added"
    else
        echo "❌ ERROR: Failed to add IAM policy binding for Cloud Run Service Account to Compute Engine - Create/update VMs"
        echo "   Please check your permissions and try again"
        exit 1
    fi
fi

echo "Compute Engine - Create/update VMs added to the service account"

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

# Download all service account keys (JSON) and save them in a folder called "config"
mkdir -p config
gcloud iam service-accounts keys create config/airflow-sa.json --iam-account airflow-sa@$PROJECT_ID.iam.gserviceaccount.com --project=$PROJECT_ID
gcloud iam service-accounts keys create config/cloud-run-sa.json --iam-account cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com --project=$PROJECT_ID
gcloud iam service-accounts keys create config/compute-engine-sa.json --iam-account compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com --project=$PROJECT_ID

echo "Service account keys downloaded and saved to config folder"

echo "--------------------------------"
echo "Done setting up the project"