import json
from urllib import request

USER_AGENT = "Document Copilot amirnookam@gmail.com"   # ایمیل خودتان را بگذارید
CIK = "0000320193"  # شناسه شرکت اپل


def get_json(url):
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


data = get_json(f"https://data.sec.gov/submissions/CIK{CIK}.json")
print(data["name"])
print(list(data["filings"]["recent"].keys()))