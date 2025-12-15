
import json
import pprint
from dateutil import parser
import datetime
# install with
# pip install requests
import requests
import tracemalloc

# 2/6/2022. inferior spell check methods.
# install with
# pip install pyspellchecker
#from spellchecker import SpellChecker
# install with
# pip install pyenchant
# use pip3 on mac
#import enchant # not interesting, it suggested replacing both Willmann and Wlllmann with Mailman

import sys
import os
import copy
from consts import REFUND,DECLINED,ADMIN_API_VERSION,SHOP_NAME
from credentials import Credentials
from graphql_queries import MUTATE_CUSTOM_ATTRIBUTES
from utils import NeafVendorPropertiesTup,normalizeAddress,NeafVendorTup,OrderDetailTup,OrderPropertiesTup,RAC_DIR,NOTE_ATTRIBUTE_KEY
from utils import NeafSSTup,get_default_neaf_year,getFromProperties,USE_GRAPHQL
from access_shopify import goodDateStr
from pdf_neaf_vendor_invoice import convert_text_to_pdf_neaf_invoice

# 1/26/2025. 2 critical functions for processing order_note_attributes are applyOrderNoteAttributeEdit and useOrderNoteAttributeEdits

# keys for note_attributes
DELETE_ORIGINAL_BADGE = 'Delete_Original_Badge_Name'
BADGE = 'Badge_Name'
DELETE_ORIGINAL_ORDER_NOTE = 'Delete_Original_Order_Note'
ORDER_NOTE = 'Order_Note'
COMPANY_NAME = 'Company_Name'
NAME =  'Name'
EMAIL = 'Email'
PRIZE_DONATION = 'Prize_Donation'
PRIZE_DONATION_VALUE = 'Prize_Donation_Value'
EXCLUDE = 'Exclude'
DONATION = 'Donation'
DECLINE_NEAF_2023 = 'Decline_NEAF_2023'
# 11/14/2022. this isn't a key into the note_attributes. It's a signal to delete a prior edit.
DELETE_PRIOR_EDIT = 'DELETE_PRIOR_EDIT'

# 12/19/2022. the 2nd item in each tuple is a signal for the chooseOrderForEditItem function. It maps to variable inside chooseOrderForEditItem of onlyNeedOrderNum.
# when requesting 'exclude order' or 'convert order to donation' only an order_num is needed because the entire order is either excluded or treated as donation.
# when requesting 'new company' you need both the new company name and the order_num it's applied to.
DESC_FOR_ACTION_NEEDING_1_ORDER = {COMPANY_NAME: ('new company',False), NAME: ('name',False), EXCLUDE: ('exclude order',True), DONATION: ('convert order to donation',True),
                                   DECLINE_NEAF_2023:('decline NEAF 2023',True),EMAIL:('email',False),PRIZE_DONATION:('prize donation',False),PRIZE_DONATION_VALUE:('prize donation',False),
                                   DELETE_ORIGINAL_ORDER_NOTE:('delete original order note',True)}
# 12/29/2022. these action cannot both be present in the same order_num
INCOMPATIBLE_ACTIONS = (EXCLUDE,DONATION)

# action choices that appear on gui
DELETE_ORIGINAL_BADGE_ACTION = 'delete original badge name by #'
BADGE_ACTION = 'add new badge name'
DELETE_ORIGINAL_ORDER_NOTE_ACTION = 'delete original order note'
ORDER_NOTE_ACTION = 'add new order note'
COMPANY_NAME_ACTION = 'change company name'
NAME_ACTION = 'change name of person associated with company'
EMAIL_ACTION = 'change email'
PRIZE_DONATION_ACTION = 'change prize donation'
PRIZE_DONATION_VALUE_ACTION = 'change prize donation value'
EXCLUDE_ACTION = 'exclude an order'
DONATION_ACTION = 'convert order to donation'
DECLINE_NEAF_2023_ACTION = 'ordered previously but declined NEAF 2023'
DELETE_PRIOR_EDIT_ACTION = 'delete a prior edit action'
VALID_EDIT_ACTIONS = (DELETE_ORIGINAL_BADGE_ACTION,BADGE_ACTION,DELETE_ORIGINAL_ORDER_NOTE_ACTION,ORDER_NOTE_ACTION,COMPANY_NAME_ACTION,NAME_ACTION,EMAIL_ACTION,
                      PRIZE_DONATION_ACTION,PRIZE_DONATION_VALUE_ACTION,EXCLUDE_ACTION,DONATION_ACTION,
                      DECLINE_NEAF_2023_ACTION,DELETE_PRIOR_EDIT_ACTION)
ACTIONS_MISSING_EDIT_ITEM = (DELETE_ORIGINAL_ORDER_NOTE_ACTION,DECLINE_NEAF_2023_ACTION)

# map from action on gui to key in note_attributes
EDIT_ACTION_TO_ACTION_MAP = {DELETE_ORIGINAL_BADGE_ACTION:DELETE_ORIGINAL_BADGE,BADGE_ACTION:BADGE,DELETE_ORIGINAL_ORDER_NOTE_ACTION:DELETE_ORIGINAL_ORDER_NOTE,
                             ORDER_NOTE_ACTION:ORDER_NOTE,COMPANY_NAME_ACTION:COMPANY_NAME,NAME_ACTION:NAME,EMAIL_ACTION:EMAIL,
                             PRIZE_DONATION_ACTION:PRIZE_DONATION,PRIZE_DONATION_VALUE_ACTION:PRIZE_DONATION_VALUE,
                             EXCLUDE_ACTION:EXCLUDE,DONATION_ACTION:DONATION,DECLINE_NEAF_2023_ACTION:DECLINE_NEAF_2023,DELETE_PRIOR_EDIT_ACTION:DELETE_PRIOR_EDIT}

DONATION_SKU = 'THIS ORDER HAS BEEN CONVERTED TO A DONATION'
EXCLUDE_SKU = 'THIS ORDER IS EXCLUDED AND WILL BE IGNORED'

