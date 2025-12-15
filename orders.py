import datetime
import os
import csv
import copy
import random
from collections import namedtuple
from consts import MEMBERSHIP,DONATION,RAD,NEAIC_ATTEND,NEAIC_EXHIBITOR,NEAF_ATTEND,NEAF_ATTEND_RAFFLE,NEAF_VENDOR,NEAF_SOLAR_STAR_PARTY,HSP,HSP_RAFFLE,RLS,MISSING,ADMIN,NEAF_ATTEND_DOOR_PRIZE
from consts import SSP,TEST,NEAF_VIRTUAL_DOORPRIZE,ALL,NUMBER_OF_DOORPRIZE_WINNERS,NEAF_VIRTUAL_DOORPRIZE_DROPDOWN,NEAF_RELATED_PRODUCT_TYPES,NEAF_YEAR_DEFAULT,USE_GRAPHQL
from utils import normalizeAddress,convertToStr,get_target_dict,writerow_UnicodeEncodeError,RAC_DIR,normalize_phone_num,get_max_len
from utils import getFromProperties,getPropertiesDict,OrderTup,PROPERTIES_DICT,ORDER_FIELDS_LIST,NOTE_ATTRIBUTE_KEY,PROPERTIES_KEY
from access_shopify import AccessShopify
from constant_contact import get_cc_door_prize_list

NEAIC_FIELDS = 'firstName lastName emailAddress phone state_country admissionCnt workShopCnt paidAmount note'
NEAIC_HEADER = ('First Name','Last Name','E-mail Address','Phone','Called','State/Country','WorkShop','Paid Amount($)','Date entered','Note')
NeaicTup = namedtuple('NeaicTup',NEAIC_FIELDS)
# heading for csv
ORDER_HEADING = ['Seq','Order#','Date','Name','Address','Addr2','City/State','Phone#','email','Product','Dsc Code','Quan','Pr','Tot','Paid','Note']
ORDER_NUM_AT_DATE_FIELDS = 'date order_num desc'
ORDER_NUM_AT_DATE_FIELDS_LIST = ORDER_NUM_AT_DATE_FIELDS.split()
orderNumAtDateTup = namedtuple('orderNumAtDateTup',ORDER_NUM_AT_DATE_FIELDS)
ORDER_NUM_AT_DATE_HEADING = ['Seq','Date','Order#','Description']

EMAIL_MANAGEMENT_HEADER = ['GLOBAL','NEAF ATTENDEES & DOOR PRIZE LIST','NEAF VENDORS','NEAIC ATTENDEES','MEMBERSHIPS','SSP','DINNER']
EMAIL_MANAGEMENT_FIELDS = 'glob neaf_attendees_and_door_prize neaf_vendors neaic_attendees memberships ssp dinner'
EMAIL_MANAGEMENT_FIELDS_LIST = EMAIL_MANAGEMENT_FIELDS.split()
EmailManagementTup =  namedtuple('EmailManagementTup',EMAIL_MANAGEMENT_FIELDS)

CC_DOOR_PRIZE = 'cc_door_prize'

def get_unique_key(dpt_dict,order_num):
    # 2/3/2019. there could be multiple products under a single order num. each will get it owns line in this program.  for example order #6612
    # for neaic_attend is 2 admissions and 1 workshop. give them order nums 6612-1 and 6612-2
    index = 1
    first_key = '{0}-{1}'.format(order_num,index)
    dpt = dpt_dict.get(order_num)
    dpt_first = dpt_dict.get(first_key)
    if not dpt and not dpt_first:
        # this is the first time this order_num has been found. no special treatment. use as is for key
        return order_num
    if dpt and not dpt_first:
        # a first dupe of order_num has been found. special treatment needed. need to rename the prior order_num like 6612 as 6612-1
        dpt = dpt._replace(order_num=first_key)
        dpt_dict[first_key] = dpt
        del dpt_dict[order_num]

    # dupes have been found. return new key
    index = 2
    while True:
        new_key = '{0}-{1}'.format(order_num,index)
        if not dpt_dict.get(new_key):
            return new_key
        index += 1
    raise Exception('Should never reach this point in get_unique_key. If so we have error processing order_num:{0}.'.format(order_num))
    return

