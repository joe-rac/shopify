import copy
import json
# install with
# pip install requests
import requests
import pprint
from consts import SHOP_NAME,ADMIN_API_VERSION
from graphql_queries import MUTATE_CUSTOM_ATTRIBUTES,ORDER_ID_AND_NOTE_ATTRIBUTES
from utils import appendMsg
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

def edges_node_to_list(val):
    if not isinstance(val,dict):
        return val
    edges_list = val.get('edges')
    pageInfo = val.get('pageInfo')
    if pageInfo is None and isinstance(edges_list,list) and len(edges_list) == 0:
        # 2/13/2025. this block for refund that's missing refundLineItems but has refund against entire order. Example is #15317 with totalRefundedSet of $306.
        return []
    if isinstance(edges_list,list) and len(edges_list) == 0:
        # 1/15/2026. this block if no orders for given sku and date range are returned. for example on this day no rad have yet been placed.
        return []
    cleanup_val =  bool(len(val) == 2 and edges_list and pageInfo) or bool(len(val) == 1 and edges_list)
    if not cleanup_val:
        return val
    if not isinstance(edges_list,list) or not edges_list or not isinstance(edges_list[0],dict) or len(edges_list[0]) != 1 or not edges_list[0].get('node') :
        return val
    new_val = []
    for edge in edges_list:
        new_val.append(edge['node'])
    return new_val

def load_and_adjust_custom_attributes(order_num,key,value=None,delete_key=False):
    '''
    3/29/2026:
    Load customAttributes under the order with order_num into memory and return that image to caller.
    Can optionally edit that customAttributes image before returning it. Can 1) edit value in existing key/value pair, 2) add new key/value pair, 3) delete existing key/value pair.
    If both passed in order_num and key are blank just return unedited customAttributes.
    This function writes nothing back to Shopify. Use mutate_custom_attributes to write customAttributes back to Shopify.

    Args:
        order_num (str): ex. '15264'
        key (str): ex. 'Badge_Name_15264_4'
        value (str): ex. 'Moshe Yisroel'

    Returns:
        tuple: (msg, order_id, success, customAttributes)
            msg (str): status or error message
            order_id (str): Shopify order ID, ex. gid://shopify/Order/6145908867154
            success (bool): True if update succeeded
            customAttributes (list[dict]): updated attributes
    '''

    order_id = None
    success = False
    customAttributes = []
    kStr = f"'{key}'" if isinstance(key,str) else f'{key}'
    vStr = f"'{value}'" if isinstance(value,str) else f'{value}'

    msg = appendMsg(f"Entering load_and_adjust_custom_attributes with order_num:{order_num}, key:{kStr}, value:{vStr}, delete_key:{delete_key}",print_new_msg=False)
    if not delete_key and ((not key and value) or (key and not value)):
        msg = msg = appendMsg(msg,f'success:{success}, order_id:{order_id}',print_new_msg=False)
        msg = appendMsg(msg,f"key:{kStr}/value:'{value} is invalid. They must both exist to edit the pair or both missing to only return existing customAttributes.",print_new_msg=False)
        return msg,order_id,success,customAttributes
    if not key and delete_key:
        msg = msg = appendMsg(msg,f'success:{success}, order_id:{order_id}',print_new_msg=False)
        msg = appendMsg(msg,f"delete_key:{delete_key} and key:{kStr} are incompatible. Cannot delete if not passing in key.",print_new_msg=False)
        return msg,order_id,success,customAttributes
    if delete_key and value:
        msg = msg = appendMsg(msg,f'success:{success}, order_id:{order_id}',print_new_msg=False)
        msg = appendMsg(msg,f"delete_key:{delete_key} and value:{vStr} are incompatible. When deleting a key no value can be entered.",print_new_msg=False)
        return msg,order_id,success,customAttributes
    gql = ORDER_ID_AND_NOTE_ATTRIBUTES.replace('#ORDER_NUM', str(order_num))
    url, headers = get_url_and_headers()
    response = requests.post(url, data=gql, headers=headers)
    msg = appendMsg(msg,f'status_code from requests.post:{response.status_code}',print_new_msg=False)
    rd = response.json()
    #print(pprint.pformat(rd, width=200))

    errors = rd.get('errors')
    if errors:
        msg = msg = appendMsg(msg,f'success:{success}, order_id:{order_id}',print_new_msg=False)
        msg = appendMsg(msg,f'GraphQL errors:\n{pprint.pformat(errors, width=200)}',print_new_msg=False)
        return msg,order_id,success,customAttributes

    orders = edges_node_to_list(rd.get('data', {}).get('orders', {}))
    if not orders:
        msg = msg = appendMsg(msg,f'success:{success}, order_id:{order_id}',print_new_msg=False)
        msg = appendMsg(msg,f'Did not find order for order_num:{order_num}',print_new_msg=False)
        return msg,order_id,success,customAttributes

    order_id = orders[0]['id']
    customAttributes = orders[0]['customAttributes']
    customAttributes_orig = copy.deepcopy(customAttributes)
    if not key and not value:
        success = True
        msg = msg = appendMsg(msg,f'success:{success}, order_id:{order_id}',print_new_msg=False)
        msg = appendMsg(msg,f'key/value pair are both missing. Only return existing customAttributes.',print_new_msg=False)
        return msg,order_id,success,customAttributes

    item_index = None
    value_current = None
    for i,customAtribute in enumerate(customAttributes):
        if key == customAtribute['key']:
            item_index = i
            value_current = customAtribute['value']

    if delete_key:
        if item_index is None:
            msg = msg = appendMsg(msg,f'success:{success}, order_id:{order_id}',print_new_msg=False)
            msg = appendMsg(msg,f"Failure try to delete key:{key}. It does not exist in customAttributes.",print_new_msg=False)
            return msg,order_id,success,customAttributes
        else:
            del customAttributes[item_index]
            msg = appendMsg(msg,f"Deleted item with key:{key} from customAttributes.",print_new_msg=False)
    else:
        if item_index is not None:
            if value == value_current:
                msg = msg = appendMsg(msg,f'success:{success}, order_id:{order_id}',print_new_msg=False)
                msg = appendMsg(msg,f"The requested key:{kStr}/value:{vStr} pair already exists in customAttributes. No action will be taken.",print_new_msg=False)
                return msg,order_id,success,customAttributes
            else:
                msg = appendMsg(msg,f"The requested key:{kStr} already exists but will change value from '{value_current}' to {vStr}.",print_new_msg=False)
                customAttributes[item_index] = {'key':key,'value':value}
        else:
            customAttributes.append({'key':key,'value':value})

    success = True
    msg = msg = appendMsg(msg,f'success:{success}, order_id:{order_id}',print_new_msg=False)
    msg = appendMsg(msg,f'original customAttributes:\n{pprint.pformat(customAttributes_orig, width=200)}',print_new_msg=False)
    msg = appendMsg(msg,f'new customAttributes:\n{pprint.pformat(customAttributes, width=200)}',print_new_msg=False)
    return msg,order_id,success,customAttributes

