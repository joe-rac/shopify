import pprint
from consts import SKUS_TO_LOAD_DICT,ALL,MEMBERSHIP,REFUND,ShopifyCommonTup,MISSING,FAILED_REFUND
from utils import remove_unicode,getItem,normalize_phone_num,convert_utc_to_local_datetime
from get_shopifycommon_tup_list_utils import skipExcludedCovidSkuOrders,show_ShopifyCommonTup_list,refund_desc,get_ShopifyCommonTup_highest_price,convert_ShopifyCommonTup_to_refund
from get_shopifycommon_tup_list_utils import _buildRefundNote,refunds_list_desc,get_line_item_TOTAL_to_sku_quantity_map,_buildRefundLineItemsDesc
from order_events import get_phone_or_email_from_order_event_timeline

def get_line_item(line_items,sku):
    for li in line_items:
        if li['sku'] == sku:
            return li
    raise Exception('Failure in get_line_item. Cannot find sku:{0} in passed in line_items of size {1}.'.format(sku,len(line_items)))
    return

def get_refund_line_items_dollarsRefunded_and_desc(refund_line_items,line_items):
    refund_line_items_dollarsRefunded = 0
    refund_line_items_desc = ''
    for rli in refund_line_items:
        li = rli['lineItem']
        quantity = rli.get('quantity')
        line_item = get_line_item(line_items, li.get('sku'))
        price = round(float(li['originalUnitPrice']))
        refund_line_items_dollarsRefunded += quantity * price
        refund_line_items_desc = _buildRefundLineItemsDesc(refund_line_items_desc, rli, line_item=line_item)
    return refund_line_items_dollarsRefunded,refund_line_items_desc

