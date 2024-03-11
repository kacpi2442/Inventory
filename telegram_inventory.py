import asyncio
import tempfile
import io
from threading import Thread
from telegram import ForceReply, Update, ReplyKeyboardRemove
from telegram.ext import Application, ConversationHandler, ContextTypes, MessageHandler, filters, CommandHandler
from inventory_flask import Entity, Barcode
from sqlalchemy.orm import Session
import zxingcpp
import os
from PIL import Image
from datetime import datetime

botToken = os.environ["BOT_TOKEN"]

ADDING = 1

class TelegramInventoryBot():
    def __init__(self, token, dbSession: Session):
        print(token)
        self.application = Application.builder().token(token).build()
        self.dbSession = dbSession
        self.tmpDir = tempfile.TemporaryDirectory()

        # on different commands - answer in Telegram
        # self.application.add_handler(CommandHandler("start", self.start))
        # self.application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND & ~filters.REPLY, self.photo_received))
        # self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.REPLY, self.text_received))
        # self.application.add_handler(MessageHandler(filters.REPLY, self.handle_reply))
        conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.PHOTO & ~filters.COMMAND & ~filters.REPLY, self.photo_received),
                          MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.REPLY, self.text_received),
                          CommandHandler("start", self.start)],
            states={
                ADDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.adding)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel),]
        )
        self.application.add_handler(conv_handler)

    async def handleCodes(self, update: Update, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        items = Entity.query.filter(Entity.barcodes.any(Barcode.barcode == query)).all()
        if len(items) == 0:
            items = Entity.query.filter(Entity.name.contains(query)).all()
            if len(items) == 0:
                await update.message.reply_html(
                    f'"{query}" not found in inventory, adding as new item. Please enter the name of the item.\nType /cancel to cancel.', 
                    reply_markup=ForceReply(selective=True), 
                    reply_to_message_id=update.message.message_id)
                context.user_data['adding'] = query
                return ADDING
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
        return ConversationHandler.END

    async def photo_received(self, update: Update, context):
        if (update.message.photo):
            photoFileId = update.message.photo[-1].file_id
            photoFile = await self.application.bot.get_file(photoFileId)
            
            res = await photoFile.download_as_bytearray()
            barcode = Image.open(io.BytesIO(res))
            ret = ConversationHandler.END # TODO: Really think if this is the best way to handle this
            for code in zxingcpp.read_barcodes(barcode):
                # print('Found barcode:'
		        #     f'\n Text:    "{code.text}"'
		        #     f'\n Format:   {code.format}'
		        #     f'\n Content:  {code.content_type}'
		        #     f'\n Position: {code.position}')
                ret = await self.handleCodes(update, code.text, context)
            return ret
                

    async def text_received(self, update: Update, context):
        query = update.message.text
        ret = await self.handleCodes(update, query, context)
        return ret

    async def adding(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = update.message.text
        barcode = context.user_data['adding']
        print(f"Adding {name} with barcode {barcode}")
        ## Add the item to the inventory
        item = Entity(name=name, created=datetime.now(), modified=datetime.now())
        self.dbSession.add(item)
        self.dbSession.commit()
        barcodeEntity = Barcode(entity_id=item.id, barcode=barcode)
        self.dbSession.add(barcodeEntity)
        self.dbSession.commit()
        await update.message.reply_html(
            rf'Added "{name}" to inventory under barcode: {barcode}.')
        return ConversationHandler.END
            
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Canceled', reply_markup=ReplyKeyboardRemove())
        # TODO: Cancel forced reply
        return ConversationHandler.END

    async def run_bot(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        res = Entity.query.all()
        await update.message.reply_html(
            rf"Hi, send me a photo of a barcode to add it to the inventory or show the details of existing items."
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