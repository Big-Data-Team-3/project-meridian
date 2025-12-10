# Cloud SQL Client Testing Guide

## Required Environment Variables

To test the Cloud SQL client, you need to set the following environment variables:

### Database Configuration

```bash
# Cloud SQL instance connection name (format: project:region:instance)
export DB_HOST="project-meridian-480018:us-central1:free-trial-first-project"

# Database user credentials
export DB_USER="postgres"
export DB_PASSWORD="team3_admin@meridian"

# Database name
export DB_NAME="postgres"

# Database type (optional, defaults to postgresql)
export DB_TYPE="postgresql"
```

### GCP Authentication

```bash
# Path to GCP service account JSON file
# This file must have Cloud SQL Client permissions
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account.json"
```

**Example paths:**
- `/Users/smatcha/Documents/BigData/project-meridian/config/cloud-run-sa.json`
- `/Users/smatcha/Documents/BigData/project-meridian/config/compute-engine-sa.json`

## Setting Up Environment Variables

### Option 1: Export in Terminal

```bash
export DB_HOST="project-meridian-480018:us-central1:free-trial-first-project"
export DB_USER="postgres"
export DB_PASSWORD="team3_admin@meridian"
export DB_NAME="postgres"
export GOOGLE_APPLICATION_CREDENTIALS="/Users/smatcha/Documents/BigData/project-meridian/config/cloud-run-sa.json"
```

### Option 2: Use .env File

Create or update `.env` file in project root:

```bash
DB_HOST=project-meridian-480018:us-central1:free-trial-first-project
DB_USER=postgres
DB_PASSWORD=team3_admin@meridian
DB_NAME=postgres
DB_TYPE=postgresql
GOOGLE_APPLICATION_CREDENTIALS=/Users/smatcha/Documents/BigData/project-meridian/config/cloud-run-sa.json
```

Then load it:
```bash
export $(cat .env | grep -v '^#' | xargs)
```

## Running Tests

### Test 1: Basic Connection Test

```bash
cd /Users/smatcha/Documents/BigData/project-meridian
python meridian-backend/database/test_connection.py
```

This tests:
- Cloud SQL client initialization
- Basic database connection
- Database name verification
- PostgreSQL version check

### Test 2: Comprehensive CRUD Test

```bash
cd /Users/smatcha/Documents/BigData/project-meridian
python meridian-backend/database/test_crud_operations.py
```

This tests:
1. ✅ Basic connection
2. ✅ Table existence (threads, messages)
3. ✅ CREATE operation (INSERT thread)
4. ✅ READ operation (SELECT thread)
5. ✅ UPDATE operation (UPDATE thread)
6. ✅ DELETE operation (DELETE thread)
7. ✅ Message operations (INSERT, SELECT messages)

## Expected Output

### Successful Test Output

```
🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 
CLOUD SQL CLIENT COMPREHENSIVE TEST SUITE
🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 🔍 

============================================================
ENVIRONMENT VARIABLES CHECK
============================================================
✅ DB_HOST: project-meridian-480018:us-central1:free-trial-first-project
✅ DB_USER: postgres
✅ DB_PASSWORD: **********
✅ DB_NAME: postgres
✅ GOOGLE_APPLICATION_CREDENTIALS: /path/to/credentials.json (file exists)

✅ All required environment variables are set

============================================================
TEST 1: Basic Connection Test
============================================================
✅ Cloud SQL client initialized
✅ Connection successful: SELECT 1 = 1
✅ Connected to database: postgres
✅ PostgreSQL version: PostgreSQL 15.x

============================================================
TEST 2: Table Existence Check
============================================================
✅ Threads table exists: True
✅ Messages table exists: True

... (more tests)

============================================================
TEST SUMMARY
============================================================
✅ PASS - Connection
✅ PASS - Table Existence
✅ PASS - CREATE
✅ PASS - READ
✅ PASS - UPDATE
✅ PASS - DELETE
✅ PASS - Messages

============================================================
Total: 7/7 tests passed
============================================================

🎉 All tests passed! Cloud SQL client is working correctly.
```

## Troubleshooting

### Error: "Your default credentials were not found"

**Solution:** Ensure `GOOGLE_APPLICATION_CREDENTIALS` is set and points to a valid service account JSON file.

```bash
# Check if variable is set
echo $GOOGLE_APPLICATION_CREDENTIALS

# Check if file exists
ls -la $GOOGLE_APPLICATION_CREDENTIALS
```

### Error: "Missing required database configuration"

**Solution:** Ensure all database environment variables are set:
- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

### Error: "Tables don't exist"

**Solution:** Run database migrations first:

```bash
python meridian-backend/database/run_migrations.py
```

### Error: "Connection refused" or "Network error"

**Solution:** 
1. Verify Cloud SQL instance is running
2. Check that your IP is authorized in Cloud SQL instance settings
3. Verify the connection name format: `project:region:instance`

## Service Account Permissions

Your service account JSON file must have the following IAM roles:
- `roles/cloudsql.client` - To connect to Cloud SQL instances
- (Optional) `roles/cloudsql.admin` - For full database management

## Next Steps

Once all tests pass:
1. ✅ Cloud SQL client is working correctly
2. ✅ Database connection is established
3. ✅ CRUD operations are functional
4. ✅ Ready to integrate with backend APIs

You can now proceed with testing the backend API endpoints that use the Cloud SQL client.