class AccessOrders(AccessShopify):

    def __init__(self,sku_key,created_at_min,created_at_max=None,order_to_debug=None,verbose=False):
        super(AccessOrders, self).__init__('',created_at_min,created_at_max,order_to_debug,verbose)
        self.sku_key = sku_key
        return

    def getCompanyName(self,sct):
        companyName = ''
        properties = sct.line_item.get(PROPERTIES_KEY())
        if not properties:
            return companyName
        for item in properties:
            if item.get(NOTE_ATTRIBUTE_KEY(),'') == 'My Company Name':
                companyName = item.get('value','')
                return companyName
        return companyName

    def append_to_shopifyTup_dict(self,dpt_dict,sct):

        # 1/15/2023. append_to_shopifyTup_dict is implemented in each class that derives from AccessShopify and is responsible for much of the polymorphism of this class heirarchy.
        #            so far the classes AccessOrders, DoorPrize and NEAFVendor implement append_to_shopifyTup_dict.
        #            append_to_shopifyTup_dict sums all the line items in sct to orders under st_dict

        # sct is union of all interesting order items in shopify. each product is interested in a subset of these items.
        # TODO create different tups analogous to OrderTup to hold items specific for each product. most likely all products will at least hold the OrderTup items.
        key =  get_unique_key(dpt_dict,sct.order_num)
        properties = sct.line_item.get(PROPERTIES_KEY())
        requested_properties = {}
        phone_num_from_property = getFromProperties('Phone Number', properties, requested_properties)
        propertiesDict = getPropertiesDict(properties, ('Phone Number',))
        companyName = self.getCompanyName(sct)
        address1,address2,address3,city,province_code,zipc,country = normalizeAddress(sct.default_address)
        order_id = sct.order_id if sct.order_id else ''
        phone_num = phone_num_from_property or (sct.phone_num if sct.phone_num else '')
        phone_num = normalize_phone_num(phone_num)
        # 2/5/2024. added round to price to handle non-USD purchases. example isorder #13671 for NEAIC 2024 admission from Leigh Bryan in Australia. paid $541AUD that was converted to $355.68USD
        #           even though product was $365.Rounded to $356
        price = round(float(sct.line_item['originalUnitPriceSet']['shopMoney']['amount'])) if USE_GRAPHQL[0] else round(float(sct.line_item['price']))
        total = price * sct.quantity
        paid = None
        created_at = sct.created_at[0:10] + ' ' + sct.created_at[11:19]
        stateOrCountry = sct.province_code if sct.country_code == 'US' else sct.country_code
        note = sct.note.replace('\r',' ').replace('\n',' ')

        dpt = OrderTup(key,order_id,companyName,created_at,sct.name,sct.first_name,sct.last_name,address1,address2,address3,stateOrCountry,phone_num,sct.email,
                       sct.sku,sct.discount_codes,sct.quantity,sct.discount_allocations,price,total,paid,propertiesDict,note)
        dpt_dict[key] = dpt
        return

