

import requests
import json
from consts import SHOP_NAME,SHOPIFY_API_VERSION
from credentials import Credentials

def get_first_n_products(n=3):

    # Use your existing credentials.txt reader here
    private_token = Credentials().SHOPIFY_STOREFRONT_PRIVATE_TOKEN

    url = f"https://{SHOP_NAME}.myshopify.com/api/{SHOPIFY_API_VERSION}/graphql.json"

    headers = {"Content-Type": "application/json","Shopify-Storefront-Private-Token": private_token}

    query = """
    {
        products(first: N) {
            nodes {
                id
                title
                handle
            }
        }
    }
    """
    query = query.replace(': N',f': {n}')

    response = requests.post(url,headers=headers,json={"query": query},timeout=30)

    print("HTTP status:", response.status_code)
    print(json.dumps(response.json(), indent=4))

    return

def get_variant_ids(product_handle='electricity'):

    url = f"https://{SHOP_NAME}.myshopify.com/api/{SHOPIFY_API_VERSION}/graphql.json"

    headers = {"Content-Type": "application/json","Shopify-Storefront-Private-Token": Credentials().SHOPIFY_STOREFRONT_PRIVATE_TOKEN
    }

    query = """
    query ($handle: String!) {
        product(handle: $handle) {
            title
            variants(first: 20) {
                nodes {
                    id
                    title
                }
            }
        }
    }
    """

    response = requests.post(url,headers=headers,json={"query": query, "variables": {"handle": product_handle}},timeout=30)

    response.raise_for_status()
    result = response.json()
    print(json.dumps(result, indent=4))
    return result

def create_cart(variant_id, quantity, company_name):

    url = f"https://{SHOP_NAME}.myshopify.com/api/{SHOPIFY_API_VERSION}/graphql.json"

    headers = {"Content-Type": "application/json","Shopify-Storefront-Private-Token": Credentials().SHOPIFY_STOREFRONT_PRIVATE_TOKEN}

    query = """
    mutation ($input: CartInput!) {
        cartCreate(input: $input) {
            cart {
                id
                checkoutUrl
                lines(first: 10) {
                    nodes {
                        quantity
                        attributes {
                            key
                            value
                        }
                        merchandise {
                            ... on ProductVariant {
                                id
                                title
                                product {
                                    title
                                }
                            }
                        }
                    }
                }
                cost {
                    totalAmount {
                        amount
                        currencyCode
                    }
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    """

    variables = {
        "input": {
            "lines": [{
                "merchandiseId": variant_id,
                "quantity": quantity,
                "attributes": [{
                    "key": "My Company Name",
                    "value": company_name
                }]
            }]
        }
    }

    response = requests.post(url,headers=headers,json={"query": query, "variables": variables},timeout=30)

    print("HTTP status:", response.status_code)
    result = response.json()
    print(json.dumps(result, indent=4))
    response.raise_for_status()
    return result

def purchase_electricity():

    # 10/22/2026: Retrieve variant ID dynamically in production. to get variant_id run get_variant_ids()
    variant_id = "gid://shopify/ProductVariant/33981256272"
    company_name = "RAC Headless Test"
    quantity = 1

    result = create_cart(variant_id,quantity=quantity,company_name=company_name)

    if result.get("errors"):
        print("GraphQL errors:", result["errors"])
        return

    cart_result = result["data"]["cartCreate"]

    if cart_result["userErrors"]:
        print("Cart errors:", cart_result["userErrors"])
        return

    cart = cart_result["cart"]

    if cart:
        print("\nCHECKOUT URL:")
        print(cart["checkoutUrl"])

    return

#get_first_n_products()
#get_variant_ids()
purchase_electricity()