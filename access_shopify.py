"""
Created on Sun Feb 15 18:13:25 2015

@author: joe1
"""
import copy
# install with
# pip install requests
# use pip3 on mac
import requests
import json
import datetime
import time
import pprint
# install with
# pip install python-dateutil
# use pip3 on mac
from dateutil import parser
import tracemalloc
from consts import NEAF_YEAR_VALID,NEAF_YEAR_DEFAULT,USE_GRAPHQL,SKUS_TO_LOAD_DICT
from consts import NEAF_YEAR_ALL,ALL,SHOP_NAME,API_KEY_2,PASSWORD_2,API_KEY_RW,PASSWORD_RW,RawOrdersTup
from utils import get_default_neaf_year,remove_unicode,NeafVendorTup,OrderTup,get_date,utc_for_midnight_local
from graphql_queries import ORDER_DETAILS,ORDERS_BY_SKU_BETWEEN_DATES,ORDER_BY_NAME
from graphql_utils import get_orders_cursor_items,get_url_and_headers
from get_shopifycommontup_list import get_shopifyCommonTup_list
from get_shopifycommontup_list_graphql import get_shopifyCommonTup_list_graphql

def goodDateStr(dstr):
    date_str = None
    error_msg = ''
    dstr = '' if not dstr else str(dstr)
    if not dstr.strip():
        dstr = 'BLANK'
    try:
        date_str = parser.parse(dstr).strftime('%Y-%m-%d')
        return date_str,error_msg
    except ValueError:
        error_msg = "Date of '{0}' is not valid.".format(dstr)
        return date_str,error_msg

def get_st_dict_stats(st_dict):
    keys = sorted(st_dict.keys())
    first_key = keys[0]
    last_key = keys[-1]
    val_first = st_dict[first_key]
    val_last = st_dict[last_key]
    first_key_toks = first_key.split('-')
    last_key_toks = last_key.split('-')
    return int(first_key_toks[0]),val_first.created_at[:10],int(last_key_toks[0]),val_last.created_at[0:10]

def apply_discount(st_dict,order_num):
    nvt = st_dict.get(order_num)

    # 7/26/2019. previously we thought discount only for NEAF vendor managment tool but we found order like #8918 that had $7 discount on $27 POS sunday admission to NEAF.
    # but this function only works for nvt of type NeafVendorTup. #8918 is on type OrderTup.
    if not nvt or not isinstance(nvt, (NeafVendorTup,OrderTup)):
        # this order contained no products of interest or we are not running vendor management tool, we are doing something else like door prize
        return

    if isinstance(nvt,NeafVendorTup):
        total_cost = nvt.total_cost
        total_discounts = nvt.total_discounts
        discount_codes = nvt.discount_codes
    else:
        total_cost = nvt.total
        total_discounts = nvt.discount
        discount_codes = nvt.discount_code

    paid = 0.0 if discount_codes in ('EDUCATION','CHECK') else total_cost - total_discounts
    total_due = total_cost if discount_codes == 'CHECK' else None
    if isinstance(nvt,NeafVendorTup):
        nvt = nvt._replace(paid=paid,total_due=total_due)
    else:
        nvt = nvt._replace(paid=paid)
    st_dict[order_num] = nvt
    return


