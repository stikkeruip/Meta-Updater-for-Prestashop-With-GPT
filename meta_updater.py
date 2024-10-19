import os
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# PrestaShop API details from environment variables
prestashop_url = os.getenv('PRESTASHOP_URL')  # Should include '/api'
api_key = os.getenv('PRESTASHOP_API_KEY')
shop_base_url = os.getenv('SHOP_BASE_URL')  # Base URL of the customer-facing shop
client = OpenAI(api_key=os.getenv('OPEN_API_KEY'))

def update_product_meta(product_id):
    product_page_url = f"{shop_base_url}/index.php?id_product={product_id}&controller=product"
    headers = {'User-Agent': 'Mozilla/5.0'}
    page_response = requests.get(product_page_url, headers=headers)

    if page_response.status_code != 200:
        print(f"Failed to retrieve product page: {page_response.status_code}")
        return

    soup = BeautifulSoup(page_response.content, 'html.parser')
    description = soup.find('div', class_='shopi_descripton') or soup.find('div', string=lambda x: x and 'Prodigal Pen' in x)
    active_ingredients = soup.find('div', id='showhidetarget4')
    how_to_use = soup.find('div', id='showhidetarget6')

    description_text = description.get_text(strip=True) if description else "Description not found"
    active_ingredients_text = active_ingredients.get_text(strip=True) if active_ingredients else "Active ingredients not found"
    how_to_use_text = how_to_use.get_text(strip=True) if how_to_use else "How to use not found"

    print(description_text)
    print(active_ingredients_text)
    print(how_to_use_text)

    product_url = f"{prestashop_url}/products/{product_id}"
    response = requests.get(product_url, headers=headers, auth=HTTPBasicAuth(api_key, ''))

    if response.status_code != 200:
        print(f"Failed to retrieve product {product_id}: {response.status_code}")
        return

    root = ET.fromstring(response.content)

    # Remove non-writable fields
    non_writable_fields = ["manufacturer_name", "quantity", "position_in_category"]
    parent_map = {c: p for p in root.iter() for c in p}
    for field in non_writable_fields:
        for elem in root.findall(f".//{{*}}{field}"):
            parent = parent_map.get(elem)
            if parent is not None:
                parent.remove(elem)

    product_name_elem = root.find(".//{*}name/{*}language")
    product_name = product_name_elem.text if product_name_elem is not None else ""

    short_description_elem = root.find(".//{*}description_short/{*}language")
    short_description = short_description_elem.text if short_description_elem is not None else ""
    brand, short_description_text = "", ""
    if short_description:
        parts = short_description.split('-', 1)
        if len(parts) == 2:
            brand = parts[0].strip()[3:]
            short_description_text = parts[1].strip()[:-4]
        else:
            short_description_text = short_description.strip()

    brand_title_case = brand.title()
    product_name_title_case = product_name.title()
    short_description_text = short_description_text.title()

    meta_title = f"{brand_title_case} {product_name_title_case} - {short_description_text}"
    print(f"Generated Meta Title: {meta_title}")

    gpt_prompt = (f"Write an SEO meta description for the following product: {product_name}. "
                  f"Product description: {short_description_text}. How to use: {how_to_use_text}. "
                  f"Ingredients: {active_ingredients_text}. Output only the description, max 160 characters.")
    gpt_response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": gpt_prompt}], max_tokens=50)
    meta_description_gpt = gpt_response.choices[0].message.content.strip()
    print(f"Generated Meta Description: {meta_description_gpt}")

    for language in root.findall(".//{*}meta_title/{*}language"):
        language.text = meta_title

    for language in root.findall(".//{*}meta_description/{*}language"):
        language.text = meta_description_gpt

    for language in root.findall(".//{*}link_rewrite/{*}language"):
        language.text = product_name.lower().replace(" ", "-")

    updated_data = ET.tostring(root, encoding='utf-8', method='xml')
    update_response = requests.put(product_url, data=updated_data, headers=headers, auth=HTTPBasicAuth(api_key, ''))

    if update_response.status_code in [200, 201]:
        print(f"Product {product_id} updated successfully!")
    else:
        print(f"Failed to update product {product_id}: {update_response.status_code}")
        print(update_response.text)

# Example usage
def update_all_products(product_ids):
    for product_id in product_ids:
        update_product_meta(product_id)

# Example call to update all products
product_ids = [12]  # Add more product IDs as needed
update_all_products(product_ids)
