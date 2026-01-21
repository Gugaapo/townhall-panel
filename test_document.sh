#!/bin/bash

# Get token
TOKEN=$(curl -s -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@townhall.com&password=admin123' | jq -r '.access_token')

echo "Token obtained: ${TOKEN:0:50}..."

# Create a document
echo -e "\n=== Creating Document ===\n"
curl -X POST 'http://localhost:8000/api/v1/documents' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Budget Request for Infrastructure 2025",
    "description": "Request for approval of infrastructure budget allocation for fiscal year 2025",
    "document_type": "request",
    "priority": "high",
    "metadata": {
      "deadline": "2025-12-31T17:00:00Z",
      "tags": ["budget", "2025", "infrastructure"],
      "custom_fields": {
        "fiscal_year": "2025",
        "amount": "500000"
      }
    }
  }' | jq

# List documents
echo -e "\n=== Listing Documents ===\n"
curl -X GET 'http://localhost:8000/api/v1/documents' \
  -H "Authorization: Bearer $TOKEN" | jq

# Get document stats
echo -e "\n=== Document Statistics ===\n"
curl -X GET 'http://localhost:8000/api/v1/documents/stats/overview' \
  -H "Authorization: Bearer $TOKEN" | jq
