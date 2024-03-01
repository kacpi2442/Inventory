from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
from datetime import datetime

# Colors.
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
db = SQLAlchemy(app)

class Entity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent = db.Column(db.Integer, db.ForeignKey('entity.id'))
    name = db.Column(db.String(100), nullable=False)
    created = db.Column(db.DateTime())
    modified = db.Column(db.DateTime())

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class EntityProperties(db.Model):
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), primary_key=True)
    value = db.Column(db.String(100))

class EntityPhoto(db.Model):
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), primary_key=True)
    image = db.Column(db.LargeBinary, nullable=False)

class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Ownership(db.Model):
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), primary_key=True)
    own = db.Column(db.Numeric(10,2), nullable=False)

class Barcode(db.Model):
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), primary_key=True)
    barcode = db.Column(db.String(100), unique=True)

idx_entity_name = Index('idx_entity_name', Entity.name)
idx_property_name = Index('idx_property_name', Property.name)
idx_owner_name = Index('idx_owner_name', Owner.name)

app_header = 'Inventory'

@app.route('/') 
def index():
    items = Entity.query.all()
    for item in items:
        barcode = Barcode.query.filter_by(entity_id=item.id).first()
        item.barcode = barcode.barcode if barcode else None
        if item.parent:
            if db.session.get(Entity, item.parent):
                item.parent = db.session.get(Entity, item.parent).name
            else:
                item.parent = "Location not found"
        else:
            item.parent = None
        # item.created = item.created.strftime('%Y-%m-%d %H:%M:%S')
        # item.modified = item.modified.strftime('%Y-%m-%d %H:%M:%S')
        ownership = Ownership.query.filter_by(entity_id=item.id).first() # Todo: Handle multiple owners.
        item.own = ownership.own if ownership else None
        if item.own == 100:
            owner = Owner.query.get(ownership.owner_id)
            item.owner_name = owner.name if owner else None
        elif item.own:
            item.owner_name = 'Shared'
        else:
            item.owner_name = None
    return render_template('index.html', items=items, header=app_header)

@app.route('/details/<int:item_id>', methods=['GET'])
def details(item_id):
    item = Entity.query.get(item_id)
    barcode = Barcode.query.filter_by(entity_id=item.id).first()
    item.barcode = barcode.barcode if barcode else None
    item.parent = db.session.get(Entity, item.parent).name if item.parent else None
    item.created = item.created.strftime('%Y-%m-%d %H:%M:%S')
    item.modified = item.modified.strftime('%Y-%m-%d %H:%M:%S')
    ownership = Ownership.query.filter_by(entity_id=item.id).first()
    return render_template('details.html', item=item, ownership=ownership)

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
