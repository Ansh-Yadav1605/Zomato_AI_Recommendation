import requests

url = "https://web-production-91927.up.railway.app/health"
print("Pinging health check URL...")
try:
    resp = requests.get(url, timeout=10)
    print("Status code:", resp.status_code)
    print("Body:", resp.text)
except Exception as e:
    print("Request failed:", e)
