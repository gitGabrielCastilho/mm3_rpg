#!/usr/bin/env python
"""Apply migrations directly"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
django.setup()

from django.core.management import call_command
print("Applying migrations...")
call_command('migrate', 'domains_warfare')
print("Done!")
