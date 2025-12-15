import pprint
from consts import SKUS_TO_LOAD_DICT,ALL,MEMBERSHIP,REFUND,ShopifyCommonTup,MISSING,FAILED_REFUND,USE_GRAPHQL
from utils import remove_unicode,getItem,normalize_phone_num
from get_shopifycommon_tup_list_utils import skipExcludedCovidSkuOrders,show_ShopifyCommonTup_list,build_skus_refunded,get_ShopifyCommonTup_highest_price,convert_ShopifyCommonTup_to_refund
from order_events import get_phone_or_email_from_order_event_timeline


def date_beyond_max(dt,dt_max):
    toks = dt.split('T')
    return toks[0] > dt_max

def get_discount_codes(order):
    discount_codes = ''
    dcodes = order['discount_codes']
    for dcode in dcodes:
        code = dcode['code']
        discount_codes += ', '+code if discount_codes else code
    return discount_codes

def getName(item_dict):
    first_name = getItem(item_dict, 'first_name')
    last_name = getItem(item_dict,'last_name')
    if first_name and last_name:
        name = first_name+' '+last_name
    elif not first_name and not last_name:
        name = MISSING
    elif first_name:
        name = first_name
    elif last_name:
        name = last_name
    if not first_name:
        first_name = MISSING
    if not last_name:
        last_name = MISSING
    return name,first_name,last_name

