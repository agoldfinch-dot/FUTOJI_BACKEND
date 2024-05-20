import os
import random
import json
import requests

from sql import *
from typing import Union
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from fastapi.responses import FileResponse, PlainTextResponse

SBIS_KEY = os.environ.get("SBIS_KEY")
app = FastAPI()

class Order(BaseModel):
    name: str
    lastName: Union[str, None] = None
    price: float = None
    phone: str
    nomenclature: list
    comment: Union[str, None] = None
    adress: str
    persons: int = 1
    paymentType: str 

def get_adress(adress):
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
    }  
    parameters = {
    'enteredAddress': adress,
    'pageSize': '5'
    }
    url = 'https://api.sbis.ru/retail/delivery/suggested-address?'  
    response = requests.get(url, params=parameters, headers=headers)

    adrJ = response.json()["addresses"][0]["addressJSON"]
    adrF = str(response.json()["addresses"][0]["addressFull"])
    return adrJ, adrF

def get_delivery(adress):
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
    }  
    parameters = {
    'adress': adress,
    'pointId': 250
    }
    url = 'https://api.sbis.ru/retail/delivery/cost?'  
    response = requests.get(url, params=parameters, headers=headers)

   
@app.get('/robots.txt', response_class=PlainTextResponse)
def robots():
    data = """User-agent: *\nDisallow: /"""
    return data

@app.post('/orders/create')
def create_order(order: Order):
    nomenclature = []
    for i, j in order.nomenclature:
        print(i)
        nomenclature.append({"id": int(i), "count":int(j), "priceListId":25})

    adrJ, adrF = get_adress(order.adress)
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
        'Content-Type': 'application/json'
    }  

    parameters = json.dumps({
        'product': 'delivery',
        'pointId': 250,
        'comment': order.comment,
        'customer': {"name": order.name, "lastname":order.lastName, "phone": order.phone},
        "datetime": "2024-05-20 20:50:20", # <-------- ЭТО ТОЖЕ НАДО ПОЛУЧАТЬ С МЕТОДА НО МНЕ БЫЛО ПОХ НАДО ИСПРАВИТЬ
        "nomenclatures": nomenclature, # <------- ЭТО ☠️
        "delivery": {"addressFull":adrF, "addressJSON": adrJ, "persons":order.persons,"changeAmount": order.price,"paymentType": order.paymentType, "isPickup": False}
    })
    url = 'https://api.sbis.ru/retail/order/create'  
    response = requests.post(url, data=parameters, headers=headers)
    return response.json()


@app.get("/categories")
def get_Categories():
    categories = {'data': []}
    for i, j in get_all_categories():
        categories['data'].append({'name': j, 'id':i})
    return categories
    

@app.get("/categories/getById")
def get_Category(id: Union[str, None] = None):
    if id == None: 
        raise HTTPException(404,{"error":"No id"})
    category = {'data':[]}
    for id, name, price, img, ingredients, description, mass in get_dishes_by_parent_id(id):
        category['data'].append({'id':id, 'name': name, 'price': price, 'image': f'/images/getById?q={id}'if not img == None else None , 'ingredients': ingredients, 'description': description, 'mass': mass})
    if category == {'data':[]}:
        raise HTTPException(404,{"error":"No data"})
    return category

@app.get("/products/getById")
def get_Product_by_id(q: Union[str, None] = None):
    product = {}
    ans = get_dish_info_by_child_id(q)
    if ans == None:
        raise HTTPException(404,{"error": "No such product"})
    id, name, price, img, ingredients, description, mass = get_dish_info_by_child_id(q)
    product['name'] = name
    product['id'] = id
    product['price'] = float(price)
    product['ingredients'] = ingredients
    product['picture'] = f'/images/getById?q={id}' if img != None else None
    product['about'] = description
    product['mass'] = mass
    return {'data': product}

@app.get("/products/getByName")
def get_Product_by_name(s: Union[str, None] = None):
    if s == None: 
        raise HTTPException(404,{"error":"No search params"})
    dishes = {'data': []}
    dishesArr = get_dishs_by_name(s)
    if dishesArr == None:
        raise HTTPException(404,{'data': []})
    for id, name, price, img, ingredients, description, mass in dishesArr:
        dishes['data'].append({'id':id, 'name': name, 'price': price, 'image': f'/images/getById?q={id}' if not img == None else None , 'ingrediensts': ingredients, 'description': description, 'mass': mass})
    return dishes

@app.get("/images/getById")
def get_Product_by_id(q: Union[str, None] = None):
    if os.path.isfile(f"./img/{q}.jpg"):
        f = open(f"./img/{q}.jpg", "rb")
        return Response(f.read(), media_type='image/jpeg')
    link = get_image_by_child_id(q)[0]
    headers = {"X-SBISAccessToken": SBIS_KEY} 
    response = requests.get(f"https://api.sbis.ru/retail{link}", headers=headers)
    with open(f'./img/{q}.jpg', 'wb') as f:
        f.write(response.content)
    return Response(response.content, media_type='image/jpeg')