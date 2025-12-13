# DRY RUN (Individual Project Setup)

## Step 1

Please clone the repository from `git clone <REPO.GIT/REPO_URL>`.

## Step 2

Then the next step is to set the environment variables in your project, in two files -- `.env`.

### How to Get These Values (Step-by-Step Guide)

#### 1. **PROJECT_ID** - Your GCP Project ID

**Option A: Use an existing project**sh
# List all your GCP projects
gcloud projects list

# Output will show:
# PROJECT_ID              NAME                  PROJECT_NUMBER
# project-meridian-480018 Meridian Project     959890924234

# Copy the PROJECT_ID from the output**Option B: Create a new project**sh
# Create a new GCP project (project IDs must be globally unique)
gcloud projects create your-project-id

# Set it as the default project
gcloud config set project your-project-id

# Verify it's set
gcloud config get-value project**Option C: Get current active project**
gcloud config get-value project**Add to .env:**
PROJECT_ID=your-project-id-here---

#### 2. **REGION** - GCP Region

Choose a GCP region closest to your users. Common options:
- `us-central1` (Iowa, USA) - Recommended for US deployments
- `us-east1` (South Carolina, USA)
- `us-west1` (Oregon, USA)
- `europe-west1` (Belgium)
- `asia-southeast1` (Singapore)

**Add to .env:**
REGION=us-central1---

#### 3. **INSTANCE_CONNECTION_NAME** - Cloud SQL Connection String

**Format:** `project:region:instance-name`

**Option A: After creating Cloud SQL instance**
# Run the Cloud SQL setup script
./scripts/setup_cloud_sql.sh

# The script will output the INSTANCE_CONNECTION_NAME
# Example: project-meridian-480018:us-central1:meridian-db**Option B: Get from existing instance**
# List Cloud SQL instances
gcloud sql instances list --project=YOUR_PROJECT_ID

# Get connection name for a specific instance
gcloud sql instances describe INSTANCE_NAME \
  --project=YOUR_PROJECT_ID \
  --format='value(connectionName)'**Option C: From GCP Console**
1. Go to https://console.cloud.google.com/sql/instances
2. Click on your instance
3. Copy the "Connection name" (format: `project:region:instance-name`)

**Add to .env:**h
INSTANCE_CONNECTION_NAME=project-meridian-480018:us-central1:meridian-db---

#### 4. **DB_USER** - Database Username

Set this when creating your Cloud SQL instance. Choose a username (e.g., `meridian_user`, `postgres`, `admin`).

**Add to .env:**
DB_USER=meridian_user
---

#### 5. **DB_PASS** - Database Password

**Important:** Use a strong, secure password (at least 16 characters, mix of letters, numbers, symbols).

**Generate a secure password:**
# On macOS/Linux
openssl rand -base64 32

# Or use a password manager**Add to .env:**
DB_PASS=your-secure-password-here**Note:** Never commit this password to version control!

---

#### 6. **DB_NAME** - Database Name

Choose a name for your production database (e.g., `meridian_prod`, `meridian_production`).

**Add to .env:**sh
DB_NAME=meridian_prod**Optional:** If you want to use a different name for production:ash
PROD_DB_NAME=meridian_prod---

#### 7. **OPENAI_API_KEY** - Your OpenAI API Key

1. **Sign up/Login** to OpenAI: https://platform.openai.com/
2. **Go to API Keys**: https://platform.openai.com/api-keys
3. **Click "Create new secret key"**
4. **Copy the key** (starts with `sk-`)
5. **Save it immediately** - you won't be able to see it again!

**Add to .env:**
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx**Security Note:** Keep this key secret! Never commit it to version control.

---

#### 8. **NEXT_PUBLIC_GOOGLE_CLIENT_ID** - Google OAuth Client ID

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Select your project** (or create one)
3. **Enable Google+ API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google+ API" or "Identity Toolkit API"
   - Click "Enable"