def normalize_big_string(str):
    if not str:
        return ''
    str = str.replace('\r',' ')
    toks = str.split('\n')
    toks2 = []
    toks2 = [t for t in toks if t]
    str = ' '.join(toks2)
    return str

def appendToNames(names,name):
    if not name:
        return
    toks = name.split('|')
    names.extend(toks)
    return

def getExtraBadgeNamesList(extra_badge_names):
    ebn_list = []
    if extra_badge_names:
        toks = extra_badge_names.split('\r')
        toks = [tok.strip().replace('\n','') for tok in toks]
        for tok in toks:
            toks2 = tok.split(',')
            ebn_list.extend([tok2.strip() for tok2 in toks2 if tok2])
    return ebn_list

def buildCompanyBadgeList(full):
    company_badge = {}
    i = 1
    for company,nvt in full.items():
        if nvt.declined_neaf_2023:
            # 3/12/2023. example of declined is company of 'Meade Instruments' with order_num '9117'
            # 4/9/2022. the function removeBadgesFromRefundedOrders is an early place to remove invalid badge names but problem is they also disappear from invoice.
            continue
        for name in nvt.badge_names:
            company_badge[i] = (company,name)
            i += 1
    #for tup in  company_badge:
    #    print tup
    return company_badge

def confirm_no_unexpected_fields_in_properties(requested_properties,properties):
    bad_items = ''
    for prop in properties:
        name = prop[NOTE_ATTRIBUTE_KEY()]
        if not requested_properties.get(name):
            bad_items += "'{0}'".format(name)
    error = "Unexpected items of '{0}' found in properties.".format(bad_items) if bad_items else ''
    return error

def set_vendor_properties_tup(properties,order_num,name,email):

    requested_properties = {}
    company_from_property = getFromProperties('My Company Name',properties,requested_properties)
    if company_from_property:
        company_from_property = [company_from_property]
    else:
        company_from_property = []

    cellno = getFromProperties('Cell Phone',properties,requested_properties)
    name_on_badge = getFromProperties('Name on Badge',properties,requested_properties)
    badge1_name = getFromProperties('Name on 1st Badge',properties,requested_properties)
    badge2_name = getFromProperties('Name on 2nd Badge',properties,requested_properties)
    requested_booth_loc = getFromProperties('Req. Approximate Location',properties,requested_properties) or getFromProperties('Approx. Desired Location **',properties,requested_properties)
    prize1 = getFromProperties('Prize Donation 1',properties,requested_properties)
    prize1_value = getFromProperties('Prize 1 Retail Value',properties,requested_properties)
    prize2 = getFromProperties('Prize Donation 2',properties,requested_properties)
    prize2_value = getFromProperties('Prize 2 Retail Value',properties,requested_properties)
    extra_badge_names = getFromProperties('Extra Badge Names',properties,requested_properties)
    ive_reviewed_vendor_packet = getFromProperties("I've reviewed Vendor Packet*",properties,requested_properties)

    extra_badge_names = getExtraBadgeNamesList(extra_badge_names)
    error = confirm_no_unexpected_fields_in_properties(requested_properties,properties)

    nvpt = NeafVendorPropertiesTup(company_from_property,cellno,name_on_badge,badge1_name,badge2_name,requested_booth_loc,prize1,prize1_value,prize2,prize2_value,extra_badge_names,
                                   ive_reviewed_vendor_packet,error)

    return nvpt

def get_neaf_year(neaf_year):
    default_neaf_year = get_default_neaf_year()
    if neaf_year is None:
        neaf_year = default_neaf_year
        msg = 'Previously you were running with all NEAF years since 2015. Now you will run with default NEAF year of {0} only.'
        msg = msg.format(default_neaf_year)
    else:
        neaf_year = None
        msg = 'Previously you were running with default NEAF year of {0}. Now you will run with all NEAF years since 2015.'
        msg = msg.format(default_neaf_year)
    return neaf_year

def goodDatetimeStr(dstr):
    dt = parser.parse(dstr)
    return dt.strftime('%m/%d/%Y %H:%M:%S')

def convertToKey(identifier):
    if not identifier:
        return ''
    identifier = identifier.upper().strip()
    identifier = identifier.replace(' ','').replace(',','').replace('.','').replace('-','').replace('(','').replace(')','').replace('&','').replace("'",'').replace('/','')
    return identifier

def useNameFromAttribute(nvt):
    if not nvt.name_from_attribute:
        return nvt
    opList = []
    for opt in nvt.order_properties:
        opt = opt._replace(names=[nvt.name_from_attribute])
        opList.append(opt)
    nvt = nvt._replace(name=nvt.name_from_attribute,order_properties=opList)
    return nvt

def useOrderNoteAttributeEdits(nvt):

    # 1/26/2025. 2 critical functions for processing order_note_attributes are applyOrderNoteAttributeEdit and useOrderNoteAttributeEdits
    # 12/29/2022. use the edits that were previously persisted under the order note attributes in the NeafVendorTup.

    if not nvt.order_note_attributes:
        return nvt

    onaStr = pprint.pformat(nvt.order_note_attributes, width=100)
    print('\nEntering useOrderNoteAttributeEdits for order_num:{0}, company:{1}. Processing user requested edits of nvt.order_note_attributes of\n{2}\n'.format(nvt.order_num,nvt.company,onaStr))

    edit_cnt = 0
    for nvdict in nvt.order_note_attributes:
        name = nvdict[NOTE_ATTRIBUTE_KEY()]
        value = nvdict['value']
        if name.startswith(COMPANY_NAME):
            edit_cnt += 1
            # we have found a company name edit. apply it here.
            nvt = nvt._replace(company_from_attribute=value)
        elif name.startswith(NAME):
            edit_cnt += 1
            # we have found a name edit. temporarily apply it here. very shortly after set it with useNameFromAttribute(nvt)
            nvt = nvt._replace(name_from_attribute=value)
        elif name.startswith(EMAIL):
            edit_cnt += 1
            # we have found an email edit. apply it here.
            nvt = nvt._replace(email=value)
        elif name.startswith(PRIZE_DONATION) and not name.startswith(PRIZE_DONATION_VALUE):
            edit_cnt += 1
            # we have found a prize donation edit. apply it here.
            nvt = nvt._replace(prize_donation=value)
        elif name.startswith(PRIZE_DONATION_VALUE):
            edit_cnt += 1
            # we have found a prize donation value edit. apply it here.
            nvt = nvt._replace(prize_donation_value=value)
        elif name.startswith(DONATION):
            edit_cnt += 1
            # we have found a donation edit. apply it here.
            nvt = nvt._replace(donation_order_from_attribute=nvt.order_num)
        elif name.startswith(EXCLUDE):
            edit_cnt += 1
            # we have found an exclude edit. apply it here.
            nvt = nvt._replace(exclude_order_from_attribute=nvt.order_num)
        elif name.startswith(DECLINE_NEAF_2023):
            edit_cnt += 1
            # we have found an order that for company that paid for NEAF during covid but has declined to show up for NEAF 2023.
            nvt = nvt._replace(declined_neaf_2023=DECLINED)

    return nvt

