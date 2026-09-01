
import csv
import datetime
import tracemalloc
import tempfile
import os
import copy
from consts import NEAF_VENDOR,NEAF_VENDOR,NEAF_FULL,NEAF_RAW,NEAF_COMPANY_BADGE,NEAF_YEAR_DEFAULT,REFUND,N_A
from utils import get_date,NeafVendorCollectionsTup,show_dict,show_neaf_vendor_dict,NeafVendorTup,getCurrencySymbolFromCode,NEAF_VENDOR_FIELDS
from utils import NeafSSTup,writerow_UnicodeEncodeError,RAC_DIR,ERROR,STARS,nvtDesc,NOTE_ATTRIBUTE_KEY,CUSTOM_ATTRIBUTES_KEY
from neaf_vendor_utils import useOrderNoteAttributeEdits,getNamesFromOrderProperty,setAddress,setName,setCost,setOrderDetails,setOrderProperties,useNameFromAttribute
from neaf_vendor_utils import addItemToNvtDict,set_vendor_properties_tup,mergeNvts,mergedDiscounts,getBadgeEntitledCntAndNames,removeBadgesFromRefundedOrders,applyBadgeNameEdits
from neaf_vendor_utils import convert_neafVendorTup_to_processed,get_distinct_order_properties,item_count_description,build_address_text,normalize_big_string
from neaf_vendor_utils import displayLargeStringWithMargin,dash_string,goodDatetimeStr,buildCompanyBadgeList,buildLastOrderDateVendorsMap,convertToKey,save_invoice,get_vendor_sign_in_row
from neaf_vendor_utils import invoice_subdir,getNormalizedBadgeNames,updateOrderNoteAttributes,DONATION_SKU,EXCLUDE_SKU,appendError,appendError_and_replace_in_nvt_dict
from neaf_vendor_utils import INCOMPATIBLE_ACTIONS,VALID_EDIT_ACTIONS,EDIT_ACTION_TO_ACTION_MAP,BADGE,DELETE_ORIGINAL_BADGE,EMAIL,DESC_FOR_ACTION_NEEDING_1_ORDER,DELETE_PRIOR_EDIT
from neaf_vendor_utils import DELETE_ORIGINAL_BADGE_ACTION,DELETE_ORIGINAL_ORDER_NOTE,ORDER_NOTE,NAME
from order_num_to_company import buildOrderNumToCompanyMap
from access_shopify import AccessShopify