class AccessShopify(object):

    def __init__(self,neaf_year,created_at_min,created_at_max,order_to_debug,verbose):

        self.error = ''
        self.neaf_year_raw = neaf_year.lower()
        self.order_to_debug = order_to_debug

        if created_at_min:
            if not get_date(created_at_min):
                self.error = "created_at_min: '{0}' passed to AccessShopify.__init__ not in valid date form.".format(created_at_min)
                return
        if created_at_max:
            if not get_date(created_at_max):
                self.error = 'created_at_max:{0} passed to AccessShopify.__init__ not in valid date form.'.format(created_at_max)
                return
        if created_at_min and created_at_max and created_at_min > created_at_max:
            msg = 'created_at_min:{0} and created_at_max:{1} passed to AccessShopify.__init__ are invalid. created_at_min must be less than or equal to created_at_max.'
            self.error = msg.format(created_at_min,created_at_max)
            return

        if not neaf_year and (created_at_min and created_at_max):
            # no need for neaf year if both min and max date exist.
            pass
        else:
            neaf_year = str(neaf_year) if neaf_year else NEAF_YEAR_DEFAULT
        nyr_default = get_default_neaf_year()
        nyr = ''
        if neaf_year.isdigit():
            nyr = int(neaf_year)
            if nyr < 2015 or nyr > nyr_default:
                self.error = 'neaf_year:{0} is invalid. Must be from {1} to {2}.'.format(nyr,2015,nyr_default)
        elif neaf_year and neaf_year not in NEAF_YEAR_VALID:
            self.error = 'neaf_year of {0}. Must be one of {1} or blank.'.format(neaf_year,NEAF_YEAR_VALID)
        if self.error:
            return
        if neaf_year == NEAF_YEAR_ALL:
            self.neaf_year = ''
        else:
            self.neaf_year = nyr

        if neaf_year and (created_at_min or created_at_max):
            self.error = 'neaf_year:{0}, created_at_min:{1} and created_at_max:{2} are incompatible. Either use neaf_year or created_at_min/created_at_max.'.format(neaf_year,created_at_min,created_at_max)
            return

        if USE_GRAPHQL[0]:
            if self.order_to_debug:
                if created_at_min or created_at_max:
                    self.error = 'order_to_debug:{0}, created_at_min:{1} and created_at_max:{2} are incompatible. Either use order_to_debug or use created_at_min and created_at_max.'
                    self.error = self.error.format(self.order_to_debug,created_at_min,created_at_max)
                    return
                self.created_at_min = None
                self.created_at_max = None

        if not USE_GRAPHQL[0] or not self.order_to_debug:
            if created_at_min:
                self.created_at_min,self.error = goodDateStr(created_at_min)
            else:
                self.created_at_min = '2014-10-01' if neaf_year == NEAF_YEAR_ALL else '{0}-10-01'.format(self.neaf_year-1)
            if created_at_max:
                self.created_at_max,self.error = goodDateStr(created_at_max)
            else:
                if self.neaf_year:
                    self.created_at_max = '{0}-06-01'.format(self.neaf_year)
                else:
                    now = datetime.datetime.now()
                    self.created_at_max = '{0}-{1}'.format(now.year+1,now.strftime('%m-%d'))
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            if self.created_at_max > today:
                self.created_at_max = today

            if self.created_at_min and self.created_at_max and self.created_at_min > self.created_at_max:
                self.error = 'created_at_min:[0} and created_at_max:{1} are incompatible. created_at_min must be less than or equal to created_at_max.'
            if self.error:
                return

        self.verbose = verbose
        self.msg = ''
        if self.error:
            return
        self.total_raw_orders_count = 0
        self.last_page_comment = ''
        self.sku_key = None # is assigned in derived class
        self.raw = {}
        # 11/14/2002 use this map to update self.raw NeafVendorTup elements with edits to order_note_attributes
        self.order_id_to_order_num_map = {}
        self.excludedCovidSkuOrdersDict = {}
        self.refundNotes = []
        self.note_attributes_Notes = []
        # 12/30/2022. call self.shopifyOrdersFromHttps() later to populate self.rawOrdersTupList
        self.rawOrdersTupList = []

        return

    def print_and_save(self,msg,always_print=False,verbose=None):
        verbose_local = verbose if verbose is not None else self.verbose
        if verbose_local or always_print:
            print(msg)
        if verbose_local:
            self.msg += msg + '\n'
        return

    def append_to_shopifyTup_dict(self,nvt_dict,sct):
        msg = 'Derived class does not have append_to_shopifyTup_dict(self,nvt_dict,sct) defined. Thats bad.'
        raise Exception(msg)
        return

    def getRangeItems(self,orders):
        # TODO 12/27/2024. delete this function when we have migrated to GraphQL
        last_order = orders[0]
        first_order = orders[-1]
        first_key = first_order['name']
        first_date = first_order['created_at'][0:10]
        last_key = last_order['name']
        last_date = last_order['created_at'][0:10]
        return first_key,first_date,last_key,last_date

    def getRangeItemsGraphQL(self,orders):
        last_order = orders[0]
        first_order = orders[-1]
        first_key = first_order['name']
        first_date = first_order['createdAt'][0:10]
        last_key = last_order['name']
        last_date = last_order['createdAt'][0:10]
        return first_key,first_date,last_key,last_date

    def _getPaginationItems(self,page,reqstr,response):
        headers = response.headers
        linkFull = headers.get('Link')
        if not linkFull:
            if page == 1:
                # 3/4/2021. if its first page the enter Link section could be missing if there are less than 250 orders. that happens if you don't go too far back in time
                # for created_at_min.
                linkFull = ''
            else:
                msg = "Failure getting Shopify data from internet while procesing URL\n{0}\nExpecting response.headers['Link'] to exist but its missing. " + \
                      "Its needed to support cursor-based pagination to next page. You're really fucked now. Pray. Wait a few minutes and try again."
                self.error = msg.format(reqstr,response.status_code)
            return linkFull

        if 'rel="next"' not in linkFull and 'rel="previous"' not in linkFull :
            msg = 'Failure getting Shopify data from internet while procesing URL\n{0}\n' + \
                'Expecting to find either substring rel="next" or rel="previous" in response.headers[Link] but both are missing.'
            self.error = msg.format(reqstr)
            return linkFull

        if 'rel="next"' not in linkFull:
            # we've reached the end of the data
            return ''

        ind = linkFull.index('rel="next"')
        link = linkFull[:ind]
        ind = link.rindex('>')
        link = link[:ind]
        ind = link.rindex('https')
        link = link[ind:]

        return link

    def shopifyOrdersFromHttps(self,limit=250):

        # TODO 12/27/2024. delete this function when we have migrated to GraphQL
        # 12/30/2022. populate self.rawOrdersTupList with raw shopify data from their webservice.

        page = 0
        total_raw_orders_count = 0
        self.rawOrdersTupList.clear()

        today = datetime.datetime.now().strftime('%Y-%m-%d')
        if today == self.created_at_max:
            # 4/9/2021. found weird behavior with created_at_max today. when running at 10PM only orders up to 7:45PM were picked up. see if this helps. maybe there's an issue
            # wih UT that this might fix?
            created_at_max = datetime.datetime.now().date() + datetime.timedelta(days=1)
            created_at_max = created_at_max.strftime('%Y-%m-%d')
        else:
            created_at_max = self.created_at_max
        msg = '\nIn shopifyOrdersFromHttps accessing orders at https://{0}.myshopify.com/admin/orders.json with limit={1}, created_at_min={2} 00:01, created_at_max={3} 23:59\n'
        print(msg.format(SHOP_NAME,limit,self.created_at_min,created_at_max))

        while True:
            page += 1
            # 3/13/2019 TODO go here for documentation on options for order.json url. https://help.shopify.com/api/reference/order
            # 12/18/2012. see comment of same date in main() for full dump of entire order. this is only a small part of it.

            if page == 1:

                reqstr = 'https://{0}.myshopify.com/admin/orders.json?' +\
                    'fields=created_at,note,note_attributes,total_discounts,discount_codes,id,name,customer,billing_address,refunds,line_items&limit={1}'+\
                    '&created_at_min={2} 00:01&created_at_max={3} 23:59'  # 3/31/2017. added total_discounts and discount_codes
                reqstr = reqstr.format(SHOP_NAME,limit,self.created_at_min,created_at_max)
            else:
                reqstr = link

            try:
                response = requests.get(reqstr,auth=(API_KEY_2,PASSWORD_2))
            except Exception as ex:
                self.error = 'Exception running\n{0}\nof\n{1}\nWe are screwed.'.format(reqstr,ex)
                return
            if response.status_code != 200:
                msg = 'Failure getting Shopify data from internet while procesing URL\n'+'{0}\nstatus_code was {1}. Should be 200 if everything was working. Say a prayer and try again.'
                self.error = msg.format(reqstr,response.status_code)
                return None,None

            link = self._getPaginationItems(page,reqstr,response)
            if self.error:
                return

            res_text = response.text
            #res_text = res_text.encode('ascii','ignore')
            rd =  json.loads(res_text)
            orders = list(rd.values())[0]
            #orders = remove_unicode(orders)
            raw_orders_count = len(orders)
            if not raw_orders_count:
                # we have processed last page, we are done
                break

            total_raw_orders_count += raw_orders_count
            first_key,first_date,last_key,last_date = self.getRangeItems(orders)
            range_msg = 'from {0}/{1} to {2}/{3}'.format(first_key,first_date,last_key,last_date)
            self.last_page_comment = '{0} page {1}, {2} orders {3}. Tot. order cnt.:{4}.'
            self.last_page_comment = self.last_page_comment.format(reqstr[:reqstr.index('?')],page,raw_orders_count,range_msg,total_raw_orders_count)
            self.print_and_save(self.last_page_comment,always_print=True,verbose=True)

            rawOrdersTup = RawOrdersTup(page,raw_orders_count,orders)
            self.rawOrdersTupList.append(rawOrdersTup)

            if not link:
                # we've reached the end of data. we're done.
                break

        print('\nmemory usage at exit from AccessShopify.shopifyOrdersFromHttps after raw shopify data is loaded : {0}\n'.format(tracemalloc.get_traced_memory()[0]))
        return

    def edges_node_to_list(self,val):
        if not isinstance(val,dict):
            return val
        edges_list = val.get('edges')
        pageInfo = val.get('pageInfo')
        if pageInfo is None and isinstance(edges_list,list) and len(edges_list) == 0:
            # 2/13/2025. this block for refund that's missing refundLineItems but has refund against entire order. Example is #15317 with totalRefundedSet of $306.
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

    def getOrdersFromGraphqlRes(self, res):

        # 1/1/2025. slightly improve the data structures in res but don't adjust the basic graphql schema.

        orders = res.get('data', {}).get('orders', {})
        if not orders:
            self.error = "res.get('data',{}).get('orders',{}) returned no orders. Expecting a dict of orders to be returned by GraphQL request ORDERS_BY_SKU_BETWEEN_DATES."
            return

        new_orders = self.edges_node_to_list(orders)

        for new_order in new_orders:
            new_order['lineItems'] = self.edges_node_to_list(new_order['lineItems'])
            new_order['events'] = self.edges_node_to_list(new_order['events'])
            refunds = new_order['refunds']
            if refunds:
                for refund in refunds:
                    refund['refundLineItems'] = self.edges_node_to_list(refund.get('refundLineItems',[]))

        # 2/14/2025. run this print in console to see orders in their cleaned up format.
        # print(pprint.pformat(new_orders,width=250))

        return new_orders

    def createdAtMaxBugFixHack(self, res,created_at_max_utc):

        # TODO 1/19/2025. WARNING: I had date range query from accesshopify_by_date_range_and_sku in debug_utils of
        #                 created_at:>=2021-03-02T05:00:00Z AND created_at:<2021-03-03T05:00:00Z.
        #                 Intent was to find all orders for eastern time zone day of 2012-03-02.
        #                 It should have selected 4 orders from 2021-03-02 of #10636, #10637, #10638 and #10639 but for some inexplicable reason it pulled in another 2 of
        #                 #10640, createdAt:2021-03-03T17:18:24Z and #1064, createdAt:2021-03-04T01:41:57Z. I reproduce problem in Shopify GraphiQL App. In fact an upper
        #                 bound of 2021-03-03T00:00:00Z reproduces problem but 2021-03-02T23:59:59Z returns the 4 orders as expected.

        # 1/19/2025. this function will trim away orders with createdAt greater than created_at_max_utc

        orders_list = res.get('data',{}).get('orders',{}).get('edges',[])
        orders_to_discard = []
        msgs = []
        for i,order in enumerate(orders_list):
            createdAt = order['node']['createdAt']
            order_num = order['node']['name']
            if createdAt > created_at_max_utc:
                orders_to_discard.append(i)
                msgs.append('{0}:{1}'.format(order_num,createdAt))
        if not orders_to_discard:
            return
        for i in reversed(orders_to_discard):
            del orders_list[i]

        msg = 'GraphQL query had created_at_max:{0} but for some half-assed reason these orders with these created_at dates were still selected. Delete them.\n{1}'
        self.print_and_save(msg.format(created_at_max_utc,', '.join(msgs)), always_print=True, verbose=True)
        return

    def shopifyOrdersFromGraphQL(self,limit=200):

        # 12/30/2022. populate self.rawOrdersTupList with raw shopify data from their GraphQL webservice.

        memusage_at_entry = tracemalloc.get_traced_memory()[0]
        page = 0
        total_raw_orders_count = 0
        self.rawOrdersTupList.clear()

        sku_str = ' sku starts with:{0},'.format(self.sku_key) if self.sku_key else ''
        order_to_debug_str = ' order_to_debug:{0},'.format(self.order_to_debug) if self.order_to_debug else ''
        msg = '\nIn shopifyOrdersFromGraphQL accessing orders at https://{0}.myshopify.com/admin/api/2022-01/graphql.json with limit={1},{2}{3} created_at_min={4}, created_at_max={5}\n'
        print(msg.format(SHOP_NAME,limit,sku_str,order_to_debug_str,str(self.created_at_min),str(self.created_at_max)))

        url, headers = get_url_and_headers()
        if self.order_to_debug:

            # 1/3/2025. if debugging a single order use ORDER_BY_NAME here.
            # TODO 2/16/2025. future enhancement is to support more than one order using strings like this, 1234|5678|99999 . build appropriate OR condtion when this is supported.

            req = ORDER_BY_NAME
            toks = str(self.order_to_debug).split('|')
            if len(toks) == 1:
                req = req.replace('ORDER_NUM',str(self.order_to_debug))
            else:
                order_num_query = ' OR '.join(['name:#'+tok for tok in toks])
                req = req.replace('name:#ORDER_NUM',order_num_query)
            req = req.replace('INSERT_ORDER_DETAILS_HERE', ORDER_DETAILS)

        else:

            # 1/3/2025. this is normal block used when running applications. use ORDERS_BY_SKU_BETWEEN_DATES which supports request by skus and date range.

            created_at_max = parser.parse(self.created_at_max) + datetime.timedelta(days=1)
            created_at_max = created_at_max.strftime('%Y-%m-%d')

            # 1/18/2025. graphql expects datetimes in queries to be UTC so convert these items.
            created_at_min_utc = utc_for_midnight_local(self.created_at_min)
            created_at_max_utc = utc_for_midnight_local(created_at_max)

            req = ORDERS_BY_SKU_BETWEEN_DATES
            req = req.replace('LIMIT',str(limit))
            # 1/2/2025. this block does all adjustments for skus
            if self.sku_key == ALL:
                # 1/2/2025. load all skus between requested dates. remove sku clause
                req = req.replace('(sku:SKU_PREFIX_HERE*) AND ','')
            else:
                skus_to_load = SKUS_TO_LOAD_DICT[self.sku_key]
                sku_clause = ''
                for sku in skus_to_load:
                    delim = ' OR ' if sku_clause else ''
                    sku_clause += '{0}sku:{1}*'.format(delim,sku)
                req = req.replace('sku:SKU_PREFIX_HERE*',sku_clause)
            req = req.replace('CREATED_AT_MIN', created_at_min_utc)
            req = req.replace('CREATED_AT_MAX', created_at_max_utc)
            req = req.replace('INSERT_ORDER_DETAILS_HERE', ORDER_DETAILS)
            orig_req = req
            req = req.replace('after: "END_CURSOR_HERE",', '')

        while True:
            page += 1
            request = requests.post(url, data=req, headers=headers)
            res = json.loads(request.text)
            errors = res.get('errors')
            if errors:
                self.error = pprint.pformat(errors,width=100)
                return

            if not self.order_to_debug:
                # TODO 1/19/2025. This is a mysterious hack. See comments in function createdAtMaxBugFixHack.
                self.createdAtMaxBugFixHack(res,created_at_max_utc)

            # 1/1/2025. slightly improve the data structures in res but don't adjust the basic graphql schema.
            orders = self.getOrdersFromGraphqlRes(res)
            if self.error:
                return
            raw_orders_count = len(orders)

            total_raw_orders_count += raw_orders_count
            first_key, first_date, last_key, last_date = self.getRangeItemsGraphQL(orders)
            range_msg = 'from {0}/{1} to {2}/{3}'.format(first_key, first_date, last_key, last_date)
            self.last_page_comment = '{0}, page {1}, {2} orders {3}. Tot. order cnt.:{4}.'
            self.last_page_comment = self.last_page_comment.format(url, page, raw_orders_count,range_msg, total_raw_orders_count)
            self.print_and_save(self.last_page_comment, always_print=True, verbose=True)

            rawOrdersTup = RawOrdersTup(page, raw_orders_count, orders)
            self.rawOrdersTupList.append(rawOrdersTup)

            endCursor, hasNextPage = get_orders_cursor_items(res)
            if not hasNextPage:
                break
            req = orig_req.replace('END_CURSOR_HERE', endCursor)

        memusage_at_exit = tracemalloc.get_traced_memory()[0]
        delta_memusage = memusage_at_exit - memusage_at_entry
        msg = '\ntot memusage at exit from AccessShopify.shopifyOrdersFromGraphQL after raw shopify data is loaded : {0}, delta memusage in this function:{1}\n'
        print(msg.format(memusage_at_exit,delta_memusage))
        return

    def convertShopifyOrdersToRacOrders(self):

        # 12/27/2024. this function called by Orders, NEAFVendor and DoorPrize classes. Each of those classes implements their own self.append_to_shopifyTup_dict function.

        # 12/30/2022. this function populates self.raw from self.rawOrdersTupList which was built in previous call to shopifyOrdersFromHttps.
        #             iterate through self.rawOrdersTupList and populate st_dict which is passed to self.append_to_shopifyTup_dict.

        # key for collection of self.raw is order_num which is also distinct identifier in raw json result
        # if in NEAF vendor management tool a given company could have multiple orders. sum those orders together under the company later.

        smallest_order_num = 9999999
        largest_order_num = 0

        if self.error:
            # if pre-existing error from shopifyOrdersFromHttps do nothing.
            return
        response_dict = {}
        del self.refundNotes[:]
        self.excludedCovidSkuOrdersDict.clear()
        i = 0

        # 2/2/2023. debug controls the print of debug info in get_shopifyCommonTup_list and get_shopifyCommonTup_list_graphql
        debug = False
        # 2/12/2025. lineItemCount is count of number of line items that are turned into ShopifyCommonTup objects in get_shopifyCommonTup_list and get_shopifyCommonTup_list_graphql.
        lineItemCount = 0

        for rawOrdersTup in self.rawOrdersTupList:
            i += 1
            page = rawOrdersTup.page
            raw_orders_count = rawOrdersTup.raw_orders_count
            orders = rawOrdersTup.orders

            sctList = []
            if USE_GRAPHQL[0]:
                # 1/2/2025. get_shopifyCommonTup_list where we convert self.rawOrdersTupList which is in shopify form straight from the webservice to list of ShopifyCommonTup
                #           objects in sctList which is close to final form and
                #           has been reduced in size by filtering requested skus specified by sku_key.
                #           self.order_to_debug exist then sctList is further reduced to just lineitems in that order.
                #           The critical function that converts ShopifyCommonTup to final form specific to each class is self.append_to_shopifyTup_dict which after this function.
                #           To dump brief summary of every line item included ShopifyCommonTup pass in debug as True.
                error,found_order_to_debug,lineItemCount = get_shopifyCommonTup_list_graphql(orders,self.neaf_year_raw,self.sku_key,self.order_to_debug,sctList,self.refundNotes,
                                                                                     self.note_attributes_Notes,self.excludedCovidSkuOrdersDict,debug,lineItemCount,self.verbose)
            else:
                # 12/30/2022. get_shopifyCommonTup_list where we convert self.rawOrdersTupList which is in shopify form straight from the webservice to list of ShopifyCommonTup
                #             objects in sctList which is close to final form and
                #             has been reduced in size by filtering requested skus specified by sku_key.
                #             self.order_to_debug exist then sctList is further reduced to just lineitems in that order.
                #             The critical function that converts ShopifyCommonTup to final form specific to each class is self.append_to_shopifyTup_dict which after this function.
                #             To dump brief summary of every line item included ShopifyCommonTup pass in debug as True.
                error,found_order_to_debug,lineItemCount = get_shopifyCommonTup_list(orders,self.neaf_year_raw,self.sku_key,self.order_to_debug,self.created_at_max,sctList,self.refundNotes,
                                                                                     self.note_attributes_Notes,self.excludedCovidSkuOrdersDict,debug,lineItemCount,self.verbose)
            if error:
                self.error = error
                return None,None

            st_dict = {}
            for sct in sctList:
                # 1/15/2023. append_to_shopifyTup_dict is implemented in each class that derives from AccessShopify and is responsible for much of the polymorphism of this class heirarchy.
                #            so far the classes AccessOrders, DoorPrize and NEAFVendor implement append_to_shopifyTup_dict.
                #            append_to_shopifyTup_dict sums all the line items in sct to orders under st_dict
                self.append_to_shopifyTup_dict(st_dict, sct)

            for st in st_dict.values():
                apply_discount(st_dict, st.order_num)

            if self.error:
                return
            self.total_raw_orders_count += raw_orders_count
            response_dict.update(st_dict)
            if st_dict:
                first_key,first_date,last_key,last_date = get_st_dict_stats(st_dict)
                range_msg = ' orders range from #{0}/{1} to #{2}/{3}.'.format(first_key,first_date,last_key,last_date)
                smallest_order_num = min(smallest_order_num, first_key)
                largest_order_num = max(largest_order_num, last_key)
            else:
                range_msg = ''
            self.last_page_comment = 'Processing page {0} with {1} orders. {2} orders of sku_key {3} found. {4} orders of sku_key {3} found in {5} total orders so far.{6}'
            self.last_page_comment = self.last_page_comment.format(page,raw_orders_count,len(st_dict),self.sku_key,len(response_dict),self.total_raw_orders_count,range_msg)
            self.print_and_save(self.last_page_comment,always_print=True,verbose=True)

        if self.excludedCovidSkuOrdersDict:
            self.print_and_save('\nIn AccessShopify.convertShopifyOrdersToRacOrders the following orders for these COVID skus were skipped:\n')
            numOrdersSkipped = 0
            for sku,orders in self.excludedCovidSkuOrdersDict.items():
                nos = len(orders)
                numOrdersSkipped += nos
                self.print_and_save('{0} orders skipped for COVID sku {1}:\n{2}'.format(nos,sku,','.join(orders)))
            self.print_and_save('Total COVID sku orders skipped:{0}\n'.format(numOrdersSkipped))

        if self.refundNotes:
            self.print_and_save('\nIn AccessShopify.convertShopifyOrdersToRacOrders the following {0} refunds were made:\n'.format(len(self.refundNotes)))
            for refundNote in self.refundNotes:
                self.print_and_save('{0}'.format(refundNote))
            self.print_and_save('\n')

        if self.verbose:

            if self.note_attributes_Notes:
                msg = '\nIn AccessShopify.convertShopifyOrdersToRacOrders verbose:{0} the following {1} note_attributes were found:\n'
                self.print_and_save(msg.format(self.verbose,len(self.note_attributes_Notes)))
                for note_attributes_note in self.note_attributes_Notes:
                    self.print_and_save('{0}'.format(note_attributes_note))

            msg = '\nIn AccessShopify.convertShopifyOrdersToRacOrders verbose:{0}. Displaying all {1} shopify items to be processed. They have been reduced by requested skus and created_at_min.\n'
            self.print_and_save(msg.format(self.verbose,len(response_dict)))

            cnt = 0
            for key,dpt in list(response_dict.items()):
                cnt += 1
                self.print_and_save('{0}: key:{1} {2}'.format(cnt,key,dpt))

            self.print_and_save('\n')

        for order_num,nvt in response_dict.items():
            self.raw[order_num.strip()] = nvt

        for order_num,nvt in self.raw.items():
            self.order_id_to_order_num_map[nvt.order_id] = order_num

        print('\nmemory usage at exit from AccessShopify.convertShopifyOrdersToRacOrders: {0}\n'.format(tracemalloc.get_traced_memory()[0]))
        return smallest_order_num,largest_order_num

