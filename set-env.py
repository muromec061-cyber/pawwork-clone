#!/usr/bin/env python3
"""Set Cloudflare Workers environment variables and webhook."""
import json, urllib.request, sys, os

CF_TOKEN = os.environ.get("CF_API_TOKEN", "")
CF_ACCOUNT = os.environ.get("CF_ACCOUNT", "")
SCRIPT = os.environ.get("CF_SCRIPT", "pawwork-bot")
WORKER_URL = os.environ.get("WORKER_URL", f"https://{SCRIPT}.muromec061.workers.dev")

# Secrets to set (from environment)
secrets = {
    "TELEGRAM_TOKEN": os.environ.get("TELEGRAM_TOKEN", ""),
    "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", ""),
    "GH_TOKEN": os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", ""),
}

def api(method, path, body=None):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/{path}"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, 
                                  method=method)
    req.add_header("Authorization", f"Bearer {CF_TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:300]
        print(f"  [HTTP {e.code}] {err}")
        return None

# Step 1: Set environment variables
print("Setting environment variables...")
for name, value in secrets.items():
    if not value:
        print(f"  [SKIP] {name}: no value (set GH_TOKEN env var)")
        continue
    result = api("PUT", f"workers/scripts/{SCRIPT}/environment-variables/{name}", {
        "type": "secret_text",
        "name": name,
        "text": value,
    })
    if result and result.get("success"):
        print(f"  [OK] {name}: set")
    else:
        print(f"  [FAIL] {name}")

# Step 2: Set webhook
print("\nSetting Telegram webhook...")
tg_token = secrets["TELEGRAM_TOKEN"]
webhook_url = f"{WORKER_URL}/webhook"

body = json.dumps({
    "url": webhook_url,
    "allowed_updates": ["message", "callback_query"],
}).encode()

req = urllib.request.Request(
    f"https://api.telegram.org/bot{tg_token}/setWebhook",
    data=body,
    headers={"Content-Type": "application/json"},
)
try:
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    if result.get("ok"):
        print(f"  [OK] Webhook set to {webhook_url}")
        print(f"      Description: {result.get('description', '')}")
    else:
        print(f"  [FAIL] {result}")
except Exception as e:
    print(f"  [ERROR] {e}")

# Step 3: Test webhook
print("\nTesting webhook...")
req = urllib.request.Request(webhook_url.replace("/webhook", "/health"))
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print(f"  [OK] Health check: {resp.read().decode()[:200]}")
except Exception as e:
    print(f"  [ERROR] Health check: {e}")
