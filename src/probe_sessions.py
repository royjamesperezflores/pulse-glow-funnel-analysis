"""Smallest possible ShopifyQL request: does this token reach the sessions dataset?

Not part of the pipeline. This exists to turn an unknown into a named error.
"""
import json
import os

import requests
from dotenv import load_dotenv

from shopify_client import get_access_token

load_dotenv()

STORE = os.getenv("SHOPIFY_STORE")
API_VERSION = "2025-10"  # shopifyqlQuery requires 2025-10 or higher
URL = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}/graphql.json"

QUERY = """
{
  shopifyqlQuery(query: "FROM sessions
SHOW sessions, sessions_with_cart_additions, sessions_that_reached_checkout, sessions_that_completed_checkout
TIMESERIES day
SINCE -7d UNTIL today") {
    tableData { columns { name dataType } rows }
    parseErrors
  }
}
"""

token = get_access_token()
response = requests.post(
    URL,
    headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
    json={"query": QUERY},
    timeout=30,
)

print(f"HTTP {response.status_code}")
print(json.dumps(response.json(), indent=2))