def main():
    
    # some sample shopify queries other than orders, not that interesting.
    '''
    response = requests.get( 'https://%s.myshopify.com/admin/products/count.json' % SHOP_NAME,
                               auth=(API_KEY,PASSWORD))   
    print response.text  
    response = requests.get( 'https://%s.myshopify.com/admin/orders/count.json' % SHOP_NAME,
                               auth=(API_KEY,PASSWORD))   
    if response.status_code != 200:
        print 'Failure, response.status_code is {0}'.format(response.status_code)                         
    print response.text      
    # max response size is 250. have to read pages after that.   
    response = requests.get( 'https://%s.myshopify.com/admin/orders.json?since_id=3010' % SHOP_NAME,
                               auth=(API_KEY,PASSWORD)) 
    text1 = response.text                           
    print response.status_code 
    req = 'https://%s.myshopify.com/admin/orders.json?updated_at_min=2015-02-01 00:00:01 EDT -04:00' % SHOP_NAME
    response = requests.get(req,auth=(API_KEY,PASSWORD))     
    print response.status_code    
    text2 = response.text  '''
    
    # look at doc C:\Users\joe1\rac\ecommerce\docs\shopify_api_json_schema.txt on 76 Lime Kiln computer for details on 
    # schema for orders .  small modification to build_door_prize_dict_from_shopify and get_doorPrizeTup_dict should 
    # support processing of NEAF vendor orders.
    
    #reqstr = 'https://%s.myshopify.com/admin/orders.json?' +\
    #    'fields=created_at,id,name,customer,line_items&limit=250&page=1&created_at_min=2014-10-01 00:01'


    order_id = 1980097560658 # test order #9130 for Joe's dumb ass scopes
    #order_id = 1974718529618 # order #9129 for photonic cleaning
    order_id = 2144708198482 # order #9481 for nimax with partial refund an cancel
    order_id = 2144844677202 # order #9483 also for nimax, partial refunds
    order_id = 5060039639122 # order 13167 for Donald A Kaplan buying membership at club table for NEAF 2023 using POS
    order_id = 6208463405138 # order 15568 for Celestron with NEAF Vendor Payment of $1450 with bad  'note_attributes': [{'name': '1 - NEAF Vendor Payment', 'value': ''}]
    #order_id = '6234913341522' # order 15713 for NEAIC with no note_attribute items of []

    #reqstr = 'https://{0}.myshopify.com/admin/orders/{1}.json'
    reqstr = 'https://{0}.myshopify.com/admin/api/2019-10/orders/{1}.json'
    req = reqstr.format(SHOP_NAME,order_id)
    response = requests.get(req,auth=(API_KEY_RW,PASSWORD_RW))
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
    r = requests.put(url=req, data=note_update, auth=(API_KEY_RW,PASSWORD_RW),headers = r_headers)

    return

