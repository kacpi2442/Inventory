from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Colors.
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
db = SQLAlchemy(app)

class Entity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    parent = db.Column(db.Integer)
    created = db.Column(db.DateTime())
    modified = db.Column(db.DateTime())

class Barcode(db.Model):
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), primary_key=True)
    barcode = db.Column(db.String(100))


@app.route('/') 
def index():
    items = Entity.query.all()
    for item in items:
        barcode = Barcode.query.filter_by(entity_id=item.id).first()
        item.barcode = barcode.barcode if barcode else None
        item.parent = Entity.query.get(item.parent).name if item.parent else None
    return render_template('index.html', items=items)

@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    parent = request.form['parent']
    # Current timestamp as for created and modified.
    modified = created = datetime.now()
    entity = Entity(name=name, parent=parent, created=created, modified=modified)
    # Get the last inserted id.
    db.session.add(entity)
    db.session.commit()
    entity_id = entity.id
    # Add barcode.
    barcode = request.form['barcode']
    barcode = Barcode(entity_id=entity_id, barcode=barcode)
    db.session.add(barcode)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/update/<int:item_id>', methods=['POST'])
def update(item_id):
    item = Entity.query.get(item_id)
    item.name = request.form['name']
    item.parent = request.form['parent']
    item.modified = datetime.now()
    db.session.commit()
    # Update barcode.
    barcode = Barcode.query.filter_by(entity_id=item_id).first()
    barcode.barcode = request.form['barcode']
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    item = Entity.query.get(item_id)
    db.session.delete(item)
    db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    #db.create_all()
    app.run()
