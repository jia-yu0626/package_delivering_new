import requests
import sys

BASE_URL = "http://127.0.0.1:5000"
SESSION = requests.Session()

def test_negative_values():
    # 1. Login
    login_data = {
        "username": "test_py_2",
        "password": "password123"
    }
    r = SESSION.post(f"{BASE_URL}/login", data=login_data)
    
    # 2. Try Create Package with negative weight
    pkg_data = {
        "recipient_name": "Negative Test",
        "recipient_phone": "0987654321",
        "recipient_address": "Receiving St",
        "weight": "-2.5",
        "width": "10",
        "height": "10", 
        "length": "10",
        "package_type": "SMALL_BOX",
        "delivery_speed": "STANDARD",
        "payment_method": "CASH"
    }
    
    # We follow redirects, so the final page should have the flash error message
    r = SESSION.post(f"{BASE_URL}/create_package", data=pkg_data, allow_redirects=True)
    
    # Check if error message is present in response
    if "重量與尺寸必須大於 0" in r.text or "must be positive" in r.text:
        print("SUCCESS: Negative value rejected.")
    else:
        print("FAILURE: Negative value accepted or no error message found.")
        print(r.text) # Debug

if __name__ == "__main__":
    try:
        test_negative_values()
    except Exception as e:
        print(e)
