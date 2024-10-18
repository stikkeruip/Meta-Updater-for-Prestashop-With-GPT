import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# PrestaShop API details from environment variables
prestashop_url = os.getenv('PRESTASHOP_URL')
api_key = os.getenv('PRESTASHOP_API_KEY')


def update_product_meta(product_id, meta_title, meta_description, link_rewrite):
    # Construct the product URL with the API key as a parameter
    product_url = f"{prestashop_url}/products/{product_id}?ws_key={api_key}"

    # Headers for request
    headers = {
        'Content-Type': 'application/xml',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    # Fetch the product data without using HTTPBasicAuth
    response = requests.get(product_url, headers=headers)

    if response.status_code == 200:
        # Parse XML response
        tree = ET.ElementTree(ET.fromstring(response.content))
        root = tree.getroot()

        # Update meta title, meta description, and URL (link_rewrite)
        root.find('meta_title/language').text = meta_title
        root.find('meta_description/language').text = meta_description
        root.find('link_rewrite/language').text = link_rewrite

        # Convert updated XML back to string
        updated_data = ET.tostring(root)

        # Send the PUT request to update the product without using HTTPBasicAuth
        update_response = requests.put(product_url, data=updated_data, headers=headers)

        if update_response.status_code == 200:
            print(f"Product {product_id} updated successfully!")
        else:
            print(f"Failed to update product {product_id}: {update_response.content}")
    else:
        print(f"Failed to retrieve product {product_id}: {response.content}")


# Example: update meta title, description, and URL for the specific product ID 12
update_product_meta(12, "New Meta Title for Prodigal Pen", "New Meta Description for Prodigal Pen",
                    "prodigal-pen-updated")
