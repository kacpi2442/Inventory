from sqlalchemy import Column, MetaData, ForeignKey, Integer, String, Numeric, DateTime, LargeBinary, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class Entity(Base):
    __tablename__ = 'entity'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('entity.id'))
    name = Column(String(100), nullable=False)
    created = Column(DateTime)
    modified = Column(DateTime)

    barcodes = relationship('Barcode', backref='entity', lazy=True)
    children = relationship('Entity', back_populates="parent", lazy=True)
    parent = relationship('Entity', back_populates="children", remote_side=[id], lazy=True)
    ownerships = relationship('Ownership', backref='entity', lazy=True)
    properties = relationship('EntityProperties', backref='entity', lazy=True)
    photos = relationship('EntityPhoto', backref='entity', lazy=True)

class Property(Base):
    __tablename__ = 'property'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

class EntityProperties(Base):
    __tablename__ = 'entity_properties'

    entity_id = Column(Integer, ForeignKey('entity.id'), primary_key=True)
    property_id = Column(Integer, ForeignKey('property.id'), primary_key=True)
    value = Column(String(100))

    property = relationship('Property', lazy=True)

class EntityPhoto(Base):
    __tablename__ = 'entity_photo'

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entity.id'))
    image = Column(LargeBinary, nullable=False)

class Owner(Base):
    __tablename__ = 'owner'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

class Ownership(Base):
    __tablename__ = 'ownership'

    entity_id = Column(Integer, ForeignKey('entity.id'), primary_key=True)
    owner_id = Column(Integer, ForeignKey('owner.id'), primary_key=True)
    own = Column(Numeric(10,2), nullable=False)

    owner = relationship('Owner', lazy=True)

class Barcode(Base):
    __tablename__ = 'barcode'

    entity_id = Column(Integer, ForeignKey('entity.id'), primary_key=True)
    barcode = Column(String(100), unique=True, primary_key=True)

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=True)
    default_owner_id = Column(Integer, ForeignKey('owner.id'), nullable=True)

idx_entity_name = Index('idx_entity_name', Entity.name)
idx_property_name = Index('idx_property_name', Property.name)
idx_owner_name = Index('idx_owner_name', Owner.name)
