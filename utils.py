"""
Created on Sat Mar 07 17:58:17 2015

@author: joe1
"""
# utilities used by door_prize and search_and_confirm modules

import os
import re
import unicodedata
import csv
# 1/9/2025. install with
#           pip install pytz
import pytz
import datetime
import inspect
# install with
# pip install python-dateutil
# use pip3 on mac
from dateutil import parser
from datetime import date
from collections import namedtuple

import consts
from consts import ERROR,MISSING,N_A,CURRENCY_SYMBOL_FROM_CODE
eastern_zone = pytz.timezone("US/Eastern")
utc_format = "%Y-%m-%dT%H:%M:%SZ"

def NOTE_ATTRIBUTE_KEY():
    return 'key'

def CUSTOM_ATTRIBUTES_KEY():
    return 'customAttributes'

DOOR_PRIZE_HEADER = ['order-number','order_id','order-created_at','order-billing_address-name','order-billing_address-phone', 'order-email','order-line_items-sku',
                     'order-line_items-quantity','CONFIRM_NOTE']
# CONFIRM_NOTE is used for search_and_confirm. if someone is searched for and then confirmed CONFIRM_NOTE will say
# Confirmed:2015-03-07T14:23:14
XPORTER_FIELDS = 'order_num order_id created_at name phone_num email sku quantity CONFIRM_NOTE'
DoorPrizeTup = namedtuple('DoorPrizeTup', XPORTER_FIELDS)
# any changes to NEAF_VENDOR_FIELDS need change to append_to_neafVendorRawTup_dict func in access_shopify.py .
# error is something like contradictory company name in default_address and properties.
ORDER_DETAIL_FIELDS = 'created_at order_num sku name quantity unit_price unit_price_presentment currencyCode order_note order_note_attributes'
OrderDetailTup = namedtuple('OrderDetailTup', ORDER_DETAIL_FIELDS)
ORDER_PROPERTIES_FIELDS = 'order_num names address1 address2 address3 phone_num email'
OrderPropertiesTup = namedtuple('OrderPropertiesTup', ORDER_PROPERTIES_FIELDS)

# XXX when changing NeafVendorTup make sure adjustments made to keys_to_be_summed and keys_to_be_merged in mergedNvts in neaf_vendor_utils.py .

# XXX 3/25/2023. Keep NEAF_VENDOR_FIELDS usage here in sync with usage in NeafVendorTup in neaf_vendor.py near line 118.
#                NEAF s/s fields runs from company to error

# 12/27/2022. Bizarrely order_num is in there twice, 2nd time its orderNumber. that's the simplest way of getting it into the s/s in the current framework where s/s fields run
#             from company to error in NeafVendorTup schema.
NEAF_VENDOR_FIELDS = 'order_num created_at sku quantity CONFIRM_NOTE '\
    'company_from_property company_from_attribute name_from_attribute '\
    'company last_order_date orderNumber name address1 address2 address3 phone_num cellno '\
    'email booth_st_qty booth_st booth_prem_qty booth_prem upgrade_st_to_prem_qty upgrade_st_to_prem total_adj_booth_qty get_booths_from '\
    'extra_tables_qty extra_tables extra_chairs_qty extra_chairs elec carpet additional_badges_qty additional_badges wifi shipping_box '\
    'shipping_pallet sponsorship donation donation_order_from_attribute exclude_order_from_attribute declined_neaf_2023 prize_donation prize_donation_value '\
    'currencyCode total_cost  paid total_due check_number total_discounts  discount_codes booth_comments sales_comments order_note error '\
    'total_cost_presentment paid_presentment total_due_presentment total_discounts_presentment '\
    'shipping_box_qty shipping_pallet_qty order_num_to_donation_map order_note_attributes order_id refund_note refund_created_at '\
    'name_on_badge badge1_name badge2_name extra_badge_names badge_names_orig badge_entitled_cnt badge_names '\
    'first_order_date debug order_details order_properties'
NeafVendorTup = namedtuple('NeafVendorTup', NEAF_VENDOR_FIELDS)

