import copy
from consts import NEAF_VENDOR,NEAF_YEAR_COVID,COVID_NEAF_VENDOR_SKUS_TO_EXCLUDE,COVID_NEAF_VENDOR_SKUS_TO_EXCLUDE_CONDITIONALLY,USE_GRAPHQL
from consts import VIRTUAL_NEAF_ORDER_RANGE,NEAF_ATTEND,NEAF_VIRTUAL_DOORPRIZE,N_A,MISSING,REFUND
from utils import get_max_len,getItem,NOTE_ATTRIBUTE_KEY,PROPERTIES_KEY

class HTTP_KEYS_RESTER(object):
    created_at = 'created_at'
    refund_line_items = 'refund_line_items'
    order_adjustments = 'order_adjustments'
    discount_codes = 'discount_codes'
    first_name = 'first_name'
    last_name = 'last_name'
    note_attributes = 'note_attributes'
    total_discounts = 'total_discounts'
    billing_address = 'billing_address'
    default_address = 'default_address'
    province_code = 'province_code'
    country_code = 'country_code'
    line_items = 'line_items'

class HTTP_KEYS_GRAPHQL(object):
    created_at = 'createdAt'
    refund_line_items = 'refundLineItems'
    order_adjustments = 'adjustments'
    discount_codes = 'discountCodes'
    first_name = 'firstName'
    last_name = 'lastName'
    note_attributes = 'customAttributes'
    total_discounts = 'currentTotalDiscountsSet' # this one is more complex. we need order['currentTotalDiscountsSet']['shopMoney']['amount']
    billing_address = 'billingAddress'
    default_address = 'addresses'
    province_code = 'province'
    country_code = 'country'
    line_items = 'lineItems'

def skipExcludedCovidSkuOrders(neaf_year_raw,sku_key,sku,customer,created_at,order_num,excludedCovidSkuOrdersDict):

    # TODO 1/29/2022. possibly add created_at logic for neaf_vendor_sponsor_logo_and_link, neaf_vendor_sponsor_ad_and_link which are 2 items in COVID_NEAF_VENDORS_SKUS_TO_EXCLUDE .
    #  we might only want to exlude them if they were bought explicitly for virtual NEAF. 2 examples in orders #9426 and #9277

    skip = 0
    created_at = created_at[:10]
    if sku_key == NEAF_VENDOR and neaf_year_raw == NEAF_YEAR_COVID:
        if sku in COVID_NEAF_VENDOR_SKUS_TO_EXCLUDE:
            # 1/15/2023. special treatment here for NEAF Vendor Management Tool queries for neaf_year of NEAF_YEAR_COVID:'covid'. 'covid' means NEAF 2023 but sum together
            # all NEAF vendor orders from 2020, 2021, 2022 and 2023. however exclude the NEAF Vendor purchases for virtual NEAFs of 2020 and 2021 in COVID_NEAF_VENDORS_SKUS_TO_EXCLUDE.
            skip = 1
        if sku in COVID_NEAF_VENDOR_SKUS_TO_EXCLUDE_CONDITIONALLY and VIRTUAL_NEAF_ORDER_RANGE.neaf_start <= created_at <= VIRTUAL_NEAF_ORDER_RANGE.neaf_end:
            # 1/30/2022. similar special treatment as above block but conditional on being in date range for virtual NEAF
            skip = 1

    if sku_key == NEAF_ATTEND and sku == NEAF_VIRTUAL_DOORPRIZE:
        # TODO 1/19/2023. this block can be eliminated after NEAF 2023. needed to ignore virtual NEAF activity from 2020 to 2022.
        skip = 1

    if skip:
        excludedCovidSkuOrders = excludedCovidSkuOrdersDict.get(sku, [])
        if not excludedCovidSkuOrders:
            excludedCovidSkuOrdersDict[sku] = excludedCovidSkuOrders
        excludedCovidSkuOrders.append(order_num)
    return skip

def get_company(li):
    company = ''
    for p in li.get(PROPERTIES_KEY(),[]):
        if p.get(NOTE_ATTRIBUTE_KEY()) == 'My Company Name':
            company = p.get('value')
            break
    return company

def get_note_attributes(sct):
    nastr = ''
    nas = sct.note_attributes
    if not nas:
        return nastr
    for na in nas:
        name = na[NOTE_ATTRIBUTE_KEY()]
        value = na['value']
        delim = ', ' if nastr else ''
        if value == N_A:
            nastr += '{0}{1}'.format(delim,name)
        else:
            nastr += '{0}{1}:{2}'.format(delim,name,value)
    return nastr

