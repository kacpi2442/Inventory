from inventory_flask import app, db

async def run_flask_app():
    app.run()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
