# GCP Setup Command-Level Documentation

This document provides detailed command-level documentation for the GCP setup process used in the Meridian project. All commands are extracted from `scripts/setup_gcp.sh`.

## Prerequisites

Before running the setup script, ensure you have:

1. **Google Cloud SDK installed** (`gcloud` CLI)
2. **Authenticated with GCP**:
   ```bash
   gcloud auth login
   ```
3. **A `.env` file** in the project root containing:
   ```
   PROJECT_ID=your-project-id-here
   ```

## 1. Project Setup

### Get Project ID from Environment File

```bash
PROJECT_ID=$(grep "^PROJECT_ID=" .env | cut -d '=' -f 2 | tr -d '"' | tr -d "'" | tr -d '[' | tr -d ']' | xargs)
```

**Purpose:** Extracts the project ID from the `.env` file, removing any quotes, brackets, or whitespace.

**Parameters:**
- `grep "^PROJECT_ID=" .env`: Finds the line starting with PROJECT_ID=
- `cut -d '=' -f 2`: Gets the value after the equals sign
- `tr -d '"' | tr -d "'" | tr -d '[' | tr -d ']'`: Removes quotes and brackets
- `xargs`: Trims whitespace

### Check/Create Project

```bash
if [ -z "$PROJECT_ID" ]; then
    echo "PROJECT_ID is not set"
    PROJECT_ID="meridian-project"
fi
```

**Purpose:** Sets a default project ID if none is provided.

**Parameters:**
- `$PROJECT_ID`: The extracted project ID
- `"meridian-project"`: Default fallback project name

### Verify Project Existence

```bash
if gcloud projects list --filter="projectId=$PROJECT_ID" --format="get(projectId)" | grep -q $PROJECT_ID; then
    echo "Project $PROJECT_ID already exists"
else
    echo "Creating project $PROJECT_ID"
    gcloud projects create $PROJECT_ID --set-as-default
fi
```

**Purpose:** Checks if the project exists, creates it if it doesn't.

**Commands:**
- `gcloud projects list --filter="projectId=$PROJECT_ID"`: Lists projects matching the ID
- `--format="get(projectId)"`: Outputs only the project ID
- `gcloud projects create $PROJECT_ID --set-as-default`: Creates project and sets as default

## 2. API Enablement

### Essential APIs

```bash
gcloud services enable compute.googleapis.com              # Compute Engine
gcloud services enable storage-component.googleapis.com     # Cloud Storage (GCS)
gcloud services enable sqladmin.googleapis.com              # Cloud SQL
```

**Purpose:** Enables core GCP APIs required for the project.

**APIs Enabled:**
- `compute.googleapis.com`: Compute Engine API (VMs)
- `storage-component.googleapis.com`: Cloud Storage API (GCS buckets)
- `sqladmin.googleapis.com`: Cloud SQL Admin API (PostgreSQL)

### Optional but Recommended APIs

```bash
gcloud services enable run.googleapis.com                   # Cloud Run (if using)
gcloud services enable containerregistry.googleapis.com      # Container Registry
gcloud services enable cloudbuild.googleapis.com             # Cloud Build (for CI/CD)
```

**Purpose:** Enables additional APIs for deployment and CI/CD.

**APIs Enabled:**
- `run.googleapis.com`: Cloud Run API (serverless containers)
- `containerregistry.googleapis.com`: Container Registry API (Docker images)
- `cloudbuild.googleapis.com`: Cloud Build API (automated builds)

### Monitoring and Logging APIs

```bash
gcloud services enable logging.googleapis.com                # Cloud Logging
gcloud services enable monitoring.googleapis.com            # Cloud Monitoring
```

**Purpose:** Enables observability services for debugging and monitoring.

**APIs Enabled:**
- `logging.googleapis.com`: Cloud Logging API (logs collection)
- `monitoring.googleapis.com`: Cloud Monitoring API (metrics and alerts)

### Verify Enabled APIs

```bash
gcloud services list --enabled --format="get(name)"
```

**Purpose:** Lists all enabled APIs in the current project.

**Parameters:**
- `--enabled`: Shows only enabled services
- `--format="get(name)"`: Outputs only the service names

## 3. Service Account Creation

### Compute Engine Service Account

#### Check Existence
```bash
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
        exit 1
    fi
fi
```

**Purpose:** Creates a service account for Compute Engine VMs.

**Parameters:**
- `compute-engine-sa`: Service account name
- `--display-name`: Human-readable name
- `--description`: Purpose description
- `--project`: Target project

### Cloud Run Service Account

```bash
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
        exit 1
    fi
    echo "✅ Service Account for Cloud Run created: cloud-run-sa"
fi

# Verify service account exists
if ! gcloud iam service-accounts describe $CLOUD_RUN_SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    echo "❌ ERROR: Cloud Run service account does not exist. Cannot add IAM bindings."
    exit 1
fi
```

**Purpose:** Creates and verifies a service account for Cloud Run services.

**Parameters:**
- `cloud-run-sa`: Service account name
- `--display-name`: Human-readable name
- `--description`: Purpose description
- `--project`: Target project

### Airflow Service Account

```bash
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
        exit 1
    fi
fi
```

**Purpose:** Creates a service account for Airflow orchestration.

**Parameters:**
- `airflow-sa`: Service account name
- `--display-name`: Human-readable name
- `--description`: Purpose description
- `--project`: Target project

## 4. IAM Permission Binding

### Cloud Storage (GCS) Access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

**Purpose:** Grants read/write access to Cloud Storage buckets.

**Parameters:**
- `$PROJECT_ID`: Target project
- `--member`: Service account email
- `--role="roles/storage.objectAdmin"`: Storage Object Admin role

