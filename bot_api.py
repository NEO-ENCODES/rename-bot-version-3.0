import os
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler
from shared_queue import queue

async def cmd_start(update: Update, context):
    await update.message.reply_text("Welcome! Reply to a document with /rename <new filename> to process it.")

async def cmd_rename(update: Update, context):
    # Verify the user replied to a message containing a document.
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("Please reply to a document with /rename <new filename>.")
        return

    new_name = " ".join(context.args)
    if not new_name:
        await update.message.reply_text("Please provide a new file name.")
        return

    # Get the forwarding chat ID from environment variables.
    forward_chat_id = os.environ.get("FORWARD_CHAT_ID")
    if not forward_chat_id:
        await update.message.reply_text("Forward chat not configured. Contact the administrator.")
        return

    # Forward the replied-to message to the designated forwarding chat.
    fwd_msg = await context.bot.forward_message(
        chat_id=forward_chat_id,
        from_chat_id=update.message.chat_id,
        message_id=update.message.reply_to_message.message_id
    )
    # Queue the task using the forwarded message's identifiers.
    task = {
        "chat_id": forward_chat_id,
        "message_id": fwd_msg.message_id,
        "new_name": new_name,
    }
    await queue.put(task)
    print("[Bot API] Task enqueued:", task)
    await update.message.reply_text("Your file is being processed. Please wait...")

async def run_bot_api():
    token = os.environ.get("BOT_TOKEN")
    webhook_url_base = os.environ.get("WEBHOOK_URL")  # e.g. "https://your-app.koyeb.app"
    if not token or not webhook_url_base:
        raise ValueError("BOT_TOKEN and WEBHOOK_URL must be set")
    full_webhook_url = webhook_url_base.rstrip("/") + "/" + token

    # Build the Telegram application.
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("rename", cmd_rename))
    
    print("Initializing Bot API component (webhook mode)...")
    await app.initialize()
    
    # Set the webhook with Telegram.
    await app.bot.set_webhook(full_webhook_url)
    print("Webhook set to:", full_webhook_url)
    
    # Create a custom aiohttp web application to serve the webhook and health check.
    from aiohttp import web

    async def webhook_handler(request):
        try:
            data = await request.json()
        except Exception:
            return web.Response(status=400, text="Bad Request")
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response(text="OK")
    
    aio_app = web.Application()
    # Route for webhook updates.
    aio_app.router.add_post(f"/{token}", webhook_handler)
    # Health check endpoint.
    aio_app.router.add_get("/health", lambda request: web.Response(text="ok"))
    
    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    print("Bot API webhook server running on port 8000")
    
    # Block forever so the server remains up.
    await asyncio.Event().wait()

# For standalone testing, you can uncomment:
# if __name__ == '__main__':
#     nest_asyncio.apply()
#     asyncio.run(run_bot_api())
