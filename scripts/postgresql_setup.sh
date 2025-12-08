#! /bin/bash

# This script is used to setup the PostgreSQL database for the project.

# Install PostgreSQL using Homebrew
brew install postgresql@15

# Start the PostgreSQL service
brew services start postgresql@15

# For Apple Silicon Macs, you may need to update your PATH for PostgreSQL 15 (Comment if you're on an Intel Mac)
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# For Intel Macs, you may need to update your PATH for PostgreSQL 15 (Uncomment if you're on an Intel Mac)
# echo 'export PATH="/usr/local/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
# source ~/.zshrc

# Verify the installation and check the version
psql --version

# Create the database for the project
if ! psql -l | grep -q meridian_financial_db; then
    createdb meridian_financial_db
else
    echo "Database already exists: meridian_financial_db"
fi

# Verify the database was created
psql -l | grep meridian_financial_db

# Create the user for the project
if ! psql -l | grep -q meridian_financial_user; then
    createuser -s meridian_financial_user
else
    echo "User already exists: meridian_financial_user"
fi

echo "To connect to the database, run: psql meridian_financial_db"