def setAddress(nvt,sct):
    default_address = sct.default_address
    if not default_address:
        return nvt
    address1,address2,address3,city,province_code,zipc,country = normalizeAddress(default_address)
    nvt = nvt._replace(address1=address1,address2=address2,address3=address3)
    return nvt

def setName(nvt,properties):
    try:
        processNameFromBadge = nvt.name and nvt.company and (nvt.name.upper().startswith(nvt.company.upper()) or nvt.company.upper().startswith(nvt.name.upper()))
    except:
        msg = 'Failure in setName with nvt.name:{0}, nvt.company:{1}'.format(nvt.name,nvt.company)
        raise Exception(msg)
    if processNameFromBadge:
        dummy_requested_properties = {}
        name = getFromProperties('Name on 1st Badge',properties,dummy_requested_properties)
        nvt = nvt._replace(name=name)
    return nvt

def appendError(tup,error):
    orig_error = tup.error
    if not orig_error and error:
        tup = tup._replace(error=error)
    elif orig_error and error:
        tup = tup._replace(error=orig_error+' '+error)
    return tup

def appendMsg(origMsg,msg):
    if not origMsg and msg:
        origMsg = msg
    elif origMsg and msg:
        origMsg += ' ' + msg
    return origMsg

def get_price_in_shopifyCommonTup(sct):
    sku = sct.sku
    # standard products paid by credit card use this standard shopify price
    # 2/5/2024. added round because foreign customers payments converted to USD and there are decimals that should be ignored.
    price = round(float(sct.line_item['originalUnitPriceSet']['shopMoney']['amount'])) if USE_GRAPHQL[0] else round(float(sct.line_item['price']))
    return price

def setCost(nvt,sct):

    price = get_price_in_shopifyCommonTup(sct)
    qty = sct.quantity
    cost = price * qty

    # total due is typically, by definition, 0 because all orders paid in full by credit card.
    # its also 0 for EDUCATION discount code since they pay nothing. Its cost for discount code CHECK since they pay nothing online but owe
    # full amount by check
    total_discounts = 0.0 if nvt.discount_codes == 'CHECK' else nvt.total_discounts
    total_due = None # total_due is calculated after all the line items under a given order are processed in apply_discount function.
    if ',' in nvt.discount_codes:
        msg = "discount_codes of '{0}' are invalid. Only a single discount code is allowed.".format(nvt.discount_codes)
        nvt = appendError(nvt,msg)
    sku = sct.sku

    if nvt.exclude_order_from_attribute == nvt.order_num:
        # 12/29/2022. skip accumulating line items for excluded orders. an example is nvt.exclude_order_from_attribute and nvt.order_num of '9377' for Outdoor Sports Optics.
        price = 0.0
        qty = 0
        cost = 0.0
    elif nvt.donation_order_from_attribute == nvt.order_num and 'sponsor' not in sku:
        # 12/29/2022. example is nvt.order_num 9328 for Astro-Physics
        #             example where we do not enter this block even though nvt.donation_order_from_attribute == nvt.order_num are both '9132' is nvt.company of 'Celestron'
        #             where sku is 'neaf_vendor_sponsor_platinum'
        nvt = nvt._replace(donation=cost)
        # 12/29/2023. nvt ends up in raw but the only use of order_num_to_donation_map is in full for use in build_invoice so it serves no purpose to
        #             populate it here but do it for sake of completeness.
        nvt.order_num_to_donation_map[nvt.order_num] = cost
    elif sku.startswith('neaf_vendor_extra_shipping_box') or sku.startswith('neaf_vendor_extra_shipping_crate'):
        nvt = nvt._replace(shipping_box = cost, shipping_box_qty=qty)
    elif sku.startswith('neaf_vendor_extra_shipping_pallet'):
        nvt = nvt._replace(shipping_pallet = cost,shipping_pallet_qty=qty)
    elif sku.startswith('neaf_vendor_extra_electricity'):
        nvt = nvt._replace(elec = cost)
    elif sku.startswith('neaf_vendor_extra_wifi'):
        nvt = nvt._replace(wifi = cost)
    elif sku.startswith('neaf_vendor_additional_badge'):
        qty = qty + nvt.additional_badges_qty if nvt.additional_badges_qty else qty
        nvt = nvt._replace(additional_badges_qty = qty,additional_badges = cost)
    elif sku.startswith('neaf_vendor_booth_standard'):
        nvt = nvt._replace(booth_st = cost,booth_st_qty = qty)
    # elif sku.startswith('neaf_vendor_booth_economy'):
    #     nvt = nvt._replace(booth_econ = cost)
    #     nvt = nvt._replace(booth_econ_qty = qty)
    elif sku.startswith('neaf_vendor_booth_premium'):
        nvt = nvt._replace(booth_prem = cost,booth_prem_qty = qty)
    elif sku.startswith('neaf_vendor_extra_8ft_table'):
        nvt = nvt._replace(extra_tables = cost,extra_tables_qty = qty)
    elif sku.startswith('neaf_vendor_extra_chair'):
        nvt = nvt._replace(extra_chairs = cost,extra_chairs_qty = qty)
    elif sku.startswith('neaf_vendor_extra_carpet'):
        nvt = nvt._replace(carpet = cost)
    elif sku.startswith('neaf_vendor_sponsor'):
        nvt = nvt._replace(sponsorship = cost)

    elif sku.startswith(REFUND):
        # 2/2/2023. this is sku I convert real sku to if line item was in refunded order
        pass

    else:
        msg = 'Unsupported sku of {0} with cost:{1}, qty:{2}'
        nvt = appendError(nvt,msg.format(sku,cost,qty))
    try:
        nvt = nvt._replace(total_cost=cost,total_due=total_due,total_discounts=total_discounts)
    except:
        print('problem processing nvt:{0}'.format(nvt))
    return nvt

