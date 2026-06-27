import requests

url = "https://web-production-91927.up.railway.app/health"
print("Pinging health check URL with a longer timeout...")
try:
    resp = requests.get(url, timeout=30)
    print("Status code:", resp.status_code)
    print("Body:", resp.text)
except Exception as e:
    print("Request failed:", e)