# 11/10/2018. new collection similar to NeafVendorTup and DoorPrizeTup need for orders app
PROPERTIES_DICT = 'propertiesDict'
ORDER_FIELDS = 'order_num order_id company_name created_at name first_name last_name address1 address2 address3 stateOrCountry phone_num email sku discount_code quantity ' +\
               'discount price total paid ' + PROPERTIES_DICT + ' note'
ORDER_FIELDS_LIST = ORDER_FIELDS.split()
OrderTup = namedtuple('OrderTup',ORDER_FIELDS)

COMMENT = 'COMMENT'
STARTUP_PARAMETERS_FIELDS = [COMMENT]
StartupParameters = namedtuple('StartupParameters',STARTUP_PARAMETERS_FIELDS,defaults=(None,) * len(STARTUP_PARAMETERS_FIELDS))

# 3/24/2023. screen sizes
SMALL = 'SMALL'
MEDIUM = 'MEDIUM'
LARGE = 'LARGE'

def _neaf_ss_fields():
    return NEAF_VENDOR_FIELDS[NEAF_VENDOR_FIELDS.index('company last_order_date'):NEAF_VENDOR_FIELDS.index('error')+5]
NeafSSTup = namedtuple('NeafSSTup', _neaf_ss_fields())
NEAF_VENDOR_PROPERTIES_FIELDS = 'company_from_property cellno name_on_badge badge1_name badge2_name requested_booth_loc get_booths_from prize1 prize1_value prize2 prize2_value extra_badge_names '+\
                                'ive_reviewed_vendor_packet error'
NeafVendorPropertiesTup = namedtuple('NeafVendorPropertiesTup',NEAF_VENDOR_PROPERTIES_FIELDS)

DoorPrizeSrcDicts = namedtuple('DoorPrizeSrcDicts', 'winner cc cc_reject shopify')
DoorPrizeResDicts = namedtuple('DoorPrizeResDicts', 'eligible reject')
NEAF_VENDOR_COLLECTIONS_FIELDS = 'raw neaf_ss full vendor_invoices vendor_last_order_date_map last_order_date_vendors_map company_badge'
NeafVendorCollectionsTup = namedtuple('NeafVendorCollectionsTup', NEAF_VENDOR_COLLECTIONS_FIELDS)

MAX_KEY_SUFFIX = 100
DOOR_PRIZE_DIR = 'door_prize'
DOOR_PRIZE_WINNER = 'door_prize_winner_{neaf_year}_{neaf_day_of_week}'
DICT_DELIMITER_FRONT = '+-------------+ '
STARS = '*******************************************************************************************************'

def set_precommit_sanity_check():
    consts.PRECOMMIT_SANITY_CHECK = None
    precommit_filename = None
    for frame_info in inspect.stack():
        filename = frame_info.filename
        if filename.endswith("precommit_sanity.py"):
            precommit_filename = filename
            if 'RAC_share' in filename:
                consts.PRECOMMIT_SANITY_CHECK = 'RAC_share'
            elif 'RAC' in filename:
                consts.PRECOMMIT_SANITY_CHECK = 'RAC'
            else:
                print(f"Failure setting consts.PRECOMMIT_SANITY_CHECK in set_precommit_sanity_check(). Expecting to find either 'RAC' or 'RAC_share' in {filename}.")
    if consts.PRECOMMIT_SANITY_CHECK:
        print(f"In set_precommit_sanity_check() consts.PRECOMMIT_SANITY_CHECK set to {consts.PRECOMMIT_SANITY_CHECK} because filename of executable is {precommit_filename}.")
    return
set_precommit_sanity_check()

