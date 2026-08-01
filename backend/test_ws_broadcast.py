import asyncio
import json
import sys

async def test():
    try:
        import httpx
    except ImportError:
        print("httpx not available, using urllib")
        import urllib.request, urllib.parse
        data = json.dumps({"email": "admin@inframind.ai", "password": "SecurePass123"}).encode()
        req = urllib.request.Request("http://localhost:8000/api/v1/auth/login",
            data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            token = json.loads(resp.read())["access_token"]
    else:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://localhost:8000/api/v1/auth/login",
                json={"email": "admin@inframind.ai", "password": "SecurePass123"}
            )
            token = r.json()["access_token"]

    uuid = "dev_4516524eda034535a4401795243ddae5"
    url = f"ws://localhost:8000/api/v1/ws/metrics/{uuid}?token={token}"
    print("Connecting to:", url[:80] + "...")

    try:
        import websockets
    except ImportError:
        print("websockets not installed — installing...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "websockets", "-q"])
        import websockets

    messages_received = 0
    async with websockets.connect(url) as ws:
        print("Connected! Waiting for metric broadcasts (max 20s)...")
        try:
            async with asyncio.timeout(20):
                while messages_received < 3:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    msg_type = data.get("type")
                    if msg_type == "metric":
                        messages_received += 1
                        cpu = data.get("cpu_usage_percent")
                        ram = data.get("ram_usage_percent")
                        bat = data.get("battery_percent")
                        ts  = data.get("collected_at")
                        print(f"[MSG {messages_received}] cpu={cpu}% ram={ram}% battery={bat} ts={ts}")
                    elif msg_type == "ping":
                        print("[PING] heartbeat received")
        except asyncio.TimeoutError:
            print("Timeout after 20s")

    print("")
    print(f"Total metric messages received: {messages_received}")
    if messages_received > 0:
        print("SUCCESS: WebSocket broadcast is FULLY WORKING!")
    else:
        print("FAIL: No metric broadcasts received — loop capture not working")

asyncio.run(test())
