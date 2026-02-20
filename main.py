import os
import json
import time
import asyncio
import websockets
from websockets.http import Headers
from seleniumbase import Driver

RATE_LIMIT_SECONDS = 10
PORT = int(os.environ.get("PORT", 8765))
HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

async def process_request(path, request_headers):
    if request_headers.get("Upgrade", "").lower() == "websocket":
        return None
    return (200, Headers({"Content-Type": "text/plain"}), b"OK")

async def handle_client(websocket):
    last_request = 0

    try:
        async for message in websocket:
            now = time.monotonic()

            if now - last_request < RATE_LIMIT_SECONDS:
                await websocket.send(json.dumps({
                    "type": "error",
                    "error": "Rate limit exceeded"
                }))
                continue

            last_request = now

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "error": "Invalid JSON"
                }))
                continue

            if data.get("type") != "cookie":
                continue

            driver = None
            try:
                driver = Driver(uc=True, headless=True)
                driver.get("https://play.blooket.com/play")

                driver.sleep(5)

                cookies = driver.get_cookies()
                cookie_header = "; ".join(
                    f"{c['name']}={c['value']}" for c in cookies
                )

                await websocket.send(json.dumps({
                    "type": "cookies",
                    "cookie": cookie_header
                }))

            except Exception as e:
                await websocket.send(json.dumps({
                    "type": "error",
                    "error": str(e)
                }))
            finally:
                if driver:
                    driver.quit()

    except websockets.exceptions.ConnectionClosed:
        pass

async def main():
    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        PORT,
        process_request=process_request,
        max_size=2**20,
        ping_interval=20,
        ping_timeout=20,
    ):
        if HOSTNAME:
            print(f"WebSocket running at wss://{HOSTNAME}")
        else:
            print(f"WebSocket running at ws://0.0.0.0:{PORT}")

        await asyncio.Future()

asyncio.run(main())
