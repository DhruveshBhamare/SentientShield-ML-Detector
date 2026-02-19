#!/usr/bin/env python3
"""
Test script for NeuralFort AI-Based Intelligent Infrastructure Resilience Framework
"""

import requests
import json
import time
import sys

def test_neuralfort_api():
    """Test NeuralFort API endpoints"""
    base_url = "http://localhost:8000/neuralfort"
    
    print("🧠 Testing NeuralFort AI Framework...")
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: Website registration
    print("\n2. Testing website registration...")
    test_website = {
        "website_name": "test-infrastructure.com",
        "website_url": "https://test-infrastructure.com",
        "owner_email": "admin@test-infrastructure.com"
    }
    
    try:
        response = requests.post(f"{base_url}/website/register", json=test_website)
        if response.status_code == 200:
            result = response.json()
            print("✅ Website registration successful")
            print(f"Activation Key: {result.get('activation_key', 'N/A')}")
            activation_key = result.get('activation_key')
        else:
            print(f"❌ Website registration failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Website registration error: {e}")
        return False
    
    # Test 3: Framework activation
    print("\n3. Testing framework activation...")
    activation_data = {
        "website_name": "test-infrastructure.com",
        "activation_key": activation_key
    }
    
    try:
        response = requests.post(f"{base_url}/activate", json=activation_data)
        if response.status_code == 200:
            print("✅ Framework activation successful")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Framework activation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Framework activation error: {e}")
        return False
    
    # Test 4: Framework status
    print("\n4. Testing framework status...")
    try:
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            print("✅ Framework status retrieved")
            status = response.json()
            print(f"Status: {status.get('status', 'N/A')}")
            print(f"Uptime: {status.get('uptime_seconds', 'N/A')} seconds")
        else:
            print(f"❌ Framework status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Framework status error: {e}")
        return False
    
    # Test 5: Metrics
    print("\n5. Testing metrics retrieval...")
    try:
        response = requests.get(f"{base_url}/metrics")
        if response.status_code == 200:
            print("✅ Metrics retrieved successfully")
            metrics = response.json()
            print(f"CPU Usage: {metrics.get('cpu_percent', 'N/A')}%")
            print(f"Memory Usage: {metrics.get('memory_percent', 'N/A')}%")
            print(f"Disk Usage: {metrics.get('disk_percent', 'N/A')}%")
        else:
            print(f"❌ Metrics retrieval failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Metrics retrieval error: {e}")
        return False
    
    # Test 6: LLM Insights
    print("\n6. Testing LLM insights...")
    try:
        response = requests.get(f"{base_url}/llm/insights")
        if response.status_code == 200:
            print("✅ LLM insights retrieved")
            insights = response.json()
            print(f"Key Findings: {insights.get('key_findings', 'N/A')}")
            print(f"Recommendations: {len(insights.get('recommendations', []))} items")
        else:
            print(f"❌ LLM insights failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ LLM insights error: {e}")
        return False
    
    print("\n🎉 All NeuralFort tests passed successfully!")
    return True

def test_dashboard_access():
    """Test dashboard accessibility"""
    print("\n🌐 Testing dashboard access...")
    
    dashboards = [
        "http://localhost:8000/static/dashboard.html",
        "http://localhost:8000/static/neuralfort_dashboard.html"
    ]
    
    for dashboard in dashboards:
        try:
            response = requests.get(dashboard)
            if response.status_code == 200:
                print(f"✅ {dashboard} - Accessible")
            else:
                print(f"❌ {dashboard} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {dashboard} - Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting NeuralFort Framework Test Suite")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print("✅ Main API server is running")
    except:
        print("❌ Main API server is not running. Please start it first:")
        print("   cd api && python main.py")
        sys.exit(1)
    
    # Run tests
    success = test_neuralfort_api()
    test_dashboard_access()
    
    if success:
        print("\n🎊 NeuralFort Framework is fully operational!")
        print("\nNext steps:")
        print("1. Open the NeuralFort dashboard: http://localhost:8000/static/neuralfort_dashboard.html")
        print("2. Register your infrastructure website")
        print("3. Activate the framework with your activation key")
        print("4. Monitor your infrastructure resilience in real-time!")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")
        sys.exit(1)