# ================================
# STREAMER.PY
# Pyrogram se Telegram video stream
# Koi size limit nahi!
# ================================

import asyncio
import os
import logging
from flask import Flask, request, Response
from pyrogram import Client
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================
# CONFIG
# Render environment variables se
# ================================
API_ID   = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PORT     = int(os.environ.get("PORT", 8000))

# ================================
# Flask App
# ================================
app = Flask(__name__)

# ================================
# Pyrogram Client
# ================================
client = Client(
    "stream_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    no_updates=True  # Updates nahi chahiye
)

# Event loop
loop = asyncio.new_event_loop()

# ================================
# Stream Function
# ================================
async def stream_file(file_id, start=0, end=None):
    """
    Telegram se file chunks mein stream karo.
    Range support ke saath.
    """
    async for chunk in client.stream_media(
        file_id,
        offset=start,
        limit=end
    ):
        yield chunk

# ================================
# Routes
# ================================

@app.route('/health')
def health():
    """Health check"""
    from flask import jsonify
    return jsonify({
        'status': 'ok',
        'streamer': 'pyrogram',
        'connected': client.is_connected
    })

@app.route('/stream')
def stream():
    """
    Video stream endpoint.
    /stream?file_id=TELEGRAM_FILE_ID
    """
    file_id = request.args.get('file_id', '')

    if not file_id:
        return "file_id missing!", 400

    # Range header nikalo
    range_header = request.headers.get('Range', '')
    start = 0
    end   = None

    if range_header:
        # "bytes=start-end" format
        try:
            range_val = range_header.replace('bytes=', '')
            parts     = range_val.split('-')
            start     = int(parts[0]) if parts[0] else 0
            end       = int(parts[1]) if parts[1] else None
        except:
            start = 0
            end   = None

    def generate():
        """Generator — chunks yield karo"""
        async def async_gen():
            async for chunk in client.stream_media(
                file_id,
                offset=start // (1024 * 1024),  # MB mein
            ):
                yield chunk

        # Async generator ko sync mein chalao
        async_iterator = async_gen()

        while True:
            try:
                chunk = loop.run_until_complete(
                    async_iterator.__anext__()
                )
                yield chunk
            except StopAsyncIteration:
                break
            except Exception as e:
                logger.error(f"Stream error: {e}")
                break

    # Response banao
    if range_header:
        status_code = 206
        headers = {
            'Content-Type':  'video/mp4',
            'Accept-Ranges': 'bytes',
            'Content-Range': f'bytes {start}-*/*',
        }
    else:
        status_code = 200
        headers = {
            'Content-Type':  'video/mp4',
            'Accept-Ranges': 'bytes',
        }

    return Response(
        generate(),
        status=status_code,
        headers=headers,
        direct_passthrough=True
    )

# ================================
# Pyrogram Start
# ================================
def start_pyrogram():
    """Pyrogram client background mein chalao"""
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.start())
    logger.info("✅ Pyrogram connected!")
    loop.run_forever()

# ================================
# MAIN
# ================================
if __name__ == '__main__':
    logger.info("🚀 Streamer starting...")
    logger.info(f"API_ID: {API_ID}")

    # Pyrogram thread
    pyro_thread = threading.Thread(
        target=start_pyrogram,
        daemon=True
    )
    pyro_thread.start()

    # Thoda wait karo connect hone do
    import time
    time.sleep(5)

    logger.info(f"🌐 Flask on port {PORT}")
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=False,
        use_reloader=False
    )
