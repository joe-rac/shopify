
import pprint
import requests
import json
# valid sku keys
from consts import MEMBERSHIP,DONATION,NEAF_ATTEND,NEAF_ATTEND_RAFFLE,NEAIC_ATTEND,RAD,HSP,HSP_RAFFLE,RLS,SSP,DOOR_PRIZE,MERCH,NEAF_VENDOR,USE_GRAPHQL,ADMIN,ALL
from consts import SHOP_NAME,ADMIN_API_VERSION
from credentials import Credentials
from orders import AccessOrders,Orders
from utils import remove_unicode
from neaf_vendor import NEAFVendor

import tracemalloc
tracemalloc.start()
print('At debug_utils module startup we have current:{0}, peak:{1} from tracemalloc.get_traced_memory()'.format(*tracemalloc.get_traced_memory()))

refund_examples = [
    ('2025-01-19', '2025-01-20', 15317), # Amateur Astronomers Assoc. of Pittsburgh, #15317(1/19/2025). refund of $306 to whole order
    ('4/29/2019', '4/30/2019', 8948),  # for SSP Travis Adams had refund_line_items of membership refunded but kept SSP chicken barbecue lineitem.
    ('3/2/2021', '3/3/2021', 10638),  # company is AAPOD2. dollars on order. refunded full $20 on logo and link
    ('1/22/2020', '1/22/2020', 9239),  # dollars on order. software bisque. refunded $50 on badge.
    ('1/26/2023','1/27/2023', 11709),  # a full refunded order for IOptron for $2612.
    ('1/27/2020', '1/28/2020', 9255),  # Rowan Engineering. attempted but failed refund of entire order of $534
    ('3/6/2020', '3/7/2020', 9481),  # Nimax refunded 3/6/2020. table went from 5 to 2 for $165 refunded. chairs went 4 to 2 for $24 refunded. refund 2 badges for $100.
                                     # failed to refund $128 years later on 4/14/2023.
    ('1/30/2024', '1/31/2024', 13695), # Software Bisque had 2 orders, 13704|13695. has company name and badge name edits. only #13695 had refund. $1130 for 2 booths out of $2178 total refunded
    ('1/31/2024', '2/1/2024', 13712), # Explore Scientific had 2 orders, 13712|13717. refunded 8 standard booths in 13712 and he bought 8 premium in 13717.
    ('11/20/2023','11/21/2023',13415), # Airy Disk. full refund of $1442 then another order with pay by check.
    ('3/29/2020','3/30/2020',9541),    # Don Spong. refund of NEAF Virtual Experience ticket.
    ('2/26/2020','2/27/2020',9404),    # Nimax. refunded $402, full order refunded. intent was standard booth, not premium.
    ('2/20/2019','2/21/2019',7618),    # QHYCCD. refunded $396, full order refund of booth.
]

def accesshopify_by_date_range_and_sku(ind=8,use_graphlql=True):

    orig_use_graphql = USE_GRAPHQL[0]
    USE_GRAPHQL[0] = use_graphlql

    # 1/2/2025. this block returns 7 orders
    order_to_debug = None
    product_type = None # ALL # ADMIN # DONATION # NEAF_VENDOR # ALL
    created_at_min = '2021-03-02'
    created_at_max = '2021-03-02'

    # 1/8/2025. zwo is missing $200 live stream order because I left out sku. I just added it to product as neaf_vendor_sponsor_live_stream.
    # order_to_debug = 15252
    # product_type = None
    # created_at_min = None  # '2019-04-29'
    # created_at_max = None  # '2019-04-29'

    if USE_GRAPHQL[0]:
        created_at_min = None
        created_at_max = None
        order_to_debug = refund_examples[ind][2]
    else:
        created_at_min = refund_examples[ind][0]
        created_at_max = refund_examples[ind][1]
        order_to_debug = refund_examples[ind][2]


    # this block for Thomas Simstad, New Mexico Skies high priced order for $2000 of neaf_vendor_sponsor_live_steam
    # created_at_min = None # '2025-01-31'
    # created_at_max = None # '2025-02-01'
    # order_to_debug = 15436 # 15404

    # bought raffle ticket with swipper and need to get phone number off timeline
    created_at_min = None
    created_at_max = None
    #order_to_debug = '13167' # '13136' # '13167'

    # 15569, skywatcher has 848-248-0424 in old phone_num but MISSING in new.
    # 15472, Willie Yee has SIDE DOOR in old address2 but MISSING in new.
    # 15478, Frank      has address2 Jackson, NJ old but Pomona with 2C in address2 in new
    # 15334, Sarah has blank for address2 and phone_num but MISSING for both in new (REPAIRED)
    # 15512, funny looking X in address.
    order_to_debug = '15512'

    # this block loads 22 orders from #15397 to #15418. its good example to test processing of many orders in single query.
    # created_at_min = '2025-01-31'
    # created_at_max = '2025-02-01'
    # order_to_debug = None
    # product_type = ALL

    verbose = False
    orders = Orders(product_type,order_to_debug=order_to_debug,verbose=verbose)
    if orders.error:
        print(orders.error)
        USE_GRAPHQL[0] = orig_use_graphql
        return
    orders.shopifyLoad(created_at_min=created_at_min,created_at_max=created_at_max)

    msg = orders.error if orders.error else orders.show_dicts()
    print(msg)

    #accessOrders = AccessOrders( sku_key,created_at_min,created_at_max=None, order_to_debug, verbose)
    USE_GRAPHQL[0] = orig_use_graphql

    return