def RAC_DIR():

    ddir = os.path.expanduser(r"~\Desktop")
    ddir_onedrive = os.path.expanduser(r"~\OneDrive\Desktop")
    ddir_exists = os.path.isdir(ddir)
    ddir_onedrive_exists = os.path.isdir(ddir_onedrive)
    if not ddir_exists and not ddir_onedrive_exists:
        raise Exception(f'In RAC_DIR() neither desktop paths {ddir} or {ddir_onedrive} exist. Need at least one.')

    if ddir_onedrive_exists:
        ddir = ddir_onedrive
    racdir = os.path.join(ddir,'RAC_DIR')

    last_racdir = getattr(RAC_DIR,'_last_racdir',None)
    if consts.PRECOMMIT_SANITY_CHECK:
        # 1/28/2026. if we are in pre-commit sanity check mode. we do something like this code block below. just use value of PRECOMMIT_SANITY_CHECK set in set_precommit_saity_check.
        racdir = os.path.join(racdir,'precommit_sanity',consts.PRECOMMIT_SANITY_CHECK)
        if racdir != last_racdir:
            print(f"In RAC_DIR() return {racdir} because consts.PRECOMMIT_SANITY_CHECK is {consts.PRECOMMIT_SANITY_CHECK}.")
    else:
        if racdir != last_racdir:
            print(f"In RAC_DIR() return {racdir}.")
    RAC_DIR._last_racdir = racdir

    return racdir

def door_prize_dir():
    return os.path.join(RAC_DIR(),DOOR_PRIZE_DIR)

def pdf_path(neaf_year,neaf_day_of_week):
    fname = os.path.join(door_prize_dir(), DOOR_PRIZE_WINNER.format(neaf_year=neaf_year,neaf_day_of_week=neaf_day_of_week) + '.pdf')
    return fname

def get_emails_in_door_prize_dict(door_prize_dict):
    emails_in_door_prize_dict = {}
    for dpt in door_prize_dict.values():
        emails_in_door_prize_dict[dpt.email] = dpt
    return emails_in_door_prize_dict

def goodDateStr(dstr):
    date_str = None
    error_msg = ''
    dstr = '' if not dstr else str(dstr)
    if not dstr.strip():
        dstr = 'BLANK'
    try:
        date_str =  parser.parse(dstr).strftime('%Y-%m-%d')
        return date_str,error_msg
    except ValueError:
        error_msg = "Date of '{0}' is not valid.".format(dstr)
        return date_str,error_msg

def get_default_neaf_year():
    # a safe date to start NEAF for following year is november
    month = datetime.datetime.now().date().month
    year = datetime.datetime.now().date().year
    year = year + 1 if month >= 11 else year
    return year

def get_date(date_and_time_str):
    if not date_and_time_str:
        return None
    toks = date_and_time_str.split('T')
    if len(toks) == 2:
        # date in form '2018-12-10T23:05:50-05:00'
        return toks[0]
    toks = date_and_time_str.split('/')
    if len(toks)==3:
        # date in form 10/15/55
        m = toks[0]
        d = toks[1]
        y = toks[2]
        if not m.isdigit() or not d.isdigit() or not y.isdigit():
            return None
        yr = int(y)
        yr = yr + 2000 if yr<100 else yr
        if yr <2000 or yr>2050:
            return None
        return '{0:04d}-{1:02d}-{2:02d}'.format(yr,int(m),int(d))
    toks = date_and_time_str.split('-')
    if len(toks)==3:
        # date already in expected form of 2018-05-10
        yr = toks[0]
        m = toks[1]
        d = toks[2]
        return '{0:04d}-{1:02d}-{2:02d}'.format(int(yr),int(m),int(d))
    return None

def convert_utc_to_local_datetime(utc_dtime_str):
    if utc_dtime_str is None:
        # 12/17/2025. added this block to handle cancelledAt for all orders that were never canceled. they have cancelledAt of None.
        return utc_dtime_str
    utc_datetime = datetime.datetime.strptime(utc_dtime_str, utc_format)
    utc_datetime = pytz.utc.localize(utc_datetime)
    eastern_datetime = utc_datetime.astimezone(eastern_zone)
    local_dtime_str = datetime.datetime.strftime(eastern_datetime, '%Y-%m-%dT%H:%M:%S')
    return local_dtime_str

