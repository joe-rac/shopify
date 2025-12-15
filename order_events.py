
import requests
import json
import pprint
import time
from consts import SHOP_NAME,MISSING,ADMIN_API_VERSION
from credentials import Credentials
from utils import remove_unicode

def get_order_event_timeline(order_id):
    reqstr = 'https://{0}.myshopify.com/admin/api/{1}/orders/{2}.json'
    # 1/27/2024. how to get event timeline
    reqstr = 'https://{0}.myshopify.com/admin/api/{1}/orders/{2}/events.json'
    req = reqstr.format(SHOP_NAME, ADMIN_API_VERSION, order_id)
    response = requests.get(req, auth=(Credentials().SHOPIFY_API_KEY_RW, Credentials().SHOPIFY_PASSWORD_RW))
    # print((response.status_code))
    # print response.text
    rd = json.loads(response.text)  # ['events']
    rd = remove_unicode(rd)
    return rd

def get_phone_or_email_from_order_event_timeline(order_id):
    email = MISSING
    phone_num = MISSING
    #time.sleep(1)
    rd = get_order_event_timeline(order_id)
    events = rd.get('events')
    if not events:
        return email, phone_num
    for event in events:
        args = event.get('arguments')
        if len(args) == 4:
            if args[0] == 'Order Receipt':
                email = args[1]
            elif args[0] == 'POS and Mobile Receipt':
                phone_num = args[1]
    return email,phone_num

def tutorial_phone_or_email():
    order_id = 5059982131282
    email,phone_num = get_phone_or_email_from_order_event_timeline(order_id)
    print('email:{0}, phone_num:{1}.'.format(email,phone_num))
    return

def tutorial():
    order_id = 5060039639122  # order 13167 for Donald A Kaplan buying membership at club table for NEAF 2023 using POS.
                              # {'arguments': ['POS and Mobile Receipt', '+19176964343', 'api_client_id', 129785], ...
    order_id = 5059982131282  # order 13136 for John F May
                              # {'arguments': ['Order Receipt', 'johnmay31@hotmail.com', 'api_client_id', 129785],
    order_id = 5059969646674  # order 13160 for Linda Gutterman
                              # no email or sms information
    #order_id = 5059965157458  # order 13159 for Lance Gilden
                              # {'arguments': ['POS and Mobile Receipt', '+15162078960', 'api_client_id', 129785], ...
    rd = get_order_event_timeline(order_id)
    msg = pprint.pformat(rd, width=200)
    print(msg)
    return

#tutorial_phone_or_email()
#tutorial()