#accesshopify_by_date_range_and_sku()

def neafvendors_from_orders(ind=12,use_graphql=True):

    orig_use_graphql = USE_GRAPHQL[0]
    USE_GRAPHQL[0] = use_graphql

    from neaf_vendor import NEAFVendor
    neaf_year = '' # '2024'
    verbose = False

    if USE_GRAPHQL[0]:
        created_at_min = None
        created_at_max = None
        order_to_debug = refund_examples[ind][2]
    else:
        pass
        created_at_min = None
        created_at_max = None
        #created_at_min = refund_examples[ind][0]
        #created_at_max = refund_examples[ind][1]
        #order_to_debug = refund_examples[ind][2]

    # missing oberwerk donation value on s/s.
    # created_at_min = '2019-04-29'
    # created_at_max = created_at_min
    # TODO 2/18/2024. supporting a single order_to_debug works fine for Oberwerk since they only did one order. That won't work for other vendors.
    #                 support multiple orders for single vendor like for Explore Scientific with
    #                 order_to_debug = '13717|13712'
    # order_to_debug = '8948'
    # 12/16/2025. 17190|17193|17198|17206|17218 are 5 canceled orders for Joes half assed scope. working on bug fix to exclude them from further NEAF vendor processing.
    order_to_debug = '17190|17193|17198|17206|17218'

    nv = NEAFVendor(neaf_year,created_at_min,created_at_max,order_to_debug,verbose)
    nv.shopifyLoad()
    if nv.error:
        print(nv.error)
    else:
        print(nv.output_nvt_csv('neaf_management'))
        #company_key = 'Australis'
        invoice = next(iter(nv.nv_collections.vendor_invoices.values()))
        print(invoice)

    USE_GRAPHQL[0] = orig_use_graphql

    return

neafvendors_from_orders()

def neafvendor_load(neaf_year='2025',verbose=False, use_graphql=True):
    USE_GRAPHQL[0] = use_graphql
    neafVendor = NEAFVendor(neaf_year=neaf_year, verbose=verbose)
    if neafVendor.error:
        print(neafVendor.error + '\n' + neafVendor.msg)
        return
    neafVendor.shopifyLoad()
    if neafVendor.error:
        print(neafVendor.error)
    else:
        all_invoices = neafVendor.nv_collections.vendor_invoices

    return
#neafvendor_load()

def create_neaic_report():

    verbose = False
    product_type = NEAIC_ATTEND
    created_at_min = '2024-01-01'
    created_at_max = None
    order_to_debug = None

    orders = Orders(product_type, verbose=verbose)
    msg, order_num = orders.get_latest_neaic_order_number()
    orders.shopifyLoad(created_at_min=created_at_min, created_at_max=created_at_max, order_to_debug=order_to_debug)
    msg = orders.error if orders.error else orders.neaic_attendee_dump_to_csv(incremental_since_last_run=True)

    print(msg)

    return

def rester_sample_read():

    # some sample shopify queries other than orders, not that interesting.

    '''
    response = requests.get( 'https://%s.myshopify.com/admin/products/count.json' % SHOP_NAME, auth=(Credentials().SHOPIFY_API_KEY,Credentials().SHOPIFY_PASSWORD))
    print response.text
    response = requests.get( 'https://%s.myshopify.com/admin/orders/count.json' % SHOP_NAME, auth=(Credentials().SHOPIFY_API_KEY,Credentials().SHOPIFY_PASSWORD))
    if response.status_code != 200:
        print 'Failure, response.status_code is {0}'.format(response.status_code)
    print response.text
    # max response size is 250. have to read pages after that.
    response = requests.get( 'https://%s.myshopify.com/admin/orders.json?since_id=3010' % SHOP_NAME,auth=(Credentials().SHOPIFY_API_KEY,Credentials().SHOPIFY_PASSWORD))
    text1 = response.text
    print response.status_code
    req = 'https://%s.myshopify.com/admin/orders.json?updated_at_min=2015-02-01 00:00:01 EDT -04:00' % SHOP_NAME
    response = requests.get(req,auth=(Credentials().SHOPIFY_API_KEY,Credentials().SHOPIFY_PASSWORD))
    print response.status_code
    text2 = response.text  '''

    # look at doc C:\Users\joe1\rac\ecommerce\docs\shopify_api_json_schema.txt on 76 Lime Kiln computer for details on
    # schema for orders .  small modification to build_door_prize_dict_from_shopify and get_doorPrizeTup_dict should
    # support processing of NEAF vendor orders.

    #reqstr = 'https://%s.myshopify.com/admin/orders.json?' +\
    #    'fields=created_at,id,name,customer,line_items&limit=250&page=1&created_at_min=2014-10-01 00:01'

    return

