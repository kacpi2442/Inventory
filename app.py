import json
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
from datetime import datetime
import os
import base64

basedir = os.path.abspath(os.path.dirname(__file__))

# Colors.
app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'instance/inventory.db')
db = SQLAlchemy(app)

class Entity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('entity.id'))
    name = db.Column(db.String(100), nullable=False)
    created = db.Column(db.DateTime())
    modified = db.Column(db.DateTime())
    barcodes = db.relationship('Barcode', backref='entity', lazy=True)
    children = db.relationship('Entity', back_populates="parent", lazy=True)
    parent = db.relationship('Entity', back_populates="children", remote_side=[id], lazy=True)
    ownerships = db.relationship('Ownership', backref='entity', lazy=True)
    properties = db.relationship('EntityProperties', backref='entity', lazy=True)
    photos = db.relationship('EntityPhoto', backref='entity', lazy=True)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class EntityProperties(db.Model):
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), primary_key=True)
    value = db.Column(db.String(100))
    property = db.relationship('Property', lazy=True)

class EntityPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'))
    image = db.Column(db.LargeBinary, nullable=False)

class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Ownership(db.Model):
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), primary_key=True)
    own = db.Column(db.Numeric(10,2), nullable=False)
    owner = db.relationship('Owner', lazy=True)

class Barcode(db.Model):
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'))
    barcode = db.Column(db.String(100), unique=True, primary_key=True)

idx_entity_name = Index('idx_entity_name', Entity.name)
idx_property_name = Index('idx_property_name', Property.name)
idx_owner_name = Index('idx_owner_name', Owner.name)

app_header = 'Inventory'

@app.route('/') 
def index():
    return render_template('index.html', items=Entity.query.all(), header=app_header)

@app.route('/details/<int:item_id>', methods=['GET'])
def details(item_id):
    item = db.get_or_404(Entity, item_id)
    # Get the image. TODO: Handle multiple images.
    image = None
    for image_data in item.photos:
        image = base64.b64encode(image_data.image).decode('utf-8')
    return render_template('details.html', detailedItem=item, header=item.name, items=item.children, image=image)

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

# Update one selected property.
@app.route('/update_property/<int:item_id>', methods=['POST'])
def update_property(item_id):
    item = Entity.query.get(item_id)
    property_id = request.form['property']
    value = request.form['value']
    # Check if the property already exists.
    existing = db.session.query(EntityProperties).filter(EntityProperties.entity_id==item_id, EntityProperties.property_id==property_id).first()
    if existing:
        existing.value = value
    else:
        new_property = EntityProperties(entity_id=item_id, property_id=property_id, value=value)
        db.session.add(new_property)
    # Update the modified date.
    item.modified = datetime.now()
    db.session.commit()
    return redirect(url_for('index'))

# Add a new photo.
@app.route('/add_photo/<int:item_id>', methods=['POST'])
def add_photo(item_id):
    item = Entity.query.get(item_id)
    photo = request.files['photo']
    photo = EntityPhoto(entity_id=item_id, image=photo.read())
    db.session.add(photo)
    db.session.commit()
    # Update the modified date.
    item.modified = datetime.now()
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