def utc_for_midnight_local(dt):
    dt_time = dt + 'T00:00:00'
    midnight = datetime.datetime.strptime(dt_time,'%Y-%m-%dT%H:%M:%S')
    etz = pytz.timezone("US/Eastern")
    etz_datetime = etz.localize(midnight)
    utc_datetime = etz_datetime.astimezone(pytz.utc)
    utc_str = datetime.datetime.strftime(utc_datetime,'%Y-%m-%dT%H:%M:%SZ')
    return utc_str

def delta_on_date_str(dtstr,days):
    dt = date.fromisoformat(dtstr)
    dt = dt + datetime.timedelta(days=days)
    new_date_str =  datetime.datetime.strftime(dt,"%Y-%m-%d")
    return new_date_str

def convertToStr(msgs):
    msg = ''
    for m in msgs:
        msg += m + '\n'
    return msg

def normalize_phone_num(phone_num):
    if not phone_num:
        return phone_num
    if phone_num.isdigit() and len(phone_num) == 10:
        phone_num = phone_num[0:3]+'-'+phone_num[3:6]+'-'+phone_num[6:]
    if len(phone_num) == 13 and phone_num[0] == '+' and  phone_num[1:].isdigit():
        phone_num = phone_num[1:]
    if phone_num.isdigit() and len(phone_num) == 12:
        phone_num = '+'+phone_num[0:2]+' '+phone_num[2:5]+' '+phone_num[5:8]+' '+phone_num[8:]

    if '-' not in phone_num and len(phone_num) >= 10:
        phone_num = phone_num[:-7] + '-' + phone_num[-7:-4] + '-' + phone_num[-4:]
    if phone_num.startswith('+1'):
        phone_num = phone_num[2:]

    return phone_num.strip()

def get_max_len(item,max_len):
    max_len = len(str(item)) if len(str(item)) > max_len else max_len
    return max_len

def remove_unicode(data):
    #import collections
    if isinstance(data, str):
        try:
            #sdata = data.encode('ascii','ignore')
            sdata = data.decode("utf-8") if isinstance(data,bytes) else data
            #sdata = data.str(data)
        except Exception as ex:
            sdata = 'UNICODE_ERROR'
        return sdata

    elif isinstance(data, dict):
        return dict(list(map(remove_unicode, iter(data.items()))))
    elif isinstance(data, list):
        return list(map(remove_unicode, data))
    elif isinstance(data, tuple):
        ldata = list(data)
        ldata = list(map(remove_unicode, ldata))
        return tuple(ldata)

    # 3/14/2022. this block was eliminated and repalced with 3 block above that explicitly handle dict, list, tuple because
    # collections.Mapping and collections.Iterable did not exist on mac.
    # I could have used collections._collections_abc.Mapping and collections._collections_abc.Iterable but seems like a pain in the ass.
    # elif isinstance(data, collections.Mapping):
    #     return dict(list(map(remove_unicode, iter(data.items()))))
    # elif isinstance(data, collections.Iterable):
    #     return type(data)(list(map(remove_unicode, data)))

    else:
        return data

def getCurrencySymbolFromCode(code):
    code = code.strip()
    return CURRENCY_SYMBOL_FROM_CODE.get(code,code+' ')

_BIDI = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
def normalize_unicode_text(s):

    # 2/20/2026. XXX this function suggested by ChatGPT to
    #                removing Unicode format/control characters (category Cf)
    #                normalizing compatibility characters (NFKC)
    #                converting non-breaking whitespace to normal whitespace
    #                producing display-safe, width-stable text

    if s is None:
        return ""

    # normalize compatibility forms (helps with odd punctuation/spaces)
    s = unicodedata.normalize("NFKC", s)
    # NBSP -> plain space
    s = s.replace("\u00a0", " ")
    # remove bidi marks
    s = _BIDI.sub("", s)
    # remove other invisible "format" chars (Unicode category Cf)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf")
    # collapse whitespace runs
    s = re.sub(r"[ \t]+", " ", s).strip()

    return s