def build_skus_refunded_graphql(order_num,refunds_list,line_items,note,debug):

    # 2/14/2025. the refunds inside each refunds_list element fall into 5 categories.

    # 1) each refund_line_items refunds an entire line item. totalRefundedSet is negative number for dollars refunded.
    #    #8948, #9481(refund_line_items[0] and refund_line_items[1]), #9541, #9404, #13695, #13712, #13415, #7618

    # 2) refund_line_items exist but totalRefundedSet is 0. There was some failure when trying to grant refund.
    #    #9255, #9481(refund_line_items[2])

    # 3) dollars of refund in order_adjustments exactly equal and opposite to 1 line item. no refund_line_items. refund that line item.
    #    #10638, #9239, #11709

    # 4) dollars of refund in totalRefundedSet does not match any line item but is <= dollars of entire order. no refund_line_items. refund dollars to order, don't refund a specific sku.
    #    #15317

    # 5) failure to categorize. this is a bug and needs repair. No sample orders so far for this use case.


    # some examples of refunds:

    # Amateur Astronomers Assoc. of Pittsburgh, #15317(1/19/2025). refund of $306 to whole order
    # for SSP Travis Adams, #8948, had refund_line_items of membership refunded but kept SSP chicken barbecue lineitem.
    # company is AAPOD2. #10638. dollars on order. refunded full $20 on logo and link
    # dollars on order. software bisque. #9239. refunded $50 on badge.
    # a full refunded order for IOptron #11709 for $2612.
    # Rowan Engineering. #9255. attempted but failed refund of entire order of $534
    # Nimax refunded 3/6/2020. #9481. table went from 5 to 2 for $165 refunded. chairs went 4 to 2 for $24 refunded. refund 2 badges for $100. failed to refund $128 years later on 4/14/2023.
    # Software Bisque had 2 orders, 13704|13695. has company name and badge name edits. only 13695 had refund. $1130 for 2 booths out of $2178 total refunded
    # Explore Scientific had 2 orders, 13712|13717. refunded 8 standard booths in 13712 and he bought 8 premium in 13717.
    # Airy Disk. #13415. full refund of $1442 then another order with pay by check.
    # Don Spong. #9541. refund of NEAF Virtual Experience ticket.
    # Nimax. #9404. refunded $402, full order refunded. intent was standard booth, not premium.
    # QHYCCD. #7618. full refund.

    # 2/6/2025. unfortunately semantics of the skus_refunded dict takes 2 forms. typically for cases 1) to 3) the key is sku getting refund and value is the quantity of the given sku being refunded.
    #           for case 4) the key is REFUND and the value is dollars refunded to entire order because refund can't be ascribed to a single sku.
    skus_refunded = {}

    refund_note = ''
    refund_created_at = ''

    if not refunds_list:
        return skus_refunded, refund_note, refund_created_at, note

    desc = refunds_list_desc(order_num,line_items,refunds_list)
    if debug:
        print(desc)
    line_item_TOTAL_to_sku_quantity_map = get_line_item_TOTAL_to_sku_quantity_map(line_items)

    for r_ind,refunds in enumerate(refunds_list):

        rca = getItem(refunds,'createdAt')
        rca = convert_utc_to_local_datetime(rca)
        rca = rca[:10] if rca else rca
        refund_created_at = (refund_created_at if rca in refund_created_at else refund_created_at+'|'+rca) if refund_created_at else rca
        r_note = getItem(refunds,'note')
        refund_note = _buildRefundNote(refund_note, r_note)

        if not refunds:
            # 2/5/2025. I have no use case for this block but this old check on existence of refunds has been around for a long time so just keep it.
            refund_note = _buildRefundNote(refund_note,'For order_num:{0} found invalid element refunds_list[{1}]:{2} for len(refunds_list):{3}'.format(order_num,r_ind,refunds,len(refunds_list)))
            continue

        # 2/3/2025. the 2 major data structures for describing refunds are set here: refund_line_items or totalRefundedSet.
        refund_line_items = refunds.get('refundLineItems')
        # TODO 2/11/2025. the half assed negative sign is for backward compatibility with rester which had -306 for #15137. In future consider retaining original sign.
        totalRefundedSet = -round(float(refunds['totalRefundedSet']['shopMoney']['amount']))

        refund_line_items_dollarsRefunded,refund_line_items_desc = get_refund_line_items_dollarsRefunded_and_desc(refund_line_items, line_items)
        if not refund_note:
            # 2/7/2025. typically I have the presense of mind to enter note when granting refund but I didn't do that for #13712 so do this.
            refund_note = refund_line_items_desc

        if refund_line_items_dollarsRefunded and not totalRefundedSet:

            # 2/5/2025. this block for sub-category 2). These refunds were not delivered to customer and shopify represents these failures poorly.

            refund_note = _buildRefundNote(refund_note,'WARNING: REFUNDS OF {0} NOT CORRECTLY DISPLAYED.'.format(refund_line_items_desc))

        elif refund_line_items_dollarsRefunded == -totalRefundedSet:

            # 2/5/2025. this block for sub-category 1) for processing of normal refunds.

            for rli in refund_line_items:
                skus_refunded[rli['lineItem']['sku']] = rli['quantity']

        elif not refund_line_items and totalRefundedSet < 0:
            sku_quantity_toks = line_item_TOTAL_to_sku_quantity_map.get(-totalRefundedSet)
            sku_quantities = sku_quantity_toks.split('|') if sku_quantity_toks else []

            if len(sku_quantities) == 1:
                sku = sku_quantities[0].split('/')[0]
                quantity = int(sku_quantities[0].split('/')[1])
            else:
                sku = None

            if sku:

                # 2/5/2025. this block for sub-category 3). assume a complete refund of the line item with sku.

                skus_refunded[sku] = quantity

            else:

                # 2/5/2025. this block for sub-category 4). assigns these dollars of refunds to entire order.

                skus_refunded[REFUND] = totalRefundedSet

        else:

            # 2/5/2025. this block for sub-category 5). is for a failure to match any of the 5 sub-categories. No use cases so far.

            desc = refund_desc(r_ind, refunds)
            print('order_num',order_num,'desc',desc)
            refund_note = _buildRefundNote(refund_note, 'FAILURE PROCESSING:\n{0}'.format(desc))

    return skus_refunded, refund_note, refund_created_at, note

def improve_events_and_get_items(events):
    ev_email = None
    ev_phone_num = None
    for ev in events:
        ev['createdAt'] = convert_utc_to_local_datetime(ev['createdAt'])
        mes = ev['message']
        # 2/18/2025. parse messages like this:
        #            for #13167. 'message': 'Joe Moskowitz sent a pos and mobile receipt SMS to Donald A Kaplan (+1 917-696-4343).'},
        #            for #13136. 'message': 'Joe Moskowitz sent an order receipt email to James A Myruski (astrojim1@live.com).'},
        if 'receipt email' in mes and '(' in mes and ')' in mes:
            ev_email = mes[mes.index('(')+1:mes.index(')')]
        if 'receipt SMS' in mes and '(' in mes and ')' in mes:
            ev_phone_num = mes[mes.index('(')+1:mes.index(')')]
            ev_phone_num = normalize_phone_num(ev_phone_num)
    return ev_email,ev_phone_num