def _merged_sku_and_quantity(orig_nvt,new_nvt):
    orig_skus = orig_nvt.sku.split('|')
    _orig_skus = orig_skus[:]
    new_skus = new_nvt.sku.split('|')
    orig_quantities = [int(q) for q in str(orig_nvt.quantity).split('|')]
    new_quantities = [int(q) for q in str(new_nvt.quantity).split('|')]
    for i,new_sku in enumerate(new_skus):
        new_exists = False
        for j,orig_sku in enumerate(orig_skus):
            if orig_sku == new_sku:
                # new sku already exists in orig, increment the orig quantity by the new quantity
                new_exists = True
                orig_quantities[j] += new_quantities[i]
                break
        if not new_exists:
            # the new sku does not exist in the orig. add it orig sku and quantity
            _orig_skus.append(new_sku)
            orig_quantities.append(new_quantities[i])

    orig_nvt = orig_nvt._replace(quantity='|'.join([str(oq) for oq in orig_quantities]))
    orig_nvt = orig_nvt._replace(sku='|'.join([osk for osk in _orig_skus]))
    return orig_nvt

def sumNvtItems(keys,orig,new):
    orig_dict = orig._asdict()
    i = 0
    for key in keys:
        i += 1
        orig_item = orig_dict.get(key)
        new_item = new._asdict().get(key)
        if orig_item is not None and new_item is not None:
            try:
                orig_item += new_item
            except:
                print('For key:{0} (item:{1} out of {2} total keys) failed merging new_item:{3} into orig_item:{4}'.format(key,i,len(keys),new_item,orig_item))
        else:
            orig_item = orig_item or new_item
        orig_dict[key] = orig_item
    orig = NeafVendorTup(**orig_dict)
    return orig

def basicMerge(orig_item,new_item):
    if orig_item and new_item and (new_item not in orig_item and orig_item not in new_item) :
        orig_item += '|'+new_item
    else:
        orig_item = orig_item or new_item
    return orig_item

def mergeNvtItems(keys,orig,new):
    orig_dict = orig._asdict()
    for key in keys:
        orig_item = orig_dict.get(key)
        new_item = new._asdict().get(key)
        orig_item = basicMerge(orig_item,new_item)
        orig_dict[key] = orig_item
    orig = NeafVendorTup(**orig_dict)
    return orig

def mergeOrderDetails(orig_nvt,new_nvt):
    # merge OrderDetailTup items in the new_nvt.order_details dict into orig_nvt.order_details
    orig_nvt.order_details.extend([od for od in new_nvt.order_details])
    return orig_nvt

def mergeOrderProperties(orig_nvt,new_nvt):
    # merge OrderPropertiesTup items in the new_nvt.order_properties list into orig_nvt.order_properties
    for nop in new_nvt.order_properties:
        order_num_exists = False
        for oop in orig_nvt.order_properties:
            if oop.order_num == nop.order_num:
                order_num_exists = True
                break
        if not order_num_exists:
            orig_nvt.order_properties.append(nop)
    return orig_nvt

def mergeOrderNoteAttributes(orig_nvt,new_nvt):

    # 12/19/2022. critical function merges that order_note_attributes under an order in raw with order_note_attributes under a company in full.
    # must work well with applyOrderNoteAttributeEdit that edits order_note_attributes under a company stored in full yet persists those edits under an order.

    if not new_nvt.order_note_attributes:
        return orig_nvt
    if not orig_nvt.order_note_attributes:
        ona = copy.deepcopy(new_nvt.order_note_attributes)
        orig_nvt = orig_nvt._replace(order_note_attributes=ona)
        return orig_nvt

    for new_ona_dict in new_nvt.order_note_attributes:
        new_name = new_ona_dict[NOTE_ATTRIBUTE_KEY()]
        new_value = new_ona_dict['value']
        exists_in_orig = False
        for orig_ona_dict in orig_nvt.order_note_attributes:
            orig_name = orig_ona_dict[NOTE_ATTRIBUTE_KEY()]
            orig_value = orig_ona_dict['value']
            if orig_name == new_name and orig_value == new_value:
                exists_in_orig = True
        if not exists_in_orig:

            # we found new item in new_nvt.order_note_attributes that does not exist in orig_nvt.order_note_attributes. add it
            orig_nvt.order_note_attributes.append(new_ona_dict)

    return orig_nvt

def mergeUnusualItems(orig_nvt,new_nvt):
    # items that are merged here aren't simple numerical sums as in keys tuple in mergedNvts and they aren't string concatentations as in keys2 tuple.
    if new_nvt.first_order_date < orig_nvt.first_order_date:
        orig_nvt = orig_nvt._replace(first_order_date=new_nvt.first_order_date)
    if new_nvt.last_order_date > orig_nvt.last_order_date:
        orig_nvt = orig_nvt._replace(last_order_date=new_nvt.last_order_date)
    if new_nvt.order_note_attributes:
        orig_nvt = mergeOrderNoteAttributes(orig_nvt, new_nvt)
    if new_nvt.donation:
        cur_donation = orig_nvt.order_num_to_donation_map.get(new_nvt.order_num,0.0) + new_nvt.donation
        orig_nvt.order_num_to_donation_map[new_nvt.order_num] = cur_donation
    if new_nvt.declined_neaf_2023:
        orig_nvt = orig_nvt._replace(declined_neaf_2023=new_nvt.declined_neaf_2023)
    return orig_nvt

