import os
import asyncio
import shutil
from telethon import TelegramClient
from telethon.sessions import StringSession
from shared_queue import queue
from telethon.tl.functions.account import TerminateAllSessionsRequest


api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
session_str = os.environ.get("SESSION")
if not (api_id and api_hash and session_str):
    raise ValueError("API_ID, API_HASH, and SESSION must be set")

client = TelegramClient(StringSession(session_str), api_id, api_hash)

async def run_telethon_processor():
    await client.start()
    # Terminate all other sessions except the current one
    await client(TerminateAllSessionsRequest())
    print("Terminated all other sessions. Telethon processor component is running...")
    while True:
        task = await queue.get()
        try:
            chat_id = task.get("chat_id")
            msg_id = task.get("message_id")
            new_name = task.get("new_name")
            print(f"[Processor] Received task for chat_id: {chat_id}, msg_id: {msg_id}, new_name: {new_name}")
            
            # Attempt to get the entity.
            try:
                entity = await client.get_entity(chat_id)
            except Exception as e:
                print(f"[Processor] Failed to get entity for chat_id {chat_id}: {e}")
                continue

            # Retrieve the message by its id
            msg = await client.get_messages(entity, ids=msg_id)
            if not msg:
                print("[Processor] Document not found in message. (Maybe the forwarded message is not accessible?)")
                continue
            if isinstance(msg, list):
                if len(msg) > 0:
                    msg = msg[0]
                else:
                    print("[Processor] Received empty message list.")
                    continue
            if not msg.document:
                print("[Processor] Message does not contain a document.")
                continue
            doc = msg.document
            print(f"[Processor] Found document: {doc.file_name} (ID: {doc.id})")
            if not os.path.exists("downloads"):
                os.makedirs("downloads")
            download_path = f"downloads/{doc.id}_{doc.file_name}"
            print(f"[Processor] Downloading file to {download_path}...")
            await client.download_media(doc, file=download_path)
            final_name = new_name if new_name else doc.file_name
            new_path = f"downloads/{final_name}"
            shutil.move(download_path, new_path)
            print(f"[Processor] File downloaded and renamed to {new_path}, now uploading...")
            await client.send_file(chat_id, new_path, caption=final_name)
            os.remove(new_path)
            print("[Processor] File processed and sent.")
        except Exception as e:
            print("[Processor] Error processing task:", e)
        finally:
            queue.task_done()
        await asyncio.sleep(0.5)  # small delay to avoid tight loop

async def main():
    await run_telethon_processor()

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
