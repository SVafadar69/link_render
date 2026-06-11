import json
from dotenv import load_dotenv 
import os 
import openai 
from openai import OpenAI
from groq import Groq
import discord
from datetime import timezone
from typing import List
import chromadb
from chromadb.utils import embedding_functions
from chromadb.utils.embedding_functions import ChromaCloudSpladeEmbeddingFunction
from chromadb.execution.expression.operator import K
from chromadb import Search, K, Knn, Rrf, Schema, SparseVectorIndexConfig, K
import ast
load_dotenv()


openai_api_key = os.getenv("OPENAI_API_KEY")
chromadb_api_key = os.getenv("CHROMA_API_KEY")
chromadb_tenant= os.getenv("CHROMADB_TENANT")
chromadb_database= os.getenv("CHROMADB_DATABASE")
chroma_collection_name = os.getenv("CHROMA_COLLECTION_NAME")
discord_bot_token = os.getenv("DISCORD_BOT_TOKEN")
discord_channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))
groq_api_key = os.getenv('groq_api_key')

os.environ['CHROMA_API_KEY'] = chromadb_api_key

starting_chunk_index = 163

client = discord.Client(intents=discord.Intents.default())
chroma_client = chromadb.CloudClient(
  api_key= chromadb_api_key,
  tenant= chromadb_tenant, 
  database= chromadb_database
)
schema = Schema()
openai_client = OpenAI(
    api_key = openai_api_key
)


sparse_ef = ChromaCloudSpladeEmbeddingFunction()
schema.create_index(
    config=SparseVectorIndexConfig(
        source_key=K.DOCUMENT,
        embedding_function=sparse_ef
    ),
    key="sparse_embedding"
)

collection_anduril = chroma_client.get_or_create_collection(
    name=chroma_collection_name,
    schema=schema
)

def run_hybrid_search(collection, query, limit=30):
    """Combined semantic and keyword search using RRF."""
    ranker = Rrf(
        ranks=[
            Knn(query=query, return_rank=True),
            Knn(query=query, key="sparse_embedding", return_rank=True)
        ],
        weights=[0.5, 0.5],
        k=100
    )
    search = (Search()
              .rank(ranker)
              .limit(limit)
              .select(K.DOCUMENT, K.SCORE))
    return collection.search(search)

def retrieve_collection(collection_name: str, schema: Schema, client: chromadb.CloudClient): 
    collection = client.get_or_create_collection(name=collection_name,schema=schema)
    return collection

def retrieve_prompt(prompt_name: str) -> str: 
    prompt = open(prompt_name, 'r', encoding='utf-8').read()
    return prompt

def answer_query(system_prompt: str) -> str: 
    response = openai_client.responses.create(
        model="gpt-5.4-nano",
        input=system_prompt 
    )
    return response.output_text

def groq_answer(system_prompt: str) -> str: 
   
    client = Groq(api_key = groq_api_key)
    completion = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
      {
        "role": "system",
        "content": system_prompt
      },
      
    ],
    temperature=1,
    max_completion_tokens=8192,
    top_p=1,
    reasoning_effort="high",
    stream=False,
    stop=None)

    return completion.choices[0].message.content or ""
        
formatted_messages = []

def chunk_documents(messages: list, chunk_size: int = 10, overlap: int = 3):
    step = chunk_size - overlap

    for chunk_start in range(0, len(messages), step):
        chunk = messages[chunk_start:chunk_start + chunk_size]
        print(f'chunk: {chunk}')

        if not chunk:
            continue

        chunk_end = chunk_start + len(chunk) - 1

        ids = [
            f"shay_chunk_{chunk_start}_{chunk_end}"
        ]

        documents = [
            "\n".join(
                f'sender_name: {msg["sender_name"]}\nmessage: {msg["text"]}'
                for msg in chunk
            )
        ]

        metadatas = [
            {
                "messages_metadata": json.dumps([
                    {
                        "sender": msg["sender_name"],
                        "message_id": msg['message_id']
                    }
                    for msg in chunk
                ])
            }
        ]


        collection_anduril.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        print(f"Uploaded anduril chunk {chunk_start} to {chunk_end}")


@client.event
async def on_rate_limit(payload):
    print(f'Rate limit hit -> bucket: {payload.bucket}')

@client.event
async def on_ready():
    channel = client.get_channel(discord_channel_id)
    print(f'channel: {channel}')
    messages = [
        {
            'message_id': str(msg.id),
            'sender_name': msg.author.display_name, 
            'text': msg.content
        }
        async for msg in channel.history(limit = None)
    ]
    print(f"Got {len(messages)} messages")

    with open('discord_messages', 'a', encoding='utf-8') as file: 
        file.write(str(messages))
    await client.close()

def retrieve_messages(messages_path: str = 'discord_messages'):
    messages = ast.literal_eval(open(messages_path, 'r', encoding='utf-8').read())
    senders = set([message.get('sender_name', '') for message in messages])
    print(len(senders))
    print(senders)

# client.run(discord_bot_token)
if __name__ == "__main__":
    messages = ast.literal_eval(open('discord_messages', 'r', encoding='utf-8').read())
    #chunk_documents(messages)
    query = 'What is Steven currently building?'
    responses = run_hybrid_search(collection = collection_anduril, query = query)
    documents = responses.get('documents', '')
    print(F'responses: {documents}')
    print(len(documents))
    system_prompt = retrieve_prompt('search_prompt.txt').format(USER_QUERY = query, DOCS = documents)
    print(f'system_prompt: {system_prompt}')
    llm_response = answer_query(system_prompt = system_prompt)
    print(f'llm_responses: {llm_response}')