### Cloud SQL Client Access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"
```

**Purpose:** Allows connection to Cloud SQL databases.

**Parameters:**
- `$PROJECT_ID`: Target project
- `--member`: Service account email
- `--role="roles/cloudsql.client"`: Cloud SQL Client role

### Logging Permissions

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"
```

**Purpose:** Enables writing logs to Cloud Logging.

**Parameters:**
- `$PROJECT_ID`: Target project
- `--member`: Service account email
- `--role="roles/logging.logWriter"`: Logs Writer role

### Monitoring Permissions

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.metricWriter"
```

**Purpose:** Enables writing metrics to Cloud Monitoring.

**Parameters:**
- `$PROJECT_ID`: Target project
- `--member`: Service account email
- `--role="roles/monitoring.metricWriter"`: Monitoring Metric Writer role

## 5. Cloud Build Permissions

### Get Project Number

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
```

**Purpose:** Gets the numeric project ID for Cloud Build service account.

**Parameters:**
- `$PROJECT_ID`: Project ID
- `--format="value(projectNumber)"`: Outputs only the project number

### Container Registry Access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
    --role="roles/storage.admin"
```

**Purpose:** Grants access to push Docker images to Container Registry.

**Parameters:**
- `$PROJECT_ID`: Target project
- `--member`: Cloud Build service account
- `--role="roles/storage.admin"`: Storage Admin role

### Cloud Run Deployment Access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
    --role="roles/run.admin"
```

**Purpose:** Allows Cloud Build to deploy to Cloud Run.

**Parameters:**
- `$PROJECT_ID`: Target project
- `--member`: Cloud Build service account
- `--role="roles/run.admin"`: Cloud Run Admin role

### Compute Engine Deployment Access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
    --role="roles/compute.instanceAdmin.v1"
```

**Purpose:** Allows Cloud Build to create/update Compute Engine VMs.

**Parameters:**
- `$PROJECT_ID`: Target project
- `--member`: Cloud Build service account
- `--role="roles/compute.instanceAdmin.v1"`: Compute Instance Admin role

## 6. Service Account Key Creation

### Create Keys Directory

```bash
mkdir -p config
```

**Purpose:** Creates the config directory for storing service account keys.

### Download Service Account Keys

```bash
gcloud iam service-accounts keys create config/airflow-sa.json \
    --iam-account airflow-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --project=$PROJECT_ID

gcloud iam service-accounts keys create config/cloud-run-sa.json \
    --iam-account cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --project=$PROJECT_ID

gcloud iam service-accounts keys create config/compute-engine-sa.json \
    --iam-account compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --project=$PROJECT_ID
```

**Purpose:** Downloads JSON keys for each service account for local authentication.

**Parameters:**
- `config/{service-account}.json`: Output file path
- `--iam-account`: Service account email
- `--project`: Target project

## Service Accounts Created

The setup script creates the following service accounts:

| Service Account | Purpose | Key File |
|----------------|---------|----------|
| `compute-engine-sa` | Compute Engine VMs (Airflow, Chroma, FastAPI) | `config/compute-engine-sa.json` |
| `cloud-run-sa` | Cloud Run services | `config/cloud-run-sa.json` |
| `airflow-sa` | Airflow DAGs and orchestration | `config/airflow-sa.json` |

## IAM Roles Assigned

### Compute Engine Service Account Roles
- `roles/storage.objectAdmin`: Read/write Cloud Storage objects
- `roles/cloudsql.client`: Connect to Cloud SQL databases
- `roles/logging.logWriter`: Write logs to Cloud Logging
- `roles/monitoring.metricWriter`: Write metrics to Cloud Monitoring

### Cloud Run Service Account Roles
- `roles/storage.objectAdmin`: Read/write Cloud Storage objects
- `roles/cloudsql.client`: Connect to Cloud SQL databases
- `roles/logging.logWriter`: Write logs to Cloud Logging

### Cloud Build Service Account Roles
- `roles/storage.admin`: Push images to Container Registry
- `roles/run.admin`: Deploy to Cloud Run
- `roles/compute.instanceAdmin.v1`: Create/update Compute Engine VMs

## Security Notes

1. **Service account keys are sensitive**: Never commit them to version control
2. **Use .gitignore**: Ensure `config/*.json` is in `.gitignore`
3. **Principle of least privilege**: Only necessary permissions are granted
4. **Key rotation**: Regularly rotate service account keys
5. **Environment-specific keys**: Consider different keys for dev/staging/prod

## Troubleshooting

### Common Errors

1. **"API not enabled"**: Run `gcloud services enable [API_NAME]`
2. **"Permission denied"**: Ensure you have Project Editor/Owner role
3. **"Service account already exists"**: The script handles this gracefully
4. **"Project not found"**: Verify PROJECT_ID in `.env` file

### Verification Commands

```bash
# Check enabled APIs
gcloud services list --enabled

# List service accounts
gcloud iam service-accounts list

# Check IAM policy for a service account
gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:serviceAccount:compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com"

# Verify service account key
gcloud iam service-accounts keys list --iam-account compute-engine-sa@$PROJECT_ID.iam.gserviceaccount.com
```

## Next Steps

After running the setup script successfully:

1. **Configure authentication** in your applications using the downloaded JSON keys
2. **Create infrastructure** (VMs, databases, buckets) using the service accounts
3. **Deploy services** (Airflow, FastAPI, Chroma) to Compute Engine
4. **Set up CI/CD** pipelines using Cloud Build

## Cost Considerations

- **Free tier**: Many GCP services have generous free tiers
- **API enablement**: No cost for enabling APIs
- **Service accounts**: No cost for service accounts or IAM
- **Monitoring**: Cloud Logging and Monitoring have free tiers
- **Storage**: Cloud Storage has free tier (5GB)

The setup is designed to minimize costs while providing all necessary infrastructure for the Meridian project.
