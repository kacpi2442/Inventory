import tempfile
import io
from telegram import ForceReply, Update, ReplyKeyboardRemove
from telegram.ext import Application, ConversationHandler, ContextTypes, MessageHandler, filters, CommandHandler
from models import Entity, Barcode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import zxingcpp
import os
from PIL import Image
from datetime import datetime

botToken = os.environ["BOT_TOKEN"]

# setup sqlalchemy engine
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance/inventory.db')
Session = sessionmaker(create_engine(DATABASE_URI))

ADDING, SELECT_PARENT, ASSIGN_PARENT = range(3)

class TelegramInventoryBot():
    def __init__(self, token, dbSession):
        self.application = Application.builder().token(token).build()
        self.dbSession = dbSession
        self.tmpDir = tempfile.TemporaryDirectory()

        # on different commands - answer in Telegram
        # self.application.add_handler(CommandHandler("start", self.start))
        # self.application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND & ~filters.REPLY, self.photo_received))
        # self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.REPLY, self.text_received))
        # self.application.add_handler(MessageHandler(filters.REPLY, self.handle_reply))
        conv_handler = ConversationHandler(
            entry_points=[MessageHandler(~filters.REPLY & ~filters.COMMAND, self.handle_barcode),
                          CommandHandler("start", self.start),
                          CommandHandler("assign_parent", self.assign_parent_prompt),],
            states={
                ADDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.adding)],
                SELECT_PARENT: [MessageHandler(~filters.COMMAND, self.select_parent)],
                ASSIGN_PARENT: [MessageHandler(~filters.COMMAND, self.assign_parent)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel),]
        )
        self.application.add_handler(conv_handler)
        print("Bot initialized.")

    async def assign_parent_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_html(
            f'Enter the parent barcode or ID.\nType /cancel to cancel.', 
            reply_markup=ForceReply(selective=True), 
            reply_to_message_id=update.message.message_id)
        return SELECT_PARENT
    
    async def select_parent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # query = update.message.text
        query = (await self.returnBarcodesOrQueryFromUpdate(update))[0]
        item = self.dbSession.query(Entity).filter(Entity.barcodes.any(Barcode.barcode == query)).first()
        if not item:
            item = self.dbSession.query(Entity).get(query)
        if not item:
            await update.message.reply_html(
                f'"{query}" not found in inventory, please enter the barcode or ID of the parent item.\nType /cancel to cancel.', 
                reply_markup=ForceReply(selective=True), 
                reply_to_message_id=update.message.message_id)
            return SELECT_PARENT
        context.user_data['parent'] = item.id
        # await update.message.reply_html(
        #     f'Enter the child barcode or ID.\nType /cancel to cancel.', 
        #     reply_markup=ForceReply(selective=True), 
        #     reply_to_message_id=update.message.message_id)
        await self.showItemsInfo(update, item.id, context, desc_prefix=f'Parent selected.\nEnter child barcode or ID to assign.\n\n', searchByID=True)
        return ASSIGN_PARENT
    
    async def assign_parent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # query = update.message.text
        query = (await self.returnBarcodesOrQueryFromUpdate(update))[0]
        item = self.dbSession.query(Entity).filter(Entity.barcodes.any(Barcode.barcode == query)).first()
        if not item:
            item = self.dbSession.query(Entity).get(query)
        if not item:
            await update.message.reply_html(
                f'"{query}" not found in inventory, please enter the barcode or ID of the child item.\nType /cancel to cancel.', 
                reply_markup=ForceReply(selective=True), 
                reply_to_message_id=update.message.message_id)
            return ASSIGN_PARENT
        parent = context.user_data['parent']
        # item.parent_id = parent
        self.dbSession.query(Entity).filter(Entity.id == item.id).update({Entity.parent_id: parent})
        self.dbSession.commit()
        # await update.message.reply_html(
        #     f'Assigned {item.name} as a child of {self.dbSession.query(Entity).get(parent).name}.')
        await self.showItemsInfo(update, item.id, context, desc_prefix=f'Parent assigned.\nType /cancel to cancel or enter another barcode or ID to assign next item.\n\n', searchByID=True)
        return ASSIGN_PARENT

    async def showItemsInfo(self, update: Update, query, context: ContextTypes.DEFAULT_TYPE, desc_prefix=None, searchByID=False) -> None:
        if searchByID:
            items = [self.dbSession.query(Entity).get(query)]
        else:
            items = self.dbSession.query(Entity).filter(Entity.barcodes.any(Barcode.barcode == query)).all()
            if len(items) == 0:
                items = self.dbSession.query(Entity).filter(Entity.name.contains(query)).all()
                if len(items) == 0:
                    await update.message.reply_html(
                        f'"{query}" not found in inventory, adding as new item. Please enter the name of the item.\nType /cancel to cancel.', 
                        reply_markup=ForceReply(selective=True), 
                        reply_to_message_id=update.message.message_id)
                    context.user_data['adding'] = query
                    return ADDING
        for item in items[:3]:
            description = ""
            if desc_prefix:
                description += desc_prefix
            description += f"<b>{item.name}</b>\n"
            if item.parent:
                if item.parent.parent:
                    description += f"Parent: {item.parent.name} -> {item.parent.parent.name}\n"
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
    
    async def returnBarcodesOrQueryFromUpdate(self, update: Update):
        if (update.message.photo):
            photoFileId = update.message.photo[-1].file_id
            photoFile = await self.application.bot.get_file(photoFileId)
            res = await photoFile.download_as_bytearray()
            barcodes_img = Image.open(io.BytesIO(res))
            barcodes = []
            for code in zxingcpp.read_barcodes(barcodes_img):
                barcodes.append(code.text)
            return barcodes
        elif (update.message.text):
            # if update.message.text.startswith("INV") or update.message.text.isnumeric():
            return [update.message.text]
        return None
    
    async def handle_barcode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ret = ConversationHandler.END # TODO: Really think if this is the best way to handle this?
        barcodes = await self.returnBarcodesOrQueryFromUpdate(update)
        if barcodes:
            for barcode in barcodes:
                ret = await self.showItemsInfo(update, barcode, context)
        else:
            await update.message.reply_html(
                f'No barcode found in the message, try again.', 
                reply_to_message_id=update.message.message_id)
        return ret

    async def adding(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = update.message.text
        barcode = context.user_data['adding']
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

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        res = self.dbSession.query(Entity).all()
        await update.message.reply_html(
            f"Hi, send me a photo of a barcode to add it to the inventory or show the details of existing items.\nYou can also type the barcode or ID directly.\nType /assign_parent to assign a parent to an item.\n"
        )
    def run_bot(self):
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def run_telegram_bot(dbSession) -> None:
    bot = TelegramInventoryBot(botToken, dbSession)
    bot.run_bot()

if __name__ == "__main__":
    run_telegram_bot(Session())