import aiohttp
import os

FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY")

async def call_foundry_agent(user_text: str) -> str:
    url = f"{FOUNDRY_ENDPOINT}/agents/asst_XmGngtgUhF3Jb6kyPcvry0Rb/invoke"

    headers = {
        "Authorization": f"Bearer {FOUNDRY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "input": user_text
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json()

            # 🔁 Adjust based on your agent response format
            return data.get("output", "Sorry, I couldn't process that.")