4. **Create OAuth Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - If prompted, configure OAuth consent screen first:
     - User Type: External (or Internal if using Google Workspace)
     - App name: "Meridian Trading System"
     - Support email: Your email
     - Add scopes: `email`, `profile`, `openid`
     - Save and continue
   - Application type: **Web application**
   - Name: "Meridian Frontend"
   - Authorized JavaScript origins:
     - `http://localhost:3000` (for local development)
     - `https://your-frontend-url.run.app` (for production)
   - Authorized redirect URIs:
     - `http://localhost:3000/api/auth/callback/google` (for local)
     - `https://your-frontend-url.run.app/api/auth/callback/google` (for production)
   - Click "Create"
5. **Copy the Client ID** (ends with `.apps.googleusercontent.com`)

**Add to .env:**
NEXT_PUBLIC_GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
---

#### 9. **GOOGLE_CLIENT_SECRET** - Google OAuth Client Secret

1. **From the same OAuth credentials page** (see step 8 above)
2. **Click on the OAuth client you just created**
3. **Copy the "Client secret"** (starts with `GOCSPX-`)

**Add to .env:**
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx**Security Note:** Keep this secret! Never commit it to version control.

---

### Quick Setup Checklist

- [ ] Install gcloud CLI (see [Installation Guide](#gcloud-installation))
- [ ] Login to gcloud: `gcloud auth login`
- [ ] Set PROJECT_ID in `.env`
- [ ] Set REGION in `.env`
- [ ] Get OPENAI_API_KEY from https://platform.openai.com/api-keys
- [ ] Create Google OAuth credentials and add to `.env`
- [ ] Run `./scripts/setup_cloud_sql.sh` to get INSTANCE_CONNECTION_NAME
- [ ] Set DB_USER, DB_PASS, DB_NAME in `.env`
- [ ] Verify all variables are set: `cat .env`

---

### Gcloud Installation

If you don't have gcloud CLI installed:

**macOS (using Homebrew):**h
brew install --cask google-cloud-sdk
source ~/.zshrc**Linux:**
curl https://sdk.cloud.google.com | bash
exec -l $SHELL**Windows:**
- Download from: https://cloud.google.com/sdk/docs/install-sdk#windows

**Verify installation:**sh
gcloud --version
gcloud auth login---

### Complete Example `.env` File

# ============================================
# GCP Configuration
# ============================================
PROJECT_ID=project-meridian-480018
REGION=us-central1

# ============================================
# Cloud SQL Database
# ============================================
INSTANCE_CONNECTION_NAME=project-meridian-480018:us-central1:meridian-db
DB_USER=meridian_user
DB_PASS=your-secure-password-here-min-16-chars
DB_NAME=meridian_prod

# ============================================
# OpenAI API
# ============================================
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ============================================
# Google OAuth
# ============================================
NEXT_PUBLIC_GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx

# ============================================
# Service URLs (Auto-generated during deployment)
# ============================================
# These will be automatically added by ./scripts/deploy_to_cloud_run.sh:
# AGENTS_SERVICE_URL=https://meridian-agents-xxx-uc.a.run.app
# BACKEND_URL=https://meridian-backend-xxx.us-central1.run.app
# FRONTEND_URL=https://meridian-frontend-xxx.us-central1.run.app---

### Notes

- **Never commit your `.env` file** to version control - it contains sensitive credentials
- The deployment script (`./scripts/deploy_to_cloud_run.sh`) will automatically add service URLs to your `.env` file:
  - `AGENTS_SERVICE_URL` (generated after agents service deployment)
  - `BACKEND_URL` (generated after backend service deployment)
  - `FRONTEND_URL` (generated after frontend service deployment)
- If `GOOGLE_CLIENT_ID` is not set, the script will use `NEXT_PUBLIC_GOOGLE_CLIENT_ID` as a fallback
- If `PROD_DB_NAME` is set, it will be used instead of `DB_NAME` for production deployment

## Step 3

Congrats! You're really close to getting this done

# Step 1: Setup GCP project and service accounts
./scripts/setup_gcp.sh

# Step 2: Create Cloud SQL database instance
./scripts/setup_cloud_sql.sh

# Step 3: Deploy everything to Cloud Run
./scripts/deploy_to_cloud_run.sh

NOTE: If you want to run this thing Locally, run this ./scripts/docker_deployment.sh. Please make sure you have enough free memory (~8GB) in Docker and it is running (Docker Engine needs to be running).