def mergedNvts(orig_nvt,new_nvt):

    # 12/19/2022. this function is heart of algorithm that builds full view of order under company. it's called under 2 very different circumstances.
    # first it sums line items under orders, then it sums orders under companies by building full from raw when called from build_neaf_vendor_full_dict_from_shopify.
    # this is critical function that build full from raw.

    if orig_nvt.order_num == '4391':
        #print 'xx'
        pass
    created_at = orig_nvt.created_at if orig_nvt.created_at<new_nvt.created_at else new_nvt.created_at
    orig_nvt = orig_nvt._replace(created_at=created_at)
    orig_nvt = _merged_sku_and_quantity(orig_nvt,new_nvt)
    # 12/29/2022. summing means numerically adding numbers.
    keys_to_be_summed = ('booth_st_qty','booth_st','booth_prem_qty','booth_prem','extra_tables_qty','extra_tables',
           'extra_chairs_qty','extra_chairs','elec','carpet','additional_badges_qty','additional_badges','wifi','shipping_box',
           'shipping_box_qty','shipping_pallet','shipping_pallet_qty','sponsorship','donation','total_cost')
    orig_nvt = sumNvtItems(keys_to_be_summed,orig_nvt,new_nvt)
    # 12/29/2022 merging means concatenate string with "|"
    keys_to_be_merged = ('order_id','order_num','name','orderNumber','address1','address2','address3','phone_num','cellno','email','order_note','refund_note','refund_created_at',
        'name_on_badge','badge1_name','badge2_name','extra_badge_names','prize_donation','prize_donation_value',
        'donation_order_from_attribute','exclude_order_from_attribute','error')
    # 12/29/2022. all remaining items that can't be summed or merged ae handled here.
    orig_nvt = mergeUnusualItems(orig_nvt,new_nvt)

    if orig_nvt.company != new_nvt.company:
        msg = "PROBLEM PROCESSING COMPANY: orig_nvt.company:'{0}', new_nvt.company:'{1}'. THEY SHOULD ALWAYS MATCH. FIX PROGRAM."
        raise Exception(msg.format(orig_nvt.company,new_nvt.company))

    for nc in new_nvt.company_from_property:
        if nc not in orig_nvt.company_from_property:
            orig_nvt.company_from_property.append(nc)

    orig_nvt = mergeNvtItems(keys_to_be_merged,orig_nvt,new_nvt)
    orig_nvt = mergeOrderDetails(orig_nvt,new_nvt)
    orig_nvt = mergeOrderProperties(orig_nvt,new_nvt)

    return orig_nvt

def mergedDiscounts(orig_nvt,new_nvt):
    # merging of discounts cannot take place in mergedNvts because that function is called twice, first for merging line items under orders, then
    # for merging orders under companies. we can only merge discounts during that 2nd merge of orders under companies
    keys = ('total_due','total_discounts','paid')
    keys2 = ('discount_codes',)
    orig_nvt = sumNvtItems(keys,orig_nvt,new_nvt)
    orig_nvt = mergeNvtItems(keys2,orig_nvt,new_nvt)
    return orig_nvt

def addItemToNvtDict(nvt_dict,key,new_nvt):
    # this function only called when merging line items, new_nvt, under single order.
    # add new_nvt to nvt_dict with key of order_num. if entry already exists in dict with that key of order_num accumulate line items in the order.
    orig_nvt = nvt_dict.get(key)
    if not orig_nvt:
        # first time line items under this given order_num are being processed
        nvt_dict[key] = new_nvt
        return
    # order already exists. sum line items under this order and update dict with key of order_num
    orig_nvt = mergedNvts(orig_nvt,new_nvt)
    nvt_dict[key] = orig_nvt
    return

def space_before_dollar_sign(val):
    if '$' not in val:
        return val
    dind = val.index('$')
    if val[dind-1:dind] == ' ':
        return val
    val = val[0:dind]+' '+val[dind:]
    return val

def setOrderDetails(nvt,sct):
    # add OrderDetailTup items to order details dict of nvt.order_details
    name = space_before_dollar_sign(sct.line_item['name'])
    name = name.replace('</p>',' ')
    unit_price = get_price_in_shopifyCommonTup(sct)
    odt = OrderDetailTup(sct.created_at, sct.order_num, sct.sku, name, sct.quantity, unit_price, nvt.order_note, nvt.order_note_attributes)
    order_details = [odt]
    nvt = nvt._replace(order_details=order_details)
    return nvt

def equivalent_identifiers(ident1,ident2):
    ident1_key = convertToKey(ident1)
    ident2_key = convertToKey(ident2)
    if ident1_key == ident2_key:
        return True
    if ident1_key in ident2_key or ident2_key in ident1_key:
        return True
    toks1 = ident1.split()
    toks2 = ident2.split()
    if len(toks1) == len(toks2):
        # for 'Telescope Support Systems' 'Jeff Thrush' equivalent to 'Jeffrey Thrush'
        i=-1
        for tok1 in toks1:
            i+=1
            tok2 = toks2[i]
            if tok1 not in tok2 and tok2 not in tok1:
                return False
        return True
    else:
        # for 'Willman-Bell' 'Patricia Remklaus' equivalent to 'Patricia B Remklaus'
        more_toks = toks1 if len(toks1)>len(toks2) else toks2
        less_toks = toks1 if len(toks1)<len(toks2) else toks2
        for less_tok in less_toks:
            if less_tok not in more_toks:
                return False
        return True

    return False

