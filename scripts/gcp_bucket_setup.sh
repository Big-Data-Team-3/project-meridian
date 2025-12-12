#! /bin/bash

# This script is used to setup the GCP bucket for the project.

# Get the project ID from the .env file, handling quotes and whitespace for the project ID
PROJECT_ID=$(grep "^PROJECT_ID=" .env | cut -d '=' -f 2 | tr -d '"' | tr -d "'" | tr -d '[' | tr -d ']' | xargs)

# Create a new bucket
echo "--------------------------------"
echo "Creating bucket: meridian-raw-data"
# Check if bucket already exists before creating; handle errors if creation fails
if ! gcloud storage buckets list --project=$PROJECT_ID | grep -q "meridian-raw-data"; then
    echo "Creating bucket: meridian-raw-data"
    if gcloud storage buckets create gs://meridian-raw-data \
        --location=us-central1 \
        --project=$PROJECT_ID; then
        echo "✅ Bucket created: meridian-raw-data"
    else
        echo "❌ ERROR: Failed to create bucket: meridian-raw-data"
        echo "   Please check your permissions, internet connection, and billing status"
        exit 1
    fi
else
    echo "Bucket already exists: meridian-raw-data"
fi

echo "--------------------------------"
echo "Creating objects in the bucket..."
# Create objects in the bucket

# Create the bucket first (if it doesn't exist)
# Check if bucket already exists before creating
if gsutil ls -b gs://meridian-raw-data &>/dev/null; then
    echo "✅ Bucket already exists: meridian-raw-data"
else
    echo "Creating bucket: meridian-raw-data"
    if gsutil mb -p $PROJECT_ID -c standard -l us-central1 gs://meridian-raw-data; then
        echo "✅ Bucket created: meridian-raw-data"
    else
        echo "❌ ERROR: Failed to create bucket: meridian-raw-data"
        echo "   Please check your permissions, internet connection, and billing status"
        exit 1
    fi
fi

# Then create folders
echo "Creating folder structure..."

# Create main raw_data folder
if gcloud storage cp /dev/null gs://meridian-raw-data/raw_data/ --project=$PROJECT_ID 2>/dev/null; then
    echo "✅ Created folder: raw_data/"
else
    echo "⚠️  Folder may already exist: raw_data/"
fi

# Create subfolders
if gcloud storage cp /dev/null gs://meridian-raw-data/raw_data/fred/ --project=$PROJECT_ID 2>/dev/null; then
    echo "✅ Created folder: raw_data/fred/"
else
    echo "⚠️  Folder may already exist: raw_data/fred/"
fi

if gcloud storage cp /dev/null gs://meridian-raw-data/raw_data/sec/ --project=$PROJECT_ID 2>/dev/null; then
    echo "✅ Created folder: raw_data/sec/"
else
    echo "⚠️  Folder may already exist: raw_data/sec/"
fi

if gcloud storage cp /dev/null gs://meridian-raw-data/raw_data/yfinance/ --project=$PROJECT_ID 2>/dev/null; then
    echo "✅ Created folder: raw_data/yfinance/"
else
    echo "⚠️  Folder may already exist: raw_data/yfinance/"
fi

echo "✅ Folder structure setup complete!"
echo "--------------------------------"
echo "Creating Embeddings Bucket as backup for embeddings..."
if gsutil ls -b gs://meridian-embeddings &>/dev/null; then
    echo "✅ Bucket already exists: meridian-embeddings"
else
    echo "Creating bucket: meridian-embeddings"
    if gsutil mb -p $PROJECT_ID -c standard -l us-central1 gs://meridian-embeddings; then
        echo "✅ Bucket created: meridian-embeddings"
    else
        echo "❌ ERROR: Failed to create bucket: meridian-embeddings"
        echo "   Please check your permissions, internet connection, and billing status"
        exit 1
    fi
fi
echo "Creating additional folder structure: documents/, metadata/, backups/..."

# Create 'documents/' folder
if gcloud storage cp /dev/null gs://meridian-embeddings/documents/ --project=$PROJECT_ID 2>/dev/null; then
    echo "✅ Created folder: documents/"
else
    echo "⚠️  Folder may already exist: documents/"
fi

# Create 'metadata/' folder
if gcloud storage cp /dev/null gs://meridian-embeddings/metadata/ --project=$PROJECT_ID 2>/dev/null; then
    echo "✅ Created folder: metadata/"
else
    echo "⚠️  Folder may already exist: metadata/"
fi

# Create 'backups/' folder
if gcloud storage cp /dev/null gs://meridian-embeddings/backups/ --project=$PROJECT_ID 2>/dev/null; then
    echo "✅ Created folder: backups/"
else
    echo "⚠️  Folder may already exist: backups/"
fi
