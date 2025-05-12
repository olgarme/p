import requests
import json
from datetime import datetime

def test_twilio_webhook():
    url = "https://p-production-7684.up.railway.app/twilio"

    test_cases = [
        {
            "description": "Normal speech event",
            "data": {
                "CallSid": "test_call_sid_1",
                "From": "+15076077082",
                "To": "+15076077082",
                "SpeechResult": "Hello, this is a test"
            }
        },
        {
            "description": "Silence event (no SpeechResult)",
            "data": {
                "CallSid": "test_call_sid_2",
                "From": "+15076077082",
                "To": "+15076077082"
                # No SpeechResult
            }
        }
    ]

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Twilio-Signature": "test_signature"
    }

    for case in test_cases:
        print(f"\n--- {case['description']} ---")
        try:
            response = requests.post(url, data=case["data"], headers=headers)
            print(f"Status Code: {response.status_code}")
            try:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            except Exception:
                print(f"Raw Response: {response.text}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_twilio_webhook() 