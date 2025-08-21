"""
Manual API Testing Script
========================

Quick commands to test individual API endpoints manually.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def start(url="https://ibriz.ai", num_queries=8):
    """Start analysis for a URL"""
    data = {"url": url, "numOfQueries": num_queries}
    response = requests.post(f"{BASE_URL}/api/start-analysis", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def status():
    """Check analysis status"""
    response = requests.get(f"{BASE_URL}/api/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def results():
    """Get aggregate results"""
    response = requests.get(f"{BASE_URL}/api/aggregate-results")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Queries: {len(data.get('queries', []))}")
        print(f"Domains: {len(data.get('domain_percentages', []))}")
        print("Top 5 domains:")
        for i, domain in enumerate(data.get('domain_percentages', [])[:5]):
            print(f"  {i+1}. {domain['domain']}: {domain['percentage']}%")
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")

def query_details(query_text):
    """Get details for a specific query"""
    data = {"query": query_text}
    response = requests.post(f"{BASE_URL}/api/query-details", json=data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Query: {data['query']}")
        print(f"Response length: {len(data['gemini_response'])} chars")
        print(f"Domains: {len(data['domains'])}")
        print("Gemini response preview:")
        print(data['gemini_response'][:200] + "..." if len(data['gemini_response']) > 200 else data['gemini_response'])
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")

def reset():
    """Reset analyzer"""
    response = requests.post(f"{BASE_URL}/api/reset")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    print("Available functions:")
    print("- health() - Test health endpoint")
    print("- start(url, num_queries) - Start analysis")
    print("- status() - Check status")
    print("- results() - Get aggregate results")
    print("- query_details('query text') - Get query details")
    print("- reset() - Reset analyzer")
    print("\nExample usage:")
    print(">>> health()")
    print(">>> start('https://example.com', 5)  # Generate 5 queries")
    print(">>> status()")
