
import os
import io
import PIL
import traceback
import json
import datetime
import requests
import stat
import anyio
import hashlib
import telebot
import infoSQL
import asyncio

from mysql import *
from typing import Union
from fastapi import FastAPI, HTTPException, Response, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fastapi.responses import FileResponse, PlainTextResponse

SBIS_KEY = os.environ.get("SBIS_KEY")
app = FastAPI(docs_url="", redoc_url="", openapi_url="")


origins = ["*"]

async def get_etag(file_path):
    try:
        stat_result = await anyio.to_thread.run_sync(os.stat, file_path)
    except FileNotFoundError:
        raise RuntimeError(f"File at path {file_path} does not exist.")
    else:
        mode = stat_result.st_mode
        if not stat.S_ISREG(mode):
            raise RuntimeError(f"File at path {file_path} is not a file.")
        
        #calculate the etag based on file size and last modification time
        etag_base = str(stat_result.st_mtime) + "-" + str(stat_result.st_size)
        etag = hashlib.md5(etag_base.encode()).hexdigest()
        return etag

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
    changeAmount: Union[str, None, float] = None
    phone: str
    time: str = "now"
    nomenclature: list
    comment: Union[str, None] = None
    adress: Union[str, None] = None
    persons: int = 1
    paymentType: str 
    source: int = 1
    promo: str = ""
    isPickup: bool = False
    
class Orders(BaseModel):
    firstDate: Union[str, None] = None;
    secondDate: Union[str, None] = None;

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
    try:
        adrJ = response.json()["addresses"][0]["addressJSON"]
        adrF = response.json()["addresses"][0]["addressFull"]
        return adrJ, adrF
    except Exception:
        raise HTTPException(400, "address not found")

def get_delivery(adress):
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
    }  
    parameters = {
    'address': adress,
    'pointId': 250
    }
    url = 'https://api.sbis.ru/retail/delivery/cost?'  
    response = requests.get(url, params=parameters, headers=headers)
    return response.json()

@app.get('/robots.txt', response_class=PlainTextResponse, tags=['robots'])
def robots():
    data = """User-agent: *\nDisallow: /"""
    return data

@app.get('/order/address/coords', tags=['orders'])
def addressCords(x: Union[str, None] = None, y: Union[str, None] = None ):
    url = f"https://geocode-maps.yandex.ru/1.x/?apikey=eb7cd4e0-a9a5-4dfb-b5ca-2dcec5a4bc66&geocode={y},{x}&results=1&kind=house&format=json"

    response = requests.get(url)
    print(response.text)
    if response.status_code != 200:
        raise HTTPException(404, "not found")
    if len(response.json()['response']['GeoObjectCollection']['featureMember']) == 0:
        raise HTTPException(404, "no houses")
    data = response.json()['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['Address']['Components']
    components = {}
    for i in data:
        components[i['kind']] = i['name']
    return components

@app.get('/order/address', tags=['orders'])
def get_delivery_price(q: Union[str, None] = None):
    adrJ, adrF = get_adress(q)
    return get_delivery(adrJ)

async def telegrammSend(id, message):
    bot = telebot.TeleBot(os.environ.get('TG_KEY'), parse_mode="HTML")
    bot.send_message(id, message)

@app.post('/orders/create', tags=['orders'])
async def create_order(order: Order):
    nomenclature = []
    for i in order.nomenclature:
        nomenclature.append({"id": int(i['id']), "count":int(i['count']), "priceListId":25, 'modifiers': i.get("modifiers", None)})
    if order.adress != None:
        adrJ, adrF = get_adress("Владимирская обл., Собинский р-н., " +order.adress)
        address = order.adress
    else:
        adrJ, adrF = None, None
        address = "Самовывоз"
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
        'Content-Type': 'application/json'
    }  
    now = datetime.datetime.now()
    date = now.date()
    if order.time == "now":
        hour = now.hour
        minute = now.minute + 2
        if minute >= 60:
            hour += 1
            minute = 0
    else:
        _time = order.time.split(':')
        hour = int(_time[0])
        minute = int(_time[1])
    if hour * 60 + minute >= 1322:
        raise HTTPException(400,{'data': 'Мы закрыты!'})
    if hour * 60 + minute < 600:
        raise HTTPException(400,{'data': 'Мы закрыты!'})
    prom = None
    if order.promo != None:
        prom = order.promo.lower()
    promos = {"гей порно": "Svoyak backend", "день рождения": "HB backend", "момент": "HappyHour back"}
    parameters = json.dumps({
        'product': 'delivery',
        'pointId': 250,
        "promocode": promos.get(prom, prom),
        'comment': f'{order.comment}\n{order.adress}',
        'customer': {"name": order.name, "lastname":order.lastName, "phone": order.phone},
        "datetime": f"{date} {hour:02}:{minute:02}:00", 
        "nomenclatures": nomenclature,
        "delivery": {"addressFull":adrF, "addressJSON": adrJ, "persons":order.persons, "changeAmount": float(order.changeAmount) if order.changeAmount != None else None, "paymentType": order.paymentType, "isPickup": order.isPickup}
    })
    url = 'https://api.sbis.ru/retail/order/create'  
    response = requests.post(url, data=parameters, headers=headers)
    if response.status_code != 200:
        raise HTTPException(400, response.json())
    
    responseJson = response.json()
    
    try:
        text = f"<b>Новый заказ!</b>\n<b>к {responseJson['datetime']}</b>\n<i>{responseJson['customer']['name']} ({order.name})</i>\n<b>{responseJson['customer']['phone']}</b><b>\n{address}</b>\n<b>{responseJson['totalPrice']}</b>"
        sendMessage = asyncio.create_task(telegrammSend(-1002163907296, text))
        addOrder = asyncio.create_task(infoSQL.addOrder(responseJson['customer']['phone'], responseJson['customer']['name'], order.nomenclature, order.source, responseJson['totalPrice']))
        await sendMessage
        await addOrder

    except Exception as e:
        traceback.print_exc()

    return response.json()