class Orders(object):

    # load back to January 1st of this many years prior to current year.
    MAX_YEARS_LOOKBACK = 0 # TODO was originally 1
    # store this number of history items.
    NUM_HIST_ITEMS = 5
    # TODO 9/4/2022. add to SKUS_TO_LOAD_DICT and PRODUCT_TYPES together. when adding a new product category add here and also in SKUS_TO_LOAD_DICT in consts.py
    PRODUCT_TYPES = (NEAF_ATTEND,NEAF_ATTEND_DOOR_PRIZE,NEAF_ATTEND_RAFFLE,NEAF_VENDOR,NEAF_SOLAR_STAR_PARTY,HSP,HSP_RAFFLE,RLS,SSP,TEST,MEMBERSHIP,DONATION,RAD,NEAIC_ATTEND,NEAIC_EXHIBITOR,
                     CC_DOOR_PRIZE,NEAF_VIRTUAL_DOORPRIZE_DROPDOWN,ADMIN,ALL)

    def set_product_type(self,product_type):

        self.product_type = ''
        if self.order_to_debug:
            if product_type:
                self.error = "Requested order_to_debug:'{0}' but also requested product_type:{1}. product_type must be None if using order_to_debug.".format(self.order_to_debug,product_type)
                return
            return

        if product_type not in Orders.PRODUCT_TYPES:
            self.error = 'Requested product_type:{0} is not valid. Must be one of {1}.'.format(product_type,Orders.PRODUCT_TYPES)

        if product_type == NEAF_VIRTUAL_DOORPRIZE_DROPDOWN:
            # 4/9/2021. this special treatment for product type dropdown choice of 'neaf_attend_virtual_door_prize and 20 raffle winners'.
            # we convert it to sku of neaf_attend_virtual_door_prize
            product_type = NEAF_VIRTUAL_DOORPRIZE

        self.product_type = product_type
        return

    def __init__(self,product_type,number_of_address_rows=1,order_to_debug=None,verbose=False):
        self.error = ''
        self.order_to_debug = order_to_debug
        self.set_product_type(product_type)
        self.logging = False
        self.verbose = verbose
        self.msg = ''
        self.order_dir = os.path.join(RAC_DIR(),'orders')
        self.results_dir = os.path.join(self.order_dir,'results')
        if self.order_to_debug:
            self.created_at_min = None
            self.created_at_max = None
        else:
            if self.product_type in NEAF_RELATED_PRODUCT_TYPES:
                self.created_at_min = str(int(NEAF_YEAR_DEFAULT) - 1) + '-07-01'
            else:
                start_date = datetime.datetime.now() - datetime.timedelta(days=370)
                self.created_at_min = start_date.strftime('%Y-%m-%d') # '{0}-01-01'.format(start_year)
            self.created_at_max = datetime.datetime.now().strftime('%Y-%m-%d')
        self.smallest_order_num = None
        self.largest_order_num = None
        self.run_time = datetime.datetime.now().strftime('%H:%M:%S')
        self.number_of_address_rows = int(number_of_address_rows)
        # these items are populated in shopifyLoad()
        self.full_order_dict = {}
        self.full_order_with_properties_dict = {}
        self.orderWithPropertiesList = []
        self.order_dict = {}
        self.order_keys = []
        self.refundNotes = []

        return

    def get_row(self,item_fields,item):
        irow = []
        idict = item._asdict()
        for field_name in item_fields:
            irow.append(idict[field_name])
        return irow

    def build_from_cc(self):
        msg_cc = 'Start loading Constant Contact door prize entrants from {0} to {1}'.format(self.created_at_min,self.created_at_max)
        print(msg_cc)
        ccdpt_list = get_cc_door_prize_list(self.created_at_min,self.created_at_max)
        date_to_cc_map = {}
        i = 1
        for ccdpt in ccdpt_list:
            order_num = None
            order_id = None
            created_at = ccdpt.modified_date
            created_at += '_{0:04d}'.format(i)
            i += 1
            name = ccdpt.first_name+' '+ccdpt.last_name
            address1 = address2 = address3 = stateOrCountry = ' '
            phone_num = ccdpt.home_phone
            email = ccdpt.email_address
            sku = 'Constant Contact door prize'
            quantity = 1
            company_name = ''
            price = 0
            discount = 0
            discount_code = ''
            total = 0
            paid = 0
            propertiesDict = {}
            note = ''
            cc_order = OrderTup(order_num,order_id,company_name,created_at,name,ccdpt.first_name,ccdpt.last_name,address1,address2,address3,stateOrCountry,phone_num,
                                email,sku,discount_code,quantity,discount,price,total,paid,propertiesDict,note)
            date_to_cc_map[created_at] = cc_order

        # build in date order
        full_order_dict_cc = {}
        dates = sorted(date_to_cc_map.keys())
        seq = 0
        for dt in dates:
            seq += 1
            order_num = "{:05d}".format(seq)
            cc_order = date_to_cc_map[dt]
            cc_order = cc_order._replace(order_num=order_num,created_at=cc_order.created_at[:10])
            full_order_dict_cc[order_num] = cc_order

        msg = '{0} items from Constant Contact Door Prize registrations at NEAF.'.format(len(full_order_dict_cc))
        print(msg)
        msg_cc += '\n'+msg
        return msg_cc,full_order_dict_cc

    def keysFromOrderNums(self, orderDictKeys):
        keys = []
        for odk in orderDictKeys:
            toks = odk.split('-')
            orderNum = toks[0]
            if len(orderNum) == 4:
                orderNum = ' '+orderNum
            if len(toks) == 2:
                orderNum += '-'+toks[1]
            keys.append(orderNum)
        keys = sorted(keys)
        keys2 = []
        for key in keys:
            if key.startswith(' '):
                key = key[1:]
            keys2.append(key)
        return keys2

    def build_full_order_with_properties_dict(self):

        # 2/26/2023. populate self.full_order_with_properties_dict

        BAD_KEY = 'confirm_RAC_&_$75_HSP'

        def getGoodKeyForNamedTuple(desc):
            return desc.replace('(', '').replace(')', '').replace(' ', '_').replace('\'','').replace('*','').replace('/','_')

        def fixKeysInPropertiesDict(goodPropertyKeys,properties):
            propertiesWithGoodKeys = {}
            for k,v in properties.items():
                propertiesWithGoodKeys[getGoodKeyForNamedTuple(k)] = v
            for goodKey in goodPropertyKeys:
                existingItem = propertiesWithGoodKeys.get(goodKey)
                if existingItem is None:
                    propertiesWithGoodKeys[goodKey] = None
            return propertiesWithGoodKeys

        goodPropertyKeys = set()
        for order_num,otup in self.full_order_dict.items():
            properties = otup.propertiesDict
            for desc in properties.keys():
                desc = getGoodKeyForNamedTuple(desc)
                if desc != BAD_KEY:
                    goodPropertyKeys.add(desc)
        goodPropertyKeys = list(goodPropertyKeys)
        orderFieldsList = list(ORDER_FIELDS_LIST[:-1])
        orderFieldsList.remove(PROPERTIES_DICT)

        self.orderWithPropertiesList = orderFieldsList + goodPropertyKeys + ORDER_FIELDS_LIST[-1:]
        try:
            OrderWithPropertiesTup = namedtuple('OrderWithPropertiesTup',self.orderWithPropertiesList)
        except Exception as ex:
            print('Exception:\n{0}\n'.format(ex))

        for order_num, otup in self.full_order_dict.items():
            propertiesWithGoodKeys = fixKeysInPropertiesDict(goodPropertyKeys,otup.propertiesDict)
            owptKwargs = otup._asdict()
            if BAD_KEY in owptKwargs:
                del owptKwargs[BAD_KEY]
            del owptKwargs[PROPERTIES_DICT]
            owptKwargs.update(propertiesWithGoodKeys)
            if BAD_KEY in owptKwargs:
                del owptKwargs[BAD_KEY]
            try:
                owpt = OrderWithPropertiesTup(**owptKwargs)
            except Exception as ex:
                print('Exception:\n{0}\n'.format(ex))
            self.full_order_with_properties_dict[order_num] = owpt

        return

    def build_order_collections(self):
        if self.error:
            self.error = 'Cannot run build_order_collections. Entered this function with error:{0}'.format(self.error)
            return

        self.full_order_dict.clear()
        if self.product_type == CC_DOOR_PRIZE:
            cc_msg,cc_full_order_dict = self.build_from_cc()
            self.msg = cc_msg
            self.full_order_dict.update(cc_full_order_dict)
        else:
            accessOrders = AccessOrders(self.product_type,self.created_at_min,self.created_at_max,order_to_debug=self.order_to_debug,verbose=self.verbose)
            if accessOrders.error:
                self.error = accessOrders.error
                return

            if USE_GRAPHQL[0]:
                accessOrders.shopifyOrdersFromGraphQL()
            else:
                accessOrders.shopifyOrdersFromHttps()
            if accessOrders.error:
                self.error = accessOrders.error
                return

            # 12/30/2022. this function populates self.raw from self.rawOrdersTupList which was built in shopifyOrdersFromHttps.
            #             it also calls  append_to_shopifyTup_dict is implemented in each class that derives from AccessShopify and is
            #             responsible for much of the polymorphism of this class heirarchy.
            self.smallest_order_num,self.largest_order_num = accessOrders.convertShopifyOrdersToRacOrders()
            if self.error:
                return

            self.full_order_dict.update(accessOrders.raw)
            self.msg = accessOrders.msg
            self.refundNotes = accessOrders.refundNotes

        # 2/26/2023. populate self.full_order_with_properties_dict
        self.build_full_order_with_properties_dict()

        self.order_dict = self.full_order_dict
        self.order_keys.clear()
        self.order_keys.extend(self.keysFromOrderNums(self.order_dict.keys()))
        return

    def create_dirs(self):
        if not os.path.exists(self.order_dir):
            print('Directory that holds order items of {0} does not exist. Creating it now.'.format(self.order_dir))
            os.makedirs(self.order_dir)
        if not os.path.exists(self.results_dir):
            print('Directory that holds results csv files of {0} does not exist. Creating it now.'.format(self.results_dir))
            os.makedirs(self.results_dir)
        return

    def shopifyLoad(self, created_at_min=None,created_at_max=None,order_to_debug=None ):
        if self.error:
            self.error = 'Cannot run shopifyLoad. Entered this function with error:{0}'.format(self.error)
            return

        self.create_dirs()

        # 3/13/2023. this block override default created_at_min and created_at_max set in Orders cstr
        if created_at_min:
            if self.order_to_debug and USE_GRAPHQL[0]:
                self.error = 'In shopifyLoad order_to_debug:{0} and created_at_min:{1}. created_at_min must be None if using order_to_debug.'.format(self.order_to_debug,created_at_min)
                return
            self.created_at_min = created_at_min
        if created_at_max:
            if self.order_to_debug and USE_GRAPHQL[0]:
                self.error = 'In shopifyLoad order_to_debug:{0} and created_at_max:{1}. created_at_max must be None if using order_to_debug.'.format(self.order_to_debug,created_at_max)
                return
            self.created_at_max = created_at_max

        self.build_order_collections()
        if self.error:
            self.error = 'In shopifyLoad generated this error in build_order_collections.\nERROR:\n{0}'.format(self.error)
        return

    def show_hints(self):
        hints = '''
    ---------------------------------------------------------------------------------------------------------------------

        Manage Shopify orders for many product categories

        Earliest date load time(created_at_min): {0}

        All product types: {1}
        Current loaded product type:{2}. Can find orders of this product type by text search or all orders greater than requested date.

        Folder holding all files used by this program: {3}
        Folder holding "dump to csv" results: {4}
        Number of orders for product type {2}:{5},  Number of raw shopify orders processed in last request:{6}

        Instructions for choosing NUMBER_OF_DOORPRIZE_WINNERS:{7} for 'NEAF: The Virtual Experience' raffle:
        1) Enter 'created_at_min' as the day prior to raffle entries opening.
        2) Choose product type of 'neaf-attend_virtual_door_prize and {7} raffle winners'
        3) Choose 'Dump to csv - 1 line per item' and get your winner as 2nd csv file

        {8}
        {9}
        {10}
    ---------------------------------------------------------------------------------------------------------------------
        '''

        shopifyCnt = len(self.order_dict)

        refundNotesStr = '\nREFUND NOTES\n{0}'.format(''.join(self.refundNotes)) if self.refundNotes else ''
        msgStr = '\nMESSAGE:\n{0}'.format(self.msg) if self.msg else ''
        errStr = '\nERROR:\n{0}'.format(self.error) if self.error else ''
        allProductTypes = ', '.join(Orders.PRODUCT_TYPES)
        numRawShopify = len(self.full_order_dict)

        return hints.format(self.created_at_min,allProductTypes,self.product_type,self.order_dir,self.results_dir,numRawShopify,shopifyCnt,NUMBER_OF_DOORPRIZE_WINNERS,
                            refundNotesStr,msgStr,errStr)

    def append_row(self,msgs,fmt,cnt,k,created_at,name,address,phone_num,email,sku,discount_code,quantity,price,total,paid,note):
        cnt = str(cnt)+'.' if cnt != '' else ''
        quantity = str(quantity) if quantity != '' else ''
        price = str(price) if price != '' else ''
        total = str(total) if total != '' else ''
        paid = str(paid)   if paid  != '' else ''
        try:
            _msg = fmt.format(cnt,k,created_at,name,address,phone_num,str(email),sku,discount_code,quantity,price,total,paid,note)
        except Exception as ex:
            _msg = ex
            print(_msg)
        _msg = _msg.rstrip()
        msgs.append(_msg)
        return

    def show_order_dict(self,order_dict):

        # save requested order_dict to be displayed here in self.order_dict in preparation to save to csv with dump_to_csv
        # 2/6/2025. show_order_dict and show_ShopifyCommonTup_list have a similar design concept. They both set column widths to minimum needed to display data.

        if not order_dict and not self.error:
            msg = 'Cannot show order_dict passed to self.show_order_dict(). order_dict is empty.'
            return msg
        if not order_dict and self.error :
            return self.error

        self.order_dict = order_dict
        self.order_keys.clear()
        self.order_keys.extend(self.keysFromOrderNums(self.order_dict.keys()))

        msgs = []
        cnt = 0
        cnt_max = 3
        key_max = 6
        created_at_max = 4
        name_max = 4
        address1_max = 7
        address2_max = 5
        address3_max = 5
        phone_num_max = 6
        email_max = 5
        sku_max = 7
        dc_max = 8
        quantity_max = 4
        price_max = 2
        total_max = 3
        paid_max = 4
        note_max = 4

        for k,v in order_dict.items():
            cnt += 1

            cnt_max = get_max_len(str(cnt)+'.',cnt_max)
            key_max = get_max_len(k,key_max)
            created_at_max = get_max_len(v.created_at,created_at_max)
            name_max = get_max_len(v.name,name_max)
            address1_max = get_max_len(v.address1,address1_max)
            address2_max = get_max_len(v.address2,address2_max)
            address3_max = get_max_len(v.address3,address3_max)
            phone_num_max = get_max_len(v.phone_num,phone_num_max)
            email_max = get_max_len(v.email,email_max)
            sku_max = get_max_len(v.sku,sku_max)
            dc_max = get_max_len(v.discount_code,dc_max)
            quantity_max = get_max_len(v.quantity,quantity_max)
            price_max = get_max_len(v.price,price_max)
            total_max = get_max_len(v.total,total_max)
            paid = round(v.paid)
            paid_max = get_max_len(paid,paid_max)
            note = v.note[:43] + '...' if len(v.note) > 42 else v.note
            note_max = get_max_len(note,note_max)

        if self.number_of_address_rows == 1:
            address1_max = max(address3_max,14)
        elif self.number_of_address_rows == 2:
            address1_max = max(address1_max,address3_max)
        else:
            address1_max = max(address1_max,address2_max,address3_max)

        fmt = '{{:{0}s}}  {{:{1}s}}    {{:{2}s}}  {{:{3}s}}  {{:{4}s}}  {{:{5}s}}  {{:{6}s}}  {{:{7}s}}  {{:{8}s}}  {{:{9}s}}  {{:{10}s}}  {{:{11}s}} {{:{12}s}} {{:{13}s}}'
        fmt = fmt.format(cnt_max,key_max,created_at_max,name_max,address1_max,phone_num_max,email_max,sku_max,dc_max,quantity_max,price_max,total_max,paid_max,note_max)

        h_fmt = fmt[:3]+'s} '+fmt[6:]
        # modify address items of 'Address','Addr2','City/State' and replace with 'Address' only
        order_heading = copy.deepcopy(ORDER_HEADING)
        del order_heading[5:7]
        order_heading[4] = 'City/State/Zip' if self.number_of_address_rows == 1 else order_heading[4]
        _msg = h_fmt.format(*order_heading)
        msgs.append(_msg)

        cnt = 0

        for k in reversed(self.order_keys):
            cnt += 1
            v = order_dict[k]

            # print 1, 2 or 3 address rows
            first_address_item = v.address3 if self.number_of_address_rows == 1 else v.address1
            note = v.note[:43] + '...' if len(v.note) > 42 else v.note
            paid = round(v.paid)
            self.append_row(msgs,fmt,cnt,k,v.created_at,v.name,first_address_item,v.phone_num,v.email,v.sku,v.discount_code,v.quantity,v.price,v.total,paid,note)
            if self.number_of_address_rows == 3 and v.address2:
                self.append_row(msgs,fmt,'','','','',v.address2,'','','','','','','')
            if self.number_of_address_rows in (2,3):
                self.append_row(msgs,fmt,'','','','',v.address3,'','','','','','','')

        if len(msgs)==1:
            msgs.append('--------------- NO ITEMS FOUND ---------------')
        msg = convertToStr(msgs)

        if self.error:
            msg = self.error + '\n\n' + msg

        return msg

    def set_number_of_address_rows(self,val):
        self.number_of_address_rows = int(val) if isinstance(val,str) else val
        return

    def show_dicts(self):
        if not self.full_order_dict:
            msg = 'Orders.full_order_dict is empty. Nothing to show.'
            return msg
        msg = self.show_order_dict(self.full_order_dict)
        return msg

    def csv_fname(self,prefix=''):
        timestr = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        if prefix:
            prefix += '_'
        if prefix == 'customized_':
            order_range_str = 'order_num_{0}_to_{1}'.format(self.smallest_order_num,self.largest_order_num )
            fname = os.path.join(self.results_dir,prefix+self.product_type+'_'+order_range_str+'.csv')
        else:
            fname = os.path.join(self.results_dir,prefix+self.product_type+'_'+timestr+'.csv')
        return fname

    def email_management_csv_fname(self):
        timestr = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        fname = os.path.join(self.results_dir,'email_management_'+timestr+'.csv')
        return fname

    def get_latest_neaic_order_number(self):
        prefix = 'customized_neaic_attend_order_num_'
        for (dirpath, dirnames, filenames) in os.walk(self.results_dir):
            break
        neaic_reports = [f for f in filenames if f.startswith(prefix)]
        neaic_last_order = sorted([f[f.index('_to_')+4:-5] for f in neaic_reports])[-1]
        file_with_neaic_last_order = [f for f in neaic_reports if neaic_last_order in f][0]
        return int(neaic_last_order),file_with_neaic_last_order

    def neaic_attendee_dump_to_csv(self, incremental_since_last_run = False):

        def buildItem(orig,latest):
            if not orig:
                return latest
            if not latest:
                return orig
            if orig == latest:
                return orig
            return orig + '/' + latest

        def normalizePhone(pn):
            # 1/16/2025. for reasons I don't understand some phone numbers printing weird on the custom NEAIC report.
            #            #15285 has +41794803637 but prints as 62
            #            #15104 has +20 3 3219800 but prints as -9918
            #            get rid of leading + I guess.
            if pn and pn[0] == '+':
                pn = '"' + pn + '"'
            return pn

        def buildPhone(ntup_phone,otup_phone_num,workshop):
            if ntup_phone and not otup_phone_num:
                return ntup_phone
            if not ntup_phone and otup_phone_num:
                return otup_phone_num
            if not not ntup_phone and not otup_phone_num:
                return ntup_phone
            if workshop:
                return ntup_phone

            return normalizePhone(otup_phone_num)

        def mergeNotes(o_note,n_note):
            if not o_note:
                return n_note
            if not n_note:
                return o_note
            if n_note == o_note:
                return o_note
            o_note += ' | ' + n_note
            return o_note

        def append_additional_attendees_to_note(otup):

            # 2/9/2025. this function appends the otup.propertiesDict member of 'Additional Attendees' to note to show . This will let 'Additional Attendees' appear on
            #           the customized_neaic_attend report. example is #15385, #15320

            new_note = ''
            additionalAttendees = otup.propertiesDict.get('Additional Attendees')
            if not additionalAttendees:
                return new_note
            additionalAttendees = 'Additional Attendees: ' + additionalAttendees.replace('\r',' ').replace('\n',' ')
            new_note = otup.note + ' | ' + additionalAttendees if otup.note else additionalAttendees
            return new_note

        if self.product_type != NEAIC_ATTEND:
            msg = "Cannot use 'NEAIC attendee report, Dump to csv' with product type '{0}'. Can only use with product type '{1}'.\n".format(self.product_type,NEAIC_ATTEND)
            return msg

        if incremental_since_last_run:
            neaic_last_order, file_with_neaic_last_order = self.get_latest_neaic_order_number()
            msg_incremental='In neaic_attendee_dump_to_csv order_num:{0} processed in prior run that built {1}.'.format(neaic_last_order,file_with_neaic_last_order)
            print(msg_incremental)
            msg_incremental += '\n'
        else:
            msg_incremental = ''

        ntupDict = {}
        for key in sorted(self.order_dict.keys(),reverse=True):
            otup = self.order_dict[key]
            order_num = int(otup.order_num.split('-')[0])
            if incremental_since_last_run and order_num <= neaic_last_order:
                continue
            new_note = append_additional_attendees_to_note(otup)
            if new_note:
                otup = otup._replace(note=new_note)
            self.smallest_order_num = order_num
            ntup = ntupDict.get(otup.name)
            workshop = 'workshop' in otup.sku
            quantity = otup.quantity

            if not ntup:
                admissionCnt = 0 if workshop else quantity
                workShopCnt = quantity if workshop else 0
                ntupDict[otup.name] = NeaicTup(otup.first_name,otup.last_name,otup.email,normalizePhone(otup.phone_num),otup.stateOrCountry,admissionCnt,workShopCnt,otup.total,otup.note)
            else:
                firstName = buildItem(ntup.firstName,otup.first_name)
                lastName = buildItem(ntup.lastName,otup.last_name)
                emailAddress = buildItem(ntup.emailAddress,otup.email)
                phone = buildPhone(ntup.phone,otup.phone_num,workshop)
                stateOrCountry = buildItem(ntup.state_country,otup.stateOrCountry)
                admissionCnt = ntup.admissionCnt + (0 if workshop else quantity)
                workShopCnt =  ntup.workShopCnt  + (quantity if workshop else 0)
                paidAmount =   ntup.paidAmount   + otup.total
                note = mergeNotes(otup.note,ntup.note)

                ntupDict[otup.name] = NeaicTup(firstName,lastName,emailAddress,phone,stateOrCountry,admissionCnt,workShopCnt,paidAmount,note)

        fname = self.csv_fname(prefix='customized')

        with open(fname,'w') as csv_file:
            wr = csv.writer(csv_file,  quoting=csv.QUOTE_ALL, lineterminator='\n') # delimiter=' ',quotechar='|', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            wr.writerow(NEAIC_HEADER)
            for ntup in ntupDict.values():

                if ntup.admissionCnt == 1:
                    wsFront = 'Registration - NEAIC Admission'
                elif ntup.admissionCnt > 1:
                    wsFront = '{0} Registrations - NEAIC Admissions'.format(ntup.admissionCnt)
                else:
                    wsFront = '*** NOT REGISTERED *** '

                wsBack = '' if ntup.workShopCnt == 0 else ' +{0}WS'.format(ntup.workShopCnt)
                workshopStr = '{0}{1}'.format(wsFront,wsBack)
                paidAmountStr = '${:.2f}'.format(ntup.paidAmount)

                ntrow = [ntup.firstName,ntup.lastName,ntup.emailAddress,ntup.phone,' ',ntup.state_country,workshopStr,paidAmountStr,'',ntup.note]
                writerow_UnicodeEncodeError(wr,ntrow)

        msg = 'Find results for {0} NEAIC attendees at {1} .\n{2}'.format(len(ntupDict),fname,msg_incremental)

        return msg

    def dump_to_csv(self):

        # 2/26/2022. previously in build_full_order_with_properties_dict we built self.full_order_with_properties_dict for save to csv here.

        if not self.full_order_with_properties_dict:
            msg = "Failure dumping csv file in self.dump_to_csv(). self.full_order_with_properties_dict was not yet populated inside self.shopifyLoad(). Do 'SHOPIFY LOAD (must do this first)'."
            return msg

        fname = self.csv_fname()
        with open(fname,'w') as csv_file:
            wr = csv.writer(csv_file,  quoting=csv.QUOTE_ALL, lineterminator='\n') # delimiter=' ',quotechar='|', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            wr.writerow(self.orderWithPropertiesList)
            for key in reversed(self.order_keys):
                member  = self.full_order_with_properties_dict[key]
                mrow = self.get_row(self.orderWithPropertiesList,member)
                writerow_UnicodeEncodeError(wr,mrow)

        msg = 'Find results for {0} orders at {1} .'.format(len(self.order_dict),fname)
        return msg

    def dump_to_csv_door_prize_winners(self,mrows):

        def build_csv_file(fname,mrows_winners):

            with open(fname,'w') as csv_file:
                wr = csv.writer(csv_file,  quoting=csv.QUOTE_ALL, lineterminator='\n')
                wr.writerow(ORDER_FIELDS_LIST)
                for mrow in mrows_winners:
                    writerow_UnicodeEncodeError(wr,mrow)

            return

        fname = self.csv_fname(prefix='winners')
        mrows_winners = []
        duplicate_email_cnt = 0
        numHigh = len(mrows) - 1
        winning_emails = {}
        i = 0
        while len(mrows_winners) < NUMBER_OF_DOORPRIZE_WINNERS:
            i += 1
            ind = random.randint(0, numHigh)
            mrow = mrows[ind]
            email = mrow[8]
            if not winning_emails.get(email):
                winning_emails[email] = True
                mrows_winners.append(mrow)
            else:
                duplicate_email_cnt += 1
            if duplicate_email_cnt > 10 * len(mrows):
                # we have an insufficient number of entries to give away NUMBER_OF_DOORPRIZE_WINNERS prizes. we have 10 times as many dupes as entrants.
                # clearly we aren't going to be able to give away any more prizes.
                break

        build_csv_file(fname,mrows_winners)
        door_prize_winners_msg = 'Also find {0} results for door prize winner chosen from {1} door prize entries at {2} .'.format(len(mrows_winners),numHigh+1,fname)

        return door_prize_winners_msg

    def dump_to_csv_1_line_per_item(self):

        # previously we saved order_dict displayed in show_order_dict in self.order_dict for saving to csv here.
        # however dump here is different then dump in dump_to_csv. create 1 line per item. uses are:
        # 1) building list for selecting winners on neaf virtual door prize
        # 2) selecting winners for HSP raffle where you have product variants where you can buy more than 1 ticket.
        # 3) selecting winners for NEAF raffle where you have product variants where you can buy more than 1 ticket.

        skuSubstringForLineMultiplier = '_raffle_'
        skuMultipliersFound = {}

        fname = self.csv_fname()
        rowCnt = 0
        mrows = []
        with open(fname,'w') as csv_file:
            wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL, lineterminator='\n')
            wr.writerow(ORDER_FIELDS_LIST)
            indQuantity = ORDER_FIELDS_LIST.index('quantity')
            indPrice = ORDER_FIELDS_LIST.index('price')
            indTotal = ORDER_FIELDS_LIST.index('total')
            for key in reversed(self.order_keys):
                member  = self.order_dict[key]
                sku = member.sku
                if skuSubstringForLineMultiplier in sku:
                    skuBack = sku[sku.index(skuSubstringForLineMultiplier) + len(skuSubstringForLineMultiplier):]
                    if not skuBack.isdigit():
                        msg = 'In dump_to_csv_1_line_per_item failure processing sku:{0}. sku contains skuSubstringForLineMultiplier of {1} but skuBack:{2} is not an integer.'
                        raise Exception(msg.format(sku,skuSubstringForLineMultiplier,skuBack))
                    skuMultiplier = int(skuBack)
                    if skuMultiplier > 1:
                        skuMultipliersFound[sku] = skuMultipliersFound.get(sku,0) + skuMultiplier
                else:
                    skuMultiplier = 1

                mrow = self.get_row(ORDER_FIELDS_LIST,member)
                quantity = mrow[indQuantity]
                price = mrow[indPrice]
                mrow[indTotal] = price
                mrow[indQuantity] = 1
                for i in range(0,quantity):
                    for i in range(0,skuMultiplier):
                        rowCnt += 1
                        writerow_UnicodeEncodeError(wr,mrow)
                        mrows.append(mrow)

        if self.product_type == NEAF_VIRTUAL_DOORPRIZE:
            door_prize_winners_msg = self.dump_to_csv_door_prize_winners(mrows)
        else:
            door_prize_winners_msg = ''

        msg = 'Find results for {0} orders spread out into {1} rows at {2} .'.format(len(self.order_dict),rowCnt,fname)
        if door_prize_winners_msg:
            msg += '\n' + door_prize_winners_msg
        else:
            winner_ind = random.randint(0,rowCnt-1)
            winner = mrows[winner_ind]
            msg1 = '\nThe randomly selected row is item {0} in csv, order_num:{1}, name:{2}, email:{3}. created_at:{4}, sku:{5}'
            msg1 = msg1.format(winner_ind+1,winner[0],winner[4],winner[9],winner[3],winner[13])
            msg += msg1

        if skuMultipliersFound:
            msg1 = '\n\n' + '*****************************************\n' + \
                   'The following skus had their rows multiplied by these amounts: {0}\n' + \
                    '*******************************************'
            msg1 = msg1.format(skuMultipliersFound)
            msg += msg1

        return msg

    def emDict_item(self,eMDict_asdict,key,i):
        em_list = eMDict_asdict[key]
        if i >= len(em_list):
            return ''
        return em_list[i]

    def dump_to_email_management_csv(self):
        # glob neaf_attendees_and_door_prize neaf_vendors neaic_attendees memberships ssp dinner
        eMDict = EmailManagementTup({},{},{},{},{},{},{})
        i = 0
        for k,v in self.full_order_dict.items():
            i += 1
            email = v.email
            if not email:
                continue
            email = email.strip().lower()
            sku = v.sku
            if not eMDict.glob.get(email):
                eMDict.glob[email] = True
            if sku.startswith('Constant Contact') or sku.startswith('neaf_attend'):
                if not eMDict.neaf_attendees_and_door_prize.get(email):
                    eMDict.neaf_attendees_and_door_prize[email] = True
            elif sku.startswith('neaf_vendor'):
                if not eMDict.neaf_vendors.get(email):
                    eMDict.neaf_vendors[email] = True
            elif sku.startswith('neaic_attend'):
                if not eMDict.neaic_attendees.get(email):
                    eMDict.neaic_attendees[email] = True
            elif sku.startswith('rac_'):
                if not eMDict.memberships.get(email):
                    eMDict.memberships[email] = True
            elif sku.startswith('ssp_'):
                if not eMDict.ssp.get(email):
                    eMDict.ssp[email] = True
            elif sku.startswith('rad_'):
                if not eMDict.dinner.get(email):
                    eMDict.dinner[email] = True

        msg = 'Processed {0} orders. glob#:{1}  neaf_attendees_and_door_prize#:{2}  neaf_vendors#:{3}  neaic_attendees#:{4}  memberships#:{5}  ssp#:{6}  dinner:{7}'
        msg = msg.format(i,len(eMDict.glob),len(eMDict.neaf_attendees_and_door_prize),len(eMDict.neaf_vendors),len(eMDict.neaic_attendees),len(eMDict.memberships),
                         len(eMDict.ssp),len(eMDict.dinner))
        print(msg)

        # remove_unicode results in eMDict to list of EmailManagementTup namedtuples

        emListCsv = []
        eMLists = EmailManagementTup(list(eMDict.glob.keys()),list(eMDict.neaf_attendees_and_door_prize.keys()),list(eMDict.neaf_vendors.keys()),list(eMDict.neaic_attendees.keys()),list(eMDict.memberships.keys()),
                                     list(eMDict.ssp.keys()),list(eMDict.dinner.keys()))
        eMLists_asdict = eMLists._asdict()
        # glob neaf_attendees_and_door_prize neaf_vendors neaic_attendees memberships ssp dinner
        for i in range(0,len(eMDict.glob)):
            glob = self.emDict_item(eMLists_asdict,'glob',i)
            neaf_attendees_and_door_prize = self.emDict_item(eMLists_asdict,'neaf_attendees_and_door_prize',i)
            neaf_vendors = self.emDict_item(eMLists_asdict,'neaf_vendors',i)
            neaic_attendees = self.emDict_item(eMLists_asdict,'neaic_attendees',i)
            memberships = self.emDict_item(eMLists_asdict,'memberships',i)
            ssp = self.emDict_item(eMLists_asdict,'ssp',i)
            dinner = self.emDict_item(eMLists_asdict,'dinner',i)
            emItem = EmailManagementTup(glob,neaf_attendees_and_door_prize,neaf_vendors,neaic_attendees,memberships,ssp,dinner)
            emListCsv.append(emItem)

        fname = self.email_management_csv_fname()
        with open(fname,'w') as csv_file:
            wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL,lineterminator='\n')
            wr.writerow(EMAIL_MANAGEMENT_HEADER)
            for emItem in emListCsv:
                mrow = self.get_row(EMAIL_MANAGEMENT_FIELDS_LIST,emItem)
                writerow_UnicodeEncodeError(wr,mrow)


        _msg = 'Find results for {0} line Email Management csv at at {1} .'.format(len(eMDict.glob),fname)
        print(_msg)
        msg += '\n'+_msg

        return msg

    def orders_by_search(self,search_for):
        target_dict,msg2 = get_target_dict(search_for,None,None,source_dict=self.full_order_dict)
        if not target_dict and msg2:
            return msg2
        msg = self.show_order_dict(target_dict)
        msg += '\n' + msg2 + '\n'
        return msg

