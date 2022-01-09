from database import global_db, Users, FoodDelivery, FoodDeliveryProducts, Products, Restaurant
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from time import sleep
from datetime import datetime
import sys
import hashlib
import random
import base64
sys.path.append("..")


def create_app():
    sleep(5)

    app = Flask(__name__)
    CORS(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:secret@mysql/restaurant'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CORS_HEADERS'] = 'Content-Type'
    app.app_context().push()

    db = global_db

    return app, db


app, db = create_app()


db.init_app(app)
db.create_all()

######################## Registration ############################


@app.route('/auth/register', methods=['POST'])
def register():
    if not request.is_json:
        return Response(status=400)

    payload = request.get_json(silent=True)

    if not payload:
        return Response(status=400)

    fields = ['address', 'email', 'password']

    for field in fields:
        if field not in payload:
            return Response(f'You did not send the {field}!', status=400)

        if payload[field] is None:
            return Response(f'Field {field} contains incorrect data!', status=400)

    hashed_password = hashlib.md5(payload['password'].encode()).hexdigest()

    user = Users(
        address=payload['address'], email=payload['email'], password=hashed_password,
    )

    db.session.add(user)

    try:
        db.session.commit()
    except Exception as e:
        return Response('Email already exists!', status=409)

    return jsonify({'user_id': user.user_id}), 201


######################## Log in ############################

@app.route("/auth/login", methods=["POST"])
def login():
    if not request.is_json:
        return Response(status=400)

    payload = request.get_json(silent=True)

    if not payload:
        return Response(status=400)

    fields = [
        'email', 'password'
    ]

    for field in fields:
        if field not in payload:
            return Response(f'You did not send the {field}!', status=400)

        if payload[field] is None:
            return Response(f'Field {field} contains incorrect data!', status=400)

    user = db.session.query(Users).filter(
        Users.email == payload['email']).first()
    if not user:
        return Response('User not found!', status=400)

    hashed_password = hashlib.md5(payload['password'].encode()).hexdigest()

    if (user.password != hashed_password):
        return Response('Wrong password!', status=401)

    user.is_logged_in = True
    db.session.commit()

    return Response('The user has successfully logged in!', status=200)

############################# Make orders #########################################

# Verifica daca parametrul este de tip float


def isfloat(value):
    return type(value) == float

# Verifica daca parametrul este de tip int


def isint(value):
    return type(value) == int


def check_user_logged(user_id):
    # check if the user exist
    user = Users.query.filter_by(user_id=user_id).first()
    if user is None:
        return Response(status=404), True

    # check if the user is logged in
    if not user.is_logged_in:
        return Response(status=403), True
    return user, False


@app.route("/delivery/add_food_delivery", methods=["POST"])
def post_food_delivery():
    payload = request.get_json(silent=True)
    # check if the json received is corect
    if not payload or "user_id" not in payload or "products" not in payload or not isint(payload["user_id"]):
        return Response(status=400)

    # check if the user is logged in
    user, failed = check_user_logged(payload["user_id"])
    if failed:
        return user

    # compute the order
    order = FoodDelivery()
    order.user_id = payload["user_id"]
    if "address" in payload:
        order.address = payload["address"]
    else:
        order.address = user.address

    # compute the price
    order.price = 0.0
    for product in payload["products"]:
        # check if the product id and quantity is an int
        if not isint(product["product_id"]) or not isint(product["quantity"]):
            return Response(status=400)

        # check if the product exist
        prod = Products.query.filter_by(
            product_id=product["product_id"]).first()
        if prod is None:
            return Response(status=404)

        # if the quantity is 0 skip
        if product["quantity"] == 0:
            continue

        if product["quantity"] > prod.quantity:
            return Response(status=423)

        prod.quantity -= product["quantity"]
        db.session.add(prod)

        # add the price of the product
        order.price += prod.price * product["quantity"]

    # place order
    db.session.add(order)
    db.session.commit()

    # add ordered products
    for product in payload["products"]:
        if product["quantity"] == 0:
            continue
        prod = FoodDeliveryProducts()
        prod.delivery_id = order.delivery_id
        prod.product_id = product["product_id"]
        prod.quantity = product["quantity"]
        db.session.add(prod)

    db.session.commit()
    return jsonify({"delivery_id": order.delivery_id}), 201


@app.route("/delivery/delivered_food", methods=["PUT"])
def delivered_food():
    payload = request.get_json(silent=True)
    # check if the json received is corect
    if not payload or "user_id" not in payload or "delivery_id" not in payload \
            or not isint(payload["user_id"]) or not isint(payload["delivery_id"]):
        return Response(status=400)

    # check if the user is logged in
    user, failed = check_user_logged(payload["user_id"])
    if failed:
        return user

    # check if the order exist
    order = FoodDelivery.query.filter_by(
        delivery_id=payload["delivery_id"]).first()
    if order is None:
        return Response(status=404)

    # check if it is the owner of the order
    if order.user_id != user.user_id:
        return Response(status=403)

    # check if the order it still available
    if order.canceled:
        return Response(status=409)

    # update the order
    order.delievered = True
    db.session.commit()
    return Response(status=200)


@app.route("/delivery/canceled_food_delivery", methods=["PUT"])
def canceled_food_delivery():
    payload = request.get_json(silent=True)
    # check if the json received is corect
    if not payload or "user_id" not in payload or "delivery_id" not in payload \
            or not isint(payload["user_id"]) or not isint(payload["delivery_id"]):
        return Response(status=400)

    # check if the user is logged in
    user, failed = check_user_logged(payload["user_id"])
    if failed:
        return user

    # check if the order exist
    order = FoodDelivery.query.filter_by(
        delivery_id=payload["delivery_id"]).first()
    if order is None:
        return Response(status=404)

    # check if it is the owner of the order
    if order.user_id != user.user_id:
        return Response(status=403)

    # check if the order it still available to be canceled
    if order.delievered:
        return Response(status=409)

    # update the order
    order.canceled = True
    db.session.commit()
    return Response(status=200)


