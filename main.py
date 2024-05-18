import os
import random
import json
import requests

from sql import *
from typing import Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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

@app.post('/orders/create')
def create_order(order: Order):
    nomenclature = []
    for i, j in order.nomenclature:
        nomenclature.append({"id": i, "count":j, "priceListId":8})

    adrJ, adrF = get_adress(order.adress)
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
        'Content-Type': 'application/json'
    }  

    parameters = json.dumps({
        'product': 'delivery',
        'pointId': 250,
        'comment': order.comment,
        'customer': {"name": order.name,"lastname":order.lastName,"phone": order.phone},
        "datetime": "2024-05-17 20:50:20", # <-------- ЭТО ТОЖЕ НАДО ПОЛУЧАТЬ С МЕТОДА НО МНЕ БЫЛО ПОХ НАДО ИСПРАВИТЬ
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
    for id, name, price in get_dishes_by_parent_id(id):
        category['data'].append({'name': name, 'price': price, 'id':id })
    if category == {'data':[]}:
        raise HTTPException(404,{"error":"No data"})
    return category

@app.get("/products/getById")
def get_Categories(q: Union[str, None] = None):
    product = {}
    ans = get_dish_info_by_child_id(q)
    if ans == None:
        raise HTTPException(404,{"error": "No such product"})
    name, price, id = get_dish_info_by_child_id(q)
    product['name'] = name
    product['id'] = id
    product['price'] = float(price)
    product['picture'] = "https://sun9-14.userapi.com/impg/Rr7AgZU1FaSq3MHF77kwc0BE8QT0YzyjTcaTkw/AqoBzUhFsOw.jpg?size=1664x1920&quality=96&sign=6b430cb8f37a8f44dde401595205d5b3&type=album"
    product['about'] = 'инновационный продукт крч все дела ага да 3121гоыалл оыаоыавоыао'
    product['mass'] = f'{random.randint(0,41243)}г'
    return {'data': product}

@app.get("/products/getByName")
def get_Dishes(s: Union[str, None] = None):
    if s == None: 
        raise HTTPException(404,{"error":"No search params"})
    dishes = {'data': []}
    dishesArr = get_dishs_by_name(s)
    if dishes == None:
        raise HTTPException(404,{'data': []})
    for name, price, id in dishesArr:
        dishes['data'].append({'name':name,'price':float(price), 'id': id})
    return dishes

