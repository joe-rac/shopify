import copy
from consts import NEAF_VENDOR,NEAF_YEAR_COVID,COVID_NEAF_VENDOR_SKUS_TO_EXCLUDE,COVID_NEAF_VENDOR_SKUS_TO_EXCLUDE_CONDITIONALLY
from consts import VIRTUAL_NEAF_ORDER_RANGE,NEAF_ATTEND,NEAF_VIRTUAL_DOORPRIZE,N_A,MISSING,REFUND
from utils import get_max_len,getItem,NOTE_ATTRIBUTE_KEY,CUSTOM_ATTRIBUTES_KEY,getCurrencySymbolFromCode

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
    for p in li.get(CUSTOM_ATTRIBUTES_KEY(), []):
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
        cur_quan = li['currentQuantity']
        cur_quantity_max = get_max_len(cur_quan, cur_quantity_max)
        price = li['originalUnitPriceSet']['shopMoney']['amount']
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
        cq_str = str(li['currentQuantity'])
        da_str = str(round(v.discount_allocations))
        price = li['originalUnitPriceSet']['shopMoney']['amount']
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
        quantity = li['currentQuantity']
        sku_quantity = sku + '/' + str(quantity)
        price = li['originalUnitPriceSet']['presentmentMoney']['amount']
        total = round(float(price)) * quantity
        prior_sku_quantity = TOTAL_to_sku_quantity_map.get(total)
        if prior_sku_quantity and sku_quantity not in prior_sku_quantity:
            sku_quantity = prior_sku_quantity + '|' + sku_quantity
        TOTAL_to_sku_quantity_map[total] = sku_quantity
    return TOTAL_to_sku_quantity_map

def refund_desc(r_ind,refunds):

    desc = ''
    note = refunds.get('note', )
    create_at = refunds['createdAt']
    desc += '{0:>2}: create_at:{1}    note:  {2}\n'.format(r_ind + 1, create_at, note)
    refund_line_items = refunds['refundLineItems']

    totalRefundedSet = refunds.get('totalRefundedSet', {})
    if totalRefundedSet:
        order_adjustments_dollarsRefunded = -round(float(totalRefundedSet['shopMoney']['amount']))
        desc += '    ....... totalRefundedSet .......\n'
        desc += '     amount:{0}\n'.format(order_adjustments_dollarsRefunded)

    # 2/4/2025. line items are refunded
    if refund_line_items:
        desc += '    ....... refundLineItems .......\n'
        for rli_ind, rli in enumerate(refund_line_items):
            li = rli['lineItem']
            msg = '    {0}:  sku:{1}  restockType:{2}  quantity(refunded):{3}  priceSet:{4}  currentQuantity(order):{5}  currency:{6}  originalUnitPrice:{7}  discountedUnitPrice:{8}\n'
            desc += msg.format(rli_ind + 1, li['sku'],rli['restockType'],rli['quantity'],rli['priceSet']['shopMoney']['amount'],
                               li['currentQuantity'],li['originalUnitPriceSet']['presentmentMoney']['currencyCode'],li['originalUnitPriceSet']['presentmentMoney']['amount'],
                               li['discountedUnitPriceSet']['presentmentMoney']['amount'])

    return desc

def refunds_list_desc(order_num,line_items,refunds_list):

    desc = '\nline_items description for order_num #{0}:\n'.format(order_num)

    for l_ind,li in enumerate(line_items):
        msg = '{0:>2}:  sku:{1:>40}  current_quantity:{2:>2}  quantity:{3:>2}  price:{4:>7}  TOTAL:{5:>7}\n'
        total = float(li['originalUnitPriceSet']['shopMoney']['amount']) * li['currentQuantity']
        desc += msg.format(l_ind + 1, li.get('sku', MISSING), li.get('currentQuantity', MISSING),li.get('quantity', MISSING), li['originalUnitPriceSet']['shopMoney']['amount'], total)


    desc += '\nrefunds list description for order_num #{0}:\n'.format(order_num)

    for r_ind,refunds in enumerate(refunds_list):
        desc += refund_desc(r_ind, refunds)

    return desc

def _buildRefundNote(refund_note,r_note):
    if not r_note:
        return refund_note
    return refund_note + '\n' + r_note if refund_note else r_note

def _buildRefundLineItemsDesc(refund_line_items_desc,rli,line_item=None):
    li = rli['lineItem']
    sku = line_item['sku'] if line_item else li.get('sku',MISSING)
    quantity = rli.get('quantity',MISSING)
    subtotal = round(float(li['originalUnitPriceSet']['presentmentMoney']['amount'])) * quantity
    csym = getCurrencySymbolFromCode(li['originalUnitPriceSet']['presentmentMoney']['currencyCode'])
    delim = ' | ' if refund_line_items_desc else ''
    msg = f'{delim}{sku} quantity:{quantity}, total:{csym}{subtotal}'
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

def convert_ShopifyCommonTup_to_refund(moneyRefunded, sct):
    presentmentRefunded = moneyRefunded['presentment']
    shopRefunded        = moneyRefunded['shop']
    sct = copy.deepcopy(sct)
    sct = sct._replace(sku=REFUND,discount_allocations=0.0,discount_codes='',total_discounts=0.0, created_at=sct.refund_created_at)
    li = sct.line_item

    li['discountedTotalSet']['shopMoney']['amount']            = str(shopRefunded)
    li['discountedTotalSet']['presentmentMoney']['amount']     = str(presentmentRefunded)
    li['originalUnitPriceSet']['shopMoney']['amount']          = str(shopRefunded)
    li['originalUnitPriceSet']['presentmentMoney']['amount']   = str(presentmentRefunded)
    li['originalTotalSet']['shopMoney']['amount']              = str(shopRefunded)
    li['originalTotalSet']['presentmentMoney']['amount']       = str(presentmentRefunded)
    li['discountedUnitPriceSet']['shopMoney']['amount']        = str(shopRefunded)
    li['discountedUnitPriceSet']['presentmentMoney']['amount'] = str(presentmentRefunded)

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



