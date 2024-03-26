import json
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
from models import metadata, Entity, Barcode, EntityPhoto, EntityProperties, Property, Ownership, Owner
from datetime import datetime
import os
import base64
import traceback

basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance/inventory.db')

# Colors.
app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
db = SQLAlchemy(app, metadata=metadata)

items_per_page = 25

@app.route('/') 
def index():
    items = db.session.query(Entity).filter_by(parent_id=None).paginate(per_page=items_per_page)
    return render_template('base.html', items=items, owners=db.session.query(Owner).all()) # Todo: Order by number of children.

@app.route('/details/<int:item_id>', methods=['GET'])
def details(item_id):
    item = db.get_or_404(Entity, item_id)
    photos_base64 = []
    for photo in item.photos:
        photos_base64.append(base64.b64encode(photo.image).decode('utf-8'))
    children = db.session.query(Entity).filter_by(parent_id=item_id).paginate(per_page=items_per_page)
    search = request.args.get('q')
    return render_template('details.html', detailedItem=item, items=children, photos_base64=photos_base64, owners=db.session.query(Owner).all(), search=search)

def search_for_item(search, paginate=False):
    if search.startswith('@ '):
        deep_search = search[2:]
        query = db.session.query(Entity).filter((Entity.name.contains(deep_search)) |
                                    (Entity.barcodes.any(Barcode.barcode == deep_search)) |
                                    (Entity.properties.any(EntityProperties.value.contains(deep_search))))
    else:
        query = db.session.query(Entity).filter((Entity.name.contains(search)) | 
                                    (Entity.barcodes.any(Barcode.barcode == search)))
    if paginate:
        return query.paginate(per_page=items_per_page)
    return query.all()

# Search for items.
@app.route('/search', methods=['GET'])
def search():
    # search = request.form['search']
    search = request.args.get('q')
    items = search_for_item(search, paginate=True)
    # If there is only one item, redirect to its details.
    if items.total == 1:
        return redirect(url_for('details', item_id=items.items[0].id, q=search))
    
    # paginate the results using sqlalchemy.
    return render_template('base.html', items=items, search=search, show_parent=True, owners=db.session.query(Owner).all())

@app.route('/edit/<int:item_id>', methods=['GET'])
def edit(item_id):
    item = db.get_or_404(Entity, item_id)
    photos_base64 = []
    for photo in item.photos:
        photos_base64.append(base64.b64encode(photo.image).decode('utf-8'))
    properties = db.session.query(Property).all()
    owners = db.session.query(Owner).all()
    children = db.session.query(Entity).filter_by(parent_id=item_id).paginate(per_page=items_per_page)
    return render_template('edit.html', detailedItem=item, items=children, photos_base64=photos_base64, editing=True, properties=properties, owners=owners)

@app.route('/add', methods=['GET'])
def add():
    properties = db.session.query(Property).all()
    owners = db.session.query(Owner).all()
    return render_template('edit.html', adding=True, properties=properties, owners=owners)


@app.route('/update', methods=['POST'])
def update():
    # {"id":"4","name":"Testowy","barcode":["2137"],"parent":"3","ownerships":[{"owner":"1","own":"70.00"},{"owner":"2","own":"20.00"},{"owner":"New owner","own":"10"}],"properties":[{"property":"1","value":"68 kg"},{"property":"2","value":"175 cm"},{"property":"new prop","value":"new val"}]}
    try:
        data = json.loads(request.data)
        item_id = data['id']
        if item_id == '':
            # Create a new item.
            item = Entity(name=data['name'], created=datetime.now(), modified=datetime.now())
            db.session.add(item)
            db.session.commit()
            item = db.get_or_404(Entity, item.id)
        else:
            item = db.get_or_404(Entity, item_id)
        item.name = data['name']
        # Try to update the parent.
        if data['parent'] == '':
            item.parent_id = None
        else:
            # Get parent by barcode.
            parent = db.session.query(Entity).filter(Entity.barcodes.any(Barcode.barcode == data['parent'])).first()
            if parent is None:
                # Get parent by ID
                parent = db.get_or_404(Entity, data['parent'])
            item.parent_id = parent.id
        # Remove all the barcodes.
        barcodes = db.session.query(Barcode).filter_by(entity_id=item.id).all()
        for barcode in barcodes:
            db.session.delete(barcode)
        db.session.commit()
        # Add new barcodes
        if data['barcode'] != ['']:
            for barcode in data['barcode']:
                barcode = Barcode(entity_id=item.id, barcode=barcode)
                db.session.add(barcode)
        # Remove all the ownerships.
        ownerships = db.session.query(Ownership).filter_by(entity_id=item.id).all()
        for ownership in ownerships:
            db.session.delete(ownership)
        db.session.commit()
        
        if data['inherit']:
            # Remove all ownerships from children.
            for child in item.children:
                ownerships = db.session.query(Ownership).filter_by(entity_id=child.id).all()
                for ownership in ownerships:
                    db.session.delete(ownership)
                db.session.commit()
        # Add new ownerships.
        if data['ownerships'] != ['']:
            for ownership in data['ownerships']:
                if ownership['owner'] == '':
                    continue
                # if owner not a number, then it's a new owner.
                if not ownership['owner'].isdigit():
                    owner = Owner(name=ownership['owner'])
                    db.session.add(owner)
                    db.session.commit()
                    owner_id = owner.id
                else:
                    owner_id = ownership['owner']
                own = ownership['own']
                ownership = Ownership(entity_id=item.id, owner_id=owner_id, own=own)
                db.session.add(ownership)
                if data['inherit']:
                    # Add the same ownership to children.
                    for child in item.children:
                        ownership = Ownership(entity_id=child.id, owner_id=owner_id, own=own)
                        db.session.add(ownership)
            
        # Remove all the properties.
        properties = db.session.query(EntityProperties).filter_by(entity_id=item.id).all()
        for property in properties:
            db.session.delete(property)
        db.session.commit()
        # # Add new properties.
        if data['properties'] != ['']:
            for property in data['properties']:
                if property['property'] == '':
                    continue
                # if property not a number, then it's a new property.
                if not property['property'].isdigit():
                    new_property = Property(name=property['property'])
                    db.session.add(new_property)
                    db.session.commit()
                    property_id = new_property.id
                else:
                    property_id = property['property']
                value = property['value']
                property = EntityProperties(entity_id=item.id, property_id=property_id, value=value)
                db.session.add(property)
        # Update the modified date.
        item.modified = datetime.now()
        db.session.commit()
        return f"Item ID:{item.id} updated successfully.", 200
    except Exception as e:
        traceback.print_exc()
        return str(e), 400

