import os
from openai import OpenAI
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Load environment variables from .env file
load_dotenv()

# PrestaShop API details from environment variables
prestashop_url = os.getenv('PRESTASHOP_URL')  # Should include '/api'
api_key = os.getenv('PRESTASHOP_API_KEY')
shop_base_url = os.getenv('SHOP_BASE_URL') # Base URL of the customer-facing shop
client = OpenAI(api_key=os.getenv('OPEN_API_KEY'))

def update_product_meta(product_id):
    # Fetch product description from product page
    product_page_url = f"{shop_base_url}/en/sampar-paris/12-prodigal-pen-updated.html"
    headers = {
        'User-Agent': 'Mozilla/5.0'  # Use a common User-Agent
    }
    page_response = requests.get(product_page_url, headers=headers)

    if page_response.status_code == 200:
        soup = BeautifulSoup(page_response.content, 'html.parser')
        # Try to find the description in multiple ways
        description_div = soup.find('div', class_='shopi_descripton')
        if not description_div:
            description_div = soup.find('div', string=lambda x: x and 'Prodigal Pen' in x)

        if description_div:
            description = description_div.get_text(strip=True)
            print(description)
        else:
            print("Description not found")

        # Fetch active ingredients
        active_ingredients_div = soup.find('div', id='showhidetarget4')
        if active_ingredients_div:
            active_ingredients = active_ingredients_div.get_text(strip=True)
            print(active_ingredients)
        else:
            print("Active ingredients not found")

        # Fetch how to use
        how_to_use_div = soup.find('div', id='showhidetarget6')
        if how_to_use_div:
            how_to_use = how_to_use_div.get_text(strip=True)
            print(how_to_use)
        else:
            print("How to use not found")
    else:
        print(f"Failed to retrieve product page: {page_response.status_code}")
        return

    # Construct the product URL
    product_url = f"{prestashop_url}/products/{product_id}"

    # Headers for request
    headers = {
        'Content-Type': 'application/xml',
        'User-Agent': 'Mozilla/5.0'  # Use a common User-Agent
    }

    # Fetch the product data using HTTPBasicAuth
    response = requests.get(product_url, headers=headers, auth=HTTPBasicAuth(api_key, ''))

    if response.status_code == 200:
        # Parse XML response
        root = ET.fromstring(response.content)

        # Build a parent map to access parent elements
        parent_map = {c: p for p in root.iter() for c in p}

        # Remove non-writable fields
        non_writable_fields = ["manufacturer_name", "quantity", "position_in_category"]
        for field in non_writable_fields:
            # Find all elements regardless of namespace
            xpath_expr = f".//{{*}}{field}"
            for elem in root.findall(xpath_expr):
                parent = parent_map.get(elem)
                if parent is not None:
                    parent.remove(elem)

        # Extract product name
        product_name = root.find(".//{*}name/{*}language").text
        print(f"Product Name: {product_name}")

        # Extract short description and split by '-'
        short_description_elem = root.find(".//{*}description_short/{*}language")
        if short_description_elem is not None:
            short_description = short_description_elem.text
            if short_description:
                parts = short_description.split('-', 1)
                if len(parts) == 2:
                    brand, short_description_text = parts
                    brand = brand.strip()[3:]
                    print(f"Brand: {brand}")
                    short_description_text = short_description_text.strip()[:-4]
                    print(f"Short Description: {short_description_text}")
                else:
                    print(f"Short Description: {short_description.strip()}")
            else:
                print("Short description is empty")
                return
        else:
            print("Short description not found")
            return

        # Generate meta_title using a consistent template
        if product_name:
            brand_title_case = brand.title()  # Ensure consistent capitalization
            product_name_title_case = product_name.title()  # Ensure consistent capitalization
            short_description_text = short_description_text.title()  # Consistent capitalization

            # Construct the meta title using the template
            meta_title = f"{brand_title_case} {product_name_title_case} - {short_description_text}"
            print(f"Generated Meta Title: {meta_title}")

        # Generate meta_description using GPT API
        if product_name:
            product_link = f"{shop_base_url}/index.php?id_product={product_id}&controller=product"
            gpt_prompt = f"Write an SEO meta description for the following product: {product_name}. " \
                         f"product description: {short_description_text} how to use: {how_to_use} ingredients: {active_ingredients}, and output only the description max 160 characters."

            # Updated API call
            gpt_response = client.chat.completions.create(model="gpt-4o",
            messages=[
                {"role": "user", "content": gpt_prompt}
            ],
            max_tokens=50)
            meta_description_gpt = gpt_response.choices[0].message.content.strip()
            print(f"Generated Meta Description: {meta_description_gpt}")

        # Update meta_title, meta_description, and link_rewrite
        for language in root.findall(".//{*}meta_title/{*}language"):
            language.text = meta_title

        for language in root.findall(".//{*}meta_description/{*}language"):
            language.text = meta_description_gpt

        for language in root.findall(".//{*}link_rewrite/{*}language"):
            language.text = product_name.lower().replace(" ", "-")

        # Convert updated XML back to string
        updated_data = ET.tostring(root, encoding='utf-8', method='xml')

        # Send the PUT request to update the product using HTTPBasicAuth
        update_response = requests.put(product_url, data=updated_data, headers=headers, auth=HTTPBasicAuth(api_key, ''))

        if update_response.status_code in [200, 201]:
            print(f"Product {product_id} updated successfully!")
        else:
            print(f"Failed to update product {product_id}: {update_response.status_code}")
            print(update_response.text)
    else:
        print(f"Failed to retrieve product {product_id}: {response.status_code}")
        print(response.text)

# Example usage
update_product_meta(
    product_id=12
)