def show_ShopifyCommonTup_list(sctList):

    # 2/6/2025. this function shows some useful items in ShopifyCommonTup list which is built in get_shopifyCommonTup_list. display the sctList. useful when debugging.
    # 2/6/2025. show_order_dict and show_ShopifyCommonTup_list have a similar design concept. They both set column widths to minimum needed to display data.

    SCT_HEADING = ['#','order#','created_at', 'name', 'company', 'email', 'sku', 'Dsc Code', 'Dsc', 'Quan', 'Cur Quan', 'Pr', 'Note', 'note_attributes', 'ref dt', 'refund_note']

    cnt = 0

    cnt_max = 2
    order_max = 6
    created_at_max = 10
    name_max = 4
    company_max = 7
    email_max = 5
    sku_max = 3
    dc_max = 8
    d_max = 3
    quantity_max = 4
    cur_quantity_max = 8
    price_max = 2
    note_max = 4
    na_max = 15
    rd_max = 6
    rn_max = 11

    for v in sctList:
        cnt += 1
        li = v.line_item

        cnt_max = get_max_len(str(cnt) + '.', cnt_max)
        order_max = get_max_len(v.order_num, order_max)
        # no need to calc created_at_max. its always 10.
        name_max = get_max_len(v.name, name_max)
        company_max = get_max_len(get_company(li),company_max)
        email_max = get_max_len(v.email,email_max)
        sku_max = get_max_len(li['sku'], sku_max)
        dc_max = get_max_len(v.discount_codes, dc_max)
        d_max = get_max_len(round(v.discount_allocations), dc_max)
        q_str = str(v.quantity) + '/' + str(li['quantity'])
        quantity_max = get_max_len(q_str, quantity_max)
        cur_quan = li['currentQuantity'] if USE_GRAPHQL[0] else li['current_quantity']
        cur_quantity_max = get_max_len(cur_quan, cur_quantity_max)
        price = li['originalUnitPriceSet']['shopMoney']['amount'] if USE_GRAPHQL[0] else li['price']
        price_max = get_max_len(round(float(price)), price_max)
        note = v.note[:43] + '...' if len(v.note) > 42 else v.note
        note_max = get_max_len(note, note_max)
        na_max = get_max_len(get_note_attributes(v), na_max)
        rd_max = get_max_len(v.refund_created_at,rd_max)
        refund_note = v.refund_note.replace('\n',' ')
        rn_max = get_max_len(refund_note,rn_max)

    fmt = '{{:{0}s}} {{:{1}s}} {{:{2}s}} {{:{3}s}} {{:{4}s}} {{:{5}s}} {{:{6}s}} {{:{7}s}} {{:{8}s}} {{:{9}s}} {{:{10}s}} {{:{11}s}} {{:{12}s}} {{:{13}s}} {{:{14}s}} {{:{15}s}}'
    fmt = fmt.format(cnt_max,order_max,created_at_max,name_max,company_max,email_max,sku_max,dc_max,d_max,quantity_max,cur_quantity_max,price_max,note_max,na_max,rd_max,rn_max)

    cnt = 0
    msgs = ['ShopifyCommonTup summary:']
    msg = fmt.format(*SCT_HEADING)
    msgs.append(msg)

    for v in sctList:
        cnt += 1
        li = v.line_item

        ca_str = v.created_at[:10]
        q_str = str(v.quantity) + '/' + str(li['quantity'])
        cq_str = str(li['currentQuantity'] if USE_GRAPHQL[0] else li['current_quantity'])
        da_str = str(round(v.discount_allocations))
        price = li['originalUnitPriceSet']['shopMoney']['amount'] if USE_GRAPHQL[0] else li['price']
        p_str = str(round(float(price)))
        note = v.note[:43] + '...' if len(v.note) > 42 else v.note
        na_str = get_note_attributes(v)
        refund_note = v.refund_note.replace('\n', ' ')

        msg = fmt.format(str(cnt),v.order_num,ca_str,v.name,get_company(li),str(v.email),li['sku'],v.discount_codes,da_str,q_str,cq_str,p_str,note,na_str,v.refund_created_at,refund_note)
        msgs.append(msg)

    desc = '\n'.join(msgs)

    return desc

