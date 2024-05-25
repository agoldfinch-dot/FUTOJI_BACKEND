import os
import random
import json
import requests

from sql import *
from typing import Union
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fastapi.responses import FileResponse, PlainTextResponse

SBIS_KEY = os.environ.get("SBIS_KEY")
app = FastAPI()


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    for i in order.nomenclature:
        nomenclature.append({"id": int(i['id']), "count":int(i['count']), "priceListId":25, 'modifiers': i.get("modifiers", None)})

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
        "datetime": "2024-05-28 15:50:20", # <-------- ЭТО ТОЖЕ НАДО ПОЛУЧАТЬ С МЕТОДА НО МНЕ БЫЛО ПОХ НАДО ИСПРАВИТЬ
        "nomenclatures": nomenclature, # <------- ЭТО ☠️
        "delivery": {"addressFull":adrF, "addressJSON": adrJ, "persons":order.persons,"changeAmount": order.price,"paymentType": order.paymentType, "isPickup": False}
    })
    url = 'https://api.sbis.ru/retail/order/create'  
    response = requests.post(url, data=parameters, headers=headers)
    return response.json()


@app.get("/categories")
def get_Categories():
    categories = {'data': []}
    for id, name in get_all_main_categories():
        category = {'name': name, 'id':id, "subCategories": []}
        for s_id, s_name in get_sub_categories(id):
            category['subCategories'].append({"id": s_id, "name": s_name})
        categories['data'].append(category)
    return categories
    
@app.get("/subCategories")
def get_sub_category(q: Union[str, None] = None):
    if q == None: 
        raise HTTPException(404, {"error":"No id"})
    sub_category = []
    subArr = get_sub_categories(q)
    if subArr == []:
        raise HTTPException(404, {"error": "No subcategories by this id"})
    for s_id, s_name in subArr:
        sub_category.append({"id": s_id, "name": s_name})
    return {'data': sub_category}

@app.get("/categories/getById")
def get_Category(q: Union[str, None] = None):
    if q == None: 
        raise HTTPException(404,{"error":"No id"})
    category = {'data':[]}
    for id, name, price, img, ingredients, description, mass, hasMods in get_dishes_by_parent_id(q):
        mods = None
        if hasMods == True:
            mods = []
            for m_id, m_name, m_price, m_img, m_ingredients, m_description, m_mass in get_mods(id):
                mod = {'id': m_id, 'name': m_name, 'price': m_price, 'image': f'/images/getById?q={m_id}' if not img == None else None , 'ingredients': m_ingredients, 'description': m_description, 'mass': m_mass}
                mods.append(mod)
        category['data'].append({'id':id, 'name': name, 'price': price, 'image': f'/images/getById?q={id}' if not img == None else None , 'ingredients': ingredients, 'description': description, 'mass': mass, 'hasMods': hasMods, 'mods': mods})
    if category == {'data':[]}:
        raise HTTPException(404,{"error":"No data"})
    return category

@app.get("/products/getById")
def get_Product_by_id(q: Union[str, None] = None):
    product = {}
    ans = get_dish_info_by_child_id(q)
    if ans == None:
        raise HTTPException(404,{"error": "No such product"})
    id, name, price, img, ingredients, description, mass, hasMods, parentId = get_dish_info_by_child_id(q)
    mods = None
    if hasMods == True:
        mods = []
        for m_id, m_name, m_price, m_img, m_ingredients, m_description, m_mass in get_mods(id):
            mod = {'id': m_id, 'name': m_name, 'price': m_price, 'image': f'/images/getById?q={m_id}' if not img == None else None , 'ingredients': m_ingredients, 'description': m_description, 'mass': m_mass}
            mods.append(mod)
    product['name'] = name
    product['id'] = id
    product['categoryId'] = parentId
    product['price'] = float(price)
    product['ingredients'] = ingredients
    product['picture'] = f'/images/getById?q={id}' if img != None else None
    product['about'] = description
    product['mass'] = mass
    product['hasMods'] = hasMods
    product['mods'] = mods
    return {'data': product}

@app.get("/products/getByName")
def get_Product_by_name(s: Union[str, None] = None):
    if s == None: 
        raise HTTPException(404,{"error":"No search params"})
    dishes = {'data': []}
    dishesArr = get_dishs_by_name(s)
    if dishesArr == None:
        raise HTTPException(404,{'data': []})
    for id, name, price, img, ingredients, description, mass, hasMods, parentId in dishesArr:
        mods = None
        if hasMods == True:
            mods = []
            for m_id, m_name, m_price, m_img, m_ingredients, m_description, m_mass in get_mods(id):
                mod = {'id': m_id, 'name': m_name, 'price': m_price, 'image': f'/images/getById?q={m_id}' if not img == None else None , 'ingredients': m_ingredients, 'description': m_description, 'mass': m_mass}
                mods.append(mod)
        dishes['data'].append({'id':id, "categoryId": parentId, 'name': name, 'price': price, 'image': f'/images/getById?q={id}' if not img == None else None , 'ingrediensts': ingredients, 'description': description, 'mass': mass, "hasMods": hasMods, "mods": mods})
    return dishes

@app.get("/images/getById")
def get_Product_by_id(q: Union[str, None] = None):
    if os.path.isfile(f"./img/{q}.webp"):
        f = open(f"./img/{q}.webp", "rb")
        return Response(f.read(), media_type='image/webp')
    link = get_image_by_child_id(q)
    if link == None:
        raise HTTPException(404,{'data': 'no such photo'})
    link = link[0]
    headers = {"X-SBISAccessToken": SBIS_KEY} 
    response = requests.get(f"https://api.sbis.ru/retail{link}", headers=headers)
    with open(f'./img/{q}.webp', 'wb') as f:
        f.write(response.content)
    return Response(response.content, media_type='image/webp')