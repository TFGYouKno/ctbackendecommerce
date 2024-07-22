from flask import Flask, jsonify, request
#Flask class gives us all the tools needed to create a flask app (web app) by creating an instance of the flask class
#jsonify - Converts data into JSON format
#request- allows us to interact with HTTP method requests as objects
from flask_sqlalchemy import SQLAlchemy
#SQLAlchemy - ORM to connectand relate Python clases to database tables
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
#DeclarativeBase - gives us the base model functionality to create the classes as models for database tables, also tracks the metadata for our tables and classes.
#Mapped - maps a class attribute to a table column in the database (or relationship)
#mapped_column - creates a specific column in a table, sets our columns and allows us to add any necessary constraints (unique, nullable, prmary_key, etc)
from flask_marshmallow import Marshmallow
#Marshmallow - allows us to create schema to validate, serialize, and deserialize JSON data
from datetime import date
#date - use this to create datetime objects
from typing import List
# List - is used to create a relationship that will return a list of objects
from marshmallow import ValidationError, fields
#ValidationError - allows us to create custom error messages
#fields - allows us to set a schema field which includes data types and constraints
from sqlalchemy import select, delete
#select - acts as our SELECTFROM query
#delete - acts as our DELETE query
from sqlalchemy import Column, Integer, String, ForeignKey, Table

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:rootroot1!@localhost/ecom'

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)

class Customer(Base):
    __tablename__ = 'customer'
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(db.String(75), nullable=False)
    email: Mapped[str] = mapped_column(db.String(150))
    phone: Mapped[str] = mapped_column(db.String(16))
    address: Mapped[str] = mapped_column(db.String(150))

    #create a one-to-many relationship between customer and orders
    orders: Mapped[List['Orders']] = db.relationship(back_populates='customer') #back populates ensures both ends of this relationship have access to this information

order_products = db.Table(
    'order_products',
    Base.metadata,
    db.Column('order_id', db.ForeignKey('orders.id'), primary_key=True),
    db.Column('product_id', db.ForeignKey('products.id'), primary_key=True)
)

class Orders(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('customer.id'))
    
    #create a many-to-one relationship between orders and customer
    customer: Mapped['Customer'] = db.relationship(back_populates='orders')
    #create a many-to-many relationship between orders and products
    products: Mapped[List['Products']] = db.relationship(secondary=order_products)

class Products(Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)


with app.app_context():
    #db.drop_all() #drops (deletes) all tables in db
    db.create_all() # first checks if table exists, if not it creates it. Won't overwrite existing tables

class CustomerSchema(ma.Schema):
    id = fields.Integer(required=False)
    customer_name = fields.String(required=True)
    email = fields.String()
    phone = fields.String()
    address = fields.String()

    class Meta:
        fields = ('id', 'customer_name', 'email', 'phone', 'address')


class OrdersSchema(ma.Schema):
    id = fields.Integer(required= False)
    order_date = fields.Date(required= False)
    customer_id = fields.Integer(required= True)

    class Meta:
        fields = ('id', 'order_date', 'customer_id', 'items') #items will be product IDs associated with order

class ProductsSchema(ma.Schema):
    id = fields.Integer(required=False)
    product_name = fields.String(required=True)
    price = fields.Float(required=True)

    class Meta:
        fields = ('id', 'product_name', 'price')


customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

order_schema = OrdersSchema()
orders_schema = OrdersSchema(many=True)

product_schema = ProductsSchema()
products_schema = ProductsSchema(many=True)

@app.route('/')
def home():
    return "Welcome to the E-Commerce API!"

# get all customers
@app.route('/customer', methods=['GET'])
def get_customers():
    query = select(Customer)
    result = db.session.execute(query).scalars()#executes query and converts each row object into scalar object (python usable object)
    customers = result.all()

    return customers_schema.jsonify(customers)


