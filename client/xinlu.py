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
#global idInstancd
idInstance = "7103869864"
#global apiTokenInstance
apiTokenInstance = "c079e284d8724fff973f8c7023f9efc360810d551ad6480c8a"
#global greenAPI
greenAPI = API.GreenApi(idInstance, apiTokenInstance)

# load environment variables
load_dotenv()

def is_last_message(last_time):
    url = f"https://api.green-api.com/waInstance{idInstance}/lastOutgoingMessages/{apiTokenInstance}"
    
    data = requests.request("GET", url, headers={}, data = {})
    not_by_phone = data.json()[0]["sendByApi"]
    data_time = data.json()[0]["timestamp"]
    response_txt_last = data.json()[0]['textMessage']
    if not_by_phone==False and data_time > last_time:
        last_time = time.time()
        return True
    else:
        return False

async def last_message():
    last_time = time.time()
    while not is_last_message(last_time):
        await asyncio.sleep(2)

async def handle_text(websocket):
    while True:

        await last_message()

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
                to_user = ""
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

    url = sys.argv[1] if len(sys.argv) > 1 else 'localhost:8000'
    asyncio.run(main(url))
