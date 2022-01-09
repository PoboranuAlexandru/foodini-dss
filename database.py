from flask_sqlalchemy import SQLAlchemy
from time import sleep

sleep(10)
global_db = SQLAlchemy()


class Users(global_db.Model):
    __tablename__ = 'Users'
    user_id = global_db.Column(global_db.Integer, primary_key=True)
    address = global_db.Column(global_db.String(200), nullable=False)
    email = global_db.Column(global_db.String(100), unique=True)
    password = global_db.Column(global_db.String(100), nullable=False)
    is_logged_in = global_db.Column(
        global_db.Boolean, default=False, nullable=False)


class Restaurant(global_db.Model):
    __tablename__ = 'Restaurant'
    restaurant_id = global_db.Column(global_db.Integer, primary_key=True)
    name = global_db.Column(global_db.String(100))
    description = global_db.Column(global_db.String(100))
    image = global_db.Column(global_db.LargeBinary)


class Products(global_db.Model):
    __tablename__ = 'Products'
    product_id = global_db.Column(global_db.Integer, primary_key=True)
    restaurant_id = global_db.Column(
        global_db.Integer, global_db.ForeignKey('Restaurant.restaurant_id'))
    name = global_db.Column(global_db.String(100))
    price = global_db.Column(global_db.Float)
    quantity = global_db.Column(global_db.Integer)
    image = global_db.Column(global_db.LargeBinary)
    description = global_db.Column(global_db.String(100))


class FoodDelivery(global_db.Model):
    __tablename__ = 'FoodDelivery'
    delivery_id = global_db.Column(
        global_db.Integer(), primary_key=True, autoincrement=True)
    user_id = global_db.Column(
        global_db.Integer, global_db.ForeignKey('Users.user_id'), nullable=False)
    canceled = global_db.Column(global_db.Boolean(), default=False)
    address = global_db.Column(global_db.String(255), nullable=False)
    discount_id = global_db.Column(global_db.Integer, global_db.ForeignKey(
        'Discounts.discount_id'), nullable=False)
    price = global_db.Column(global_db.Float(), nullable=False)
    delievered = global_db.Column(global_db.Boolean(), default=False)


class FoodDeliveryProducts(global_db.Model):
    __tablename__ = 'FoodDeliveryProducts'
    delivery_id = global_db.Column(global_db.Integer(), global_db.ForeignKey(
        'FoodDelivery.delivery_id'), primary_key=True)
    product_id = global_db.Column(global_db.Integer(), global_db.ForeignKey(
        'Products.product_id'), primary_key=True)
    quantity = global_db.Column(global_db.Integer(), nullable=False)
