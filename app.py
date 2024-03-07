from inventory_flask import app, db
from sqlalchemy.orm import Session
from telegram_inventory import run_bot_threaded

async def run_flask_app():
    app.run()

if __name__ == '__main__':
    #db.create_all()
    with app.app_context():
        with Session(db.engine) as session:
            run_bot_threaded(session)
    app.run()
