import asyncio
import json
import time
import websockets
from seleniumbase import Driver

async def handle_client(websocket):
    last_request = 0

    async for message in websocket:
        now = time.monotonic()

        if now - last_request < 10:
            await websocket.close(
                code=1008,
                reason="Rate limit exceeded"
            )
            return

        last_request = now
    
    driver = None
    try:
        driver = Driver(uc=True, headless=True)
        driver.get("https://play.blooket.com/play")

        cookies = driver.get_cookies()
        cookie_header = "; ".join(
            f"{c['name']}={c['value']}" for c in cookies
        )

        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "cookie":
                await websocket.send(json.dumps({
                    "type": "cookies",
                    "cookie": cookie_header
                }))
                break

    finally:
        if driver:
            driver.quit()

async def main():
    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        print("WebSocket server running on port 8765")
        await asyncio.Future()

asyncio.run(main())
