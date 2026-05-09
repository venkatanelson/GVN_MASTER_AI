import requests
try:
    response = requests.get("https://api.telegram.org/bot8072627750:AAHWp1Obka_cYbZVkHyKNpHO16TfL4smDGs/getMe", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
