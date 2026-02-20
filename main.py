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
    return (
        200,
        Headers({"Content-Type": "text/plain"}),
        b"OK"
    )

async def handle_client(websocket):
    last_request = 0

    try:
        message = await websocket.recv()
    except Exception:
        await websocket.close(1008, "No message received")
        return

    now = time.monotonic()
    if now - last_request < RATE_LIMIT_SECONDS:
        await websocket.close(1008, "Rate limit exceeded")
        return
    last_request = now

    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        await websocket.close(1008, "Invalid JSON")
        return

    if data.get("type") != "cookie":
        await websocket.close(1008, "Malformed request")
        return
    
    driver = None
    try:
        driver = Driver(uc=True, headless=True)
        driver.get("https://play.blooket.com/play")

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

    await websocket.close(1000, "Done")

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
