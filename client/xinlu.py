import os
import queue
import asyncio
import aiohttp
import concurrent.futures
import functools
import io
import sys
from threading import Thread
import time
import re
import uuid
import requests
import websockets

from dotenv import load_dotenv
from whatsapp_api_client_python import API

# Initialize the GreenAPI client
global idInstancd
idInstance = "7103869864"
global apiTokenInstance
apiTokenInstance = "c079e284d8724fff973f8c7023f9efc360810d551ad6480c8a"
global greenAPI
greenAPI = API.GreenApi(idInstance, apiTokenInstance)

# load environment variables
load_dotenv()

async def last_message():
    async with aiohttp.ClientSession() as session:
        url = f"https://api.green-api.com/waInstance{idInstance}/lastOutgoingMessages/{apiTokenInstance}"
        async with session.get(url) as response:
            data = await response.json()
            by_phone = data[0]["sendByApi"]
            response_txt_last = data[0]['textMessage']
            response_txt_2last = data[1]['textMessage']
            if by_phone==False and response_txt_last != response_txt_2last:
                return True

async def handle_text(websocket):
    while True:

        message = await last_message()

        url = f"https://api.green-api.com/waInstance{idInstance}/lastOutgoingMessages/{apiTokenInstance}"
        response = requests.request("GET", url, headers={}, data = {})
        response_txt = response.json()[0]['textMessage']

        await websocket.send(response_txt)
        print("sent to websocket")


# model response handler
async def receive_message(websocket):
    to_user = ""
    print("at receiving_messag task")
    while True:
        try: 
            message = await websocket.recv()
        except websockets.exception.ConnectionClosedError as e:
            message = "Connection closed unexpectedly: " + e
            break
        except Exception as e:
            message = "An error occured: " + e
            break

        if isinstance(message, str):
            if message == '[end]\n' or re.search(r'\[end=([a-zA-Z0-9]+)\]', message):
                greenAPI.sending.sendMessage('3476754292@c.us', to_user)
                break
            elif message == '[thinking]\n':
                # skip thinking message
                break
            elif message.startswith('[+]'):
                break
            elif message.startswith('[=]') or re.search(r'\[=([a-zA-Z0-9]+)\]', message):
                break
            else:
                to_user += message

        elif isinstance(message, bytes):
            continue
        else:
            print("Unexpected message")
            break
        
        print("continue receiving")

async def start_client(session_id, url):
    api_key = os.getenv('AUTH_API_KEY')
    llm_model = 'gpt-3.5-turbo-16k'  # Set the language model to gpt-3.5-turbo-16k
    uri = f"ws://{url}/ws/{session_id}?api_key={api_key}&llm_model={llm_model}"
    async with websockets.connect(uri) as websocket:
        # send client platform info
        await websocket.send('terminal')
        print(f"Client #{session_id} connected to server")
        welcome_message = await websocket.recv()
        print("welcome_message send")
        # set the character to Mask
        character = "1"
        await websocket.send(character)
        print("character send")
        
        send_task = asyncio.create_task(handle_text(websocket))
        receive_task = asyncio.create_task(receive_message(websocket))
        
        await asyncio.gather(receive_task, send_task)

async def main(url):
    session_id = str(uuid.uuid4().hex)
    task = asyncio.create_task(start_client(session_id, url))
    try:
        await task
    except KeyboardInterrupt:
        task.cancel()
        await asyncio.wait_for(task, timeout=None)
        print("Client stopped by user")

if __name__ == "__main__":
    url = 'localhost:8000'
    asyncio.run(main(url))
