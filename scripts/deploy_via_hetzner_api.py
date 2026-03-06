#!/usr/bin/env python3
"""Deploy Vektal frontend using Hetzner Cloud API and verify public gateway health."""

import os
import requests
import socket
import time

HETZNER_API_TOKEN = os.getenv('HETZNER_CLOUD_API_TOKEN')
SERVER_ID_RAW = os.getenv("HETZNER_SERVER_ID", "121393256")  # ubuntu-4gb-hel1-1
API_BASE = "https://api.hetzner.cloud/v1"
PUBLIC_DOMAIN = os.getenv("PUBLIC_DOMAIN", "app.vektal.systems")
ALLOW_DOMAIN_MISMATCH = os.getenv("ALLOW_DOMAIN_MISMATCH", "0") == "1"

def api_call(endpoint, method="GET", data=None):
    """Make Hetzner API call."""
    headers = {"Authorization": f"Bearer {HETZNER_API_TOKEN}"}
    url = f"{API_BASE}/{endpoint}"

    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)

    response.raise_for_status()
    return response.json()

def get_server_ip(server_id: int):
    """Get server IP address."""
    result = api_call(f"servers/{server_id}")
    return result['server']['public_net']['ipv4']['ip']


def resolve_domain_ipv4(domain: str) -> list[str]:
    """Resolve IPv4 addresses for the target domain."""
    try:
        infos = socket.getaddrinfo(domain, 443, socket.AF_INET, socket.SOCK_STREAM)
        return sorted({entry[4][0] for entry in infos})
    except Exception:
        return []


def enforce_domain_alignment(server_ip: str) -> bool:
    """Prevent accidental deployment to a host not behind the public domain."""
    domain_ips = resolve_domain_ipv4(PUBLIC_DOMAIN)
    if not domain_ips:
        print(f"[WARN] Could not resolve A records for {PUBLIC_DOMAIN}; skipping strict alignment check.")
        return True

    print(f"[Preflight] {PUBLIC_DOMAIN} A records: {', '.join(domain_ips)}")
    if server_ip in domain_ips:
        print("[OK] Server IP matches public domain A record")
        return True

    print(f"[WARN] Server IP {server_ip} is not in {PUBLIC_DOMAIN} A records.")
    if ALLOW_DOMAIN_MISMATCH:
        print("[WARN] Continuing because ALLOW_DOMAIN_MISMATCH=1.")
        return True

    print("[ERROR] Blocking deploy to avoid wrong-target rollout.")
    print("[HINT] Update DNS or set ALLOW_DOMAIN_MISMATCH=1 for intentional split routing.")
    return False

def trigger_webhook_deployment():
    """Trigger Dokploy webhook if available."""
    dokploy_webhook = os.getenv('DOKPLOY_WEBHOOK_URL')
    if not dokploy_webhook:
        print("[WARN] No DOKPLOY_WEBHOOK_URL found in environment")
        return False

    print("[Webhook] Triggering Dokploy deployment...")
    payload = {
        "ref": "refs/heads/master",
        "repository": {
            "full_name": "x3asarc/vektal"
        }
    }

    try:
        response = requests.post(dokploy_webhook, json=payload, timeout=10)
        if response.status_code == 200:
            print("[OK] Webhook triggered successfully")
            return True
        else:
            print(f"[WARN] Webhook returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[WARN] Webhook failed: {e}")
        return False


def wait_for_public_gateway(max_attempts=12, delay_seconds=10):
    """Poll public gateway health and return True once healthy."""
    url = f"https://{PUBLIC_DOMAIN}/health"
    print(f"[Probe] Waiting for public gateway: {url}")
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"[OK] Public gateway healthy on attempt {attempt}")
                return True
            print(f"[WARN] Attempt {attempt}/{max_attempts} returned HTTP {response.status_code}")
        except Exception as exc:
            print(f"[WARN] Attempt {attempt}/{max_attempts} failed: {exc}")
        time.sleep(delay_seconds)
    return False

def main():
    print("=" * 60)
    print("Vektal Frontend Deployment via Hetzner API")
    print("=" * 60)
    print()

    if not HETZNER_API_TOKEN:
        print("[ERROR] HETZNER_CLOUD_API_TOKEN not found in environment")
        return 1

    try:
        server_id = int(SERVER_ID_RAW)
    except ValueError:
        print(f"[ERROR] Invalid HETZNER_SERVER_ID: {SERVER_ID_RAW!r}")
        print("[HINT] Set HETZNER_SERVER_ID to a numeric Hetzner server id.")
        return 1

    # Get server info
    server_ip = get_server_ip(server_id)
    print(f"Server IP: {server_ip}")
    print(f"Server ID: {server_id}")
    print()

    if not enforce_domain_alignment(server_ip):
        return 1

    # Try webhook deployment first
    webhook_success = trigger_webhook_deployment()

    if webhook_success:
        healthy = wait_for_public_gateway()
        print()
        print("=" * 60)
        print("Deployment triggered via webhook")
        print("=" * 60)
        print()
        if healthy:
            print("Next steps:")
            print(f"  1. Visit https://{PUBLIC_DOMAIN}/dashboard")
            print("  2. Hard refresh (Ctrl+Shift+R) to see new UI")
            return 0
        print("[ERROR] Public gateway did not become healthy after deployment trigger.")
        print("[HINT] Check DNS A/AAAA records and nginx ingress on port 443.")
        return 1
    else:
        print()
        print("=" * 60)
        print("Webhook deployment not available")
        print("=" * 60)
        print()
        print("Manual deployment options:")
        print(f"  1. SSH to server: ssh root@{server_ip}")
        print(f"  2. Navigate to project: cd /root/vektal")
        print(f"  3. Pull changes: git pull origin master")
        print("  4. Rebuild: docker compose up -d nginx backend frontend --build")
        print(f"  5. Verify: curl -I https://{PUBLIC_DOMAIN}/health")
        print()
        print("Or use Dokploy dashboard to trigger deployment manually")
        return 1

if __name__ == "__main__":
    exit(main())