def make_products(orderedProducts):
    final_products = []

    for orderedProduct in orderedProducts:
        product = Products.query.filter_by(
            product_id=orderedProduct.product_id).first()

        new_product = {
            "product_id": product.product_id,
            "restaurant_id": product.restaurant_id,
            "name": product.name,
            "price": str(product.price),
            "description": product.description,
            "image": product.image,
            "quantity": orderedProduct.quantity
        }

        final_products.append(new_product)

    return final_products


def make_order(orders):
    # compute the orders in the final json structure
    final_orders = []
    for order in orders:
        order_dict = dict()
        order_dict["delivery_id"] = order.delivery_id
        order_dict["user_id"] = order.user_id
        order_dict["address"] = order.address
        order_dict["price"] = order.price
        order_dict["delievered"] = order.delievered
        order_dict["canceled"] = order.canceled

        orderedProducts = FoodDeliveryProducts.query.filter_by(
            delivery_id=order.delivery_id).all()
        order_dict["products"] = make_products(orderedProducts)

        final_orders.append(order_dict)

    return jsonify(final_orders)


@app.route("/delivery/get_ordered_food", methods=["GET"])
def get_ordered_food():
    # get all orders
    orders = FoodDelivery.query.all()

    return make_order(orders), 200


@app.route("/delivery/get_delivered_food/<int:user_id>", methods=["GET"])
def get_delivered_food(user_id):

    # check if the user is logged in
    user, failed = check_user_logged(user_id)
    if failed:
        return user

    # get all orders
    orders = FoodDelivery.query.filter_by(user_id=user_id).all()

    return make_order(orders), 200


# --------Adaugare/afisare restaurante------
@app.route('/restaurant/add', methods=['POST'])
def add_restaurant():

    if not request.is_json:
        return Response(status=400)

    payload = request.get_json(silent=True)

    if not payload:
        return Response(status=400)

    fields = ['name', 'description', 'image']

    for field in fields:
        if field not in payload:
            return Response(status=400)

        if payload[field] is None:
            return Response(status=400)

    new_restaurant = Restaurant(
        name=payload['name'], description=payload['description'], image=base64.b64decode(payload['image']))

    db.session.add(new_restaurant)

    try:
        db.session.commit()
    except:
        return Response(status=409)

    return jsonify(restaurant_id=new_restaurant.restaurant_id), 201


@app.route('/restaurant/list', methods=['GET'])
def get_restaurants():

    restaurants = Restaurant.query.all()
    all_restaurants = []

    for restaurant in restaurants:

        new_restaurant = {
            "restaurant_id": restaurant.restaurant_id,
            "name": restaurant.name,
            "description": restaurant.description,
            "image": restaurant.image
        }

        all_restaurants.append(new_restaurant)

    return jsonify(all_restaurants), 200

# --------Adaugare/afisare produse----------------


@app.route('/product/add', methods=['POST'])
def add_product():

    if not request.is_json:
        return Response(status=400)

    payload = request.get_json(silent=True)

    if not payload:
        return Response(status=400)

    fields = ['restaurant_id', 'name', 'price',
              'quantity', 'image', 'description']

    for field in fields:
        if field not in payload:
            return Response(status=400)

        if payload[field] is None:
            return Response(status=400)

    if (not isint(payload['quantity'])) or (not isfloat(payload['price'])):
        return Response(status=400)

    if payload['quantity'] < 0 or payload['price'] < 0:
        return Response(status=400)

    new_product = Products(category_id=payload['category_id'], name=payload['name'], price=payload['price'],
                           quantity=payload['quantity'], image=payload['image'], description=payload['description'])

    db.session.add(new_product)

    try:
        db.session.commit()
    except:
        return Response(status=409)

    return jsonify(product_id=new_product.product_id), 201


@app.route('/product/<int:product_id>', methods=['GET'])
def get_product_by_id(product_id):

    product_info = Products.query.get(product_id)
    if product_info is None:
        return Response(status=404)

    product_information = {
        "category_id": product_info.category_id,
        "name": product_info.name,
        "price": str(product_info.price),
        "description": product_info.description,
        "image": product_info.image
    }

    return jsonify(product_information), 200


@app.route('/product/list', methods=['GET'])
def get_products():

    products = Products.query.all()
    all_products = []

    for product in products:

        new_product = {
            "product_id": product.product_id,
            "category_id": product.category_id,
            "name": product.name,
            "price": str(product.price),
            "description": product.description,
            "image": product.image
        }

        all_products.append(new_product)

    return jsonify(all_products), 200


@app.route('/product/list/<int:restaurant_id>', methods=['GET'])
def get_products_by_restaurant(restaurant_id):

    products = Products.query.filter_by(restaurant_id=restaurant_id).all()
    all_products = []

    for product in products:

        new_product = {
            "product_id": product.product_id,
            "category_id": product.category_id,
            "name": product.name,
            "price": str(product.price),
            "description": product.description,
            "image": product.image
        }

        all_products.append(new_product)

    return jsonify(all_products), 200


@app.route('/recommend/', methods=['GET'])
def get_recommendation_by_user():

    products = Products.query.filter_by().all()
    products = random.shuffle(products)[:5]

    all_products = []

    for product in products:

        new_product = {
            "product_id": product.product_id,
            "category_id": product.category_id,
            "name": product.name,
            "price": str(product.price),
            "description": product.description,
            "image": product.image
        }

        all_products.append(new_product)

    return jsonify(all_products), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
