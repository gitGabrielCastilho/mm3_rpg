#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')

# Setup Django
sys.path.insert(0, '/d/TI/mm3_rpg')
django.setup()

from django.db import connection

print("Checking if migrations were applied...")

# Check tables
with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'domains_warfare%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables in domains_warfare: {len(tables)}")
    for table in tables:
        if 'equipment' in table.lower():
            print(f"  ✓ {table}")

# Try to apply migrations if needed
from django.core.management import call_command
print("\nApplying migrations...")
call_command('migrate', 'domains_warfare')
print("Done!")
