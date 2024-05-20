import os
import requests
import json

SBIS_KEY = os.environ.get("SBIS_KEY")

def get_menu():
    url = 'https://api.sbis.ru/retail/nomenclature/list?'
    parameters = {
        'pointId': 250,
        'priceListId': 25,
        "noStopList": False,
        'withBalance': True,
        'onlyPublished': False,
        'page': '0',
        'pageSize': '1000'
    }
    headers = {
    "X-SBISAccessToken": SBIS_KEY
    }     
    response = requests.get(url, params=parameters, headers=headers)
    with open("ss.json", "w") as f:
        json.dump(response.json(), f)
    categories = []
    for item in response.json()["nomenclatures"]:
        if item.get("isParent") and not item.get("isKit"):
            categories.append((item['hierarchicalId'], item['name']))
    return categories

# categories_with_ids = get_menu()
# for category_id, category_name in categories_with_ids:
#     print(f"ID: {category_id}, Name: {category_name}")


def get_dishes(categories_with_ids, nomenclatures):
    dishes_by_category = {category_id: [] for category_id, _ in categories_with_ids}
    
    for dish in nomenclatures:
        for category_id, _ in categories_with_ids:
            if dish.get("isParent"):
                continue;
            if dish.get("hierarchicalParent") == category_id:
                if dish.get('images') == None:
                    img = None
                else: 
                    img = dish.get('images')[0]
                dish_info = (dish['id'], dish['name'], dish.get('cost', 'Unknown'), img, dish.get('description_simple', 'None'))
                dishes_by_category[category_id].append(dish_info)
                break
    

    for category_id, dishes in dishes_by_category.items():
        dishes_by_category[category_id] = sorted(dishes, key=lambda x: x[0])
    
    return dishes_by_category


def create_info():
    with open("ss.json", "r") as f:
        data = json.load(f)

    categories_with_ids = get_menu()
    nomenclatures = data["nomenclatures"]

    dishes_by_category = get_dishes(categories_with_ids, nomenclatures)

    # Выводим результат
    for category_id, dishes in dishes_by_category.items():
        category_name = next((name for cid, name in categories_with_ids if cid == category_id), "Unknown")
        print(f"Category: {category_name}")
        for dish_info in dishes:
            dish_id, dish_name, dish_cost = dish_info
            print(f"  ID: {dish_id}, Name: {dish_name}, Cost: {dish_cost}")
        print()


