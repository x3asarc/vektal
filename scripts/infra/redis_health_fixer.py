
import os
import sys
import socket
import subprocess
import time
from urllib.parse import urlparse
from dotenv import load_dotenv, set_key

# Ensure absolute imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

load_dotenv()

def check_port(host, port, timeout=2.0):
    """Check if a port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, socket.gaierror):
        return False

def get_redis_url():
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def fix_redis():
    print("🕵️  DIAGNOSING REDIS CONNECTIVITY...")
    url = get_redis_url()
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    
    print(f"Target: {host}:{port} (from {url})")
    
    if check_port(host, port):
        print("✅ Redis port is reachable!")
        return True
    
    print(f"❌ Redis port {port} on {host} is UNREACHABLE.")
    
    # Check if we are using 'redis' hostname outside of docker
    if host == "redis":
        print("💡 Host is set to 'redis'. You might be running outside Docker.")
        print("Attempting to switch to 'localhost'...")
        new_url = url.replace("redis://redis:", "redis://localhost:")
        set_key(".env", "REDIS_URL", new_url)
        os.environ["REDIS_URL"] = new_url
        print(f"Updated .env: REDIS_URL={new_url}")
        if check_port("localhost", port):
            print("✅ Connection successful after switching to localhost!")
            return True

    # Try to start via Docker Compose
    print("🚀 Attempting to start Redis via Docker Compose...")
    success, out, err = run_command("docker compose up -d redis")
    if success:
        print("✅ Docker Compose command sent. Waiting for startup...")
        for i in range(10):
            time.sleep(2)
            if check_port(host, port) or check_port("localhost", port):
                print("✅ Redis is now UP!")
                return True
            print(f"Waiting... ({i+1}/10)")
    else:
        print(f"❌ Failed to start Docker container: {err}")
        print("Try starting Docker Desktop manually.")

    return False

if __name__ == "__main__":
    if fix_redis():
        sys.exit(0)
    else:
        sys.exit(1)
