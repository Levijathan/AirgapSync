# Airgap Sync MariaDB Integration Script

# Description:
This script automates the process of adding feeds from the AirgapIntel script into your MISP MariaDB instance.
The AirgapIntel script includes all of the default feeds from the MISP site.
It scans a specified directory for new feed folders, determines their format, and adds them to the MISP MariaDB database,
ensuring that duplicates are not inserted. The script also validates database connections, prompts users for a 
network path, and provides logging for troubleshooting.

# Features:
- Scans for new feed directories.
- Detects MISP, CSV, or plain-text feed formats.
- Ensures feeds are not duplicated in the database.
- Inserts new feeds into the MISP database with the appropriate metadata.
- Configurable database connection timeout to prevent hanging due to incorrect credentials.
- User interaction for feed selection and network path configuration.

# Usage:
Run the script and follow the prompts to integrate feeds into the database.