def setOrderProperties(nvt,sct):
    # add OrderPropertiesTup items to order details list of nvt.order_properties
    default_address_name = sct.default_address.get('name','')
    default_name_is_company = equivalent_identifiers(default_address_name,nvt.company)
    nvt_name_is_company = equivalent_identifiers(nvt.name,nvt.company)
    names = [nvt.name] if nvt.name and not nvt_name_is_company else []
    if default_address_name and not default_name_is_company and convertToKey(nvt.name) != convertToKey(default_address_name):
        names.append(default_address_name)
    opt = OrderPropertiesTup(nvt.order_num, names, nvt.address1, nvt.address2, nvt.address3, nvt.phone_num, nvt.email)
    order_properties = [opt]
    nvt = nvt._replace(order_properties=order_properties)
    return nvt

def build_shipping_description(nvt):
    if nvt.shipping_box_qty and not nvt.shipping_pallet_qty:
        desc = '# of boxes:{0}'.format(nvt.shipping_box_qty)
    elif not nvt.shipping_box_qty and nvt.shipping_pallet_qty:
        desc = '# of pallets:{0}'.format(nvt.shipping_pallet_qty)
    elif nvt.shipping_box_qty and nvt.shipping_pallet_qty:
        desc = '# of boxes:{0}, # of pallets:{1}'.format(nvt.shipping_box_qty,nvt.shipping_pallet_qty)
    else:
        desc  = ''
    return desc

def get_cost_key(order_details_sort_dict,unit_price):
    while True:
        if order_details_sort_dict.get(unit_price):
            unit_price += 0.01
        else:
            return unit_price

def convert_neafVendorTup_to_processed(full_item):
    processed_dict = {}
    full_dict = full_item._asdict()
    for key in NeafSSTup._fields:
        item = full_dict[key]
        if key == 'order_note' and item:
            item = displayLargeStringInCsv(item)
        processed_dict[key] = item
    nvprocessed_tup = NeafSSTup(**processed_dict)
    return nvprocessed_tup

def getBadgeEntitledCnt(nvt):
    badge_entitled_cnt = 0
    for order_detail in nvt.order_details:
        if 'neaf_vendor_booth_' in order_detail.sku:
            badge_entitled_cnt += 2*order_detail.quantity
        elif 'neaf_vendor_additional_badge' in  order_detail.sku:
            badge_entitled_cnt += order_detail.quantity
    return badge_entitled_cnt

def getNormalizedBadgeNames(badge_names):
    normalized_badge_names = {}
    for bn in badge_names:
        n_bn = convertToKey(bn)
        normalized_badge_names[n_bn] = bn.strip()
    return normalized_badge_names

def applyBadgeNameEdits(nvt):

    badge_names_orig = nvt.badge_names_orig
    badge_entitled_cnt = nvt.badge_entitled_cnt
    edit_add_cnt = 0
    edit_delete_cnt = 0

    if not nvt.order_note_attributes:
        return badge_names_orig,nvt.error,edit_add_cnt + edit_delete_cnt
    badge_names = []
    badge_names[:] = badge_names_orig[0:]
    error = ''

    normalized_badge_names = getNormalizedBadgeNames(badge_names)

    for nvdict in nvt.order_note_attributes:
        name = nvdict[NOTE_ATTRIBUTE_KEY()]
        value = nvdict['value']
        if name.startswith(DELETE_ORIGINAL_BADGE):
            key = convertToKey(value)
            if key in normalized_badge_names:
                edit_delete_cnt += 1
                del normalized_badge_names[key]

    for nvdict in nvt.order_note_attributes:
        name = nvdict[NOTE_ATTRIBUTE_KEY()]
        bn = nvdict['value']
        if name.startswith(BADGE):
            key = convertToKey(bn)
            bn_prior = normalized_badge_names.get(key)
            if bn_prior:
                error += "Trying to add badge name of '{0}' but badge name already exists. ".format(bn)
            else:
                # add the badge name of bn.
                normalized_badge_names[key] = bn
                edit_add_cnt += 1

    badge_names = list(normalized_badge_names.values())

    if len(badge_names) != badge_entitled_cnt:
        msg = "For company {0} after applying {1} add edits and {2} delete edits to badge names\nthe number of badge names is {3} but you are entitled to {4} badges."
        error += msg.format(nvt.company,edit_add_cnt,edit_delete_cnt,len(badge_names),badge_entitled_cnt)

    return badge_names,error,edit_add_cnt + edit_delete_cnt

def removeBadgesFromRefundedOrders(nvt):
    if nvt.sku == REFUND and not nvt.total_cost:
        # 4/8/2023. example is 'ASA America', order_num '11302'. this order was refunded in total so no badges in this order will be used.
        return True
    if nvt.exclude_order_from_attribute and not nvt.total_cost:
        # 4/8/2023. example is company of OSI, order_num 9405.
        return True
    return False

def getBadgeEntitledCntAndNames(nvt):
    badge_names = []

    if nvt.badge1_name:
        toks = nvt.badge1_name.split('|')
        badge_names.extend(toks)
    if nvt.badge2_name:
        toks = nvt.badge2_name.split('|')
        badge_names.extend(toks)
    if nvt.name_on_badge:
        toks = nvt.name_on_badge.split('|')
        for tok in toks:
            # 2/15/2025. added this loops for #15270, AstroWorld Telescopes. They ordered 5 of "Additional Badge beyond two included with Booth" but ui has no obvious place
            #            to set "Name on Badge" when doing that so they reasonably entered "Dave Schaeffer, Jennifer Higgins,Melissa Goldberg, Alyssa Dunn, Chris Boyle". The crazy part
            #            is that I never had this problem before.
            toks2 = tok.split(',')
            toks2 = [tok2.strip() for tok2 in toks2]
            badge_names.extend(toks2)
    if nvt.extra_badge_names:
        toks = nvt.extra_badge_names.split('|')
        badge_names.extend(toks)

    # remove dupes
    bname_dict = {}
    for bname in badge_names:
        toks = bname.upper().split()
        key = ' '.join(toks)
        bname_dict[key] = bname
    badge_names_orig = list(bname_dict.values())

    badge_entitled_cnt = getBadgeEntitledCnt(nvt)

    return badge_names_orig,badge_entitled_cnt

