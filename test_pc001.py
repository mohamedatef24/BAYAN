import sys
import os
sys.path.append(os.path.abspath('src'))
from app import analyze_text
import asyncio
import json

async def run_test():
    text = "القصه طويل ومملل"
    res = await analyze_text(text)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(run_test())
