"""
Airgap Sync MariaDB Integration Script

Author: James Levija
Date: 2025

Description:
This script automates the process of integrating air-gapped intelligence feeds into a MariaDB-based MISP instance.
It scans a specified directory for new feed folders, determines their format, and adds them to the MISP database,
ensuring that duplicates are not inserted. The script also validates database connections, prompts users for a 
network path, and provides logging for troubleshooting.

Features:
- Scans for new feed directories.
- Detects MISP, CSV, or text feed formats.
- Ensures feeds are not duplicated in the database.
- Inserts new feeds into the MISP database with the appropriate metadata.
- Configurable database connection timeout to prevent hanging due to incorrect credentials.
- User interaction for feed selection and network path configuration.

Usage:
Run the script and follow the prompts to integrate feeds into the database.

"""

import os
import sys
import json
import mariadb
from urllib.parse import urljoin

# --- Configuration ---
FEEDS_BASE_DIR = "AirgapIntel_Feeds"  # Base directory where feed folders are located
DEFAULT_FEED_FORMAT = "text"  # Default MISP feed format if not explicitly detected
DATABASE_CONFIG = {
    "host": "your_misp_db_host",  # Replace with your MariaDB host
    "user": "your_misp_db_user",  # Replace with your MISP database user
    "password": "your_misp_db_password",  # Replace with your MISP database password
    "database": "misp",  # Replace with your MISP database name
    "connect_timeout": 5  # Set timeout to 5 seconds
}
# --- End Configuration ---

def ascii_art():
    """Prints ASCII art for Airgap Sync."""
    print(r"""
 _______ _________ _______  _______  _______  _______    _______           _        _______ 
(  ___  )\__   __/(  ____ )(  ____ \(  ___  )(  ____ )  (  ____ \|\     /|( (    /|(  ____ \
| (   ) |   ) (   | (    )|| (    \/| (   ) || (    )|  | (    \/( \   / )|  \  ( || (    \/
| (___) |   | |   | (____)|| |      | (___) || (____)|  | (_____  \ (_) / |   \ | || |      
|  ___  |   | |   |     __)| | ____ |  ___  ||  _____)  (_____  )  \   /  | (\ \) || |      
| (   ) |   | |   | (\ (   | | \_  )| (   ) || (              ) |   ) (   | | \   || |      
| )   ( |___) (___| ) \ \__| (___) || )   ( || )        /\____) |   | |   | )  \  || (____/\
|/     \|\_______/|/   \__/(_______)|/     \||/         \_______)   \_/   |/    )_)(_______/
    """)


def test_database_connection(db_config):
    """Tests the database connection using the provided configuration."""
    try:
        with mariadb.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")  # Simple test query
                result = cursor.fetchone()
                return result[0] == 1, None  # Connection successful, no error message
    except mariadb.Error as e:
        return False, f"[ERROR] Database connection test failed!\nMariaDB Error: {e}"  # Improved error message
    except TimeoutError:
        return False, "[ERROR] Database connection timed out! Check credentials and network connectivity."


def find_new_feed_folders(base_dir, db_config):
    """Finds new feed folders that are not in the database."""
    new_feed_folders = []
    if not os.path.isdir(base_dir):
        print(f"Error: Base feed directory '{base_dir}' not found.")
        return new_feed_folders

    try:
        with mariadb.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                for folder_name in os.listdir(base_dir):
                    folder_path = os.path.join(base_dir, folder_name)
                    if not os.path.isdir(folder_path):
                        continue
                    
                    manifest_path = os.path.join(folder_path, "manifest.json")
                    csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".csv")]
                    data_files = [f for f in os.listdir(folder_path) if f != "manifest.json"]
                    
                    cursor.execute("SELECT id FROM feeds WHERE name = ?", (folder_name,))
                    existing_feed = cursor.fetchone()
                    if existing_feed:
                        print(f"[INFO] Feed folder '{folder_name}' already exists in the database (ID: {existing_feed[0]}). Skipping.")
                        continue
                    
                    source_format = "misp" if os.path.exists(manifest_path) else "csv" if csv_files else DEFAULT_FEED_FORMAT
                    
                    if data_files or os.path.exists(manifest_path):
                        new_feed_folders.append({
                            "folder_name": folder_name,
                            "folder_path": folder_path,
                            "data_files": data_files or [os.path.basename(manifest_path)],
                            "source_format": source_format
                        })
    except mariadb.Error as e:
        print(f"Error checking for existing feeds in database: {e}")
    
    return new_feed_folders


def add_feed_to_db(feed_name, feed_url, source_format, db_config):
    """Adds a new feed to the MISP database."""
    try:
        with mariadb.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM feeds WHERE name = ? OR url = ?", (feed_name, feed_url))
                if cursor.fetchone():
                    print(f"[INFO] Feed '{feed_name}' already exists. Skipping.")
                    return
                
                query = """
                INSERT INTO feeds (name, provider, url, rules, enabled, distribution, sharing_group_id, tag_id, 
                                  `default`, source_format, fixed_event, delta_merge, event_id, publish, override_ids, 
                                  settings, input_source, delete_local_file, lookup_visible, headers, caching_enabled, 
                                  force_to_ids, orgc_id, tag_collection_id)
                VALUES (?, ?, ?, NULL, 1, 0, 0, 0, 0, ?, 0, 0, 0, 1, 0, 0, 'network', 0, 1, NULL, 1, 0, 1, 0)
                """  # `default` is wrapped in backticks since it's a reserved word
                
                cursor.execute(query, (feed_name, feed_name, feed_url, source_format))
                conn.commit()
                print(f"[INFO] Feed '{feed_name}' ({source_format} format) added to MISP database with URL: {feed_url}")
    except mariadb.Error as e:
        print(f"Error adding feed '{feed_name}' to database: {e}")


def main():
    ascii_art()
    
    success, error_message = test_database_connection(DATABASE_CONFIG)
    if not success:
        print(error_message)
        sys.exit(1)
    print("[SUCCESS] Database connection test successful!")
    
    if input("Continue with feed import to MISP database? (yes/no): ").lower() != "yes":
        sys.exit(0)
    
    new_folders = find_new_feed_folders(FEEDS_BASE_DIR, DATABASE_CONFIG)
    if not new_folders:
        print("No new feed folders found. Exiting.")
        return
    
    print("\n--- New feed folders found: ---")
    for folder in new_folders:
        print(f"- {folder['folder_name']} (Format: {folder['source_format']})")
    
    if input("\nAdd all these new feeds to the MISP database? (yes/no): ").lower() != "yes":
        print("User cancelled. Exiting.")
        sys.exit(0)
    
    network_path = input("Enter the base network path (e.g., http://192.168.1.37:8080/): ").strip()
    if not network_path.startswith(("http://", "https://")):
        print("Invalid network path. Exiting.")
        sys.exit(1)
    if not network_path.endswith("/"):
        network_path += "/"
    
    print("\n--- Adding feeds to MISP database... ---")
    for folder in new_folders:
        data_filename = folder['data_files'][0] if folder['data_files'] else None
        if data_filename:
            feed_url = urljoin(network_path, urljoin(folder['folder_name'] + "/", data_filename))
            add_feed_to_db(folder['folder_name'], feed_url, folder['source_format'], DATABASE_CONFIG)
        else:
            print(f"Warning: No data file in '{folder['folder_name']}'. Skipping.")
    
    print("\n--- Feed database integration completed. ---")


if __name__ == "__main__":
    main()