def writerow_UnicodeEncodeError(wr,mrow):
    # 7/23/2020. this function written because this mrow failed:
    # [' 9648', '', '2020-04-04 09:56:06', 'Scott Wilkins', '580 u Sankarske Drahy', '', 'Česky Krumlov,  38101 Czech Republic', '', 'scott@thatsmycoffee.com', 'neaf_attend_virtual_door_prize', 1, 5, 5]
    # 'Česky Krumlov,  38101 Czech Republic' has bad character. will be converted to
    # '?esky Krumlov,  38101 Czech Republic'
    try:
        wr.writerow(mrow)
    except Exception as ex:
        #msg = 'wr.writerow(mrow) failed for mrow of\n{0}'.format(mrow)
        #print(msg)
        #print("Problem that will be circumvented is '{0}'".format(ex))
        mrow_encode = []
        for m in mrow:
            if isinstance(m,str):
                m_encode = m.encode('cp850','replace').decode('cp850')
            else:
                m_encode = m
            mrow_encode.append(m_encode)
        wr.writerow(mrow_encode)
        print("wr.writerow(mrow) failed for\n{0}\nconverted to\n{1}".format(mrow,mrow_encode))
    return

def show_neaf_vendor_dict(nv_deals_dict):
    msgs = []
    cnt = 0    
    msg = convertToStr(msgs)   
    return msg

def fix_up_search_for(search_for):
    search_for = search_for.strip().upper()
    search_for = [search_for]
    return search_for

def get_target_dict(search_for_orig,samdt,key,source_dict=None):
    # 1/11/2019. can search in a dict for the item search_for. The dict to search in can be passed in here in 2 ways. the original way that was used
    # in search_and_mark is to find dict under namedtuple samdt by key. new way for membership system is to pass in dict directly as source_dict.
    if source_dict is None: source_dict = {}
    source_dict = source_dict if source_dict else samdt._asdict()[key]
    msg = ''
    search_for = fix_up_search_for(search_for_orig)
    target_dict = {}
    cnt = 0
    for key,dpt in source_dict.items():
        cnt += 1
        #print("\n{0} out of {1}: searching for '{2}' in dpt with key {3}".format(cnt,len(source_dict),key))

        foundItem = False
        for key2, item in dpt._asdict().items():
            if foundItem:
                break
            #print('searching {0}:{1} for {2}'.format(key2, item, search_for_orig))
            item_orig = item
            item = item.strip().upper() if isinstance(item, str) else str(item)
            for sitem in search_for:
                if sitem in item:
                    foundItem = True
                    msg2 = "For order_num:{0} found item of '{1}' in {2} of '{3}'".format(dpt.order_num,search_for_orig, key2, item_orig)
                    msg += ('\n' + msg2 if msg else msg2)
                    #print(msg)
                    break
        #print('{0}: exiting from found_item loop with foundItem:{0}, msg:{1}'.format(cnt, foundItem, msg))

        if foundItem:
            target_dict[key] = dpt
    if not target_dict:
        msg = "Searched in {0} records but cannot find item '{1}'.".format(len(source_dict),search_for_orig)
    return target_dict,msg

def appendMsg(msg,new_msg=None,print_new_msg=True):
    if new_msg is None:
        # 1/28/2026. we are just starting to accumulate msg. treat msg as initial value
        if print_new_msg:
            print(msg)
        return msg
    if not new_msg:
        return msg
    if print_new_msg:
        print(new_msg)
    if msg:
        msg = msg + '\n' + new_msg
    else:
        msg = new_msg
    return msg