# get a single customer, dynamic route by ID
@app.route('/customer/<int:id>', methods=['GET'])
def get_customer(id):
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalars().first() #grabs first object from data returned
    if result is None:
        return jsonify({'message': 'Customer not found'}), 404
    
    return customer_schema.jsonify(result)

# add a customer (POST)
@app.route('/customer', methods=['POST'])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_customer = Customer(customer_name=customer_data['customer_name'], email=customer_data['email'], phone=customer_data['phone'], address=customer_data['address'])
    db.session.add(new_customer)
    db.session.commit()

    return jsonify({'message': 'Customer added successfully!'}), 201

# update a customer (PUT)
@app.route('/customer/<int:id>', methods=['PUT'])
def update_customer(id):
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalars().first()
    if result is None:
        return jsonify({'Error': 'Customer not found'}), 404
    
    customer = result
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    for field, value in customer_data.items():
        setattr(customer, field, value)

    db.session.commit()
    return jsonify({'message': 'Customer details updated successfully!'}), 200

# delete a customer (DELETE)
@app.route('/customer/<int:id>', methods=['DELETE'])
def delete_customer(id):
    query = delete(Customer).where(Customer.id == id) #DELETE FROM customer WHERE id = id
    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({'Error': 'Customer not found'}), 404
    
    db.session.commit()
    return jsonify({'message': 'Customer OBLITERATED successfully!'}), 200

#======================== PRODUCT INTERACTIONS ========================

# adding a new product
@app.route('/products', methods=['POST'])
def add_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_product = Products(product_name=product_data['product_name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()

    return jsonify({'message': 'New product added successfully!'}), 201

    #get all products
@app.route('/products', methods=['GET'])
def get_products():
    query = select(Products)
    result = db.session.execute(query).scalars()#executes query and converts each row object into scalar object (python usable object)
    products = result.all()

    return products_schema.jsonify(products)

#get a product by ID
@app.route('/products/<int:id>', methods = ['GET'])
def get_product(id):
    query = select(Products).where(Products.id == id)
    result = db.session.execute(query).scalars().first()
    if result is None:
        return jsonify({'Error' : 'Product was not found, please try again!'}), 404
    
    return product_schema.jsonify(result)

# update a product by ID (PUT)
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    query = select(Products).where(Products.id == id)
    result = db.session.execute(query).scalars().first()
    if result is None:
        return jsonify({'Error': 'Product not found'}), 404
    
    product = result
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    for field, value in product_data.items():
        setattr(product, field, value)

    db.session.commit()
    return jsonify({'message': 'Product details updated successfully!'}), 200

#remove a product by ID
@app.route('/products/<int:id>', methods=['DELETE'])
def remove_product(id):
    query = delete(Products).where(Products.id == id) 
    result = db.session.execute(query)
    if result.rowcount == 0:
        return jsonify({"Error": "Product not in the database, please try again."})
    db.session.commit()
    return jsonify({"Message": "Product successfully removed"})


#==============================ORDER INTERACTIONS=======================

@app.route('/orders', methods=['POST'])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_order = Orders(order_date= date.today(), customer_id=order_data['customer_id'])

    for item_id in order_data['items']:
        query = select(Products).filter(Products.id == item_id)
        item = db.session.execute(query).scalar()
        new_order.products.append(item)

    db.session.add(new_order)
    db.session.commit()
    return jsonify({'message': 'Order placed successfully!'}), 201

#get an order by order ID
@app.route('/order_items/<int:id>', methods=['GET'])
def order_items(id):
    query = select(Orders).filter(Orders.id == id)
    order = db.session.execute(query).scalar()

    return products_schema.jsonify(order.products)

#remove an order by order ID
@app.route("/orders/<int:id>", methods=['DELETE'])
def remove_order(id):
    query = delete(Orders).where(Orders.id == id)
    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({'Error': 'Order not found'}), 404
    
    db.session.commit()
    return jsonify({'message': 'Order successfully removed!'}), 200


if __name__ == '__main__':
    app.run(debug=True)
    