def mutate_custom_attributes(order_num, order_id, customAttributes):
    '''
    3/29/2026:
    Write the passed in customAttributes back to Shopify under the passed in order_id.

    Args:
        order_num (str): ex. '15264'
        order_id (str): ex. 'gid://shopify/Order/6145908867154'
        customAttributes (list[dict]): in form [{'key':'Badge_Name_15264_2','value':'Civilian Laurie Zeilberger'},...]

    Returns:
        success (bool)
        msg (str): status or error message

    '''
    msg = ''
    variables = {"input": {"id": order_id, "customAttributes": customAttributes }}
    vstr = pprint.pformat(variables, width=200)
    note_update = json.dumps({"query": MUTATE_CUSTOM_ATTRIBUTES,"variables": variables})
    r_headers = {'Content-Type': 'application/json'}
    req = f"https://{SHOP_NAME}.myshopify.com/admin/api/{ADMIN_API_VERSION}/graphql.json"

    r = requests.post(url=req, data=note_update, auth=(Credentials().SHOPIFY_API_KEY_RW,Credentials().SHOPIFY_PASSWORD_RW),headers = r_headers)
    if r.status_code != 200:
        msg = f"Failed updating customAttributes:\n{vstr}\nin shopify. Response status_code:{r.status_code} is invalid. Expecting 200.\nYou're fucked. Contact your programmer."
        return False,msg
    else:
        vstr = pprint.pformat(variables, width=200)
        msg = f'\nSuccessfully updated customAttributes for order_num:{order_num} at\n{req}\nwith data\n{vstr}\n'
    return True,msg
