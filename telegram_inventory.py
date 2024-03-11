import asyncio
import tempfile
import io
from threading import Thread
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from inventory_flask import Entity, Barcode
from sqlalchemy.orm import Session
import zxingcpp
import os
from PIL import Image

botToken = os.environ["BOT_TOKEN"]

class TelegramInventoryBot():
    def __init__(self, token, dbSession: Session):
        print(token)
        self.application = Application.builder().token(token).build()
        self.dbSession = dbSession
        self.tmpDir = tempfile.TemporaryDirectory()

        # on different commands - answer in Telegram
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, self.photo_received))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_received))

    async def handleCodes(self, update: Update, query):
        items = Entity.query.filter(Entity.barcodes.any(Barcode.barcode == query)).all()
        if len(items) == 0:
            items = Entity.query.filter(Entity.name.contains(query)).all()
            if len(items) == 0:
                await update.message.reply_markdown(
                    rf"Barcode: {query} not found in inventory, please add it.")
                return
        for item in items[:3]:
            description = f"<b>{item.name}</b>\n"
            if item.parent:
                if item.parent.parent:
                    description += f"Parent: {item.parent.parent.name} -> {item.parent.name}\n"
                else:
                    description += f"Parent: {item.parent.name}\n"
            if item.barcodes:
                description += f"Barcodes: {', '.join([barcode.barcode for barcode in item.barcodes])}\n"
            if item.children:
                description += f"Children: {len(item.children)}\n"
            if item.ownerships:
                for ownership in item.ownerships:
                    description += f"Owner: {ownership.owner.name} - {ownership.own}%\n"
            if item.properties:
                for prop in item.properties:
                    description += f"{prop.property.name}: {prop.value}\n"
            if item.photos:
                photo = item.photos[0].image
                photo_bytes = io.BytesIO(photo)
                await update.message.reply_photo(photo=photo_bytes, caption=description, parse_mode="HTML")
            else:
                await update.message.reply_html(rf"{description}")

    async def photo_received(self, update: Update, context):
        if (update.message.photo):
            photoFileId = update.message.photo[-1].file_id
            photoFile = await self.application.bot.get_file(photoFileId)
            
            res = await photoFile.download_as_bytearray()
            barcode = Image.open(io.BytesIO(res))
            for code in zxingcpp.read_barcodes(barcode):
                # print('Found barcode:'
		        #     f'\n Text:    "{code.text}"'
		        #     f'\n Format:   {code.format}'
		        #     f'\n Content:  {code.content_type}'
		        #     f'\n Position: {code.position}')
                # await update.message.reply_html(
                #     rf"Barcode: {code.text}")
                await self.handleCodes(update, code.text)

    async def text_received(self, update: Update, context):
        query = update.message.text
        await self.handleCodes(update, query)


    async def run_bot(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        res = Entity.query.all()
        await update.message.reply_html(
            rf"Hi, send me a photo of a barcode to add it to the inventory or show the details of existing items.",
            reply_markup=ForceReply(selective=True),
        )

async def run_telegram_bot(dbSession) -> None:
    bot = TelegramInventoryBot(botToken, dbSession)
    print("Running bot")
    await bot.run_bot()

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def run_bot_threaded(session):
    loop = asyncio.new_event_loop()
    loop.create_task(run_telegram_bot(session))
    t = Thread(target=start_background_loop, args=(loop,), daemon=True)
    t.start()