def sctdesc(sct):
    # 2/7/2025. useful utility to use during debugging to show a ShopifyCommonTup in console
    print(show_ShopifyCommonTup_list([sct]))
    return

def get_line_item_TOTAL_to_sku_quantity_map(line_items):
    TOTAL_to_sku_quantity_map = {}
    for li in line_items:
        sku = li.get('sku',MISSING)
        quantity = li['currentQuantity'] if USE_GRAPHQL[0] else li['current_quantity']
        sku_quantity = sku + '/' + str(quantity)
        price = li['originalUnitPriceSet']['shopMoney']['amount'] if USE_GRAPHQL[0] else li['price']
        total = round(float(price)) * quantity
        prior_sku_quantity = TOTAL_to_sku_quantity_map.get(total)
        if prior_sku_quantity and sku_quantity not in prior_sku_quantity:
            sku_quantity = prior_sku_quantity + '|' + sku_quantity
        TOTAL_to_sku_quantity_map[total] = sku_quantity
    return TOTAL_to_sku_quantity_map

def refund_desc(r_ind,refunds):

    desc = ''
    note = refunds.get('note', )
    create_at = refunds['createdAt'] if USE_GRAPHQL[0] else refunds.get('created_at', MISSING)
    desc += '{0:>2}: create_at:{1}    note:  {2}\n'.format(r_ind + 1, create_at, note)
    refund_line_items = refunds['refundLineItems'] if USE_GRAPHQL[0] else refunds.get('refund_line_items', [])

    if USE_GRAPHQL[0]:
        totalRefundedSet = refunds.get('totalRefundedSet', {})
        if totalRefundedSet:
            order_adjustments_dollarsRefunded = -round(float(totalRefundedSet['shopMoney']['amount']))
            desc += '    ....... totalRefundedSet .......\n'
            desc += '     amount:{0}\n'.format(order_adjustments_dollarsRefunded)
    else:
        order_adjustments = refunds.get('order_adjustments', [])
        if order_adjustments:
            # 2/12/2025. if order_adjustments exist dollars are refunded on entire order, not refunds on specific line items.
            desc += '    ....... order_adjustments .......\n'
            for oa_ind, order_adjustment in enumerate(order_adjustments):
                kind = order_adjustment.get('kind', MISSING)
                amount = order_adjustment.get('amount', MISSING)
                desc += '    {0}:   kind:{1}   amount:{2}\n'.format(oa_ind + 1, kind, amount)

    # 2/4/2025. line items are refunded
    if refund_line_items:
        if USE_GRAPHQL[0]:
            desc += '    ....... refundLineItems .......\n'
            for rli_ind, rli in enumerate(refund_line_items):
                li = rli['lineItem']
                msg = '    {0}:  sku:{1}  restockType:{2}  quantity(refunded):{3}  priceSet:{4}  currentQuantity(order):{5}  originalUnitPrice:{6}  discountedUnitPrice:{7}\n'
                desc += msg.format(rli_ind + 1, li['sku'],rli['restockType'],rli['quantity'],rli['priceSet']['shopMoney']['amount'],li['currentQuantity'],li['originalUnitPrice'],li['discountedUnitPrice'])
        else:
            desc += '    ....... refund_line_items .......\n'
            for rli_ind, rli in enumerate(refund_line_items):
                restock_type = rli.get('restock_type')
                quantity = rli.get('quantity')
                line_item = rli.get('line_item', {})
                li_quantity = line_item.get('quantity', MISSING)
                li_current_quantity = line_item.get('current_quantity', MISSING)
                quantity_refunded = li_quantity - li_current_quantity
                price = round(float(line_item['price']))
                sku = line_item.get('sku', MISSING)
                dollars_refunded = quantity_refunded * price
                msg = '    {0}:  restock_type:{1}  quantity(refunded):{2}  line_item(sku:{3}  quantity:{4}  current_quantity:{5}) DOLLARS_REFUNDED:{6}\n'
                desc += msg.format(rli_ind + 1, restock_type, quantity, sku, li_quantity, li_current_quantity,dollars_refunded)

    return desc

