import os
import json
import datetime
import requests

from mysql import *
from typing import Union
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.background import BackgroundTask
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
    changeAmount: float = None
    phone: str
    time: str = "now"
    nomenclature: list
    comment: Union[str, None] = None
    adress: str
    persons: int = 1
    paymentType: str 
    source: int = 1
    promo: str = None

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
    adrF = response.json()["addresses"][0]["addressFull"]
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

   
@app.get('/robots.txt', response_class=PlainTextResponse, tags=['robots'])
def robots():
    data = """User-agent: *\nDisallow: /"""
    return data

@app.post('/orders/create', tags=['orders'])
def create_order(order: Order):
    nomenclature = []
    for i in order.nomenclature:
        nomenclature.append({"id": int(i['id']), "count":int(i['count']), "priceListId":25, 'modifiers': i.get("modifiers", None)})

    adrJ, adrF = get_adress(order.adress)
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
        'Content-Type': 'application/json'
    }  
    now = datetime.datetime.now()
    date = now.date()
    if order.time == "now":
        hour = now.hour
        minute = now.minute
    else:
        _time = order.time.split(':')
        hour = int(_time[0])
        minute = int(_time[1])
    if hour * 60 + minute >= 1380:
        raise HTTPException(400,{'data': 'we are close'})
    if hour * 60 + minute < 600:
        hour = 10
    promos = {"Люблю Санечку": "Svoyak backend", "День Рождения": "HB backend"}
    parameters = json.dumps({
        'product': 'delivery',
        'pointId': 250,
        "promocode": promos.get(order.promo, None),
        'comment': f'{order.comment}\n{order.adress}',
        'customer': {"name": order.name, "lastname":order.lastName, "phone": order.phone},
        "datetime": f"{date} {hour}:{minute}:00", 
        "nomenclatures": nomenclature,
        "delivery": {"addressFull":adrF, "addressJSON": adrJ, "persons":order.persons,"changeAmount": order.changeAmount,"paymentType": order.paymentType, "isPickup": False}
    })
    url = 'https://api.sbis.ru/retail/order/create'  
    response = requests.post(url, data=parameters, headers=headers)
    return response.json()


@app.get("/categories", tags=['categories'])
def get_Categories():
    categories = {'data': []}
    for category in get_all_main_categories():
        category = {'name': category['Name'], 'id': category['ParentId'], "subCategories": []}
        categories['data'].append(category)
    return categories
    
# @app.get("/subCategories")
# def get_sub_category(q: Union[str, None] = None):
#     if q == None: 
#         raise HTTPException(404, {"error":"No id"})
#     sub_category = []
#     subArr = get_sub_categories(q)
#     if subArr == []:
#         raise HTTPException(404, {"error": "No subcategories by this id"})
#     for s_id, s_name in subArr:
#         sub_category.append({"id": s_id, "name": s_name})
#     return {'data': sub_category}

@app.get("/categories/getById", tags=['categories'])
def get_Category(q: Union[str, None] = None):
    if q == None: 
        raise HTTPException(404,{"error":"No id"})
    category = {'data':[]}
    for product in get_dishes_by_parent_id(q):
        mods = None
        if product['hasMods'] == True:
            mods = []
            for modi in get_mods(product['ChildId']):
                #ChildId, Name, Cost, Image, Ingredients, Description, Mass
                mod = {'id': modi['ChildId'], 'name': modi['Name'], 'price': modi['Cost'], 'image': f'/images/getById?q={modi["ChildId"]}' if not modi['Image'] == None else None , 'ingredients': modi['Ingredients'], 'description': modi['Description'], 'mass': modi['Mass']}
                mods.append(mod)
        #ChildId, Name, Cost, Image, Ingredients, Description, Mass, hasMods        
        category['data'].append({'id': product['ChildId'], 'name': product['Name'], 'price': product['Cost'], 'image': f'/images/getById?q={product["ChildId"]}' if not product['Image'] == None else None , 'ingredients': product['Ingredients'], 'description': product['Description'], 'mass': product['Mass'], 'hasMods': product['hasMods'], 'mods': mods})
    if category == {'data':[]}:
        raise HTTPException(404,{"error":"No data"})
    return category

