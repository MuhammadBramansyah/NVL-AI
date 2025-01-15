import os
import asyncio
import websocket
import logging

async def send_to_websocket(message):
    uri = f"ws://{os.getenv('WEBSOCKET_HOST')}:{os.getenv('WEBSOCKET_PORT')}/"
    async with websocket.connect(uri) as websocket:
        await websocket.send(message)
        logging.info(f"Sent message to server: {message}")