def normalizeOrderNoteAttributesSuffixes(order_note_attributes):
    # 12/19/2022. the trailing integer in the value of name in each order_note_attributes item can stop being in contiguous, ascending order within a company from 1 to N when an item is deleted.
    # there can be duplicate suffix integers as long as they are in different orders.
    # repair that here.

    # first find distinct orders

    orderSet = set()
    for ona_dict in order_note_attributes:
        name = ona_dict.get(NOTE_ATTRIBUTE_KEY())
        toks = name.split('_')
        orderSet.add(toks[-2])

    for order in orderSet:
        ind = 0
        for ona_dict in order_note_attributes:
            name = ona_dict.get(NOTE_ATTRIBUTE_KEY())
            toks = name.split('_')
            order2 = toks[-2]
            if order != order2:
                continue
            ind += 1
            name = '_'.join(toks[:-1]) + '_' + str(ind)
            ona_dict[NOTE_ATTRIBUTE_KEY()] = name

    return

def buildOrderIdToOrderNoteAttributesMap(order_id_to_order_num_map,order_note_attributes):

    def invertOrderIdToOrderNumMap(order_id_to_order_num_map):
        order_num_to_order_id_map = {}
        for order_id,order_num in order_id_to_order_num_map.items():
            order_num_to_order_id_map[order_num] = order_id
        return order_num_to_order_id_map

    order_num_to_order_id_map = invertOrderIdToOrderNumMap(order_id_to_order_num_map)
    order_id_to_order_note_attributes_map = {}
    for ona in order_note_attributes:
        toks = ona[NOTE_ATTRIBUTE_KEY()].split('_')
        order_num = toks[-2]
        order_id = order_num_to_order_id_map[order_num]
        ona_list = order_id_to_order_note_attributes_map.get(order_id,[])
        if not ona_list:
            order_id_to_order_note_attributes_map[order_id] = ona_list
        ona_list.append(ona)

    return order_id_to_order_note_attributes_map,order_num_to_order_id_map

def buildOrderNumToOrderNoteAttributesMap(order_nums,order_num_to_order_id_map,order_id_to_order_note_attributes_map):
    order_num_to_order_note_attributes_map = {}
    for order_num in order_nums:
        order_id = order_num_to_order_id_map[order_num]
        order_num_to_order_note_attributes_map[order_num] = order_id_to_order_note_attributes_map.get(order_id,[])
    return order_num_to_order_note_attributes_map
def updateOrderNoteAttributes(order_num,order_id_to_order_num_map,order_note_attributes):
    msg = ''
    normalizeOrderNoteAttributesSuffixes(order_note_attributes)
    order_id_to_order_note_attributes_map,order_num_to_order_id_map = buildOrderIdToOrderNoteAttributesMap(order_id_to_order_num_map,order_note_attributes)

    order_nums = [o_n.strip() for o_n in order_num.split('|')]

    for order_num in order_nums:
        order_id = order_num_to_order_id_map[order_num]

        ona = order_id_to_order_note_attributes_map.get(order_id,[])
        variables = {"input": {"id": order_id, "customAttributes": ona }}
        note_update = json.dumps({"query": MUTATE_CUSTOM_ATTRIBUTES,"variables": variables})
        r_headers = {'Content-Type': 'application/json'}
        req = f"https://{SHOP_NAME}.myshopify.com/admin/api/{ADMIN_API_VERSION}/graphql.json"

        r = requests.post(url=req, data=note_update, auth=(Credentials().SHOPIFY_API_KEY_RW,Credentials().SHOPIFY_PASSWORD_RW),headers = r_headers)
        if r.status_code != 200:
            msg = 'Failed updating customAttributes in shopify. Response status_code:{0} is invalid. Expecting 200.\nContact your programmer. This is a difficult internet failure.'.format(r.status_code)
            break
        else:
            print('\nSuccessfully updated customAttributes for order_num:{0} at\n{1}\nwith data\n{2}\n'.format(order_num,req,variables))

    order_num_to_order_note_attributes_map = buildOrderNumToOrderNoteAttributesMap(order_nums,order_num_to_order_id_map,order_id_to_order_note_attributes_map)

    return msg,order_num_to_order_note_attributes_map

def dash_string(n):
    return '-' * n

def normalized_phone_num(phone_num):
    if not phone_num:
        return phone_num
    phone_num = convertToKey(phone_num)
    return phone_num

def getNamesFromOrderProperty(nvt):
    names = []
    if nvt.name:
        names.append(nvt.name)
    for opt in nvt.order_properties:
        for opt_name in opt.names:
            opt_name_in_names = False
            for name in names:
                if equivalent_identifiers(name, opt_name):
                    opt_name_in_names = True
                    break
            if not opt_name_in_names:
                names.append(opt_name)
    return names

def get_distinct_order_properties(nvt):
    addresses = []
    phone_nums = []
    phone_nums_normalized = []
    phone_nums.append(nvt.cellno)
    phone_nums_normalized.append(normalized_phone_num(nvt.cellno))
    emails = []
    for opt in nvt.order_properties:
        address = (opt.address1,opt.address2,opt.address3)
        if address != (None,None,None) and address not in addresses:
            addresses.append(address)
        phone_normalized = normalized_phone_num(opt.phone_num)
        if phone_normalized and phone_normalized not in phone_nums_normalized:
            phone_nums.append(opt.phone_num)
            phone_nums_normalized.append(phone_normalized)
        if opt.email and opt.email not in emails:
            emails.append(opt.email)
    names = getNamesFromOrderProperty(nvt)
    return addresses,names,phone_nums,emails

def build_address_text(margin,addressTup,invoice):
    if addressTup[0]:
        invoice += '{0}{1}\n'.format(margin,addressTup[0])
    if addressTup[1]:
        invoice += '{0}{1}\n'.format(margin,addressTup[1])
    if addressTup[2]:
        invoice += '{0}{1}\n\n'.format(margin,addressTup[2])
    return invoice

