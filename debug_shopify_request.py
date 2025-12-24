import requests
import json
import pprint
from datetime import datetime,timedelta
from dateutil import parser
from consts import SHOP_NAME,NEAF_VENDOR,ADMIN_API_VERSION
from credentials import Credentials
from graphql_queries import ORDER_DETAILS,ORDER_BY_ORDER_ID,ORDERS_BY_SKU_BETWEEN_DATES,ORDER_BY_NAME,ORDERS_BETWEEN_DATES
from graphql_utils import get_orders_cursor_items,get_url_and_headers
from utils import remove_unicode

'''
    # some useful sample orders for debugging interesting use cases    
    order_id = 1980097560658  # test order #9130 for Joe's dumb ass scopes
    # order_id = 1974718529618 # order #9129 for photonic cleaning
    order_id = 2144708198482  # order #9481 for nimax with partial refund
    order_id = 2144844677202  # order #9483 also for nimax, partial refunds
    order_id = 5060039639122  # order 13167 for Donald A Kaplan buying membership at club table for NEAF 2023 using POS
    order_id = 5668545167442 # order 14881 for raffle with missing name. get this name of card, PINE/HOWARD E
    #order_id = 5668547231826 # order 14882 for raffle with Nina Craven.
    order_id = '5543777173586' # order 13695 with Delete_Original_Badge_Name_13695_2 : Leah Hobelman, Delete_Original_Badge_Name_13695_3 : Daniel Bisq
'''

def graphql_orders_by_sku_between_dates(sku=NEAF_VENDOR,created_at_min='2025-12-02',created_at_max='2025-12-05'):

    url,headers = get_url_and_headers()
    req = ORDERS_BY_SKU_BETWEEN_DATES
    req = req.replace('SKU_PREFIX_HERE',sku+'_')
    req = req.replace('CREATED_AT_MIN',created_at_min)
    if not created_at_max:
        created_at_max = datetime.now().date().strftime('%Y-%m-%d')
    created_at_max = parser.parse(created_at_max) + timedelta(days=1)
    created_at_max = created_at_max.strftime('%Y-%m-%d')
    req = req.replace('LIMIT','200')
    req = req.replace('CREATED_AT_MAX',created_at_max)
    req = req.replace('INSERT_ORDER_DETAILS_HERE',ORDER_DETAILS)
    orig_req = req
    req = req.replace('after: "END_CURSOR_HERE",', '')

    while True:
        request = requests.post(url, data=req, headers=headers)
        print(f'\nexecuted\nrequest = requests.post(url, data=req, headers=headers)\nwith\nurl:\n{url}\nreq:{req}\nheaders:{headers}\n')
        res = json.loads(request.text)
        errors = res.get('errors')
        if errors:
            print(f'\nQUERY FAILED with:\n{pprint.pformat(errors,width=100)}\n')
            break

        res_str = pprint.pformat(res,width=200)
        print(res_str)
        endCursor, hasNextPage = get_orders_cursor_items(res)

        if not hasNextPage:
            break
        req = orig_req.replace('END_CURSOR_HERE', endCursor)

    return

def graphql_orders_between_dates(created_at_min='2025-12-02',created_at_max='2025-12-08',fullResDump=False):

    url,headers = get_url_and_headers()
    req = ORDERS_BETWEEN_DATES
    req = req.replace('CREATED_AT_MIN',created_at_min)
    if not created_at_max:
        created_at_max = datetime.now().date().strftime('%Y-%m-%d')
    req = req.replace('LIMIT','200')
    req = req.replace('CREATED_AT_MAX',created_at_max)
    req = req.replace('INSERT_ORDER_DETAILS_HERE',ORDER_DETAILS)
    orig_req = req
    req = req.replace('after: "END_CURSOR_HERE",', '')

    while True:
        request = requests.post(url, data=req, headers=headers)
        print(f'\nexecuted\nrequest = requests.post(url, data=req, headers=headers)\nwith\nurl:\n{url}\nreq:{req}\nheaders:{headers}\n')
        res = json.loads(request.text)
        errors = res.get('errors')
        if errors:
            print(f'\nQUERY FAILED with:\n{pprint.pformat(errors,width=100)}\n')
            break

        if fullResDump:
            res_str = pprint.pformat(res,width=200)
            print(res_str)

        for i,order in enumerate(res['data']['orders']['edges']):
            order = order['node']
            print(f"{i}: name:{order['name']}, createdAt:{order['createdAt']}, cancelledAt:{order['cancelledAt']}")

        endCursor, hasNextPage = get_orders_cursor_items(res)

        if not hasNextPage:
            break
        req = orig_req.replace('END_CURSOR_HERE', endCursor)

    return

def graphql_order_by_order_id_test(order_id='6104100438098'):
    url,headers = get_url_and_headers()
    req = ORDER_BY_ORDER_ID
    req = req.replace('INSERT_ORDER_ID_HERE',order_id)
    req = req.replace('INSERT_ORDER_DETAILS_HERE',ORDER_DETAILS)
    request = requests.post(url, data=req, headers=headers)
    res = json.loads(request.text)
    errors = res.get('errors')
    if errors:
        errors_str = pprint.pformat(errors, width=100)
        print(errors_str)
    else:
        res_str = pprint.pformat(res, width=200)
        print(res_str)
    return

def graphql_order_by_name_test(name='17204'):

    # 12/26/2024. 13695 has "Additional details" of company name edit and 2 bdage name deletes. Also has refund of booth.
    # 2/28/2025.  15569 skywatcher has 848-248-0424 in old phone_num but MISSING in new.
    #             15472 Willie Yee has SIDE DOOR in old address but missing in new.
    # 12/16/2025. 17190. Caneled order for 'Joes half assed scopes'. has 'cancelledAt': '2025-12-04T17:39:18Z'.

    url,headers = get_url_and_headers()
    req = ORDER_BY_NAME
    req = req.replace('ORDER_NUM',name)
    req = req.replace('INSERT_ORDER_DETAILS_HERE',ORDER_DETAILS)
    request = requests.post(url, data=req, headers=headers)
    res = json.loads(request.text)
    errors = res.get('errors')
    if errors:
        errors_str = pprint.pformat(errors, width=100)
        print(errors_str)
    else:
        res_str = pprint.pformat(res, width=200)
        print(res_str)
    return

def main():
    #rest_api()
    #graphql_orders_by_sku_between_dates()
    graphql_orders_between_dates()
    #graphql_order_by_order_id_test()
    #graphql_order_by_name_test()
    return

main()


