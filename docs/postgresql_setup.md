## Installing PostgreSQL using Homebrew (macOS)

If you are using a Mac, the easiest way to install PostgreSQL is via [Homebrew](https://brew.sh/):

1. **Install Homebrew** (if needed):

   ```sh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install PostgreSQL:**

   ```sh
   brew install postgresql
   ```

3. **Start the PostgreSQL service:**

   ```sh
   brew services start postgresql
   ```

4. **(Apple Silicon only) Update your PATH for PostgreSQL 15 (if installed):**

   If you installed `postgresql@15` (Homebrew's default on some Apple Silicon Macs), you may need to update your shell profile so that the `psql` and related binaries are available:

   ```sh
   echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

   After this, you should be able to run `psql` and related commands from any terminal session.

    Or if you're on an Intel Mac, 
    ```sh
    echo 'export PATH="/usr/local/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
    source ~/.zshrc
    ```

4. **Verify installation and check version:**

   ```sh
   psql --version
   ```

5. **Connect to the default database:**

   ```sh
   psql postgres
   ```

You are now ready to create users, databases, and interact with PostgreSQL from your terminal.

For more Homebrew usage tips, see: https://formulae.brew.sh/formula/postgresql