def show_dict(dp_dict,fname):
    msgs = []
    cnt = 0
    msgs.append(DICT_DELIMITER_FRONT+fname+' ----------------')
    cnt_max = 0
    key_max = 0
    created_at_max = 0
    name_max = 0
    email_max = 0
    phone_num_max = 1
    sku_max = 0
    CONFIRM_NOTE_max = 1
    cnt = 0
    for k in sorted(dp_dict.keys()):
        cnt += 1
        v = dp_dict[k]
        cnt_max          = len(str(cnt))       if                    len(str(cnt))>cnt_max else cnt_max
        key_max          = len(k)              if                    len(k)>key_max else key_max
        created_at_max   = len(v.created_at)   if                    len(v.created_at)>created_at_max else created_at_max
        name_max         = len(v.name)         if v.name         and len(v.name)>name_max else name_max
        email_max        = len(v.email)        if v.email        and len(v.email)>email_max else email_max
        phone_num_max    = len(v.phone_num)    if v.phone_num    and len(v.phone_num)>phone_num_max else phone_num_max
        sku_max          = len(v.sku)          if                    len(v.sku)>sku_max else sku_max
        CONFIRM_NOTE_max = len(v.CONFIRM_NOTE) if v.CONFIRM_NOTE and len(v.CONFIRM_NOTE)>CONFIRM_NOTE_max else CONFIRM_NOTE_max
        cnt += 1
    fmt = '{{:{0}d}}. {{:{1}s}} -- {{:{2}s}}  {{:{3}s}}  {{:{4}s}}  {{:{5}s}}  {{:{6}s}}  {{:{7}s}}'
    fmt = fmt.format(cnt_max,key_max,created_at_max,name_max,email_max,phone_num_max,sku_max,CONFIRM_NOTE_max)
    cnt = 0
    for k in sorted(dp_dict.keys()):
        cnt += 1
        v = dp_dict[k]
        try:
            _msg = fmt.format(cnt,k,v.created_at,v.name,v.email,str(v.phone_num),v.sku,v.CONFIRM_NOTE if v.CONFIRM_NOTE is not None else '')
        except Exception as ex:
            _msg = 'Failure in processing item with cnt:{0}, k:{1}, v:{2}'.format(cnt,k,v)
        _msg = _msg.rstrip()
        msgs.append(_msg)
    if len(msgs)==1:
        msgs.append('--------------- NO ITEMS FOUND ---------------')
    msg = convertToStr(msgs)               
    return msg 
    
def get_key(dpt,door_prize_dict):
    key = dpt.order_num.strip()
    if not door_prize_dict.get(key):
        # this is the first entry for this order_num. no need for suffix of "-<n>" .
        return key
    # maximum size of key suffix. typical key like order number '1242'. if more than one door entry for \
    # that order could have '1242-2' . Maximum suffix size is MAX_KEY_SUFFIX. In principal there is no
    # maximum number of door prize entries in an order but if we get above MAX_KEY_SUFFIX its probably a
    # a problem    
    for suffix in range(2,MAX_KEY_SUFFIX): 
        new_key =  '{0}-{1}'.format(key,suffix)
        if not door_prize_dict.get(new_key):
            return new_key
    # if we return here we have a problem. error message in _populate_door_prize_dict will be displayed.        
    return new_key
    
def _populate_door_prize_dict(fname,dpt,key,door_prize_dict):
    dpt_old = door_prize_dict.get(key)
    if dpt_old:
        msg = 'Duplicate key of {0} for entry {1} found processing file {2}. {3} '+\
            'already has this key.'       
        input(msg.format(key,dpt,fname,dpt_old,dpt))
        raise Exception
    door_prize_dict[key] = dpt 
    return
      
def build_door_prize_dict_from_file(fname,verbose,exit_message=False):
    door_prize_dict = {}
    if os.path.exists(fname):
        reader = csv.reader(open(fname))
        headers = next(reader)
        for row in reader:
            if len(row) != len(DOOR_PRIZE_HEADER):
                msg = 'Failure in build_door_prize_dict_from_file processing file {0}. row of {1} does not have length of {2}.'
                input(msg.format(fname,row,len(DOOR_PRIZE_HEADER)))
                raise Exception
            dpt = DoorPrizeTup(*row)
            _populate_door_prize_dict(fname,dpt,dpt.order_num,door_prize_dict)
       
    if exit_message or verbose:
        msg = 'Exiting build_door_prize_dict_from_file. Built dict of size {0} from file {1}.'
        print(msg.format(len(door_prize_dict),fname))
    return door_prize_dict