def item_count_description(margin,i,item_name,invoice):
    line_end = '\n' if item_name == 'Address' else ''
    colon = ':' if item_name == 'Address' else ''
    if i==0 and item_name == 'Contact:':
        invoice += '{0}'.format(margin)
    elif i==0 and item_name != 'Address':
        invoice += '{0}{1}'.format(margin,item_name)
    elif i==1:
        invoice += '{0}2nd {1}{2}{3}'.format(margin,item_name,colon,line_end)
    elif i==2:
        invoice += '{0}3rd {1}{2}{3}'.format(margin,item_name,colon,line_end)
    elif i>2:
        invoice += '{0}{1}th {2}{3}{4}'.format(margin,i,item_name,colon,line_end)
    return invoice

def displayLargeStringInCsv(largeString,lineSize=100):
    if len(largeString) <= lineSize:
        return largeString
    toks = largeString.split()
    newLargeString = ''
    ls = ''
    for tok in toks:
        ls += (' ' + tok if ls else tok)
        if len(ls) >= lineSize:
            newLargeString += ('\r\n'+ls if newLargeString else ls)
            ls = ''
    if ls:
        newLargeString += '\r\n' + ls
    return newLargeString

def displayLargeStringWithMargin(margin,largeString,lineSize=117):
    # 5/9/2020. default size of 112 works for displaying order_notes in pdf invoice.
    # See Celestron invoice for example that gets chopped up into many lines.

    toks = largeString.split()
    buff = ' '.join(toks)

    buff_new = ''
    i = 0
    i_startLine = 0
    pos = 0
    lastBlank = None
    buffSize = len(buff)
    while True:
        if i == buffSize:
            break
        c = buff[i]
        if c == ' ':
            lastBlank = i
        if pos == lineSize - 1:
            # we have reached the end of a line
            lineEnd = '\n' if buff_new else ''
            buff_new += lineEnd + margin + buff[i_startLine:lastBlank]
            i = lastBlank + 1
            pos = 0
            i_startLine = i
        else:
            i += 1
            pos += 1

    lineEnd = '\n' if buff_new else ''
    if pos:
        buff_new += lineEnd + margin + buff[i_startLine:]

    return buff_new

def buildLastOrderDateVendorsMap(vendor_last_order_date_map):
    lo_map = {}
    for company,lod in vendor_last_order_date_map.items():
        companies = lo_map.get(lod,[])
        if not companies:
            lo_map[lod] = companies
        companies.append(company)

    last_order_date_vendors_map = {}
    keys = sorted(lo_map.keys())
    for key in keys:
        last_order_date_vendors_map[key] = lo_map[key]
    return last_order_date_vendors_map

def save_invoice(target_company,target_company_invoice,as_pdf,subdir=None):
    if not target_company:
        return 'No company yet selected. Select company and try to save to file again.',None,None
    target_company = target_company.strip().replace(' ','_')
    target_company = target_company.replace('__','_')
    tdir = RAC_DIR()
    now = datetime.datetime.now()
    now_str = now.strftime('%Y-%m-%d_%H-%M-%S')
    if subdir:
        fname = os.path.join(tdir,'neaf_output',subdir,'{0}_invoice_{1}.txt'.format(target_company,now_str))
    else:
        fname = os.path.join(tdir,'neaf_output','{0}_invoice_{1}.txt'.format(target_company,now_str))
    fname = fname.replace('|','_')
    fname = fname.replace('__','_')
    fname = fname.replace('/','_')
    fname = fname.replace('__','_')

    subdir_path = os.path.dirname(fname)
    if not os.path.exists(subdir_path):
        try:
            os.makedirs(subdir_path)
        except Exception as ex:
            msg = "Failure in save_invoice executing os.makedirs('{0}').\nException:\n{1}".format(subdir_path,ex)
            return msg,subdir_path,fname
    with open(fname,'w',encoding="utf-8") as text_file:
        try:
            text_file.write(target_company_invoice)
        except Exception as ex:
            msg = "Failure in save_invoice executing text_file.write(target_company_invoice) for fname:{0}.\nException:\n{1}".format(fname,ex)
            return msg,subdir_path,fname

    if as_pdf:
        # build path for blank neaf letterhead
        argv0 = sys.argv[0]
        delim = '/' if '/' in argv0 else '\\'
        toks = argv0.split(delim)
        rac_root = '/'.join(toks[:-2])
        blank_neaf_letterhead_path = rac_root + '/NEAF/docs/blank_neaf_letterhead.pdf'
        fname_pdf = convert_text_to_pdf_neaf_invoice(blank_neaf_letterhead_path,fname)
        # remove the text version.
        os.remove(fname)
        fname = fname_pdf

    msg = "Saved invoice for company '{0}' to file {1}".format(target_company,fname)
    return msg,subdir_path,fname

def get_vendor_sign_in_row(nvt):
    vrow = []
    vrow.append(nvt.company)
    vrow.append('') # Booth Location
    vrow.append('') # Arrival Time
    vrow.append('Y' if nvt.elec else '')
    vrow.append('Y' if nvt.wifi else '')
    badge_names = nvt.badge_names
    badge_entitled_cnt = nvt.badge_entitled_cnt
    vrow.append(badge_entitled_cnt)
    vrow.append(len(badge_names))
    vrow.append('') # Number of badges in envelope
    shipping_desc = build_shipping_description(nvt)
    vrow.append(shipping_desc)
    vrow.append('') # shipping in
    vrow.append('') # shipping out
    # TODO doorprize is very wrong. look at full s/s dump to see looks of doorprizes are missing.
    vrow.append(nvt.door_prize)
    return vrow

def invoice_subdir(dstr):
    subdir,error_msg = [None]*2
    dt,error_msg = goodDateStr(dstr)
    if error_msg:
        error_msg = error_msg+' No invoices will be saved.'
        return subdir,dt,error_msg
    else:
        subdir = 'invoices_since_{0}'.format(dt)
        subdir = subdir.replace('-','_')
        subdir = subdir.replace('__','_')
    return subdir,dt,error_msg

def badge_mis_count_report():
    #TODO create badge mis-count report that produces csv of only badge mis-count problems.
    return