def process_option(optionstr):
    search_for = None
    if optionstr.startswith(('3*',)) or optionstr.startswith(('11*',)) or optionstr.startswith(('12*',)):
        toks = optionstr.split('*')
        optionstr = toks[0]
        search_for = toks[1]
        if not search_for:
            optionstr = '-1'
        return int(optionstr),search_for
    if not optionstr.isdigit():
        return -1,search_for
    option = int(optionstr)
    if option<0 or option>13:
        return -1,search_for
    return option,search_for


def main():
    m = None
    product_type = None
    while True:
        print('\n\n5:dump to csv   6:show_dicts   7:debug on   8:debug off   9:hints   11*<...>:number of address rows   12*<product type>   13:email management csv')
        msg = '0:stop   3*<...>:orders by search   10:SHOPIFY LOAD (must do this first)  \n\nEnter Here ----->'
        optionstr = input(msg.format(m.created_at_min))
        option,search_for = process_option(optionstr)
        if option == -1:
            print('Choice not valid. Try again.')
            continue
        if not option:
            break

        if option == 12:
            m.set_product_type(search_for)
            continue
        elif option == 10:
            m = Orders(product_type)
            m.shopifyLoad()
            continue

        elif option == 3:
            msg = m.orders_by_search(search_for)
            print(msg)
            continue
        elif option == 5:
            print(m.dump_to_csv())
            continue
        elif option == 6:
            print(m.show_dicts())
            continue
        elif option == 7:
            m.logging = True
            continue
        elif option == 8:
            m.logging = False
            continue
        elif option == 9:
            print((m.show_hints()))
            continue
        elif option == 11:
            m.set_number_of_address_rows(search_for)
            continue
        elif option == 13:
            print(m.dump_to_email_management_csv())
            continue
        else:
            print('option:{0} invalid. Pick one from choices'.format(option))
            continue

    return

# comment out call to main before copying to RAC_share
#main()