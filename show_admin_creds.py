#!/usr/bin/env python3
"""
Script to reset and display admin credentials for LAMControl
"""
import os
import json
import secrets
import hashlib

# Path to credentials file
cache_dir = "cache"
creds_file = os.path.join(cache_dir, 'admin_creds.json')

# Create new admin credentials
default_username = "admin"
default_password = secrets.token_urlsafe(16)  # Generate random password

# Hash the password
password_hash = hashlib.sha256(default_password.encode()).hexdigest()

credentials = {
    "username": default_username,
    "password_hash": password_hash
}

# Create cache directory if it doesn't exist
os.makedirs(cache_dir, exist_ok=True)

# Write new credentials
with open(creds_file, 'w') as f:
    json.dump(credentials, f)

print(f"\n=== LAMControl Admin Credentials ===")
print(f"Username: {default_username}")
print(f"Password: {default_password}")
print(f"====================================")
print(f"\nCredentials saved to: {creds_file}")
print(f"You can now login to the web interface at: http://localhost:5000")
