import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

def test_health():
    """Test health check endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print("\nHealth Check:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_auth():
    """Test authentication endpoints."""
    # Test registration
    register_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User"
    }
    response = requests.post(f"{BASE_URL}{API_PREFIX}/auth/register", json=register_data)
    print("\nRegistration:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test login
    login_data = {
        "username": "test@example.com",
        "password": "testpassword123"
    }
    response = requests.post(f"{BASE_URL}/token", data=login_data)
    print("\nLogin:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json().get("access_token") if response.status_code == 200 else None

def test_recommendations(token=None):
    """Test recommendations endpoint."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.get(f"{BASE_URL}{API_PREFIX}/recommendations", headers=headers)
    print("\nRecommendations:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_content(token=None):
    """Test content endpoints."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    # Test explore
    response = requests.get(f"{BASE_URL}{API_PREFIX}/content/explore", headers=headers)
    print("\nExplore Content:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test search
    response = requests.get(
        f"{BASE_URL}{API_PREFIX}/content/search",
        params={"q": "machine learning"},
        headers=headers
    )
    print("\nSearch Content:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_user_endpoints(token=None):
    """Test user-related endpoints."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    # Test favorites
    response = requests.get(f"{BASE_URL}{API_PREFIX}/users/favorites", headers=headers)
    print("\nUser Favorites:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test settings
    response = requests.get(f"{BASE_URL}{API_PREFIX}/users/settings", headers=headers)
    print("\nUser Settings:")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def main():
    """Run all tests."""
    print("Starting API endpoint tests...")
    print("=" * 50)
    
    # Test health check
    test_health()
    
    # Test authentication
    token = test_auth()
    
    # Test other endpoints
    test_recommendations(token)
    test_content(token)
    test_user_endpoints(token)
    
    print("\nTests completed.")
    print("=" * 50)

if __name__ == "__main__":
    main() 