# Add a new photo.
@app.route('/add_photo/<int:item_id>', methods=['POST'])
def add_photo(item_id):
    item = db.session.query(Entity).get(item_id)
    photo = request.files['photo']
    photo = EntityPhoto(entity_id=item_id, image=photo.read())
    db.session.add(photo)
    db.session.commit()
    # Update the modified date.
    item.modified = datetime.now()
    return redirect(url_for('index'))

def delete_item_props(item_id):
    # Remove all the barcodes.
    barcodes = db.session.query(Barcode).filter_by(entity_id=item_id).all()
    for barcode in barcodes:
        db.session.delete(barcode)
    # Remove all the ownerships.
    ownerships = db.session.query(Ownership).filter_by(entity_id=item_id).all()
    for ownership in ownerships:
        db.session.delete(ownership)
    # Remove all the properties.
    properties = db.session.query(EntityProperties).filter_by(entity_id=item_id).all()
    for property in properties:
        db.session.delete(property)
    # Remove all the photos.
    photos = db.session.query(EntityPhoto).filter_by(entity_id=item_id).all()
    for photo in photos:
        db.session.delete(photo)

@app.route('/delete/<int:item_id>', methods=['POST', 'GET']) # Old method for deleting single item.
def delete(item_id):
    item = db.session.query(Entity).get(item_id)
    if item.parent_id:
        parent_id = item.parent_id
    else:
        parent_id = None
    delete_item_props(item.id)
    # Remove the item.
    db.session.delete(item)
    db.session.commit()
    if parent_id is not None:
        return redirect(url_for('details', item_id=parent_id))
    return redirect(url_for('index'))

def select_all(request):
    path = request.referrer.split('?')[0].split('/')[3:] # Remove the http://localhost:5000/ or any other domain.
    if path == ['']:
        return "Modifying all root items in the database is not allowed", 406
    if path[0] == 'search':
        search_query = json.loads(request.data)['search']
        items = [item.id for item in search_for_item(search_query)]
        return items, 200.
    if (path[0] == 'details' or path[0] == 'edit') and path[1].isdigit():
        id = int(path[1])
        children = db.one_or_404(Entity, id).children
        items = [child.id for child in children]
        return items, 200
    return "Invalid request", 400

@app.route('/delete_multiple', methods=['POST'])
def delete_multiple():
    try:
        data = json.loads(request.data)
        items = data['selected']
        if items == -1: # If -1, all items are selected.
            selectAll = select_all(request)
            if selectAll[1] != 200:
                return selectAll
            items = selectAll[0]
        for item_id in items:
            item = db.get_or_404(Entity, item_id)
            delete_item_props(item.id)
            # Remove the item.
            db.session.delete(item)
        db.session.commit()
        return "Items deleted successfully.", 200
    except Exception as e:
        traceback.print_exc()
        return str(e), 400
    
@app.route('/change_ownership', methods=['POST'])
def change_ownership():
    try:
        data = json.loads(request.data)
        if data['owner_id'].isdigit():
            owner = db.get_or_404(Owner, data['owner_id'])
        else:
            owner = None
        items = data['selected']
        if items == -1: # If -1, all items are selected.
            selectAll = select_all(request)
            if selectAll[1] != 200:
                return selectAll
            items = selectAll[0]
        for item_id in items:
            item = db.get_or_404(Entity, item_id)
            # Remove all the ownerships.
            ownerships = db.session.query(Ownership).filter_by(entity_id=item.id).all()
            for ownership in ownerships:
                db.session.delete(ownership)
            # Add new ownership
            if owner is not None:
                ownership = Ownership(entity_id=item.id, owner_id=owner.id, own='100')
                db.session.add(ownership)
        db.session.commit()
        return f"Ownership updated successfully.", 200
    except Exception as e:
        traceback.print_exc()
        return str(e), 400

@app.route('/change_parent', methods=['POST'])
def change_parent():
    try:
        data = json.loads(request.data)
        if data['parent_id'].isdigit() and int(data['parent_id']) > 0:
            parent = db.get_or_404(Entity, data['parent_id'])
            parent_id = parent.id
        else:
            parent_id = None
        items = data['selected']
        if items == -1: # If -1, all items are selected.
            selectAll = select_all(request)
            if selectAll[1] != 200:
                return selectAll
            items = selectAll[0]
        for item_id in items:
            item = db.get_or_404(Entity, item_id)
            item.parent_id = parent_id
        db.session.commit()
        return f"Parent updated successfully.", 200
    except Exception as e:
        traceback.print_exc()
        return str(e), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()