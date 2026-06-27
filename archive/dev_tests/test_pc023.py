import asyncio
from src.app import analyze_text
from flask import Flask, request
import json

app = Flask(__name__)

async def run_test():
    with app.test_request_context(json={'text': 'القصه طويل ومملل'}):
        res = analyze_text()
        print(res.get_data(as_text=True))

if __name__ == "__main__":
    from src.app import load_models
    print("Loading models...")
    load_models()
    asyncio.run(run_test())
