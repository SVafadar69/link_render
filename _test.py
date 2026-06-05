

from dotenv import load_dotenv 
import os 
import openai 
import discord
from typing import List
load_dotenv()


openai_api_key = os.getenv("openai_api_key")
chromadb_api_key = os.getenv("chromadb_api_key")
chromadb_tenant= os.getenv("chromadb_tenant")
chromadb_database= os.getenv("chromadb_database")
chroma_collection_name = os.getenv("chroma_collection_name")
discord_bot_token = os.getenv("discord_bot_token")
discord_channel_id = int(os.getenv("discord_channel_id"))

client = discord.Client(intents=discord.Intents.default())

def save_messages_locally(path: str = 'discord_messages', ):
    with open(path, 'a', encoding='utf-8') as file: 
        file.write(path)

@client.event
async def on_rate_limit(payload):
    print(f'Rate limit hit -> bucket: {payload.bucket}')

@client.event
async def on_ready():
    channel = client.get_channel(discord_channel_id)
    print(f'channel: {channel}')
    messages = [msg async for msg in channel.history(limit=None)]
    print(messages[-3].content)
    print('\n', type(messages[0]))
    print(messages[1])
    print('\n')
    print(messages[2])
    print('\n', messages[2])

    print(f"Got {len(messages)} messages")
    await client.close()

client.run(discord_bot_token)