def refunds_list_desc(order_num,line_items,refunds_list):

    desc = '\nline_items description for order_num #{0}:\n'.format(order_num)

    for l_ind,li in enumerate(line_items):
        msg = '{0:>2}:  sku:{1:>40}  current_quantity:{2:>2}  quantity:{3:>2}  price:{4:>7}  TOTAL:{5:>7}\n'
        if USE_GRAPHQL[0]:
            total = float(li['originalUnitPriceSet']['shopMoney']['amount']) * li['currentQuantity']
            desc += msg.format(l_ind + 1, li.get('sku', MISSING), li.get('currentQuantity', MISSING),li.get('quantity', MISSING), li['originalUnitPriceSet']['shopMoney']['amount'], total)
        else:
            total = float(li.get('price','0')) * li.get('current_quantity',0)
            desc += msg.format(l_ind+1,li.get('sku',MISSING),li.get('current_quantity',MISSING),li.get('quantity',MISSING),li.get('price',MISSING),total)

    desc += '\nrefunds list description for order_num #{0}:\n'.format(order_num)

    for r_ind,refunds in enumerate(refunds_list):
        desc += refund_desc(r_ind, refunds)

    return desc

def _buildRefundNote(refund_note,r_note):
    if not r_note:
        return refund_note
    return refund_note + '\n' + r_note if refund_note else r_note

def _buildRefundLineItemsDesc(refund_line_items_desc,rli,line_item=None):
    li = rli['lineItem'] if USE_GRAPHQL[0] else rli['line_item']
    sku = line_item['sku'] if line_item else li.get('sku',MISSING)
    quantity = rli.get('quantity',MISSING)
    if USE_GRAPHQL[0]:
        subtotal = round(float(li['originalUnitPrice'])) * quantity
    else:
        subtotal = round(rli.get('subtotal',0))
    delim = ' | ' if refund_line_items_desc else ''
    msg = '{0}{1}, quantity:{2}, total:${3}'.format(delim,sku,quantity,subtotal)
    return refund_line_items_desc + msg

def get_ShopifyCommonTup_highest_price(order_num,sctList):
    # 2/7/2025. this function returns ShopifyCommonTup of highest price in sctList for request order_num. used to find most import item in sctList.
    highestPrice = 0
    for sct in sctList:
        if sct.order_num != order_num:
            continue
        price = round(float(sct.line_item.get('price',0)))
        if price > highestPrice:
            highestPrice = price
    for sct in sctList:
        if sct.order_num != order_num:
            continue
        price = round(float(sct.line_item.get('price',0)))
        if price == highestPrice:
            break
    return sct

def convert_ShopifyCommonTup_to_refund(dollarsRefunded,sct):
    sct = copy.deepcopy(sct)
    sct = sct._replace(sku=REFUND,discount_allocations=0.0,discount_codes='',total_discounts=0.0, created_at=sct.refund_created_at)
    li = sct.line_item
    if USE_GRAPHQL[0]:
        li['originalUnitPriceSet']['shopMoney']['amount'] = str(dollarsRefunded)
    else:
        li['price'] = str(dollarsRefunded)
    # 2/7/2025. defaults to clear out line item
    li['sku'] = REFUND
    li['total_discount'] = '0.00'
    li['total_discount_set'] = {}
    li['tax_lines'] = []
    li['discount_allocations'] = []
    li['current_quantity'] = 1
    li['quantity'] = 1
    li['price_set'] = {}
    li['id'] = 0
    li['admin_graphql_api_id'] = ''
    li['name'] = ''
    li['product_id'] = 0
    li['title'] = ''
    li['variant_id'] = 0
    li['variant_title'] = ''

    return sct

