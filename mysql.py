import pymysql
import os

def get_con():
    return pymysql.connect(
        host=os.environ.get("SQL_HOST"),
        user='menuHolder',
        password=os.environ.get("SQL_PASS"),
        database='menu',  
        port=2666,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )



def get_dishes_by_parent_id(parent_id):
    con = get_con()
    cursor = con.cursor()
    cursor.execute("SELECT ChildId, Name, Cost, Image, Ingredients, Description, Mass, hasMods FROM Dishes WHERE ParentId = %s", (parent_id,))
    dishes = cursor.fetchall()
    cursor.close()
    con.close()
    if parent_id == "828":
        return dishes[::-1]
    return dishes

def get_image_by_child_id(child_id):
    con = get_con()
    cursor = con.cursor()
    cursor.execute("SELECT Image FROM Dishes WHERE ChildId = %s", (child_id,))
    img = cursor.fetchone()
    if img == None:
        cursor.execute("SELECT Image FROM Mods WHERE ChildId = %s", (child_id,))
        img = cursor.fetchone()
    cursor.close()
    con.close()
    return img

def get_mods(parent_id):
    con = get_con()
    cursor = con.cursor()
    cursor.execute("SELECT ChildId, Name, Cost, Image, Ingredients, Description, Mass FROM Mods WHERE ParentId = %s", (parent_id,))
    data = cursor.fetchall()
    cursor.close()
    con.close()
    return data

def get_all_main_categories():
    con = get_con()
    cursor = con.cursor()
    cursor.execute("SELECT ParentId, Name FROM Categories WHERE IsMain = 1")
    categories = cursor.fetchall()
    cursor.close()
    con.close()
    return categories

def get_sub_categories(id):
    con = get_con()
    cursor = con.cursor()
    cursor.execute("SELECT ParentId, Name FROM Categories WHERE Parent = %s", (id,))
    categories = cursor.fetchall()
    cursor.close()
    con.close()
    return categories

def get_dish_info_by_child_id(child_id):
    """Получает название и цену блюда по его ChildId из таблицы Dishes."""
    con = get_con()
    cursor = con.cursor()
    cursor.execute("SELECT ChildId, Name, Cost, Image, Ingredients, Description, Mass, hasMods, ParentId FROM Dishes WHERE ChildId = %s", (child_id,))
    dish_info = cursor.fetchone()
    cursor.close()
    con.close()
    return dish_info if dish_info else None

def get_dishs_by_name(name):
    """Получает название и цену блюда по его Name из таблицы Dishes."""
    con = get_con()
    cursor = con.cursor()
    nameCapitalized = f'%{name.capitalize()}%'
    nameLower = f'%{name.lower()}%'
    nameLowerAndCapitalized = f'%{name.lower().capitalize()}%'
    cursor.execute("SELECT ChildId, Name, Cost, Image, Ingredients, Description, Mass, hasMods, ParentId FROM Dishes WHERE Name LIKE %s OR Name LIKE %s OR Name LIKE %s", (nameCapitalized,nameLower, nameLowerAndCapitalized))
    dish_info = cursor.fetchall()
    cursor.close()
    con.close()
    return dish_info if dish_info else None