def read_door_prize_file(fname, neaf_year, neaf_day_of_week, verbose, exit_message=False):
    fname = os.path.join(door_prize_dir(),fname.format(neaf_year=neaf_year, neaf_day_of_week=neaf_day_of_week)+'.csv')
    door_prize_dict = build_door_prize_dict_from_file(fname,verbose,exit_message)
    return door_prize_dict,fname

def build_door_prize_cc_dict(ccdpt_list, door_prize_dict, verbose):

    # ccdpt_list is list of CcDoorPrizeTup namedtuples from constant contact already filtered by date.
    # check email addresses in ccdpt_list. if any exist in door_prize_dict don't add item to door_prize_cc_dict.
    # if logging on, display those rejected items.
    # modify sku in rejected list to indicate reason for rejection. Only current reason for rejection is already in shopify.

    emails_in_door_prize_dict = get_emails_in_door_prize_dict(door_prize_dict)
    door_prize_cc_dict = {}
    door_prize_cc_reject_dict = {}
    cnt = 0
    cnt_rej = 0
    for ccdpt in ccdpt_list:

        cc_name = ccdpt.first_name+' '+ccdpt.last_name
        e_dpt = emails_in_door_prize_dict.get(ccdpt.email_address)
        if e_dpt:
            if verbose:
                msg = 'Rejecting Constant Contact door prize entry email:{0}, name:{1} because Shopify order {2}, name:{3} has same email address.'
                print(msg.format(ccdpt.email_address,cc_name,e_dpt.order_num,e_dpt.email))   
            cnt_rej += 1
            key = 'cc_rej{:0>3d}'.format(cnt_rej)
            cc_sku = 'cc_rej:email_matches_shopify'            
        else:    
            cnt += 1
            key = 'cc{:0>4d}'.format(cnt)
            cc_sku = 'cc_door_prize'

        dpt = DoorPrizeTup(key, N_A, ccdpt.modified_date, cc_name, ccdpt.home_phone, ccdpt.email_address, cc_sku, '1', None)
        if e_dpt:
            door_prize_cc_reject_dict[key] = dpt    
        else:      
            door_prize_cc_dict[key] = dpt
            
    return door_prize_cc_dict,door_prize_cc_reject_dict

def normalizeAddress(default_address):

    def fixBigAddress1(address1,address2):
        # 1/18/2021. this function introduced to handle big address1 for order #9267 of
        # 37/A, Shaktikunj Society, Behind Samjuba hospital, bapunagar, ahmedabad, gujarat, India
        # chop it up and put in address2
        if len(address1) < 40 or address2:
            return address1,address2
        toks = address1.split(',')
        tokcnt = len(toks) // 2
        address1 = ','.join(toks[:tokcnt]).strip()
        address2 = ','.join(toks[tokcnt:]).strip()
        return address1,address2

    if not default_address:
        m = MISSING
        return m,m,m,m,m,m,m
    address1 = default_address['address1'] if default_address['address1'] else ''
    address2 = default_address['address2'] if  default_address['address2'] else ''
    city = default_address['city'] if default_address['city'] else ''
    province_key = 'province'
    province_code = default_address[province_key] if default_address[province_key] else ''
    zipc = default_address['zip'] if default_address['zip'] else ''
    country = default_address['country'] if default_address['country'] else ''
    country = '' if country == 'United States' else ' '+country
    address3 = city+', '+province_code+' '+zipc+country
    address2 = '' if address1 == address2 else address2
    address1,address2 = fixBigAddress1(address1,address2)
    return address1,address2,address3,city,province_code,zipc,country
    
def write_door_prize_file(door_prize_winner_dict, fname, neaf_year, neaf_day_of_week):

    os.makedirs(door_prize_dir(),exist_ok=True)
    fpath = os.path.join(door_prize_dir(),fname.format(neaf_year=neaf_year,neaf_day_of_week=neaf_day_of_week)+'.csv')
    msg = 'Writing door prize winner file {0} with {1} rows.'
    print(msg.format(fpath,len(door_prize_winner_dict)))
    with open(fpath,'w') as outfile:
        writer = csv.writer(outfile, lineterminator='\n')
        writer.writerow(DOOR_PRIZE_HEADER)
        for dpt in door_prize_winner_dict.values():
            writer.writerow(dpt)
    return