@app.get("/categories", tags=['categories'])
def get_Categories():
    categories = {'data': []}
    for category in get_all_main_categories():
        category = {'name': category['Name'], 'id': category['ParentId'], "subCategories": []}
        categories['data'].append(category)
    return categories
    
@app.get("/info/orders", tags=['info'])
def get_orders(q: Union[int, None] = None, l: Union[int, None] = 5):
    orders = {'data': []}
    for order in infoSQL.getOrdersByCustomerId(q, l):
        orderInfo = {"id": order['id'], "source": order['source_id'], "total": order['final_price'], "time": order['time']}
        orders['data'].append(orderInfo)
    return orders

@app.get("/info/dishesTop", tags=['info'])
def get_dishesTop(q: Union[int, None] = 5):
    dishes = {'data': []}
    for dish in infoSQL.getTopDishes(q):
        dishInfo = {"id": dish['dish_id'], "name": dish['name'], "category": dish['categories'], "count": dish['countNum']}
        dishes['data'].append(dishInfo)
    return dishes


@app.get("/info/customersTop", tags=['info'])
def get_dishesTop(q: Union[int, None] = 5):
    dishes = {'data': []}
    for dish in infoSQL.getTopCustomers(q):
        dishInfo = {"id": dish['id'],"phone": dish['phone'], "name": dish['name'], "total": dish['total']}
        dishes['data'].append(dishInfo)
    return dishes

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
    if q == "3":
        for product in infoSQL.getTopCategory():
            if product['ChildId'] == 1927:
                continue;
            mods = None
            if product['hasMods'] == True:
                mods = []
                for modi in get_mods(product['ChildId']):
                    #ChildId, Name, Cost, Image, Ingredients, Description, Mass
                    mod = {'id': modi['ChildId'], 'name': modi['Name'], 'price': modi['Cost'], 'image': f'/images/getById?q={modi["ChildId"]}' if not modi['Image'] == None else None , 'ingredients': modi['Ingredients'], 'description': modi['Description'], 'mass': modi['Mass']}
                    mods.append(mod)
            #ChildId, Name, Cost, Image, Ingredients, Description, Mass, hasMods        
            category['data'].append({'id': product['ChildId'], 'name': product['Name'], 'price': product['Cost'], 'image': f'/images/getById?q={product["ChildId"]}' if not product['Image'] == None else None , 'ingredients': product['Ingredients'], 'description': product['Description'], 'mass': product['Mass'], 'hasMods': product['hasMods'], 'mods': mods})
    else: 
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
    return {"data": mods}

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
async def get_Product_by_id(q: Union[str, None] = None,  if_none_match: str | None = Header(default=None)):
    if os.path.isfile(f"./img/{q}.webp"):
        file_etag = await get_etag(f"./img/{q}.webp")
        if if_none_match == file_etag:
            return Response(status_code=304)
        f = open(f"./img/{q}.webp", "rb")
        return Response(f.read(), media_type='image/webp', headers={"ETag": file_etag, "Cache-Control": "public, max-age=6048000"})
    link = get_image_by_child_id(q)
    if link == None:
        raise HTTPException(404,{'data': 'no such photo'})
    if link['Image'] == None:
        raise HTTPException(404, {'data': 'no such photo'})
    link = link['Image']
    headers = {"X-SBISAccessToken": SBIS_KEY} 
    response = requests.get(f"https://api.sbis.ru/retail{link}", headers=headers)
    img = PIL.Image.open(io.BytesIO(response.content)).convert('RGBA')
    destination = f"./img/{q}.webp"
    try:
        img.save(destination, "WEBP", quality=80, optimize=True)
    except IOError:
        PIL.ImageFile.MAXBLOCK = img.size[0] * img.size[1]
        img.save(destination, "WEBP", quality=80, optimize=True)
    f = open(f"./img/{q}.webp", "rb")
    file_etag = await get_etag(f"./img/{q}.webp")
    return Response(f.read(), media_type='image/webp', headers={"ETag": file_etag, "Cache-Control": "public, max-age=6048000"})