def get_discount_codes(order):
    dcodes = order['discountCodes'] # 1/2/2025. previously was discount_codes
    return ', '.join(dcodes)

def getName(item_dict):
    first_name = getItem(item_dict, 'firstName') # 1/2/2025. previously was first_name
    last_name = getItem(item_dict,'lastName') # 1/2/2025. previously was last_name
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

def getBestAddress(addresses):

    # 1/3/2025. example for how this function works is #15172 for Hutech company. addresses passed in has 6 elements. address returned is
    #           {'address1': '25691 Atlantic Ocean Dr.,', 'address2': 'Unit B-17', 'city': 'Lake Forest', 'province': 'California', 'country': 'United States', 'phone': '(949) 859-5511',
    #           'company': 'Hutech Corporation'}

    address = {}

    addr_items_to_list = {}
    for adr in addresses:
        for item,v in adr.items():
            if v is None: v = ''
            lst = addr_items_to_list.get(item,[])
            if not lst:
                addr_items_to_list[item] = lst
            lst.append(v)

    for item_key,lst in  addr_items_to_list.items():
        item_to_cnt_map = {}
        for item in lst:
            item_to_cnt_map[item] = item_to_cnt_map.get(item,0) + 1
        if len(item_to_cnt_map) > 1 and '' in  item_to_cnt_map:
            # 2/28/2025. added this block for #15569. It had item_to_cnt_map of {'': 3, '(848) 248-0424': 1, '8482480424': 1} for item_key:'phone'
            #            the most common valyue is blank but we don't want to choose that one.
            del item_to_cnt_map['']
        max_cnt = max(item_to_cnt_map.values())
        items_with_max_cnt = []
        for item,cnt in item_to_cnt_map.items():
            if item is None: item = ''
            if cnt == max_cnt:
                items_with_max_cnt.append(item)
        if len(items_with_max_cnt) == 1:
            address[item_key] = items_with_max_cnt[0] if items_with_max_cnt[0] else ''
        else:
            items_with_max_cnt = sorted(items_with_max_cnt)
            max_len = max( [len(i) for i in items_with_max_cnt] )
            for item in items_with_max_cnt:
                if len(item) == max_len:
                    address[item_key] = item if item else ''

    return address

