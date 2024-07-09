import pymysql    
import os
import datetime
import time

def get_timestamp():
    ts = time.time()
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def get_conn():
    conn = pymysql.connect(
        host=os.environ.get("SQL_HOST"),
        user='infoHolder',
        password=os.environ.get("SQL_INFO_PASS"),
        port=2666,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn

def isNewCustomer(phone):
    cursor = get_conn().cursor()
    if cursor.execute("SELECT id FROM info.customers WHERE phone = %s;", phone) != 0:
        return False
    return True;
        
def addCustomer(phone, name):
    conn = get_conn()
    cursor = conn.cursor()
    timestamp = get_timestamp()
    cursor.execute("INSERT INTO info.customers (phone, name, first_order) VALUES (%s, %s, %s)", (phone, name, timestamp))
    conn.commit()
    
def addOrderData(orderId, dishId, count):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO info.order_data (id, dish_id, count) VALUES (%s, %s, %s)", (orderId, dishId, count))
    conn.commit()

def getCustomerId(phone):
    cursor = get_conn().cursor()
    cursor.execute("SELECT id FROM info.customers WHERE phone = %s;", (phone))
    return cursor.fetchone();

def getTopCategory():
    cursor = get_conn().cursor()
    cursor.execute("SELECT menu.Dishes.ChildId as ChildId, menu.Dishes.Name as Name, menu.Dishes.Cost as Cost, menu.Dishes.Image as Image, menu.Dishes.Ingredients as Ingredients, menu.Dishes.Description as Description, menu.Dishes.Mass as Mass, menu.Dishes.hasMods as hasMods FROM info.order_data JOIN menu.Dishes ON info.order_data.dish_id = menu.Dishes.ChildId GROUP BY dish_id ORDER BY countNum DESC LIMIT 15")
    return cursor.fetchall()

def getTopDishes(limit: int):
    cursor = get_conn().cursor()
    cursor.execute("SELECT dish_id, menu.Dishes.Name as name, menu.Dishes.ParentId as categories, SUM(count) as countNum FROM info.order_data LEFT JOIN menu.Dishes ON info.order_data.dish_id = menu.Dishes.ChildId GROUP BY dish_id ORDER BY countNum DESC LIMIT %s;", (limit))
    return cursor.fetchall()

def getOrdersByCustomerId(id: int, limit: int):
    cursor = get_conn().cursor()
    cursor.execute("SELECT id, source_id, final_price, time FROM info.orders WHERE info.orders.customer_id = %s ORDER BY time DESC LIMIT %s", (id, limit))
    return cursor.fetchall()

def getTopCustomers(limit: int):
    cursor = get_conn().cursor()
    cursor.execute("SELECT cus.id AS id, cus.phone AS phone, cus.name AS name, SUM(final_price) as total FROM info.customers AS cus LEFT JOIN info.orders AS ord ON cus.id = ord.customer_id GROUP BY cus.id ORDER BY total DESC LIMIT %s;", (limit))
    return cursor.fetchall()
    

async def addOrder(phone, name, orderList, source, finalPrice):
    if isNewCustomer(phone) == True:
        addCustomer(phone, name)
    orderNomenclature = []
    for i in orderList:
        orderNomenclature.append((i['id'], i['count']))
    customerId = getCustomerId(phone)
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO info.orders (customer_id, source_id, final_price, time) VALUES (%s, %s, %s, %s)", (customerId['id'], source, finalPrice, get_timestamp()))
    orderId = cursor.lastrowid
    conn.commit()

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE info.customers SET last_order = %s WHERE id = %s", (get_timestamp(), customerId['id']))
    conn.commit()
    for dishId, count in orderNomenclature:
        addOrderData(orderId, dishId, count)
