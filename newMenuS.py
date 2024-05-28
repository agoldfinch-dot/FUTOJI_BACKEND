import pymysql
import json
import os
from sortMenu import get_menu, get_dishes

SBIS_KEY = os.environ.get("SBIS_KEY")

def create_tables(cursor):
    cursor.execute('''CREATE TABLE IF NOT EXISTS Categories (
                        ParentId INT PRIMARY KEY,
                        Name VARCHAR(255),
                        IsMain BOOLEAN,
                        Parent INT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Dishes (
                        ParentId INT,
                        ChildId INT PRIMARY KEY,
                        Name VARCHAR(255),
                        Cost VARCHAR(255),
                        Image VARCHAR(1024),
                        Ingredients TEXT,
                        Description TEXT,
                        Mass VARCHAR(255),
                        HasMods BOOLEAN,
                        FOREIGN KEY (ParentId) REFERENCES Categories (ParentId)
                    )''')
    cursor.execute("SHOW INDEX FROM Dishes WHERE Key_name = 'idx_child_id'")
    index_exists = cursor.fetchone()
    if not index_exists:
        cursor.execute('CREATE INDEX idx_child_id ON Dishes (ChildId)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Mods (
                        ParentId INT,
                        ChildId INT,
                        Name VARCHAR(255),
                        Cost VARCHAR(255),
                        Image VARCHAR(1024),  -- Изменение типа данных на TEXT
                        Ingredients TEXT,
                        Description TEXT,
                        Mass VARCHAR(255),
                        FOREIGN KEY (ParentId) REFERENCES Dishes (ChildId)
                    )''')

def insert_categories(cursor, categories_with_ids):
    for category_id, category_name, parent in categories_with_ids:
        isMain = parent is None
        cursor.execute("INSERT INTO Categories (ParentId, Name, IsMain, Parent) VALUES (%s, %s, %s, %s)",
                       (category_id, category_name, isMain, parent))

def insert_mods(cursor, mods):
    for i in mods:
        dish_id, dish_name, dish_cost, dish_image, dish_description, parent_id = i
        if dish_description:
            temp = dish_description.split('/')
            temp.extend([None] * (3 - len(temp)))
            ingredients, description, mass = temp
        else:
            ingredients = description = mass = None

        # Проверка существования ParentId в Dishes перед вставкой
        cursor.execute("SELECT ChildId FROM Dishes WHERE ChildId = %s", (parent_id,))
        if cursor.fetchone():
            cursor.execute(f"INSERT INTO Mods (ParentId, ChildId, Name, Cost, Image, Description, Ingredients, Mass) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                           (parent_id, dish_id, dish_name, dish_cost, dish_image, description, ingredients, mass))
        else:
            print(f"Пропуск модификации с ParentId {parent_id}, так как он не существует в Dishes")

def insert_dishes(cursor, dishes_by_category):
    for parent_id, dishes in dishes_by_category.items():
        for dish_info in dishes:
            dish_id, dish_name, dish_cost, dish_image, dish_description, hasMods = dish_info
            if dish_description:
                temp = dish_description.split('/')
                temp.extend([None] * (3 - len(temp)))
                ingredients, description, mass = temp
            else:
                ingredients = description = mass = None

            cursor.execute("INSERT INTO Dishes (ParentId, ChildId, Name, Cost, Image, Description, Ingredients, Mass, HasMods) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                           (parent_id, dish_id, dish_name, dish_cost, dish_image, description, ingredients, mass, hasMods))

# Подключение к базе данных
conn = pymysql.connect(
    host=os.environ.get("SQL_HOST"),
    user='menuHolder',
    password=os.environ.get("SQL_PASS"),
    database='menu',  
    port=2666,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
cursor = conn.cursor()

# Создание таблиц
create_tables(cursor)

# Получение категорий
categories_with_ids = get_menu()

# Загрузка данных из файла
with open("menuSbis.json", "r") as f:
    data = json.load(f)

nomenclatures = data["nomenclatures"]

# Получение блюд и модификаций
dishes_by_category, mods = get_dishes(categories_with_ids, nomenclatures)

# Вставка данных в таблицы
insert_categories(cursor, categories_with_ids)
insert_dishes(cursor, dishes_by_category)  # Вставка блюд перед модификациями
insert_mods(cursor, mods)

# Фиксация изменений и закрытие соединения
conn.commit()
conn.close()
