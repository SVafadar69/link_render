from dotenv import load_dotenv 
import os 
import openai 

load_dotenv()


openai_api_key = os.getenv("openai_api_key")
chromadb_api_key = os.getenv("chromadb_api_key")
chromadb_tenant= os.getenv("chromadb_tenant")
chromadb_database= os.getenv("chromadb_database")
chroma_collection_name = os.getenv("chroma_collection_name")
discord_bot_token = os.getenv("discord_bot_token")
discord_channel_id = os.getenv("discord_channel_id")