def get_shopifyCommonTup_list(orders,neaf_year_raw,sku_key,order_to_debug,created_at_max,sctList,refundNotes,note_attributes_Notes,excludedCovidSkuOrdersDict,debug,lineItemCount,verbose):

    # 12/30/2022. this function is where we convert AccessShopify.rawOrdersTupList(passed in here as orders) which is in shopify form straight from the webservice to ShopifyCommonTup
    #             which is close to final form and has been reduced in size by filtering requested skus specified by sku_key.
    #             The critical function that converts ShopifyCommonTup to final form specific to each class is self.append_to_shopifyTup_dict which is called after this function.
    #             To dump brief summary of every line item included in ShopifyCommonTup pass in debug as True. if order_to_debug exists then force debug to True.
    #             refundNotes is purely information when investigating refunds. It's dumped to logs and console.
    #             note_attributes_Notes is used to collect all note_attributes and display for informational purposes.

    error = ''
    found_order_to_debug = None
    if not order_to_debug:
        skus_to_load = SKUS_TO_LOAD_DICT.get(sku_key)
        if not skus_to_load:
            error = 'Failure in get_shopifyCommonTup_list. No item in SKUS_TO_LOAD_DICT for sku_key:{0}.'.format(sku_key)
            return error,found_order_to_debug,lineItemCount
    else:
        debug = True
    i = 0

    # 2/17/2025. order_to_debug can be single order if form '15468' or multiple orders like '15302|15303' for 10 Micron and Woodland Hills
    order_to_debug_list = str(order_to_debug).split('|') if order_to_debug else []

    sct = None # 2/9/2025. this line serves no point but it might help lessen wacky pycharm exceptions.
    for order in orders:
        i += 1
        order = remove_unicode(order)
        # order_id is internal shopify identifier for an order like 1980097560658 for order #9130.
        order_id = str(order['id'])
        order_num = order['name']
        # if not i % 50:
        #     print('i:{0}  order_num:{1}  memusage:{2}'.format(i,order_num,tracemalloc.get_traced_memory()[0]))
        if order_num.startswith('#'):
            order_num = order_num[1:]

        if order_to_debug:
            if order_num not in order_to_debug_list:
                continue
            if order_num in order_to_debug_list:
                found_order_to_debug = True

        created_at = order['created_at']
        if date_beyond_max(created_at,created_at_max):
            continue
        note = '' if not order['note'] else order['note']
        note_attributes = {} if not order.get('note_attributes') else order['note_attributes']
        if not order.get('customer'):
            #print 'failed loading order',i
            #print order
            #continue
            pass
        customer = order.get('customer',{})
        if customer is None:
            # 1/26/2024. needed this for order_num 12904
            customer = {}
        total_discount = float(order['total_discounts'])
        discount_codes = get_discount_codes(order)

        name,first_name,last_name = getName(customer)
        billing_address = order.get('billing_address', {})
        name_ba, first_name_ba, last_name_ba = getName(billing_address)
        if first_name == MISSING or last_name == MISSING:
            # 2/12/2024. added this block for order #13735 which had customer name as 'Handler' but Billing address name is 'Gene Handler'.
            if first_name == MISSING and first_name_ba != MISSING:
                first_name = first_name_ba
            if last_name == MISSING and last_name_ba != MISSING:
                last_name = last_name_ba
            name = first_name + ' ' + last_name

        email =  getItem(customer,'email')
        default_address = customer.get('default_address',{})
        if not default_address:
            #print 'i',i
            #print 'invalid order, skip',customer
            #continue
            pass
        province_code = default_address.get('province_code') or MISSING
        country_code = default_address.get('country_code') or MISSING

        phone_num = normalize_phone_num(getItem(default_address,'phone'))
        refunds = order['refunds'] if order['refunds'] else []
        line_items = order['line_items']
        skus_refunded,refund_note,refund_created_at,note = build_skus_refunded(order_num,refunds,line_items,note,debug)

        if refund_note:
            if FAILED_REFUND in refund_note:
                # 2/3/2025. only known example that takes this block is #9255
                msg = '{0}: order {1} for {2} / {3}. Date(s) of failed refund is {4}.\nRefund Note:\n{5}'
                msg = msg.format(len(refundNotes) + 1, order_num, name, email, refund_created_at,refund_note)
            else:
                msg = '{0}: order {1} for {2} / {3}. There was refund for these skus and quantities:{4}. Date(s) of refund is {5}.\nRefund Note:\n{6}'
                msg = msg.format(len(refundNotes)+1,order_num,name,email,skus_refunded,refund_created_at,refund_note)
            refundNotes.append(msg)

        if note_attributes:
            msg = '{0}: order:{1}, order_id:{2} for {3} / {4}\nnote_attributes:\n{5}'
            msg = msg.format(len(note_attributes_Notes)+1,order_num, order_id, name, email, note_attributes)
            note_attributes_Notes.append(msg)

        found_valid_line_item = False
        for line_item in line_items:
            sku = line_item['sku'] if line_item['sku'] else MISSING

            if order_num == '15252' and line_item['id'] == 14821595742290:
                # 1/8/2024. weird hack for only order #15252 for zwo. I forgot to enter sku for $2000 live stream ad. I added sku neaf_vendor_sponsor_live_steam after purchase made
                #           but its too late. Its not showing up under this order. just set the sku here.
                sku = 'neaf_vendor_sponsor_live_steam'

            quantity = line_item['quantity']

            if sku_key == MEMBERSHIP:
                # TODO 12/29/2024. this block looks odd. it might not be needed since I now support tuple for DONATION:('rac_donation','admin_donation') below.
                if skus_to_load[0] not in sku and skus_to_load[1] not in sku:
                    continue
                else:
                    # 1/26/2024. we have found valid membership order but no concept of discount for membership so just use 0. example is order_num 13657.
                    discount_allocations = 0.0
                    if not email and not phone_num:
                        email, phone_num = get_phone_or_email_from_order_event_timeline(order_id)

            else:

                # ****************************** REJECT INVALID SKUS HERE *********************************

                if sku_key != ALL and not order_to_debug:
                    # 1/8/2025. just added clause on not order_to_debug. That's because if debugging an entire order then not processing a single sku_key. rather we are processing all
                    #           skus in the given order to debug.
                    # 3/30/2023. if we are requesting all skus never skip any of them in this block.
                    valid_sku = False
                    for sku_to_load in skus_to_load:
                        if sku.startswith(sku_to_load):
                            valid_sku = True
                            break
                    if not valid_sku:
                        # we are processing a sku not in the target list. move on
                        continue

                if order_num == ' 9125':
                    # TODO 1/30/2022. this block is TEMPORARY. we lost dispute with Matrix Astro Products on this order and they were given refund by Shopify. figure out programatic
                    #                 way to determine lost disputes and then add to invoice.
                    #      2/4/2025   no evidence in rester api of customer disputes. Can find it in graphql in customerSegmentMembership
                    continue

                if skipExcludedCovidSkuOrders(neaf_year_raw,sku_key,sku,customer,created_at,order_num,excludedCovidSkuOrdersDict):
                    continue
                if sku in skus_refunded:
                    quantityRefunded = skus_refunded.get(sku)
                    if quantityRefunded == quantity:
                        # 2/6/2025. sku has been refunded in full, its gone. we want to retain some evidence of the disappeared sku so modify display of sku string to indicate
                        #           how many items are now gone. some examples are #7618, #9481, #11709.
                        quantity = 0
                        sku = '{0} {1}:{2}'.format(REFUND,quantityRefunded,sku)
                        line_item['sku'] = sku
                    else:
                        # 3/7/2020. refund for partial quantity. decrease quantity by amount refunded. example is #9483.
                        quantity -= quantityRefunded

                discount_allocations = 0.0
                da_list = line_item.get('discount_allocations')
                if da_list:
                    # 4/1/2023. example is order_num 9141 for Astronomers Without Borders. there are 3 line items. each has discount_allocations list of size 1. first one is
                    # [{'amount': '175.50', 'amount_set':
                    # {'shop_money': {'amount': '175.50', 'currency_code': 'USD'},
                    # 'presentment_money': {'amount': '175.50', 'currency_code': 'USD'}},
                    # 'discount_application_index': 0}]
                    # god knows if we can always count on this format.
                    discount_allocations = float(da_list[0]['amount']) if da_list[0].get('amount') else 0.0

            found_valid_line_item = True
            sct = ShopifyCommonTup(order_id,order_num,created_at,note,note_attributes,customer,total_discount,discount_codes,discount_allocations,name,first_name,last_name,email,default_address,
                                   province_code,country_code,phone_num,sku,quantity,refund_note,refund_created_at,line_item)
            # 2/12/2025. lineItemCount is count of number of line items that are turned into ShopifyCommonTup objects.
            lineItemCount += 1

            if order_num == 'XXX': # 2/27/2023. previously was string of '9130'. can use this block for low-tech debugging.
                sct_d = dict(sct._asdict())
                if verbose:
                    msg = pprint.pformat(sct_d,width=200)
                    print(msg)
            if sct:
                sctList.append(sct)
            else:
                print("\n\n***********************  WARNING ****************************\nsct is None. That's impossible if python is working. SHIT!\norder:\n{0}\n".format(order))

        if found_valid_line_item and REFUND in skus_refunded:
            # 2/6/2025. special treatment is needed for refunds on this order, order_num. Typically refunds can be applied to single line items in an order. Not in this case.
            #           apply the dollarsRefunded to the entire order. add additional ShopifyCommonTup to sctList for the negative amount of refund. example is #15314.
            dollarsRefunded = skus_refunded[REFUND]
            sct = get_ShopifyCommonTup_highest_price(order_num,sctList)
            sct = convert_ShopifyCommonTup_to_refund(dollarsRefunded,sct)
            sctList.append(sct)

    if debug:
        desc = show_ShopifyCommonTup_list(sctList)
        print('\n' + desc + '\n')

    # TODO 12/31/2022. some super weird shit is happening. I'm getting an occasional mysterious exception of
    #                  Process finished with exit code -1073741819 (0xC0000005)
    #                  It only happens in debug mode with the UI and it happens at exit from this function. I had a whole bunch of cosmetic refactoring that seemed to slightly drop the
    #                  frequency of this exception but it won't go away. a work around seems to be to set a BP at the return and just continue. Its not that annoying since this
    #                  function is passed order lists of size 250 so I break here 11 times.
    return error,found_order_to_debug,lineItemCount

