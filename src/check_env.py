"""Verify that credentials load from .env before we try to use them.

Prints only whether each name has a value -- never the value itself.
"""
import os

from dotenv import load_dotenv

load_dotenv()  # reads .env in the project root into the environment

REQUIRED = ("SHOPIFY_STORE", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET")

missing = []
for name in REQUIRED:
    value = os.getenv(name)
    print(f"{name}: {'set' if value else 'MISSING'}")
    if not value:
        missing.append(name)

if missing:
    raise SystemExit(f"\nMissing from .env: {', '.join(missing)}")

print("\nAll credentials loaded.")
