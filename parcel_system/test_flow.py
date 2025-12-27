import requests

BASE_URL = "http://127.0.0.1:5000"
SESSION = requests.Session()

def test_flow():
    # 1. Register
    reg_data = {
        "username": "test_py_2",
        "password": "password123",
        "full_name": "Test Python",
        "email": "tp2@example.com",
        "phone": "0912345678",
        "address": "Test Script Addr"
    }
    r = SESSION.post(f"{BASE_URL}/register", data=reg_data)
    print(f"Register: {r.status_code}")

    # 2. Login
    login_data = {
        "username": "test_py_2",
        "password": "password123"
    }
    r = SESSION.post(f"{BASE_URL}/login", data=login_data)
    print(f"Login: {r.status_code}, URL: {r.url}")

    # 3. Create Package with new fields
    pkg_data = {
        "recipient_name": "Receiver Py",
        "recipient_phone": "0987654321",
        "recipient_address": "Receiving St",
        "weight": "2.5",
        "width": "10",
        "height": "10", 
        "length": "10",
        "package_type": "SMALL_BOX",
        "delivery_speed": "STANDARD",
        "payment_method": "MOBILE_PAYMENT",
        "is_hazardous": "1",
        "is_international": "1"
    }
    r = SESSION.post(f"{BASE_URL}/create_package", data=pkg_data)
    print(f"Create Package: {r.status_code}, URL: {r.url}")
    
    # 4. Check Dashboard for package
    r = SESSION.get(f"{BASE_URL}/dashboard")
    if "Receiver Py" in r.text:
        print("Package found on dashboard!")
    else:
        print("Package NOT found.")

if __name__ == "__main__":
    try:
        test_flow()
    except Exception as e:
        print(e)