@app.get("/products/getMods", tags=['products'])
def get_Product_by_id(q: Union[str, None] = None):
    mods = []
    ans = get_mods(q)
    if ans == None:
        raise HTTPException(404,{"error": "no mods"})
    for mod in ans:
        mods.append({'id': mod['ChildId'], 'name': mod['Name'], 'price': mod['Cost'], 'image': f'/images/getById?q={mod["ChildId"]}' if not mod['Image'] == None else None , 'ingredients': mod['Ingredients'], 'description': mod['Description'], 'mass': mod['Mass']})
    return mods

@app.get("/products/getById", tags=['products'])
def get_Product_by_id(q: Union[str, None] = None):
    product = {}
    products = get_dish_info_by_child_id(q)
    if products == None:
        raise HTTPException(404,{"error": "No such product"})
    mods = None
    if products['hasMods'] == True:
        mods = []
        for modi in get_mods(products['ChildId']):
            mod = {'id': modi['ChildId'], 'name': modi['Name'], 'price': modi['Cost'], 'image': f'/images/getById?q={modi["ChildId"]}' if not modi['Image'] == None else None , 'ingredients': modi['Ingredients'], 'description': modi['Description'], 'mass': modi['Mass']}
            mods.append(mod)
    product['name'] = products['Name']
    product['id'] = products['ChildId']
    product['categoryId'] = products['ParentId']
    product['price'] = products['Cost']
    product['ingredients'] = products['Ingredients']
    product['picture'] = f'/images/getById?q={products["ChildId"]}' if products['Image'] != None else None
    product['about'] = products['Description']
    product['mass'] = products['Mass']
    product['hasMods'] = products['hasMods']
    product['mods'] = mods
    return {'data': product}

@app.get("/products/getByName", tags=['products'])
def get_Product_by_name(s: Union[str, None] = None):
    if s == None: 
        raise HTTPException(404,{"error":"No search params"})
    dishes = {'data': []}
    dishesArr = get_dishs_by_name(s)
    if dishesArr == None:
        raise HTTPException(404,{'data': []})
    for product in dishesArr:
        mods = None
        if product['hasMods'] == True:
            mods = []
            for modi in get_mods(id):
                mod = {'id': modi['ChildId'], 'name': modi['Name'], 'price': modi['Cost'], 'image': f'/images/getById?q={modi["ChildId"]}' if not modi['Image'] == None else None , 'ingredients': modi['Ingredients'], 'description': modi['Description'], 'mass': modi['Mass']}
                mods.append(mod)
        dishes['data'].append({'id': product['ChildId'], 'name': product['Name'], 'price': product['Cost'], 'image': f'/images/getById?q={product["ChildId"]}' if not product['Image'] == None else None , 'ingredients': product['Ingredients'], 'description': product['Description'], 'mass': product['Mass'], 'hasMods': product['hasMods'], 'mods': mods})
    return dishes

@app.get("/images/getById", tags=['images'])
def get_Product_by_id(q: Union[str, None] = None):
    if os.path.isfile(f"./img/{q}.webp"):
        f = open(f"./img/{q}.webp", "rb")
        return Response(f.read(), media_type='image/webp')
    link = get_image_by_child_id(q)
    if link == None:
        raise HTTPException(404,{'data': 'no such photo'})
    link = link['Image']
    headers = {"X-SBISAccessToken": SBIS_KEY} 
    response = requests.get(f"https://api.sbis.ru/retail{link}", headers=headers)
    print(response.text)
    with open(f'./img/{q}.webp', 'wb') as f:
        f.write(response.content)
    return Response(response.content, media_type='image/webp')