def get_shopifyCommonTup_list_graphql(orders,neaf_year_raw,sku_key,order_to_debug,sctList,refundNotes,note_attributes_Notes,excludedCovidSkuOrdersDict,debug,lineItemCount,verbose):

    # 12/30/2022. this function is where we convert AccessShopify.rawOrdersTupList(passed in here as orders) which is in shopify form straight from graphql to ShopifyCommonTup which is close to final form.
    #             The critical function that converts ShopifyCommonTup to final form specific to each class is self.append_to_shopifyTup_dict which is called after this function.
    #             To dump brief summary of every line item included in ShopifyCommonTup pass in debug as True. if order_to_debug exists then force debug to True.
    #             refundNotes is purely information when investigating refunds. It's dumped to logs and console.
    #             note_attributes_Notes is used to collect all customAttributes and display for informational purposes.

    error = ''
    found_order_to_debug = None
    if not order_to_debug:
        skus_to_load = SKUS_TO_LOAD_DICT.get(sku_key)
        if not skus_to_load:
            error = 'Failure in get_shopifyCommonTup_list_graphql. No item in SKUS_TO_LOAD_DICT for sku_key:{0}.'.format(sku_key)
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
        # order_id is internal shopify identifier for an order like gid://shopify/Order/1980097560658 for order #9130.
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
        created_at = order['createdAt'] # 1/2/2025. previously was created_at in rester api.
        created_at = convert_utc_to_local_datetime(created_at)
        canceled_at = order['canceledAt'] # 1/2/2025. previously was created_at in rester api.
        canceled_at = convert_utc_to_local_datetime(canceled_at)
        note = '' if not order['note'] else order['note']
        note_attributes = order['customAttributes'] # 1/2/2025. previously was note_attributes in rester api.
        if not order.get('customer'):
            #print 'failed loading order',i
            #print order
            #continue
            pass
        customer = order['customer']
        if customer is None:
            # 1/26/2024. needed this for order_num 12904
            customer = {}
        total_discount = float(order['currentTotalDiscountsSet']['shopMoney']['amount'])  # 1/2/2025. previously was total_discounts
        discount_codes = get_discount_codes(order)

        name,first_name,last_name = getName(customer)
        billing_address = order['billingAddress'] # 1/2/2025. previously was billing_address.
        name_ba, first_name_ba, last_name_ba = getName(billing_address)
        if first_name == MISSING or last_name == MISSING:
            # 2/12/2024. added this block for order #13735 which had customer name as 'Handler' but Billing address name is 'Gene Handler'.
            if first_name == MISSING and first_name_ba != MISSING:
                first_name = first_name_ba
            if last_name == MISSING and last_name_ba != MISSING:
                last_name = last_name_ba
            name = first_name + ' ' + last_name

        email =  getItem(customer,'email')
        # 7/9/2025. when loading for membership order #16445 had customer of {} so need to test for missing 'addresses'. this is one of those invalid NEAF orders placed by
        #           tap & chip where we lost all purchaser info.
        default_address = getBestAddress(customer.get('addresses',{})) # 1/2/2025. previously was default_address
        if not default_address:
            #print 'i',i
            #print 'invalid order, skip',customer
            #continue
            pass
        province_code = default_address.get('province',MISSING) # 1/3/2025. previously was province_code
        country_code = default_address.get('country',MISSING) # 1/3/2025. previously was country_code

        phone_num = normalize_phone_num(getItem(default_address,'phone'))
        ev_email,ev_phone_num = improve_events_and_get_items(order['events'])
        email = email or ev_email
        phone_num = phone_num or ev_phone_num or ''
        refunds = order['refunds']
        line_items = order['lineItems'] # 1/2/2025. previously was line_items
        skus_refunded,refund_note,refund_created_at,note = build_skus_refunded_graphql(order_num,refunds,line_items,note,debug)

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

            if order_num == '15252' and line_item['id'].endswith('14821595742290'):
                # 1/8/2024. weird hack for only order #15252 for zwo. I forgot to enter sku for $2000 live stream ad. I added sku neaf_vendor_sponsor_live_steam after purchase made
                #           but its too late. Its not showing up under this order. just set the sku here.
                sku = 'neaf_vendor_sponsor_live_steam'

            quantity = line_item['quantity']

            if sku_key == MEMBERSHIP:

                # TODO 1/2/2025. this block doesn't look meaningful since only purpose might have been to handle
                #                MEMBERSHIP:('rac_membership','rac_magazine') in SKUS_TO_LOAD_DICT which is atypical because it has 2 values.
                #                it might not be needed.

                if skus_to_load[0] not in sku and skus_to_load[1] not in sku:
                    continue
                else:
                    # 1/26/2024. we have found valid membership order but no concept of discount for membership so just use 0. example is order_num 13657.
                    discount_allocations = 0.0
                    if not email and not phone_num:
                        # TODO 2/11/2025. WARNING: get_phone_or_email_from_order_event_timeline use rester. its not yet converted to graphql.
                        email, phone_num = get_phone_or_email_from_order_event_timeline(order_id)

            else:

                # ****************************** REJECT INVALID SKUS HERE *********************************

                #  1/2/2025. this block looks odd since you'd think all the filtering on skus would have happened in shopifyOrdersFromGraphQL but there are some subtleties
                #            that are handled here. an example is selecting DONATION. order #11626 has 2 line items with skus rac_donation and rac_membership_family_renew.
                #            unfortunately graphql doesn't support filtering on line items, only on order, so rac_membership_family_renew gets selected. reject it here.
                if sku_key != ALL and not order_to_debug:
                    # 1/8/2025. just added clause on not order_to_debug. That's because if debugging an entire order then not process a single sku_key. we are processing all
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
                da_list = line_item.get('discountAllocations')
                if da_list:
                    # 2/15/2025. example is #15063 for New Jersey Astronomical Association with discount code EDUCATIONAL with discount_allocations of $593.
                    discount_allocations = float(da_list[0]['allocatedAmountSet']['shopMoney']['amount'])

            found_valid_line_item = True
            sct = ShopifyCommonTup(order_id,order_num,created_at,canceled_at,note,note_attributes,customer,total_discount,discount_codes,discount_allocations,name,first_name,last_name,email,
                                   default_address,province_code,country_code,phone_num,sku,quantity,refund_note,refund_created_at,line_item)
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
