"""
Test script for IBRIZ Analysis API
==================================

This script tests all the API endpoints to ensure they work correctly.
Run this after starting the Flask API server.
"""

import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health check endpoint."""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_start_analysis():
    """Test starting an analysis."""
    print("\n🚀 Testing start analysis...")
    try:
        # Test with custom number of queries
        data = {"url": "https://ibriz.ai", "numOfQueries": 5}
        response = requests.post(f"{BASE_URL}/api/start-analysis", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Start analysis failed: {e}")
        return False

def test_status():
    """Test getting analysis status."""
    print("\n📊 Testing status check...")
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {result}")
        return response.status_code == 200, result.get('status')
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False, None

def wait_for_completion():
    """Wait for analysis to complete."""
    print("\n⏳ Waiting for analysis to complete...")
    max_wait = 300  # 5 minutes max
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        success, status = test_status()
        if not success:
            return False
        
        if status == "complete":
            print("✅ Analysis completed!")
            return True
        elif status == "error":
            print("❌ Analysis failed!")
            return False
        
        print(f"Status: {status} - waiting...")
        time.sleep(10)
    
    print("⏰ Timeout waiting for analysis")
    return False

def test_aggregate_results():
    """Test getting aggregate results."""
    print("\n📈 Testing aggregate results...")
    try:
        response = requests.get(f"{BASE_URL}/api/aggregate-results")
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Number of queries: {result.get('num_queries', 'N/A')}")
        print(f"Number of domains: {len(result.get('domain_percentages', []))}")
        
        # Show top 3 domains
        domains = result.get('domain_percentages', [])
        if domains:
            print("Top 3 domains:")
            for i, domain in enumerate(domains[:3]):
                print(f"  {i+1}. {domain['domain']}: {domain['percentage']}% ({domain['query_count']} queries)")
        
        return response.status_code == 200, result.get('queries', [])
    except Exception as e:
        print(f"❌ Aggregate results failed: {e}")
        return False, []

def test_query_details(queries):
    """Test getting query details."""
    print("\n🔍 Testing query details...")
    if not queries:
        print("No queries available to test")
        return False
    
    try:
        # Test with the first query
        test_query = queries[0]
        data = {"query": test_query}
        response = requests.post(f"{BASE_URL}/api/query-details", json=data)
        print(f"Status: {response.status_code}")
        result = response.json()
        
        print(f"Query: {result.get('query', 'N/A')}")
        print(f"Gemini response length: {len(result.get('gemini_response', ''))} characters")
        print(f"Number of domains: {len(result.get('domains', []))}")
        
        # Show domains for this query
        domains = result.get('domains', [])
        if domains:
            print("Domains mentioned:")
            for domain in domains[:3]:  # Show top 3
                print(f"  - {domain['domain']}: {domain['count']} mentions")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Query details failed: {e}")
        return False

def test_reset():
    """Test resetting the analyzer."""
    print("\n🔄 Testing reset...")
    try:
        response = requests.post(f"{BASE_URL}/api/reset")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 IBRIZ API Test Suite")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health():
        print("❌ API server is not running or not responding")
        print("💡 Make sure to start the API server with: python api.py")
        return
    
    # Test 2: Start analysis
    if not test_start_analysis():
        print("❌ Failed to start analysis")
        return
    
    # Test 3: Wait for completion
    if not wait_for_completion():
        print("❌ Analysis did not complete successfully")
        return
    
    # Test 4: Get aggregate results
    success, queries = test_aggregate_results()
    if not success:
        print("❌ Failed to get aggregate results")
        return
    
    # Test 5: Get query details
    if not test_query_details(queries):
        print("❌ Failed to get query details")
        return
    
    # Test 6: Reset (optional)
    test_reset()
    
    print("\n✅ All tests completed successfully!")
    print("🎉 Your API is working correctly!")

if __name__ == "__main__":
    main()
