import requests
import json

BASE_URL = "http://localhost:8000"

def test_health_check():
    response = requests.get(f"{BASE_URL}/")
    print("\n1. Testing Health Check (/):")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_twilio_speech():
    data = {"SpeechResult": "Hello, this is a test"}
    response = requests.post(f"{BASE_URL}/twilio", json=data)
    print("\n2. Testing Twilio Speech (/twilio):")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_twilio_silence():
    data = {}  # Empty data simulates silence
    response = requests.post(f"{BASE_URL}/twilio", json=data)
    print("\n3. Testing Twilio Silence (/twilio):")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_end_call():
    response = requests.post(f"{BASE_URL}/end")
    print("\n4. Testing End Call (/end):")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    test_health_check()
    test_twilio_speech()
    test_twilio_silence()
    test_end_call() 