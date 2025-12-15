
from consts import SHOP_NAME,ADMIN_API_VERSION
from credentials import Credentials

def get_url_and_headers():
    url = 'https://{0}.myshopify.com/admin/api/{1}/graphql.json'.format(SHOP_NAME,ADMIN_API_VERSION)
    headers = {"Content-Type": "application/graphql","X-Shopify-Access-Token": Credentials().SHOPIFY_PASSWORD_RW }
    return url,headers

def get_orders_cursor_items(res):
    try:
        pageInfo = res['data']['orders']['pageInfo']
        endCursor = pageInfo['endCursor']
        hasNextPage = pageInfo['hasNextPage']
    except:
        endCursor = None
        hasNextPage = False
    return endCursor, hasNextPage