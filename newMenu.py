import os
import sqlite3
import json
from sortMenu import *

SBIS_KEY = os.environ.get("SBIS_KEY")
def create_tables(cursor):
    cursor.execute('''CREATE TABLE IF NOT EXISTS Categories (
                        ParentId INTEGER PRIMARY KEY,
                        Name TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Dishes (
                        ParentId INTEGER,
                        ChildId INTEGER,
                        Name TEXT,
                        Cost TEXT,
                        FOREIGN KEY (ParentId) REFERENCES Categories (ParentId)
                    )''')

def insert_categories(cursor, categories_with_ids):

    for category_id, category_name in categories_with_ids:
        cursor.execute("INSERT INTO Categories (ParentId, Name) VALUES (?, ?)", (category_id, category_name))

def insert_dishes(cursor, dishes_by_category):

    for parent_id, dishes in dishes_by_category.items():
        for dish_info in dishes:
            dish_id, dish_name, dish_cost = dish_info
            cursor.execute("INSERT INTO Dishes (ParentId, ChildId, Name, Cost) VALUES (?, ?, ?, ?)", (parent_id, dish_id, dish_name, dish_cost))


conn = sqlite3.connect('menu.db')
cursor = conn.cursor()


create_tables(cursor)


with open("ss.json", "r") as f:
    data = json.load(f)

categories_with_ids = get_menu()
nomenclatures = data["nomenclatures"]


dishes_by_category = get_dishes(categories_with_ids, nomenclatures)


insert_categories(cursor, categories_with_ids)
insert_dishes(cursor, dishes_by_category)


conn.commit()
conn.close()
