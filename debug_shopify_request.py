import requests
import json
import pprint
from datetime import datetime,timedelta
from dateutil import parser
from consts import SHOP_NAME,NEAF_VENDOR,ADMIN_API_VERSION
from credentials import Credentials
from graphql_queries import ORDER_DETAILS,ORDER_BY_ORDER_ID,ORDERS_BY_SKU_BETWEEN_DATES,ORDER_BY_NAME
from graphql_utils import get_orders_cursor_items,get_url_and_headers
from utils import remove_unicode

def rest_api():
    # some sample shopify queries other than orders, not that interesting.
    '''
    response = requests.get( 'https://%s.myshopify.com/admin/products/count.json' % SHOP_NAME,
                               auth=(Credentials().SHOPIFY_API_KEY,Credentials().SHOPIFY_PASSWORD))
    print response.text
    response = requests.get( 'https://%s.myshopify.com/admin/orders/count.json' % SHOP_NAME,
                               auth=(Credentials().SHOPIFY_API_KEY,Credentials().SHOPIFY_PASSWORD))
    if response.status_code != 200:
        print 'Failure, response.status_code is {0}'.format(response.status_code)
    print response.text
    # max response size is 250. have to read pages after that.
    response = requests.get( 'https://%s.myshopify.com/admin/orders.json?since_id=3010' % SHOP_NAME,
                               auth=(Credentials().SHOPIFY_API_KEY,Credentials().SHOPIFY_PASSWORD))
    text1 = response.text
    print response.status_code
    req = 'https://%s.myshopify.com/admin/orders.json?updated_at_min=2015-02-01 00:00:01 EDT -04:00' % SHOP_NAME
    response = requests.get(req,auth=(Credentials().SHOPIFY_API_KEY,Credentials().SHOPIFY_PASSWORD))
    print response.status_code
    text2 = response.text  '''

    # look at doc C:\Users\joe1\rac\ecommerce\docs\shopify_api_json_schema.txt on 76 Lime Kiln computer for details on
    # schema for orders .  small modification to build_door_prize_dict_from_shopify and get_doorPrizeTup_dict should
    # support processing of NEAF vendor orders.

    # reqstr = 'https://%s.myshopify.com/admin/orders.json?' +\
    #    'fields=created_at,id,name,customer,line_items&limit=250&page=1&created_at_min=2014-10-01 00:01'

    order_id = 1980097560658  # test order #9130 for Joe's dumb ass scopes
    # order_id = 1974718529618 # order #9129 for photonic cleaning
    order_id = 2144708198482  # order #9481 for nimax with partial refund an cancel
    order_id = 2144844677202  # order #9483 also for nimax, partial refunds
    order_id = 5060039639122  # order 13167 for Donald A Kaplan buying membership at club table for NEAF 2023 using POS
    order_id = 5668545167442 # order 14881 for raffle with missing name. get this name of card, PINE/HOWARD E
    #order_id = 5668547231826 # order 14882 for raffle with Nina Craven.
    order_id = '5543777173586' # order 13695 with Delete_Original_Badge_Name_13695_2 : Leah Hobelman, Delete_Original_Badge_Name_13695_3 : Daniel Bisq

    # reqstr = 'https://{0}.myshopify.com/admin/orders/{1}.json'
    reqstr = 'https://{0}.myshopify.com/admin/api/{1}/orders/{2}.json' # previously was 2019-10
    req = reqstr.format(SHOP_NAME, ADMIN_API_VERSION, order_id)

    # 1/27/2024. how to get event timeline
    # reqstr = 'https://{0}.myshopify.com/admin/api/{1}/orders/{2}/events.json'
    # req = reqstr.format(SHOP_NAME, ADMIN_API_VERSION, order_id)

    # 4/29/2024. how to get transaction from credit card from POS.
    #            returns rd['transactions'][0]['payment_details']['credit_card_name'] of 'PINE/HOWARD E' for order_id = 5668545167442
    # reqstr = 'https://{0}.myshopify.com/admin/api/{1}/orders/{2}/transactions.json'
    # req = reqstr.format(SHOP_NAME, ADMIN_API_VERSION, order_id)

    print('\nRUNNING\nreq:{0}\nCredentials().SHOPIFY_API_KEY_2:{1}, Credentials().SHOPIFY_PASSWORD_2:{2}\n'.format(req,Credentials().SHOPIFY_API_KEY_2,Credentials().SHOPIFY_PASSWORD_2))
    response = requests.get(req, auth=(Credentials().SHOPIFY_API_KEY_2, Credentials().SHOPIFY_PASSWORD_2))
    print((response.status_code))
    # print response.text
    rd = json.loads(response.text) # ['events']
    rd = remove_unicode(rd)
    # 12/18/2019. msg is full dump of orders. very useful for seeing what's available for note_attributes in function shopify_https_request
    msg = pprint.pformat(rd, width=200)
    print(msg)
    note = rd.get('note')
    print(note)
    return

def graphql_orders_by_sku_between_dates(sku=NEAF_VENDOR,created_at_min='2024-01-30',created_at_max='2024-01-30'):

    url,headers = get_url_and_headers()
    req = ORDERS_BY_SKU_BETWEEN_DATES
    req = req.replace('SKU_PREFIX_HERE',sku+'_')
    req = req.replace('CREATED_AT_MIN',created_at_min)
    if not created_at_max:
        created_at_max = datetime.now().date().strftime('%Y-%m-%d')
    created_at_max = parser.parse(created_at_max) + timedelta(days=1)
    created_at_max = created_at_max.strftime('%Y-%m-%d')
    req = req.replace('CREATED_AT_MAX',created_at_max)
    req = req.replace('INSERT_ORDER_DETAILS_HERE',ORDER_DETAILS)
    orig_req = req
    req = req.replace('after: "END_CURSOR_HERE",', '')

    while True:
        request = requests.post(url, data=req, headers=headers)
        res = json.loads(request.text)
        errors = res.get('errors')
        if errors:
            errors_str = pprint.pformat(errors,width=100)
            print(errors_str)
            break

        res_str = pprint.pformat(res,width=200)
        print(res_str)
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

def graphql_order_by_name_test(name='15569'):

    # 12/26/2024. 13695 has "Additional details" of company name edit and 2 bdage name deletes. Also has refund of booth.
    # 2/28/2025.  15569 skywatcher has 848-248-0424 in old phone_num but MISSING in new.
    #             15472 Willie Yee has SIDE DOOR in old address but missing in new.

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
    #graphql_order_by_order_id_test()
    graphql_order_by_name_test()
    return

main()


