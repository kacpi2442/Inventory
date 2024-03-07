import logging
import asyncio
from pathlib import Path
import tempfile
import io

from threading import Thread
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from inventory_flask import Entity
from sqlalchemy.orm import Session
import zxingcpp
import os
from PIL import Image

botToken = os.environ["BOT_TOKEN"]

class TelegramInventoryBot():
    def __init__(self, token, dbSession: Session):
        self.application = Application.builder().token(token).build()
        self.dbSession = dbSession
        self.tmpDir = tempfile.TemporaryDirectory()

        # on different commands - answer in Telegram
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, self.photo_received))

    async def photo_received(self, update: Update, context):
        if (update.message.photo):
            print(update.message.photo)
            photoFileId = update.message.photo[-1].file_id
            photoFile = await self.application.bot.get_file(photoFileId)
            
            res = await photoFile.download_as_bytearray()
            barcode = Image.open(io.BytesIO(res))
            for code in zxingcpp.read_barcodes(barcode):
                print()
                print('Found barcode:'
		            f'\n Text:    "{code.text}"'
		            f'\n Format:   {code.format}'
		            f'\n Content:  {code.content_type}'
		            f'\n Position: {code.position}')

    async def run_bot(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        res = Entity.query.all()
        await update.message.reply_html(
            rf"Hi chuj!",
            reply_markup=ForceReply(selective=True),
        )

async def run_telegram_bot(dbSession) -> None:
    bot = TelegramInventoryBot(botToken, dbSession)
    await bot.run_bot()

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def run_bot_threaded(session):
    loop = asyncio.new_event_loop()
    loop.create_task(run_telegram_bot(session))
    t = Thread(target=start_background_loop, args=(loop,), daemon=True)
    t.start()