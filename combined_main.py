import asyncio
import nest_asyncio
from bot_api import run_bot_api
from telethon_processor import run_telethon_processor

async def main():
    # Run both the Bot API (webhook mode) and Telethon processor concurrently
    await asyncio.gather(
        run_bot_api(),
        run_telethon_processor()
    )

if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.run(main())
