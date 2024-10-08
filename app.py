from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)
def load_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        # Handle both dictionary and list formats
        if isinstance(data, dict):
            flat_data = data.get('productData', None)
        elif isinstance(data, list):
            flat_data = data
        else:
            raise ValueError(f"Unexpected data format in {file_path}")

        if flat_data is None:
            raise ValueError(f"productData missing in {file_path}")
    return flat_data


def get_store_basket(file_path, basket):
    data = load_data(file_path)
    if data is None:
        raise ValueError(f"Data from {file_path} is None")
    return cheapestBasketPerStore(data, basket)

def cheapestBasketPerStore(data, basket):
    store_products = {}
    cheapest_products = find_cheapest_products(data, basket)

    for product_name, details in cheapest_products.items():        
        if details is None:
            print(f"No details found for product: {product_name}")
            continue 
        store = details.get('store')
        if store is None:
            print(f"Store is missing for product: {product_name}")
            continue 
        
        if store not in store_products:
            store_products[store] = []
        
        store_products[store].append({
            'name': product_name,
            'price': details.get('price', 0),
            'brand': details.get('brand', 'Unknown'),
            'quantity': details.get('quantity', 'Unknown')
        })

    return store_products
def find_cheapest_products(data, basket):
    cheapest_products = {}
    for item in basket:
        product_name = item['name'].lower()  # Convert to lowercase for case-insensitive comparison
        cheapest_products[product_name] = None
        for entry in data:
            # Skip entries that have None values for required fields
            if not entry or not entry.get('product') or entry.get('price') is None or entry.get('store') is None:
                continue

            entry_product_name = entry['product'].lower()
            # Check if the basket item name is a substring of the entry product name
            if product_name in entry_product_name:
                if (cheapest_products[product_name] is None or 
                    (entry['price'] is not None and 
                     entry['price'] < cheapest_products[product_name]['price'])):
                    cheapest_products[product_name] = {
                        'store': entry.get('store', 'Unknown'),
                        'brand': entry.get('brand', 'Unknown'),
                        'price': entry.get('price', 0),
                        'quantity': entry.get('quantity', 'Unknown')
                    }
    return cheapest_products


def calculate_total_cost(cheapest_products):
    store_totals = {}
    for product, details in cheapest_products.items():
        if not details:
            continue
        store = details['store']
        price = details['price']
        
        # Skip products with invalid or zero price
        if price is None or price <= 0:
            continue
        
        if store not in store_totals:
            store_totals[store] = 0.0
        store_totals[store] += float(price)
        
    return store_totals



def compare_stores(file_paths, basket):
    all_data = []
    for file_path in file_paths:
        try:
            data = load_data(file_path)
            if data:
                all_data.extend(data)
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")

    # Find the cheapest products for each item in the basket
    cheapest_products = find_cheapest_products(all_data, basket)
    # Calculate total cost per store
    store_totals = calculate_total_cost(cheapest_products)

    # Filter out stores with a total cost of 0
    store_totals = {store: total for store, total in store_totals.items() if total > 0}

    # Check if there are any valid store totals left
    if not store_totals:
        return {"error": "No valid store totals found"}

    # Find the cheapest store with the minimum total cost
    cheapest_store = min(store_totals, key=store_totals.get)
    cheapest_price = store_totals[cheapest_store]

    return {
        'cheapestProducts': cheapest_products,
        'totalCosts': store_totals,
        'cheapestStore': cheapest_store,
        'cheapestPrice': cheapest_price
    }


def get_store_basket(file_path, basket):
    data = load_data(file_path)
    return cheapestBasketPerStore(data, basket)

@app.route('/api/store_baskets', methods=['POST'])
def store_baskets():
    try:
        data = request.get_json()
        basket = data.get('basket', [])
        if not basket:
            raise ValueError("Basket is empty or malformed")
        aldi_basket = get_store_basket('aldiData.json', basket)
        coles_basket = get_store_basket('products_data.json', basket)
        woolworths_basket = get_store_basket('woolworthsData.json', basket)
        return jsonify({
            'aldiBasket': aldi_basket,
            'colesBasket': coles_basket,
            'woolworthsBasket': woolworths_basket
        })
    except Exception as e:
        print(f"Error: {e}") 
        return jsonify({"error": str(e)}), 500


@app.route('/api/submit', methods=['POST'])
def submit_data():
    try:
        data = request.get_json()
        print(data)
        file_paths = ['products_data.json','aldiData.json', 'woolworthsData.json']
        comparison_result = compare_stores(file_paths, data)
        return jsonify(comparison_result)
    except Exception as e:
        print(f"Error: {e}")  
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