def build_skus_refunded(order_num,refunds_list,line_items,note,debug):

    # 2/4/2025. the refunds inside each refunds_list element fall into 4 categories, 6 sub-categories:
    #           a) use refund_line_items, cases 1), 2).
    #           b) use refund_line_items but some failure when trying to grant refund, case 3).
    #           c) use order_adjustments, cases 4), 5).
    #           d) failure to categorize. this is a bug and need repair, case 6).

    # 1) each refund_line_items refunds an entire line item. no order_adjustments.
    #    #8948, #9481(refund_line_items[0] and refund_line_items[1]), #9541, #9404
    # 2) refund_line_items and order_adjustments both exist. order_adjustments sum to 0. each refund_line_items refunds an entire line item. same treatment as case 1).
    #    #13695, #13712, #13415, #7618

    # 3) refund_line_items and order_adjustments both exist. dollars of order_adjustments equals dollars in refund_line_items which means some failure when trying to grant refund.
    #    #9255, #9481(refund_line_items[2])

    # 4) dollars of refund in order_adjustments exactly equal and opposite to 1 line item. no refund_line_items. refund that line item.
    #    #10638, #9239, #11709
    # 5) dollars of refund in order_adjustments does not match any line item but is <= dollars of entire order. no refund_line_items. refund dollar to order, don't refund a specific sku.
    #    #15317

    # 6) failure to categorize. this is a bug and needs repair. No sample orders so far for this use case.


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

    # 2/6/2025. unfortunately semantics of the skus_refunded dict takes 2 forms. typically for cases 1) to 4) the key is sku getting refund and value is the quantity of the given sku being refunded.
    #           for case 5) the key is REFUND and the value is dollars refunded to entire order because refund can't be ascribed to a single sku.
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

        rca = getItem(refunds,'created_at')
        rca = rca[:10] if rca else rca
        refund_created_at = (refund_created_at if rca in refund_created_at else refund_created_at+'|'+rca) if refund_created_at else rca
        r_note = getItem(refunds,'note')
        refund_note = _buildRefundNote(refund_note, r_note)

        if not refunds:
            # 2/5/2025. I have no use case for this block but this old check on existence of refunds has been around for a long time so just keep it.
            refund_note = _buildRefundNote(refund_note,'For order_num:{0} found invalid element refunds_list[{1}]:{2} for len(refunds_list):{3}'.format(order_num,r_ind,refunds,len(refunds_list)))
            continue

        # 2/3/2025. the 2 major data structures for describing refunds are set here: refund_line_items or order_adjustments.
        refund_line_items = refunds.get('refund_line_items',[])
        order_adjustments = refunds.get('order_adjustments',[])

        order_adjustments_dollarsRefunded = 0
        for oa in order_adjustments:
            amount = round(float(oa.get('amount','0')))
            order_adjustments_dollarsRefunded += amount

        refund_line_items_dollarsRefunded = 0
        refund_line_items_desc = ''
        for rli in refund_line_items:
            quantity = rli.get('quantity')
            line_item = rli.get('line_item', {})
            price = round(float(line_item['price']))
            refund_line_items_dollarsRefunded += quantity * price
            refund_line_items_desc = _buildRefundLineItemsDesc(refund_line_items_desc,rli)
            if not refund_note:
                # 2/7/2025. typically I have the presense of mind to enter note when granting refund but I didn't do that for #13712 so do this.
                refund_note = refund_line_items_desc

        if refund_line_items_dollarsRefunded == order_adjustments_dollarsRefunded:

            # 2/5/2025. this block for sub-category 3). These refunds were not delivered to customer and shopify represents these failures poorly.

            refund_note = _buildRefundNote(refund_note,'WARNING: REFUNDS OF {0} NOT CORRECTLY DISPLAYED.'.format(refund_line_items_desc))
            continue

        elif refund_line_items_dollarsRefunded and not order_adjustments_dollarsRefunded:

            # 2/5/2025. this block for sub-categories 1) and 2) for processing of normal refunds.

            for rli in refund_line_items:
                quantity = rli.get('quantity')
                line_item = rli.get('line_item')
                if not line_item:
                    continue
                sku = line_item.get('sku')
                if not sku:
                    continue
                skus_refunded[sku] = quantity

        elif not refund_line_items and order_adjustments and order_adjustments_dollarsRefunded < 0:
            sku_quantity_toks = line_item_TOTAL_to_sku_quantity_map.get(-order_adjustments_dollarsRefunded)
            sku_quantities = sku_quantity_toks.split('|') if sku_quantity_toks else []

            if len(sku_quantities) == 1:
                sku = sku_quantities[0].split('/')[0]
                quantity = int(sku_quantities[0].split('/')[1])
            else:
                sku = None

            if sku:

                # 2/5/2025. this block for sub-category 4). assume a complete refund of the line item with sku.

                skus_refunded[sku] = quantity

            else:

                # 2/5/2025. this block for sub-category 5). assigns these dollars of refunds to entire order.

                skus_refunded[REFUND] = order_adjustments_dollarsRefunded

        else:

            # 2/5/2025. this block for sub-categoty 6). is for a failure to match any of the 5 sub-categories.

            desc = refund_desc(r_ind, refunds)
            print('order_num',order_num,'desc',desc)
            refund_note = _buildRefundNote(refund_note, 'FAILURE PROCESSING:\n{0}'.format(desc))

    return skus_refunded, refund_note, refund_created_at, note

