import sqlite3

conn = sqlite3.connect('menu.db',check_same_thread=False)
cursor = conn.cursor()

def get_dishes_by_parent_id(parent_id):
    cursor.execute("SELECT ChildId, Name, Cost, Image, Ingredients, Description, Mass, hasMods FROM Dishes WHERE ParentId=?", (parent_id,))
    dishes = cursor.fetchall()
    return dishes

def get_image_by_child_id(child_id):
    cursor.execute("SELECT Image FROM Dishes WHERE ChildId=?", (child_id,))
    img = cursor.fetchone()
    if img == None:
        cursor.execute("SELECT Image FROM Mods WHERE ChildId=?", (child_id,))
        img = cursor.fetchone()
    return img

def get_mods(parent_id):
    cursor.execute("SELECT ChildId, Name, Cost, Image, Ingredients, Description, Mass FROM Mods WHERE ParentId=?", (parent_id,))
    return cursor.fetchall()

def get_all_categories():
    cursor.execute("SELECT ParentId, Name FROM Categories")
    categories = cursor.fetchall()
    return categories

def get_dish_info_by_child_id(child_id):
    """Получает название и цену блюда по его ChildId из таблицы Dishes."""
    cursor.execute("SELECT ChildId, Name, Cost, Image, Ingredients, Description, Mass, hasMods FROM Dishes WHERE ChildId=?", (child_id,))
    dish_info = cursor.fetchone()
    return dish_info if dish_info else None

def get_dishs_by_name(name):
    """Получает название и цену блюда по его Name из таблицы Dishes."""
    nameCapitalized = f'%{name.capitalize()}%'
    nameLower = f'%{name.lower()}%'
    nameLowerAndCapitalized = f'%{name.lower().capitalize()}%'
    cursor.execute("SELECT ChildId, Name, Cost, Image, Ingredients, Description, Mass, hasMods FROM Dishes WHERE Name LIKE ? OR Name LIKE ? OR Name LIKE ?", (nameCapitalized,nameLower, nameLowerAndCapitalized))
    dish_info = cursor.fetchall()
    return dish_info if dish_info else None