#rester_sample_read()

def rester_note_attributes_update_1():

    order_id = 1980097560658 # test order #9130 for Joe's dumb ass scopes
    #order_id = 1974718529618 # order #9129 for photonic cleaning
    order_id = 2144708198482 # order #9481 for nimax with partial refund an cancel
    order_id = 2144844677202 # order #9483 also for nimax, partial refunds
    order_id = 5060039639122 # order 13167 for Donald A Kaplan buying membership at club table for NEAF 2023 using POS
    order_id = 6208463405138 # order 15568 for Celestron with NEAF Vendor Payment of $1450 with bad  'note_attributes': [{'name': '1 - NEAF Vendor Payment', 'value': ''}]
    #order_id = '6234913341522' # order 15713 for NEAIC with no note_attribute items of []

    #reqstr = 'https://{0}.myshopify.com/admin/orders/{1}.json'
    reqstr = 'https://{0}.myshopify.com/admin/api/{1}/orders/{2}.json'
    req = reqstr.format(SHOP_NAME,ADMIN_API_VERSION,order_id)
    response = requests.get(req,auth=(Credentials().SHOPIFY_API_KEY_RW,Credentials().SHOPIFY_PASSWORD_RW))
    print((response.status_code))
    #print response.text
    rd =  json.loads(response.text)['order']
    rd = remove_unicode(rd)
    # 12/18/2019. msg is full dump of orders. very useful for seeing what's available for note_attributes in function shopify_https_request
    msg = pprint.pformat(rd,width=200)
    print(msg)
    note = rd['note']
    print(note)
    return

    #note_dict = {"order":{"id":1980097560658,"note":"change to new note through python"}}

    note_dict = {"order":{"id":order_id,"note_attributes": [{"name":DELETE_BADGE+'_1',"value":"Blah Blah"},
                                                            {"name":NEW_BADGE+'_2',"value":"Mordechai Levine"},
                                                            {"name":DELETE_BADGE+'_3',"value":"joey jeff"},
                                                            ]}}
    #note_dict = {unicode('order'):{unicode('id'):1980097560658,unicode('note'):unicode('change to new note through python')}}
    #note_dict = {"id":1980097560658,"note":"change to new note through python"}

    note_update = json.dumps(note_dict)
    #note_update = unicode(note_update)
    r_headers = {'Content-Type': 'application/json'}
    r = requests.put(url=req, data=note_update, auth=(Credentials().SHOPIFY_API_KEY_RW,Credentials().SHOPIFY_PASSWORD_RW),headers = r_headers)

    return

#rester_note_attributes_update_1()

def rester_note_attributes_update_2():

    # 12/19/2022. this function used to change note_attributes from

    # [{NOTE_ATTRIBUTE_KEY(): 'Badge_Name_1', 'value': 'bob smith'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_2', 'value': 'john dow'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_3', 'value': 'Billy Bob'},
    # {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_4', 'value': 'Richard Nixon'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_5', 'value': 'Spiro Agnew'}]

    # to

    # [{NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'bob smith'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'john dow'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'Billy Bob'},
    # {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'Richard Nixon'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'Spiro Agnew'}]

    order_id = 2129787781202
    order_id = 6208463405138  # order 15568 for Celestron with NEAF Vendor Payment of $1450 with bad  'note_attributes': [{'name': '1 - NEAF Vendor Payment', 'value': ''}] changes to []

    reqstr = 'https://{0}.myshopify.com/admin/api/{1}/orders/{2}.json'
    req = reqstr.format(SHOP_NAME, ADMIN_API_VERSION, order_id)

    note_dict = {"order": {"id": order_id, "note_attributes": [{"name": "Badge_Name_9426_1", "value": "bob smith"}, {"name": "Badge_Name_9426_2", "value": "john dow"},
                                                               {"name": "Badge_Name_9426_3", "value": "Billy Bob"}, {"name": "Badge_Name_9426_4", "value": "Richard Nixon"},
                                                               {"name": "Badge_Name_9426_5", "value": "Spiro Agnew"}]
                           }}

    note_dict = {"order": {"id": order_id, "note_attributes": []
                           }}


    note_update = json.dumps(note_dict)
    r_headers = {'Content-Type': 'application/json'}
    r = requests.put(url=req, data=note_update, auth=(Credentials().SHOPIFY_API_KEY_RW, Credentials().SHOPIFY_PASSWORD_RW), headers=r_headers)

    return