#main()

def change_note_update():

    # 12/19/2022. this function used to change note_attributes from

    # [{NOTE_ATTRIBUTE_KEY(): 'Badge_Name_1', 'value': 'bob smith'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_2', 'value': 'john dow'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_3', 'value': 'Billy Bob'},
    # {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_4', 'value': 'Richard Nixon'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_5', 'value': 'Spiro Agnew'}]

    # to

    # [{NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'bob smith'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'john dow'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'Billy Bob'},
    # {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'Richard Nixon'}, {NOTE_ATTRIBUTE_KEY(): 'Badge_Name_9426', 'value': 'Spiro Agnew'}]

    order_id = 2129787781202
    order_id = 6208463405138  # order 15568 for Celestron with NEAF Vendor Payment of $1450 with bad  'note_attributes': [{'name': '1 - NEAF Vendor Payment', 'value': ''}] changes to []

    reqstr = 'https://{0}.myshopify.com/admin/api/2019-10/orders/{1}.json'
    req = reqstr.format(SHOP_NAME, order_id)

    note_dict = {"order": {"id": order_id, "note_attributes": [{"name": "Badge_Name_9426_1", "value": "bob smith"}, {"name": "Badge_Name_9426_2", "value": "john dow"},
                                                               {"name": "Badge_Name_9426_3", "value": "Billy Bob"}, {"name": "Badge_Name_9426_4", "value": "Richard Nixon"},
                                                               {"name": "Badge_Name_9426_5", "value": "Spiro Agnew"}]
                }}

    note_dict = {"order": {"id": order_id, "note_attributes": []
                }}


    note_update = json.dumps(note_dict)
    r_headers = {'Content-Type': 'application/json'}
    r = requests.put(url=req, data=note_update, auth=(API_KEY_RW, PASSWORD_RW), headers=r_headers)

    return

#change_note_update()
#main()
#build_door_prize_dict_from_shopify(verbose=True)