def show_paths_and_files_dp(neaf_year,neaf_day_of_week):
    msg =  '---------------------------------------------------------------------------------------------------\n'
    msg += 'Directory for all Door Prize items:            '+door_prize_dir()+'\n'
    msg += 'Winners filename:                       '+os.path.join(door_prize_dir(),DOOR_PRIZE_WINNER.format(neaf_year=neaf_year,neaf_day_of_week=neaf_day_of_week)+'.csv') + '\n'
    msg += 'Winners pdf:                            '+pdf_path(neaf_year,neaf_day_of_week)+'\n'
    msg += '---------------------------------------------------------------------------------------------------'
    return msg

def getItem(item_dict,key):
    if not item_dict:
        return ''
    item = item_dict.get(key)
    if not item:
        return ''
    return item

def getFromProperties(item_key,properties,requested_properties):
    # 1/19/2026. this function processes items set from the App 'PC - Product Options'.
    value = None
    # requested_properties is used to confirm no unexpected properties are encountered. if so, its an error.
    requested_properties[item_key] = True
    if not properties:
        return value
    for prop in properties:
        name = prop[NOTE_ATTRIBUTE_KEY()]
        val = prop['value']
        if name == item_key:
            value = val.strip()
            break
    return value

def getPropertiesDict(properties, excluded_items):
    # 1/19/2026. this function processes items set from the App 'PC - Product Options'.
    # 2/23/2023. example is order_num 11843.
    # properties is [{NOTE_ATTRIBUTE_KEY():'Club (optional)','value':'half assed club'},{NOTE_ATTRIBUTE_KEY():'Days participating','value':'Both'},{NOTE_ATTRIBUTE_KEY():'Equipment','value':'laser pointer, port-a-potty'}]
    # convert to {'Club (optional)' : 'half assed club', 'Days participating' : 'Both', 'Equipment' : 'laser pointer, port-a-potty'}
    propertiesDict = {}
    if not properties:
        return propertiesDict
    for pitem in properties:
        k = pitem.get(NOTE_ATTRIBUTE_KEY())
        if k in excluded_items:
            continue
        propertiesDict[k] = pitem.get('value')
    return propertiesDict

def showError(error):
    return '\n{0}\n{1}\n{0}\n'.format(STARS,error)

def build_startup_parameters(argv):

    if not isinstance(argv,list):
        # 3/28/2023. possibly not launching from rac_launcher.bat so do nothing
        return StartupParameters()
    args = argv[1:]

    print('{0} args passed to main(). They are {1}'.format(len(args),args))
    if len(args) % 2:
        msg = 'Number of args passed to main() of {0}. Must be even number in form of key/value pairs.'.format(len(args))
        raise Exception(msg)

    args_dict = {}
    for i in range(0,len(args),2):
        args_dict[args[i]] = args[i+1]

    sptdict = {}
    for k,v in args_dict.items():
        if k not in STARTUP_PARAMETERS_FIELDS:
            msg = 'In build_startup_parameters fatal error processing args:{0}. Key of {1} not in STARTUP_PARAMETERS_FIELDS:{2}.'.format(args,k,STARTUP_PARAMETERS_FIELDS)
            raise Exception(msg)
        sptdict[k] = v
    spt = StartupParameters(**sptdict)
    return spt

def nvtDesc(nvt):
    msg = 'NeafVendorTup -- order_num:{0} name:{1} company:{2}|(from_attribute):{3}|(from_property):{4} sku:{5} email:{6}'
    msg = msg.format(nvt.order_num,nvt.name,nvt.company,nvt.company_from_attribute,nvt.company_from_property,nvt.sku,nvt.email)
    return msg

if __name__ == "__main__":
    RAC_DIR()