def orders_process(ordersJson):
    response = {
        'data': 
        {
            'amount': 0,
            'total': 0
        }
    }
    for order in ordersJson['orders']:
        if order['Deleted'] or order['Return'] or order['TotalPrice'] == None:
            continue;
        response['data']['total'] += order['TotalPrice']
        response['data']['amount'] += 1

    return response


@app.post('/orders/get', tags=['orders'])
def get_orders(orders: Orders):
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
    }  
    parameters = {
    "pointId": 250,
    "fromDateTime": orders.firstDate + " 00:00:00",
    "toDateTime": orders.secondDate + ' 00:00:00',
    "pageSize": 1000
    }
    url = "https://api.sbis.ru/retail/order/list?"

    response = requests.get(url, params=parameters, headers=headers)

    return orders_process(response.json())


@app.get('/orders/get', response_class=PlainTextResponse, tags=['orders'])
def get_orders(date: Union[str, None] = None):
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
    }  
    parameters = {
    "pointId": 250,
    "fromDateTime": date + " 00:00:00",
    "toDateTime": date  + ' 23:59:00',
    "pageSize": 1000
    }
    url = "https://api.sbis.ru/retail/order/list?"

    response = requests.get(url, params=parameters, headers=headers)
    if response.status_code == 200:
        return str(orders_process(response.json())['data']['total'])
    raise HTTPException(400, "ОШИБКА")

@app.get('/orders/get/yesterday', tags=['orders'])
def get_orders():
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
    }  
    now = datetime.datetime.now()
    date = now.date()
    parameters = {
    "pointId": 250,
    "fromDateTime": f"{date.year}-{date.month if date.month // 10 >= 1 else '0' + str(date.month)}-{date.day - 1 if (date.day - 1) // 10 >= 1 else '0' + str(date.day - 1)}" + " 00:00:00",
    "toDateTime":  f"{date.year}-{date.month if date.month // 10 >= 1 else '0' + str(date.month)}-{date.day if date.day // 10 >= 1 else '0' + str(date.day)}" + " 00:00:00",
    "pageSize": 1000
    }
    url = "https://api.sbis.ru/retail/order/list?"

    response = requests.get(url, params=parameters, headers=headers)
    return orders_process(response.json())

@app.get('/orders/get/today', tags=['orders'])
def get_orders():
    headers = {
        "X-SBISAccessToken": SBIS_KEY,
    }  
    now = datetime.datetime.now()
    date = now.date()
    today = f"{date.year}-{date.month if date.month // 10 >= 1 else '0' + str(date.month)}-{date.day if date.day // 10 >= 1 else '0' + str(date.day)}"
    parameters = {
    "pointId": 250,
    "fromDateTime":  today + " 00:00:00",
    "toDateTime":  today + f" {now.hour}:{now.minute}:00",
    "pageSize": 1000
    }
    url = "https://api.sbis.ru/retail/order/list?"

    response = requests.get(url, params=parameters, headers=headers)
    return orders_process(response.json())
