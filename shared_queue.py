import asyncio

# A global asyncio queue to share tasks between the bot API and Telethon components.
queue = asyncio.Queue()