class NEAFVendor(AccessShopify):

    NEAF_YEARS = ()

    def __init__(self,neaf_year=NEAF_YEAR_DEFAULT,created_at_min=None,created_at_max=None,order_to_debug=None,verbose=False):

        # 12/30/2022. call self.shopifyLoad() to load data.

        super(NEAFVendor,self).__init__(neaf_year,created_at_min,created_at_max,order_to_debug,verbose)
        if self.error:
            return
        print('memory usage at exit from NEAFVendor.__init__(...) : {0}'.format(tracemalloc.get_traced_memory()))
        self.sku_key = NEAF_VENDOR

        return

    def append_to_shopifyTup_dict(self,nvt_dict,sct):

        # 1/15/2023. append_to_shopifyTup_dict is implemented in each class that derives from AccessShopify and is responsible for much of the polymorphism of this class heirarchy.
        #            so far the classes AccessOrders, DoorPrize and NEAFVendor implement append_to_shopifyTup_dict.
        #            append_to_shopifyTup_dict sums all the line items in sct to orders under st_dict

        # this function processes an individual line items, shopifyCommonTup of sct, in an order and merges them under a single NeafVendorTup, nvt,
        # for a given order. That nvt is added to nvt_dict collection which has key of order_num.

        key = sct.order_num
        if key == '4265':
            #print 'xx'
            pass

        (order_num,created_at,sku,quantity,CONFIRM_NOTE,
            name,address1,address2,address3,phone_num,
            email,booth_st_qty,booth_st,booth_prem_qty,booth_prem,
            upgrade_st_to_prem_qty,upgrade_st_to_prem,get_booths_from_order,sent_booths_to_orders,no_st_booths_from_order,no_pr_booths_from_order,
            extra_tables_qty,extra_tables,extra_chairs_qty,extra_chairs,elec,carpet,additional_badges_qty,additional_badges,wifi,shipping_box,
            shipping_pallet,sponsorship,donation,declined_neaf_2023,prize_donation,prize_donation_value,
            currencyCode,total_cost,paid,total_due,
            check_number,total_discounts,discount_codes,booth_comments,sales_comments,error,
            total_cost_presentment,paid_presentment,total_due_presentment,total_discounts_presentment,
            shipping_box_qty,shipping_pallet_qty,order_note,debug,order_details,order_properties,
            badge_names_orig,badge_entitled_cnt,badge_names) = (None,) * 60

        order_num = sct.order_num
        # 12/27/2022. Bizzarely order_num is in there twice, 2nd time its orderNumber. that's the simplest way of getting it into the s/s in the current framework where s/s fields run
        #             from company to error in NeafVendorTup schema.
        orderNumber = order_num
        created_at = sct.created_at
        order_note = normalize_big_string(sct.note)
        order_note_attributes = sct.note_attributes
        order_id = sct.order_id
        sku = sct.sku
        quantity = sct.quantity
        name = sct.name
        email = sct.email
        phone_num = sct.phone_num
        total_discounts             = sct.total_discounts
        total_discounts_presentment = sct.total_discounts_presentment
        discount_codes = sct.discount_codes
        default_address = sct.default_address
        refund_note = sct.refund_note
        refund_created_at = sct.refund_created_at
        company_from_attribute = None
        name_from_attribute = None
        donation_order_from_attribute = None
        exclude_order_from_attribute = None
        order_num_to_donation_map = {}
        company = default_address.get('company') if default_address.get('company') else ''

        properties = sct.line_item.get(CUSTOM_ATTRIBUTES_KEY())
        nvpt = set_vendor_properties_tup(properties)
        #requested_booth_loc = nvpt.requested_booth_loc
        if nvpt.get_booths_from_order:
            get_booths_from_order = nvpt.get_booths_from_order
        if isinstance(nvpt.no_st_booths_from_order,int):
            no_st_booths_from_order = nvpt.no_st_booths_from_order
        if isinstance(nvpt.no_pr_booths_from_order,int):
            no_pr_booths_from_order = nvpt.no_pr_booths_from_order
        if nvpt.prize1:
            prize_donation = nvpt.prize1
        if nvpt.prize2:
            prize_donation = nvpt.prize2 if not prize_donation else prize_donation+' | '+nvpt.prize2
        if nvpt.prize1_value:
            prize_donation_value = nvpt.prize1_value
        if nvpt.prize2_value:
            prize_donation_value = nvpt.prize2_value if not prize_donation_value else prize_donation_value+' | '+nvpt.prize2_value
        extra_badge_names = '|'.join(nvpt.extra_badge_names)
        created_date = get_date(created_at)
        first_order_date = created_date
        last_order_date = created_date

        # TODO 3/25/2023. Keep NeafVendorTup usage here in sync with usage in NEAF_VENDOR_FIELDS in utils.py near line 58
        #                 NEAF s/s fields runs from company to error

        nvt = NeafVendorTup(order_num, created_at, sku, quantity, CONFIRM_NOTE,

                            nvpt.company_from_property, company_from_attribute,name_from_attribute,

                            company, last_order_date, orderNumber, name, address1, address2, address3, phone_num, nvpt.cellno,
                            email, booth_st_qty, booth_st, booth_prem_qty, booth_prem,
                            upgrade_st_to_prem_qty, upgrade_st_to_prem, get_booths_from_order, sent_booths_to_orders, no_st_booths_from_order, no_pr_booths_from_order,
                            extra_tables_qty, extra_tables, extra_chairs_qty, extra_chairs, elec, carpet, additional_badges_qty, additional_badges, wifi, shipping_box,
                            shipping_pallet, sponsorship, donation, donation_order_from_attribute, exclude_order_from_attribute, declined_neaf_2023, prize_donation, prize_donation_value,
                            currencyCode, total_cost, paid, total_due, check_number, total_discounts, discount_codes, booth_comments, sales_comments, order_note, nvpt.error,

                            total_cost_presentment,paid_presentment,total_due_presentment,total_discounts_presentment,
                            shipping_box_qty, shipping_pallet_qty, order_num_to_donation_map, order_note_attributes, order_id,refund_note, refund_created_at,
                            nvpt.name_on_badge, nvpt.badge1_name, nvpt.badge2_name, extra_badge_names, badge_names_orig, badge_entitled_cnt, badge_names,
                            first_order_date, debug, order_details, order_properties)

        if self.verbose:
            print(nvtDesc(nvt))
        nvt = useOrderNoteAttributeEdits(nvt)

        nvt = setAddress(nvt,sct)
        nvt = setName(nvt,properties)
        nvt = setCost(nvt,sct)
        nvt = setOrderDetails(nvt,sct)
        nvt = setOrderProperties(nvt,sct)
        nvt = useNameFromAttribute(nvt)

        addItemToNvtDict(nvt_dict,key,nvt)
        return

    def build_neaf_vendor_full_dict_from_shopify(self,raw):

        # 12/19/2022. critical function that build full from raw. key of raw is order_num. this function collapses multiple orders under a company in raw and returns full collection with key of company.
        #             the crtical merge of nvt items under raw in nvt items under full takes place in mergedNvts.

        full = {}
        for order_num,nvt in raw.items():
            company = self.orderNumToCompanyMap.get(int(order_num))
            if not company:
                raise Exception('Fatal error in build_neaf_vendor_full_dict_from_shopify. No company returned from self.orderNumToCompanyMap[{0}]. Fix program.'.format(order_num))
            nvt = nvt._replace(company=company)

            removeBadges = removeBadgesFromRefundedOrders(nvt)
            if removeBadges:
                nvt = nvt._replace(additional_badges=None,additional_badges_qty=None,badge1_name=None,badge2_name=None,badge_entitled_cnt=None,
                                   badge_names=None,badge_names_orig=None,extra_badge_names=None,name_on_badge=None)

            orig_nvt = full.get(company)
            if orig_nvt:
                # this function used here to collapse many orders that a single company might make under a single company entry in orig_nvt
                orig_nvt = mergeNvts(orig_nvt, nvt)
                # special processing needed to merge discounts.
                orig_nvt = mergedDiscounts(orig_nvt,nvt)
            else:
                orig_nvt = copy.deepcopy(nvt)
            badge_names_orig,badge_entitled_cnt = getBadgeEntitledCntAndNames(orig_nvt)
            orig_nvt = orig_nvt._replace(badge_names_orig=badge_names_orig,badge_entitled_cnt=badge_entitled_cnt,badge_names=badge_names_orig)

            full[orig_nvt.company] = orig_nvt

        # 11/14/2022. apply badge name edits in nvt.order_note_attributes to nvt.badge_names
        for company,nvt in full.items():
            badge_names,error,edit_cnt = applyBadgeNameEdits(nvt)
            if edit_cnt:
                nvt = nvt._replace(badge_names=badge_names,error=error)
                full[nvt.company] = nvt

        return full

    def adjustBoothQuantitiesForTransfersAndUpgrades(self, full):

        # TODO 3/18/2026. implement this function that
        #                 1) error checks. There's a whole shitload of error checks for get_from_order. see code below.
        #                 2) adjusts nvt.booth_prem_qty and nvt.booth_st_qty if nvt.upgrade_st_to_prem_qty is not 0.
        #                 3) transfer booths from a source company to a destination company that has get_booths_from_order set.
        #                 .
        #                 sample order that uses upgrade_st_to_prem_qty is for Spectrum Optical Instruments. original order is #17309 with 3 standard. upgrade 1 booth in #17712.
        #                 set error if insufficient number of standard booths to upgrade.
        #                 loop through full dict and find all target orders in get_booths_from_order. for now only the "Extra NEAF Vendor Management s/s Row" product
        #                 with sku:neaf_vendor_booth_extra_ss_row uses get_booths_from_order.
        #                 confirm those orders are real. confirm no duplicate orders used in get_booths_from_order inside a company.
        #                 confirm sufficient booths in the get_booths_from_order order to divert to requesting order.
        #                 Sample orders with get_booths_from_order:
        #                    1) 19065 (Astro-Tech, quan:1) with get_booths_from_order of 17376 (Astronomics,    quan: stan:1, prem:3)
        #                    2) 19066 (10 Micron,  quan:1) with get_booths_from_order of 17377 (Woodland Hills, quan: prem:2)
        #                    3) 19067 (Sky Rover,  quan:1) with get_booths_from_order of 17376 (Astronomics,    quan: stan:1, prem:3)
        #                 duplicates are allowed across companies since a single company with many booths can feed many "Extra NEAF Vendor Management s/s Row" companies.
        #                 Sample orders for 'Spectrum Optical Instruments', 17309|17712 has 3 standard and 1 premium. it should be 2 standard and 2 premium when when
        #                    neaf_vendor_booth_premium_from_standard_early_bird:1 applied.

        # 7/16/2026. this block processes upgrade_st_to_prem_qty.

        for company,nvt in full.items():
            if nvt.upgrade_st_to_prem_qty:
                if not nvt.booth_st_qty:
                    error = f"company:{company} has upgrade_st_to_prem_qty:{nvt.upgrade_st_to_prem_qty} but has no standard booths."
                    appendError_and_replace_in_nvt_dict(full,nvt,error)
                    continue
                if nvt.upgrade_st_to_prem_qty > nvt.booth_st_qty:
                    error = f"company:{company} has upgrade_st_to_prem_qty:{nvt.upgrade_st_to_prem_qty} but only has booth_st_qty:{nvt.booth_st_qty} to be upgraded."
                    appendError_and_replace_in_nvt_dict(full,nvt,error)
                    continue
                if not nvt.booth_prem_qty:
                    nvt = nvt._replace(booth_prem_qty=nvt.upgrade_st_to_prem_qty)
                else:
                    nvt = nvt._replace(booth_prem_qty=nvt.booth_prem_qty + nvt.upgrade_st_to_prem_qty)
                nvt = nvt._replace(booth_st_qty=nvt.booth_st_qty - nvt.upgrade_st_to_prem_qty)
                full[company] = nvt

        # 4/2/2026. this block processes items in full dict that have nvt.get_booths_from_order set.

        gbfo_src_to_dsts_maps = {} # 7/14/2026. use this collection to map a single source of booths to a list of destination orders that get those booths
        for company,nvt_dst in full.items():
            if nvt_dst.get_booths_from_order:

                # 4/2/2026: some orders that hit this block with nvt.get_booths_from_order include 19065, 19066, 19067.

                # 7/13/2026. First do a whole crap load of error checking.

                if not nvt_dst.get_booths_from_order.isdigit():
                    appendError_and_replace_in_nvt_dict(full,nvt_dst,f"get_booths_from_order:'{nvt_dst.get_booths_from_order}' is invalid. It must be an integer.")
                    continue
                get_booths_from_order = int(nvt_dst.get_booths_from_order)
                if len(nvt_dst.order_num.split('|')) != 1:
                    error = f"Company:{company} with nvt.get_booths_from_order:'{nvt_dst.get_booths_from_order}' is invalid because it has nvt.order_num:{nvt_dst.order_num}. "\
                             "which means this company is built from multiple orders. Any company that uses nvt.get_booths_from_order must be built from single order."
                    appendError_and_replace_in_nvt_dict(full,nvt_dst,error)
                    continue
                if get_booths_from_order == int(nvt_dst.order_num):
                    error = f"nvt.get_booths_from_order:'{nvt_dst.get_booths_from_order}' is invalid because nvt.order_num:{nvt_dst.order_num}. "\
                             'nvt.get_booths_from_order cannot point back to itself.'
                    appendError_and_replace_in_nvt_dict(full,nvt_dst,error)
                    continue
                company_src = self.orderNumToCompanyMap.get(get_booths_from_order)
                if not company_src:
                    error = f"get_booths_from_order:'{nvt_dst.get_booths_from_order}' expected to have entry in NEAFVendor.orderNumToCompanyMap dict but no entry exists."
                    appendError_and_replace_in_nvt_dict(full,nvt_dst,error)
                    continue
                nvt_src = full.get(company_src)
                if not nvt_src:
                    error = f"get_booths_from_order:'{nvt_dst.get_booths_from_order}' has company:{company_src} but that company has no entry in full dict."
                    appendError_and_replace_in_nvt_dict(full,nvt_dst,error)
                    continue
                no_st_booths_from_order = nvt_dst.no_st_booths_from_order
                if not isinstance(no_st_booths_from_order,int):
                    appendError_and_replace_in_nvt_dict(full,nvt_dst,f"no_st_booths_from_order:'{nvt_dst.no_st_booths_from_order} is invalid. Must be blank or number.")
                    continue
                no_pr_booths_from_order = nvt_dst.no_pr_booths_from_order
                if not isinstance(no_pr_booths_from_order,int):
                    appendError_and_replace_in_nvt_dict(full,nvt_dst,f"no_pr_booths_from_order:'{nvt_dst.no_pr_booths_from_order} is invalid. Must be blank or number.")
                    continue
                if (no_st_booths_from_order or no_pr_booths_from_order) and  no_st_booths_from_order + no_pr_booths_from_order != nvt_dst.quantity:
                    error = f"no_st_booths_from_order:'{nvt_dst.no_st_booths_from_order} and no_pr_booths_from_order:'{nvt_dst.no_pr_booths_from_order} are invalid. " \
                            f"They sum to {no_st_booths_from_order + no_pr_booths_from_order} which does not equal quantity:{nvt_dst.quantity}."
                    appendError_and_replace_in_nvt_dict(full,nvt_dst,error)
                    continue
                if nvt_src.booth_st_qty and nvt_src.booth_prem_qty and not no_st_booths_from_order and not no_pr_booths_from_order:
                    error = f"get_booths_from_order:'{nvt_dst.get_booths_from_order}' has company:{company_src} but that company has both booth_st_qty:{nvt_src.booth_st_qty} and "\
                            f"booth_prem_qty:{nvt_src.booth_prem_qty}. However both no_st_booths_from_order and no_pr_booths_from_order are missing. At least one must exist."
                    appendError_and_replace_in_nvt_dict(full,nvt_dst,error)
                    continue

                # 7/14/2026. we have found both source and destination of 'get booths from order' NEAFVendorTup items. save them for further processing

                gbfo_dsts = gbfo_src_to_dsts_maps.get(company_src,[])
                if not gbfo_dsts:
                    gbfo_src_to_dsts_maps[company_src] = gbfo_dsts
                gbfo_dsts.append(nvt_dst)

        # 7/15/2026. confirm the source company has enough booths to transfer to destination companies

        src_companys_to_remove = []
        for company_src,gbfo_dsts in gbfo_src_to_dsts_maps.items():
            nvt_src = full[company_src]
            booth_st_qty_src = nvt_src.booth_st_qty if nvt_src.booth_st_qty else 0
            booth_prem_qty_src = nvt_src.booth_prem_qty if nvt_src.booth_prem_qty else 0
            st_cnt = 0
            pr_cnt = 0
            either_cnt = 0
            companies_dst = []
            for nvt_dst in gbfo_dsts:
                companies_dst.append(nvt_dst.company)
                if nvt_dst.no_pr_booths_from_order:
                    pr_cnt += nvt_dst.no_pr_booths_from_order
                if nvt_dst.no_st_booths_from_order:
                    st_cnt += nvt_dst.no_st_booths_from_order
                if not nvt_dst.no_st_booths_from_order and not nvt_dst.no_pr_booths_from_order:
                    either_cnt += nvt_dst.quantity

            companies_dst_str = ', '.join(companies_dst)
            if st_cnt and st_cnt > booth_st_qty_src:
                error = f"company:{company_src} has standard booths:{booth_st_qty_src} but the companies getting those standard booths of {companies_dst_str} of " \
                      f"are requesting a total of {st_cnt}. Not enough standard booths available."
                appendError_and_replace_in_nvt_dict(full,nvt_dst,error)
                src_companys_to_remove.append(company_src)
                continue
            if pr_cnt and pr_cnt > booth_prem_qty_src:
                error = f"company:{company_src} has premium booths:{booth_prem_qty_src} but the companies getting those premium booths of {companies_dst_str} of " \
                      f"are requesting a total of {pr_cnt}. Not enough premium booths available."
                appendError_and_replace_in_nvt_dict(full,nvt_dst,error)
                src_companys_to_remove.append(company_src)
                continue
            tot_booth_cnt_src = booth_st_qty_src + booth_prem_qty_src
            if either_cnt and either_cnt > tot_booth_cnt_src:
                error = f"company:{company_src} has booth_st_qty:{booth_st_qty_src} + booth_prem_qty:{booth_prem_qty_src} of {tot_booth_cnt_src } but the companies getting " \
                        f"those booths of {companies_dst_str} are requesting a total of {either_cnt}. Not enough booths available."
                appendError_and_replace_in_nvt_dict(full,nvt_dst,error)
                src_companys_to_remove.append(company_src)
                continue

        for src_company_to_remove in src_companys_to_remove:
            del gbfo_src_to_dsts_maps[src_company_to_remove]

        # 7/15/2026. we have completed all error checking. adjust booth_st_qty and booth_st_qty and booth_prem_qty for both source and destination companies and set
        #            sent_booth_to_order to concatenated list of destination order.

        for company_src,gbfo_dsts in gbfo_src_to_dsts_maps.items():
            nvt_src = full[company_src]
            booth_st_qty_src = nvt_src.booth_st_qty if nvt_src.booth_st_qty else 0
            booth_prem_qty_src = nvt_src.booth_prem_qty if nvt_src.booth_prem_qty else 0
            sent_booths_to_orders = '|'.join([n.order_num for n in gbfo_dsts])
            for nvt_dst in gbfo_dsts:
                booth_st_qty_dst = 0
                booth_prem_qty_dst = 0
                if nvt_dst.no_st_booths_from_order:
                    booth_st_qty_dst = nvt_dst.no_st_booths_from_order
                if nvt_dst.no_pr_booths_from_order:
                    booth_prem_qty_dst = nvt_dst.no_pr_booths_from_order
                if not nvt_dst.no_st_booths_from_order and not nvt_dst.no_pr_booths_from_order:
                    # 7/16/2026. destination booth doesn't specify whether we get premium or standard booth from source booth. that means source booth
                    #            must have only pure standard or premium.
                    if booth_st_qty_src:
                        booth_st_qty_dst = nvt_dst.quantity
                    else:
                        booth_prem_qty_dst = nvt_dst.quantity
                nvt_dst = nvt_dst._replace(booth_st_qty=booth_st_qty_dst,booth_prem_qty=booth_prem_qty_dst)
                full[nvt_dst.company] = nvt_dst
                booth_st_qty_src -= booth_st_qty_dst
                booth_prem_qty_src -= booth_prem_qty_dst
            nvt_src = nvt_src._replace(booth_st_qty=booth_st_qty_src,booth_prem_qty=booth_prem_qty_src,sent_booths_to_orders=sent_booths_to_orders)
            full[company_src] = nvt_src

        return

    def build_neaf_vendor_processed_dict_from_full(self,full):
        neaf_ss = {}
        for key,full_item in full.items():
            nvprocessed_tup = convert_neafVendorTup_to_processed(full_item)
            neaf_ss[key] = nvprocessed_tup
        return neaf_ss

    def buildTotalOrderNote(self,nvt):
        o_note = ''
        delete_original_order_note = False
        for o_item in nvt.order_note_attributes:
            name = o_item.get(NOTE_ATTRIBUTE_KEY())
            value = o_item.get('value')
            if name.startswith(DELETE_ORIGINAL_ORDER_NOTE):
                delete_original_order_note = True
            if name.startswith(ORDER_NOTE):
                delim = '\n' if o_note else ''
                o_note += '{0}{1}'.format(delim,value)
        order_note = '' if delete_original_order_note else nvt.order_note
        delim = '\n' if order_note else ''
        order_note += '{0}{1}'.format(delim,o_note)
        return order_note

    def build_invoice(self,nvt):
        margin = '    '

        invoice = '\n{0}ROCKLAND ASTRONOMY CLUB - NORTHEAST ASTRONOMY FORUM'.format(margin)
        if self.neaf_year:
            invoice += '\n{0}INVOICE for NEAF {1}'.format(margin,self.neaf_year)
        else:
            invoice += '\n{0}INVOICE for all NEAF purchases from {1} to {2}'.format(margin,self.created_at_min,self.created_at_max)
        now = datetime.datetime.now()
        invoice += '\n{0}As of {1}\n\n'.format(margin,now.strftime('%b %d, %Y  -  %#I:%M:%p'))

        addresses,names,phone_nums,emails = get_distinct_order_properties(nvt)
        for i,name in enumerate(names):
            invoice = item_count_description(margin,i,'Contact:',invoice)
            invoice += '{0}\n'.format(name)
        invoice +=  '{0}{1}\n'.format(margin,nvt.company)
        for i,addresstup in enumerate(addresses):
            invoice = item_count_description(margin,i,'Address',invoice)
            invoice = build_address_text(margin,addresses[i],invoice)
        for i,email in enumerate(emails):
            invoice = item_count_description(margin,i,'Email:',invoice)
            invoice += '{0}\n'.format(email)
        for i,phone_num in enumerate(phone_nums):
            invoice = item_count_description(margin,i,'Phone#:',invoice)
            invoice += '{0}\n'.format(phone_num)
        invoice += '\n\n'

        last_order_date = nvt.last_order_date
        # we removed option to send invoice in 2018. reactivate this block if needed.
        '''
        last_order_date = None
        if nvt.invoice_requested and nvt.invoice_requested.upper() == 'Y' :
            invoice += '{0}Customer requests they be sent an invoice.\n\n'.format(margin)
            last_order_date = nvt.last_order_date
        else:
            invoice += '{0}Customer does not want to be sent an invoice.\n\n'.format(margin)
            last_order_date = None
            '''

        if nvt.error:
            invoice += '{0}INVOICE ERROR:\n'.format(margin)
            errorMsg = nvt.error.replace('\n','\n' + margin)
            invoice += '{0}{1}\n\n'.format(margin,errorMsg)
        if nvt.declined_neaf_2023:
            invoice += '{0}DECLINED TO ATTEND NEAF 2023. ELIGIBLE TO ATTEND NEAF 2024.\n\n'.format(margin)
        order_note = self.buildTotalOrderNote(nvt)
        if order_note:
            invoice += '{0}ORDER NOTE:\n'.format(margin)
            o_n = displayLargeStringWithMargin(margin,order_note)
            invoice += '{0}\n\n'.format(o_n)
        if nvt.refund_note:
            invoice += '{0}REFUNDS ISSUED {1}:\n'.format(margin,nvt.refund_created_at)
            r_n = displayLargeStringWithMargin(margin,nvt.refund_note)
            invoice += '{0}\n\n'.format(r_n)
        if nvt.sales_comments:
            invoice += '{0}SALES COMMENTS:\n'.format(margin)
            invoice += '{0}{1}\n\n'.format(margin,nvt.sales_comments)
        if nvt.booth_comments:
            invoice += '{0}BOOTH COMMENTS:\n'.format(margin)
            invoice += '{0}{1}\n\n'.format(margin,nvt.booth_comments)

        order_detail_format = '{:4s}{:5s} {:16s} {:50s} {:8s} {:8s}\n'
        header1 = ('','Order','Order',    'SKU','Quantity','Unit')
        header2 = ('','No.',  'Date/Time','',   '',        'Price')
        header1 = order_detail_format.format(*header1)
        header1 = margin + header1[len(margin):]

        invoice += '{0}ORDERS\n'.format(margin)
        invoice += '{0}{1}\n'.format(margin,dash_string(len(header1)-4))

        invoice += header1
        header2 = order_detail_format.format(*header2)
        header2 = margin + header2[len(margin):]
        invoice += header2
        donation_orders = nvt.donation_order_from_attribute.split('|') if nvt.donation_order_from_attribute else []
        exclude_orders = nvt.exclude_order_from_attribute.split('|') if nvt.exclude_order_from_attribute else []
        found_donation_orders = []
        found_exclude_orders = []
        csym = getCurrencySymbolFromCode(nvt.currencyCode)
        for order_detail in nvt.order_details:
            csym_od = getCurrencySymbolFromCode(order_detail.currencyCode)
            if order_detail.order_num in donation_orders and 'sponsor' not in order_detail.sku:
                if order_detail.order_num in found_donation_orders:
                    continue
                found_donation_orders.append(order_detail.order_num)
                donation = str(round(nvt.order_num_to_donation_map[order_detail.order_num]))
                invoice_line = order_detail_format.format(margin, order_detail.order_num,goodDatetimeStr(order_detail.created_at), DONATION_SKU,'1','$'+donation)
            elif order_detail.order_num in exclude_orders:
                if order_detail.order_num in found_exclude_orders:
                    continue
                found_exclude_orders.append(order_detail.order_num)
                invoice_line = order_detail_format.format(margin, order_detail.order_num,goodDatetimeStr(order_detail.created_at), EXCLUDE_SKU,'','')
            else:
                invoice_line = order_detail_format.format(margin,order_detail.order_num,goodDatetimeStr(order_detail.created_at),order_detail.sku,
                                                          str(order_detail.quantity),csym_od + str(round(order_detail.unit_price_presentment)))
            invoice_line = margin + invoice_line[len(margin):]
            invoice += invoice_line

        total_discounts = str(round(nvt.total_discounts))
        #tdue = '${:.2f}'.format(nvt.total_due)
        discount_str = '   Discount:{0} with Discount Code {1}   '.format(total_discounts,nvt.discount_codes) if nvt.total_discounts else '   '

        invoice += '\n'
        total_due = csym +'0' if nvt.total_due_presentment is None else str(round(nvt.total_due_presentment)) + ' by check mailed to Rockland Astronomy Club'
        invoice += '{0}TOTAL COST:{1}{2}TOTAL PAID:{3}   TOTAL DUE:{4}\n'.format(margin,csym+str(round(nvt.total_cost_presentment)),discount_str,
                                                                                 csym+str(round(nvt.paid_presentment)),total_due)
        invoice += '{0}\n'.format(margin)

        invoice += '{0}SKU Descriptions\n'.format(margin)
        invoice += '{0}{1}\n'.format(margin,dash_string(41+1+98))
        sku_description_format = '{:4s}{:47s} {:98s}\n'
        skus_displayed = []
        for order_detail in nvt.order_details:
            if order_detail.sku in skus_displayed or order_detail.sku==REFUND:
                continue
            skus_displayed.append(order_detail.sku)
            invoice += sku_description_format.format(margin,order_detail.sku+':',order_detail.name)
        invoice += '\n'

        badge_names = nvt.badge_names
        badge_entitled_cnt = nvt.badge_entitled_cnt
        if badge_names:
            invoice += '{0}BADGE NAMES\n'.format(margin)
            invoice += '{0}{1}\n'.format(margin,dash_string(11))
            for bname in badge_names:
                invoice += '{0}{1}\n'.format(margin,bname)

        if len(badge_names)<badge_entitled_cnt:
            msg = '\n{0}You are entitled to {1} badge names but have requested only {2} badge names.\n'#\
            #"{0}Please place a free order for {3} additional badge names with 'Additional Badge beyond two included with Booth' $0 variant.\n"
            invoice += msg.format(margin,badge_entitled_cnt,len(badge_names)) # ,badge_entitled_cnt-len(badge_names))
        elif len(badge_names)>badge_entitled_cnt:
            msg = '\n{0}You are entitled to {1} badge names but have requested {2} badge names.\n'\
            "{0}Please order {3} additional badge names with 'Additional Badge beyond two included with Booth' product.\n"
            invoice += msg.format(margin,badge_entitled_cnt,len(badge_names),len(badge_names)-badge_entitled_cnt)

        invoice += '\n'
        values = str(nvt.prize_donation_value).split('|')
        donations = str(nvt.prize_donation).split('|')
        if nvt.prize_donation or nvt.prize_donation_value:
            invoice += '{0}DONATION VALUE and DESCRIPTION\n'.format(margin)
            invoice += '{0}{1}\n'.format(margin,dash_string(30))

            for value,donation in zip(values,donations):
                invoice += '{:4s}{:<14s}     {:s}\n'.format(margin,value,donation)

            invoice += '\n'

        if nvt.get_booths_from_order:
            invoice += f'Booths in this order come from order #{nvt.get_booths_from_order}\n'

        # this function only returns last_order_date for those customers requesting an invoice. It is used to run function that outputs
        # all invoices for customers that want only for customers whose last order beyond a given date
        return invoice,last_order_date

    def build_invoices(self,full):
        vendor_invoices = {}
        vendor_last_order_date_map = {}
        for key,nvt in full.items():
            vendor_invoices[key],last_order_date = self.build_invoice(nvt)
            if last_order_date:
                vendor_last_order_date_map[key] = last_order_date
        return vendor_invoices,vendor_last_order_date_map

    def buildOrderNumToCompanyMap(self,raw):

        # 2/6/2022. this function builds self.orderNumToCompanyMap dict which is used inside of build_neaf_vendor_full_dict_from_shopify to combine items in raw dict(keyed by order_num)
        # into items in full dict(keyed by company name)

        print('\nENTERING  buildOrderNumToCompanyMap {0}'.format(STARS))

        self.orderNumToCompanyMap.clear()
        orderNumToCompanyMap,self.error = buildOrderNumToCompanyMap(raw)
        if self.error:
            print(f'Error from NEAFVendor.buildOrderNumToCompanyMap:\n{self.error}\n')
        # we're done
        self.orderNumToCompanyMap.update(orderNumToCompanyMap)

        print('EXITING buildOrderNumToCompanyMap {0}\n'.format(STARS))
        return

    def get_nv_collections(self):

        # the key for raw is order_num

        if self.error:
            return
        self.print_and_save('Completed loading raw data dict of size {0}'.format(len(self.raw)))
        # the key for full is company. raw keyed by order_num. this function sums order_nums into companies

        # build self.orderNumToCompanyMap which is used inside build_neaf_vendor_full_dict_from_shopify to map self.raw(keyed by orderNum) to full(keyed by company).
        self.buildOrderNumToCompanyMap(self.raw)
        # build_neaf_vendor_full_dict_from_shopify build full from raw.
        full = self.build_neaf_vendor_full_dict_from_shopify(self.raw)
        self.adjustBoothQuantitiesForTransfersAndUpgrades(full)

        self.print_and_save('converted raw data dict of size {0} to full data dict of size {1}'.format(len(self.raw),len(full)))
        neaf_ss = self.build_neaf_vendor_processed_dict_from_full(full)

        vendor_invoices,vendor_last_order_date_map = self.build_invoices(full)
        company_badge = buildCompanyBadgeList(full)
        last_order_date_vendors_map = buildLastOrderDateVendorsMap(vendor_last_order_date_map)
        self.nv_collections =  NeafVendorCollectionsTup(self.raw, neaf_ss, full, vendor_invoices, vendor_last_order_date_map, last_order_date_vendors_map, company_badge)
        self.print_and_save('data load complete')
        return

    def buildFromPriorShopifyLoad(self):
        # 12/30/2022. buildFromPriorShopifyLoad assumes self.rawOrdersTupList is already built by shopifyOrdersFromGraphQL. buildFromPriorShopifyLoad builds self.nv_collections like this:
        #             self.rawOrdersTupList -> self.raw -> self.nv_collections

        if self.error:
            self.error = 'Cannot run NEAFVendor.buildFromPriorShopifyLoad(). NEAFVendor has pre-existing error:\n{0}'.format(self.error)
            return

        # 12/30/2022. this function populates self.raw from self.rawOrdersTupList which was built in shopifyOrdersFromGraphQL.
        self.convertShopifyOrdersToRacOrders()

        self.orderNumToCompanyMap = {}
        self.nv_collections = None
        self.get_nv_collections()
        self.target_company = None
        return

    def shopifyLoad(self):

        # 12/30/2022. load from shopify and populate all in-memory representations needed for full functionality.

        if self.error:
            self.error = 'Cannot run NEAFVendor.shopifyLoad(). NEAFVendor has pre-existing error:\n{0}'.format(self.error)
            return
        self.shopifyOrdersFromGraphQL()

        if self.error:
            self.error = 'Failure in NEAFVendor.shopifyLoad().\n{0}'.format(self.error)
            return

        # 12/30/2022. buildFromPriorShopifyLoad assumes self.rawOrdersTupList is already built by shopifyOrdersFromGraphQL.
        #             buildFromPriorShopifyLoad builds self.nv_collections like this:
        #             self.rawOrdersTupList -> self.raw -> self.nv_collections
        self.buildFromPriorShopifyLoad()
        print('memory usage at exit from NEAFVendor.shopifyLoad after all loading is done : {0}'.format(tracemalloc.get_traced_memory()))

        return

    def get_target_companies(self,search_key):
        target_companies = []
        self.target_company = None
        clean_key = convertToKey(search_key)
        for company,invoice in self.nv_collections.vendor_invoices.items():
            clean_invoice = convertToKey(invoice)
            if clean_key in clean_invoice:
                target_companies.append(company)
        if len(target_companies)==1:
            target_companies_text = "Search key of '{0}' exists in company '{1}'".format(search_key,target_companies[0])
        else:
            if target_companies:
                target_companies = sorted(target_companies, key=lambda s: s.lower())
                target_companies_text = "Search key of '{0}' exists in the following {1} companies:".format(search_key,len(target_companies))
            else:
                target_companies_text = "Search key of '{0}' does not exist in any company".format(search_key)
            i = 0
            for company in target_companies:
                i += 1
                nvt = self.nv_collections.full[company]
                target_companies_text += '\n{0:<3}: {1:<60}    last_order_date: {2:<10}    order_num: {3}'.format(i,company,nvt.last_order_date,nvt.order_num)
            if i:
                target_companies_text += '\nChoose one to display by entering 1 through {0} as company item number'.format(i)
        return target_companies,target_companies_text

    def get_target_company_invoice(self,target_companies,item_num_str):
        if not target_companies:
            target_company_invoice = 'No list of candidate companies yet chosen. Enter and process a company key.\n'
        elif not item_num_str.isdigit() or not (1 <= int(item_num_str) <= len(target_companies)):
            target_company_invoice = 'Item number of {0} is invalid. Must be number from 1 to {1}'.format(item_num_str,len(target_companies))
            self.target_company = None
        else:
            self.target_company = target_companies[int(item_num_str)-1]
            target_company_invoice = self.nv_collections.vendor_invoices[self.target_company]
        return self.target_company,target_company_invoice

    def output_nvt_csv(self,nv_src_item):
        if nv_src_item == NEAF_VENDOR:
            nvt_dict = self.nv_collections.neaf_ss
        elif nv_src_item == NEAF_FULL:
            nvt_dict = self.nv_collections.full
        elif nv_src_item == NEAF_RAW:
            nvt_dict = self.nv_collections.raw
        elif nv_src_item == NEAF_COMPANY_BADGE:
            nvt_dict = self.nv_collections.company_badge

        tdir = RAC_DIR()
        now = datetime.datetime.now()
        now_str = now.strftime('%Y-%m-%d_%H-%M-%S')
        fname = os.path.join(tdir,'neaf_output','{0}_{1}.csv'.format(nv_src_item,now_str))

        os.makedirs(os.path.dirname(fname),exist_ok=True)

        company_name_fields = ['company','name']
        header = NeafSSTup._fields if nv_src_item == NEAF_VENDOR else (company_name_fields if nv_src_item == NEAF_COMPANY_BADGE else NeafVendorTup._fields)
        new_header = []
        for hd in header:
            hd = hd.replace('_','\n')
            new_header.append(hd)
        with open(fname,'w',encoding="utf-8-sig") as nvt_csv_file:
            wr = csv.writer(nvt_csv_file, quoting=csv.QUOTE_ALL,lineterminator='\n')
            wr.writerow(new_header)
            for key,nvt in nvt_dict.items():
                writerow_UnicodeEncodeError(wr,list(nvt))
        msg = f'NEAF vendor management csv file with {len(nvt_dict.items())} items written to {fname}\n'
        return msg

    def show_neaf_vendor_dicts(self):
        # TODO I don't think this works
        msg = show_dict(self.nv_collections.raw,'neafVendorSrc.basic')
        msg += show_neaf_vendor_dict(self.nv_collections.processed)
        return msg

    def show_and_save_all_invoices(self,as_pdf):
        all_invoices_to_print = ''
        cnt = 0
        max_cnt = len(self.nv_collections.vendor_invoices)
        print('Saving {0} invoices'.format(max_cnt))
        for company,invoice in self.nv_collections.vendor_invoices.items():
            cnt += 1

            save_message_one,subdir_path,fname = save_invoice(company,invoice,as_pdf,subdir='all_invoices')
            msg = "{0:3d}: {1}".format(cnt,save_message_one)
            print(msg)
            all_invoices_to_print += msg + '\n'

        save_message = 'Saved {0} invoices to {1}.'.format(cnt,subdir_path)
        return all_invoices_to_print,save_message

    def save_vendor_sign_in_sheet(self):

        tdir = tempfile.gettempdir()
        now = datetime.datetime.now()
        now_str = now.strftime('%Y-%m-%d_%H-%M-%S')
        fname = os.path.join(tdir,'neaf_output','neaf_vendor_sign_in_{0}.csv'.format(now_str))

        os.makedirs(os.path.dirname(fname),exist_ok=True)

        # build alphabetic list of company names
        key_to_company_map = {}
        for key in self.nv_collections.full.keys():
            key_to_company_map[key.upper()] = key


        header = ('Name of\nCompany','Booth\nLocation','Arrival\nTime','Electricity','Wifi','# of Badges\nEntitled',
            '# of Badges\nRequested','# of Badges\nin Envelope','Shipping Requested','Shipping In','Shipping Out','Door Prize')
        with open(fname,'w',encoding="utf-8-sig") as nvsi_csv_file:
            wr = csv.writer(nvsi_csv_file, quoting=csv.QUOTE_ALL, lineterminator='\n')
            wr.writerow(header)
            for key in sorted(key_to_company_map.keys()):
                company = key_to_company_map[key]
                nvt = self.nv_collections.full[company]
                vendor_sign_in_row = get_vendor_sign_in_row(nvt)
                writerow_UnicodeEncodeError(wr,vendor_sign_in_row)
        msg = 'NEAF Vendor Sign-In sheet written to '+fname
        return msg

    def save_all_requested_invoices_beyond_date(self,dstr,as_pdf):
        subdir,dt,error_msg = invoice_subdir(dstr)
        if error_msg:
            return error_msg
        i=0
        for company,date in self.nv_collections.vendor_last_order_date_map.items():
            if date<= dt:
                continue
            invoice = self.nv_collections.vendor_invoices[company]
            i += 1
            invoice_msg,subdir_path,fname = save_invoice(company,invoice,as_pdf,subdir)
        if not i:
            msg = 'Did not find any invoices with last order date greater than {0}'.format(dstr)
            return msg
        msg = 'Saved {0} invoices to folder {1}'.format(i,subdir_path)
        return msg

    def chooseMandatoryOrderForEditItem(self, edit_item, nvt, action_desc_tup):

        # 12/20/2022. the edit items in DESC_FOR_ACTION_NEEDING_1_ORDER must be applied to 1 order in a company. this function makes that choice.

        # 11/13/2022. these 3 edit actions need to be applied to individual orders under a company.
        #             if the company has more than 1 order choose the target order here for actions company, donation, exclude.

        # 2/16/2020.  a new company name must be applied to a single order.
        #             if we inappropriately combine unrelated companies in multiple orders under a single company we must assign an alternate company name to one of the orders.
        #             if more than 1 order for a company we must choose 1. an example is orders 9239 and 9240 for Software Bisque

        # 11/13/2022. the whole point of the exclude action is to exclude some orders under a company. an example is questar orders for NEAF 2023. order 9308(2/6/2020) was a pay by check.
        #             Ed never deposited check and they re-ordered with order 11334(2/15/2022). we want to exclude 9308 and use 11334.

        # 11/13/2022. celestron, orders 9368(2/19/20) and 9132(12/17/19) and astrophysics, order 9328(2/11/20) converted all of these orders to donations.

        order_nums = nvt.order_num.split('|')
        action_desc = action_desc_tup[0]
        onlyNeedOrderNum = action_desc_tup[1]

        if len(order_nums) > 1:
            msg = "There are {0} orders of {1} under this company. The 'Edit Action' of '{2}' has an invalid 'Edit Item' of '{3}'. "\
                  "It must be assigned to one of those orders by setting the 'Edit Item' like this:"
        else:
            msg = "There is {0} order of {1} under this company. The 'Edit Action' of '{2}' has an invalid 'Edit Item' of '{3}'. "
        msg = msg.format(len(order_nums),nvt.order_num,action_desc,edit_item)
        i = 1
        for o_n in order_nums:
            o_n = o_n.strip()
            if onlyNeedOrderNum:
                if len(order_nums) > 1:
                    cmt = "\nEnter\n{0}\nin the 'Edit Item' field to use order {1}.".format(i,o_n)
                else:
                    cmt = "\nDo not enter anything in the 'Edit Item' field. This action has no 'Edit Item'."
            else:
                cmt = "\nEnter\n{0} {1}\nin the 'Edit Item' field to use order {2}.".format(i,edit_item,o_n)
            msg += cmt
            i += 1
            msg += '\n'

        toks = edit_item.split()
        if onlyNeedOrderNum:
            if len(order_nums) > 1:
                if len(toks) != 1 or not toks[0].isdigit():
                    return edit_item, None, None, msg
            if len(order_nums) == 1:
                if toks:
                    return edit_item, None, None, msg
                else:
                    # 1/29/2022. no need to force user to enter integer first token to specify order_num since there is only 1 order in this company, just use 1.
                    toks = ['1']
        else:
            if len(toks)<2 or not toks[0].isdigit():
                if len(order_nums) == 1:
                    # 1/29/2022. no need to force user to enter integer first token to specify order_num since there is only 1 order in this company, just use 1.
                    toks = ['1'] + toks
                else:
                    return edit_item,None,None,msg

        order_num_index = int(toks[0]) - 1
        if order_num_index < 0 or order_num_index > len(order_nums)-1:
            return edit_item,None,None,msg

        edit_item = N_A if onlyNeedOrderNum else ' '.join(toks[1:])
        order_ids = nvt.order_id.split('|')
        order_id = order_ids[order_num_index]
        order_num = order_nums[order_num_index].strip()
        msg = ''

        return edit_item,order_id,order_num,msg

    def chooseOrderForEditItem(self,nvt):
        # TODO choice of order_num is arbitrary for all edit items not in DESC_FOR_ACTION_NEEDING_1_ORDER. choose that arbitrary order_num here.
        order_nums = nvt.order_num.split('|')
        if len(order_nums) == 1:
            # only 1 order in this company. no need to choose.
            return nvt.order_id,nvt.order_num
        order_ids = nvt.order_id.split('|')
        # 12/27/2022. choose the order of lowest order number to add order note attributes for items like badge edit that don't care which order they end up in.
        #             it kind of makes sense because most first orders are for booth and thats typically the main order for a company.
        order_num = sorted(order_nums)[0]
        idx = order_nums.index(order_num)
        order_id = order_ids[idx]
        return order_id, order_num

    def deleteOriginalBadge(self,edit_item,badge_names_orig,ona):
        msg = ''
        if not edit_item.isdigit() or int(edit_item) < 1 or int(edit_item) > len(badge_names_orig):
            msg = "Entry of '{0}' to delete original badge name is invalid. Must be one of these integers that correspond to these names:".format(edit_item)
            i = 0
            for bn in badge_names_orig:
                i += 1
                msg += '\n{0}: {1}'.format(i,bn)
            msg += '\n'
            return edit_item,msg

        badgeNameToBeDeleted = badge_names_orig[int(edit_item)-1]

        for o_item in ona:
            name = o_item.get(NOTE_ATTRIBUTE_KEY(),ERROR)
            value = o_item.get('value',ERROR)
            if name.startswith(DELETE_ORIGINAL_BADGE_ACTION):
                if value == badgeNameToBeDeleted:
                    msg = "Entry of '{0}' is invalid. It corresponds to original badge name of '{1}' but this badge name has already been deleted.".format(edit_item,value)

        return badgeNameToBeDeleted,msg

    def deleteOriginalOrderItem(self,nvt,edit_item,ona):
        msg = ''
        if edit_item:
            msg = "Entry of '{0}' is invalid. No Edit Item allowed for Edit Action of deleting original order note.".format(edit_item)
        else:
            for bn in ona:
                name = bn.get(NOTE_ATTRIBUTE_KEY())
                if name.startswith(DELETE_ORIGINAL_ORDER_NOTE):
                    msg = "Edit Action of 'delete original order note' is invalid. Its already been entered. It can only be entered once per company."
                    break
        if not nvt.order_note:
            msg = "This Edit Action not valid for this company. It has no Order Note. Can only delete an original Order Note if one exists."
        return msg

    def deletePriorEdit(self,edit_item,ona):
        msg = ''
        if not len(ona):
            msg = 'There are no edits. There is nothing to delete.'
            return msg
        if not edit_item.isdigit() or int(edit_item) < 1 or int(edit_item) > len(ona):
            msg = "Entry of '{0}' to delete prior edit is invalid. Must be one of these integers that correspond to these edits:".format(edit_item)
            i = 0
            for bn in ona:
                name = bn.get(NOTE_ATTRIBUTE_KEY(),ERROR)
                value = bn.get('value',ERROR)
                i += 1
                msg += '\n{0}  --  {1}:{2}'.format(i,name,value)
            return msg + '\n'

        del ona[int(edit_item) - 1]

        return msg

    def order_note_attributes_comment(self,msg,nvt,comment_suffix=''):
        ona = nvt.order_note_attributes
        if ona:
            msg += '\n\nAll edit items{0}:'.format(comment_suffix)
            i=0
            for ona_dict in ona:
                i += 1
                msg += '\n{0}: {1}  --  {2}'.format(i,ona_dict.get(NOTE_ATTRIBUTE_KEY(),ERROR),ona_dict.get('value',ERROR))
        else:
            msg += '\n\nNo edit items entered{0}'.format(comment_suffix)
        msg += '\n'
        return msg

    def confirmNotDuplicate1OrderEdit(self,ona,action,order_num):
        msg = ''
        for ona_dict in ona:
            name = ona_dict[NOTE_ATTRIBUTE_KEY()]
            value = ona_dict['value']
            toks = name.split('_')
            action2 = '_'.join(toks[:-2])
            order_num2 = toks[-2]
            if action == action2 and order_num == order_num2:
                msg = "'Edit Action' of '{0}' for order_num {1} is invalid. We already have an order_note_attribute item of {2} with value '{3}'.\n".format(action,order_num,name,value)
                break
        return msg

    def rebuildFullandRawWithOrderNoteAttributes(self,order_num_to_order_note_attributes_map):

        # 2/16/2020. must rebuild nvt.order_note_attributes with the new ona and then reassign to self.nv_collections.full[self.target_company]. this is needed to do multiple calls
        # to this function for purposes of multiple edits without have to reload between each edit. also assign to self.raw[order_num]

        # rebuild self.raw with the new order_note_attributes
        raw = {}
        for order_num,ona in order_num_to_order_note_attributes_map.items():
            nvt_raw = self.raw[order_num]
            nvt_raw = nvt_raw._replace(order_note_attributes=ona)
            self.raw[order_num] = nvt_raw
            raw[order_num] = nvt_raw

        full = self.build_neaf_vendor_full_dict_from_shopify(raw)
        self.nv_collections.full.update(full)

        return self.nv_collections.full[self.target_company]

    def confirmActionsAreCompatible(self,ona,action):
        msg = ''
        for ona_dict in ona:
            ea = ona_dict[NOTE_ATTRIBUTE_KEY()]
            editAction = '_'.join(ea.split('_')[:-2])
            if editAction in INCOMPATIBLE_ACTIONS:
                msg = "'Edit Action' of '{0}' is incompatible with previously entered 'Edit Action' of '{1}'. Only 1 of the actions {2} can be applied to an order.\n"
                msg = msg.format(action,ea,INCOMPATIBLE_ACTIONS)
                break
        return msg

    def editItemCanBeMissing(self,edit_action):
        action = EDIT_ACTION_TO_ACTION_MAP[edit_action]
        descForActionTup = DESC_FOR_ACTION_NEEDING_1_ORDER[action]
        return descForActionTup[1]

    def applyOrderNoteAttributeEdit(self,edit_action,edit_item):

        # 1/26/2025. 2 critical functions for processing order_note_attributes are applyOrderNoteAttributeEdit and useOrderNoteAttributeEdits
        # 12/19/2022. critical function that edits order_note_attributes under a company and persists those edits under an order.
        # must work well with mergeOrderNoteAttributes that builds merged order_note_attributes in self.nv_collections.full from order_note_attributes in self.nv_collections.raw.

        # 4/9/2026. TODO enhance applyOrderNoteAttributeEdit to skip full reload and have it rebuild NEAFVendor collections.

        if not self.target_company:
            msg = 'No target company has been chosen. Cannot use this function until company chosen.'
            return msg
        if edit_action not in VALID_EDIT_ACTIONS:
            msg = "'Edit Action' of '{0}' is invalid. Most be one of {1}.".format(edit_action,VALID_EDIT_ACTIONS)
            return msg
        edit_item = edit_item.strip()
        if not edit_item and not self.editItemCanBeMissing(edit_action):
            msg = "'Edit Item' field is missing. Cannot use this function without an 'Edit Item'.\n"
            return msg
        nvt = self.nv_collections.full[self.target_company]
        ona = nvt.order_note_attributes
        ona = [] if not ona else ona # this is needed because company with no previous edits has initial ona of {} but need to convert to list because that's the form when note_attributes exist.
        entitled_cnt = nvt.badge_entitled_cnt
        badge_names = nvt.badge_names
        normalized_badge_names = getNormalizedBadgeNames(badge_names)
        n_edit_item = convertToKey(edit_item)
        badge_names_orig = nvt.badge_names_orig

        action = EDIT_ACTION_TO_ACTION_MAP.get(edit_action)

        if action == BADGE and normalized_badge_names.get(n_edit_item):
            msg = "'Edit Action' of '{0}' with 'Edit Item' of '{1}' is invalid. That badge name already exists. Duplicates not allowed.\n".format(edit_action,edit_item)
            return msg

        if action == DELETE_ORIGINAL_BADGE:
            edit_item,msg = self.deleteOriginalBadge(edit_item,badge_names_orig,ona)
            if msg:
                return msg

        if action == DELETE_ORIGINAL_ORDER_NOTE:
            msg = self.deleteOriginalOrderItem(nvt,edit_item,ona)
            if msg:
                return msg

        if action == EMAIL:
            validEmail = False
            if ' ' not in edit_item:
                toks = edit_item.split('@')
                if len(toks) == 2:
                    toks = toks[1].split('.')
                    if len(toks) == 2:
                        validEmail = True
            if not validEmail:
                msg = "'Edit Action' of '{0}' with 'Edit Item' of '{1}' is invalid. The requested email is not in valid form.\n".format(edit_action,edit_item)
                return msg

        action_desc_tup = DESC_FOR_ACTION_NEEDING_1_ORDER.get(action)
        if action_desc_tup:
            edit_item,order_id,order_num,msg = self.chooseMandatoryOrderForEditItem(edit_item, nvt, action_desc_tup)
            if msg:
                return msg
            msg = self.confirmNotDuplicate1OrderEdit(ona,action,order_num)
            if msg:
                return msg
            if action == NAME and len(edit_item.split()) < 2:
                msg = "Name of '{0}' is invalid. Must have a first name and last name.\n".format(edit_item)
                return msg
        elif action != DELETE_PRIOR_EDIT:
            order_id,order_num = self.chooseOrderForEditItem(nvt)

        if action in INCOMPATIBLE_ACTIONS:
            msg = self.confirmActionsAreCompatible(ona,action)
            if msg:
                return msg

        if action == DELETE_PRIOR_EDIT:
            msg = self.deletePriorEdit(edit_item,ona)
            if msg:
                return msg
        else:
            # 12/20/2022. the sequence number in key isn't needed. we put in dummy value of 999. its reset appropriately in updateOrderNoteAttributes by normalizeOrderNoteAttributesSuffixes
            key = '{0}_{1}_999'.format(action,order_num)
            new_ona = {NOTE_ATTRIBUTE_KEY():key,'value':edit_item}
            ona.append(new_ona)

        msg,order_num_to_order_note_attributes_map = updateOrderNoteAttributes(nvt.order_num,self.order_id_to_order_num_map,ona)
        if msg:
            return msg

        # 2/16/2020. must rebuild nvt.order_note_attributes with the new ona and then reassign to self.nv_collections.full[self.target_company]. this is needed to do multiple calls
        # to this function for purposes of multiple edits without have to reload between each edit. also assign to self.raw[order_num]
        nvt = self.rebuildFullandRawWithOrderNoteAttributes(order_num_to_order_note_attributes_map)

        if not msg:
            # 12/4/2022. we have successfully edited an item. build comment for displaying the new edits.
            msg = self.order_note_attributes_comment(msg,nvt,comment_suffix=' after edit.')

        if action == BADGE and len(normalized_badge_names) >= entitled_cnt:
            msg += '\n*******\nWARNING\n*******\nThis company is entitled to {0} badges but by adding this new badge name they have {1} badges.\n'.format(entitled_cnt,len(normalized_badge_names)+1)

        return msg

    def see_all_edit_items(self):
        if not self.target_company:
            msg = 'No target company has been chosen. Cannot use this function until company chosen.'
            return msg
        nvt = self.nv_collections.full[self.target_company]
        if nvt.badge_names_orig:
            msg = 'Original badge names entered with order:'
            i=0
            for bn in nvt.badge_names_orig:
                i += 1
                msg += '\n{0}: {1}'.format(i,bn)
        else:
            msg = 'No badges entered with order.'

        if nvt.order_note:
            o_n = displayLargeStringWithMargin('',nvt.order_note)
            msg += '\n\nOriginal Order Note:\n{0}'.format(o_n)
        else:
            msg += '\n\nNo original Order Note.'

        orderNumSet = set()
        msg += '\n\nOrder summary:'
        i = 0
        for odt in nvt.order_details:
            order_num = odt.order_num
            if order_num in orderNumSet:
                continue
            i += 1
            orderNumSet.add(order_num)
            ord_nvt = self.raw[order_num]
            nfop = getNamesFromOrderProperty(ord_nvt)
            msg2 = '\n{0}: order_num:{1}, company:{2}, company_from_property:{3}, company_from_attribute:{4}, email:{5}, name:{6}, name_from_attribute:{7}, names from order_properties:{8}'
            msg += msg2.format(i,order_num,ord_nvt.company,'|'.join(ord_nvt.company_from_property),ord_nvt.company_from_attribute,ord_nvt.email,ord_nvt.name,ord_nvt.name_from_attribute,nfop)

        msg = self.order_note_attributes_comment(msg,nvt)

        return msg

    def see_original_badge_order(self):
        if not self.target_company:
            msg = 'No target company has been chosen. Cannot use this function until company chosen.'
            return msg
        nvt = self.nv_collections.full[self.target_company]
        if not nvt.badge_names_orig:
            msg = "NO BADGES ORDERED. That's odd."
        else:
            msg = ''
            i = 0
            delim = ''
            for bn in nvt.badge_names_orig:
                i += 1
                msg += '{0}{1}: {2}'.format(delim,i,bn)
                delim = '\n'
        return msg

    def show_hints(self,spt):
        neaf_year_str = 'NEAF year being processed: {0}'.format(self.neaf_year) if self.neaf_year else \
            'Processing all NEAF invoices from {0} to {1}'.format(self.created_at_min,self.created_at_max)
        # 2/1/2020. drop any email errors since this isn't a feature currently in use
        #err_str = 'email credentials error:\n    '+spt.error if spt.error else ''
        delim = '\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n'
        err_str = '\n' + delim + self.error + delim + '\n' if self.error else ''
        startup_parameters_str = str(spt)
        nvc = self.nv_collections
        company_badge_len = len(nvc.company_badge)
        lod_keys = sorted(nvc.last_order_date_vendors_map.keys())
        nv_collections_str = '{0} badges requested. 1st order date:{1}, latest order date:{2}'
        firstOrderDate = lod_keys[0] if lod_keys else 'MISSING'
        latestOrderDate = lod_keys[-1] if lod_keys else 'MISSING'
        nv_collections_str = nv_collections_str.format(company_badge_len,firstOrderDate,latestOrderDate)
        hints = '''
----------------------------------------------------------------------------------------------------------------------

{0}

Number of companies that have registered: {1}
Number of total orders those companies have submitted: {2}
{3}{4}
{5}
Input args passed in from rac_launcher:  {6}
{7}
Current target_company:'{8}'
{9}
All NEAF Vendor Info accessed from Shopify:
1) All skus that start with 'neaf_vendor' used to build NEAF vendor info
2) Date option for either saving or emailing invoices only selects invoices with last order date greater than
   the entered date.
3) THE EMAIL FEATURE ISN'T CURRENTLY ACTIVE but if it where there are 2 email choices:
   a) email all actual invoices selected but only to the cc list. Used for testing.
   b) email to the actual companies.
4) Format for email argument passed to rac_launcher.py in rac_launcher.bat:
   <date> <email sender> <email sender pwd> <optional comma separated cc list>
   
{10}

{11}

---------------------------------------------------------------------------------------------------------------------
    '''
        refundNotesStr = '{0} REFUND NOTES:\n{1}'.format(len(self.refundNotes),'\n'.join(self.refundNotes)) if self.refundNotes else 'No REFUND NOTES'
        editNotesStr = '{0} Note Attributes:\n{1}'.format(len(self.note_attributes_Notes),'\n'.join(self.note_attributes_Notes)) if self.note_attributes_Notes else 'No Note Attributes'
        hints = hints.format(neaf_year_str,len(self.nv_collections.vendor_invoices),len(self.nv_collections.raw),'','','',startup_parameters_str,nv_collections_str,
                             self.target_company,err_str,refundNotesStr,editNotesStr)
        return hints

def set_as_pdf(as_pdf,option_args):
    if not option_args:
       msg = "Trying to set new as_pdf that's BLANK. That's invalid. No action will be taken."
       return as_pdf,msg
    o_args = option_args if option_args in (True,False) else option_args.strip().lower()
    if o_args not in ('y','n',True,False):
       msg = "Trying to set new as_pdf with '{0}'. That's invalid. Must be 'y' or 'n'.".format(o_args)
       return as_pdf,msg
    as_pdf_new = o_args if option_args in (True,False) else (True if o_args == 'y' else False)
    if as_pdf_new == as_pdf:
        msg = " No change will be made to as_pdf. New and old values are both {0}".format(o_args)
        return as_pdf,msg
    msg = "Changing as_pdf to new value of '{0}'.".format(o_args)
    return as_pdf_new,msg





