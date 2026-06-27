import os
import asyncio
import json
import sys

# Mock dotenv loading since it fails on Windows with embedded nulls
import dotenv
dotenv.load_dotenv = lambda *args, **kwargs: None
os.environ["QURAN_DB_PATH"] = "dummy"

sys.path.append(os.path.abspath('src'))
from app import analyze_text

async def run_test():
    res = await analyze_text("المهندسون صممتو المشروع")
    print("PC001:", res.get("text_corrected"))
    
    res2 = await analyze_text("القصه طويل ومملل")
    print("PC023:", res2.get("text_corrected"))
    
    res3 = await analyze_text("الشمس مشرق اليووم")
    print("PC014:", res3.get("text_corrected"))

if __name__ == "__main__":
    asyncio.run(run_test())
