
# valid sku keys
from consts import MEMBERSHIP,DONATION,NEAF_ATTEND,NEAF_ATTEND_RAFFLE,NEAIC_ATTEND,RAD,HSP,HSP_RAFFLE,RLS,SSP,DOOR_PRIZE,MERCH,NEAF_VENDOR,ADMIN,ALL
from consts import SHOP_NAME,ADMIN_API_VERSION,NEAF_YEAR_DEFAULT,SATURDAY,NEAF_YEAR_2026,HSP_YEAR_DEFAULT
from credentials import Credentials
from orders import Orders
from door_prize import DoorPrize
from neaf_vendor import NEAFVendor
from hsp_attendees import HSPAttendees
from neaf_vendor_utils import save_invoice
from utils import load_franks_rac_membership_spreadsheet

import tracemalloc
tracemalloc.start()
print('At debug_utils module startup we have current:{0}, peak:{1} from tracemalloc.get_traced_memory()'.format(*tracemalloc.get_traced_memory()))

refund_examples = [
    ('2025-01-19', '2025-01-20', 15317), # Amateur Astronomers Assoc. of Pittsburgh, #15317(1/19/2025). refund of $306 to whole order
    ('4/29/2019', '4/30/2019', 8948),  # for SSP Travis Adams had refund_line_items of membership refunded but kept SSP chicken barbecue lineitem.
    ('3/2/2021', '3/3/2021', 10638),  # company is AAPOD2. dollars on order. refunded full $20 on logo and link
    ('1/22/2020', '1/22/2020', 9239),  # dollars on order. software bisque. refunded $50 on badge.
    ('1/26/2023','1/27/2023', 11709),  # a full refunded order for IOptron for $2612.
    ('1/27/2020', '1/28/2020', 9255),  # Rowan Engineering. attempted but failed refund of entire order of $534
    ('3/6/2020', '3/7/2020', 9481),  # Nimax refunded 3/6/2020. table went from 5 to 2 for $165 refunded. chairs went 4 to 2 for $24 refunded. refund 2 badges for $100.
                                     # failed to refund $128 years later on 4/14/2023.
    ('1/30/2024', '1/31/2024', 13695), # Software Bisque had 2 orders, 13704|13695. has company name and badge name edits. only #13695 had refund. $1130 for 2 booths out of $2178 total refunded
    ('1/31/2024', '2/1/2024', 13712), # Explore Scientific had 2 orders, 13712|13717. refunded 8 standard booths in 13712 and he bought 8 premium in 13717.
    ('11/20/2023','11/21/2023',13415), # Airy Disk. full refund of $1442 then another order with pay by check.
    ('3/29/2020','3/30/2020',9541),    # Don Spong. refund of NEAF Virtual Experience ticket.
    ('2/26/2020','2/27/2020',9404),    # Nimax. refunded $402, full order refunded. intent was standard booth, not premium.
    ('2/20/2019','2/21/2019',7618),    # QHYCCD. refunded $396, full order refund of booth.
]

def accesshopify_by_date_range_and_sku(ind=8,):

    # 1/2/2025. this block returns 7 orders
    order_to_debug = None
    product_type = None # ALL # ADMIN # DONATION # NEAF_VENDOR # ALL
    created_at_min = '2021-03-02'
    created_at_max = '2021-03-02'

    # 1/8/2025. zwo is missing $200 live stream order because I left out sku. I just added it to product as neaf_vendor_sponsor_live_stream.
    # order_to_debug = 15252
    # product_type = None
    # created_at_min = None  # '2019-04-29'
    # created_at_max = None  # '2019-04-29'

    created_at_min = None
    created_at_max = None
    order_to_debug = refund_examples[ind][2]

    # this block for Thomas Simstad, New Mexico Skies high priced order for $2000 of neaf_vendor_sponsor_live_steam
    # created_at_min = None # '2025-01-31'
    # created_at_max = None # '2025-02-01'
    # order_to_debug = 15436 # 15404

    # bought raffle ticket with swipper and need to get phone number off timeline
    created_at_min = '2025-01-01'
    created_at_max = None
    #order_to_debug = '13167' # '13136' # '13167'

    # 15569, skywatcher has 848-248-0424 in old phone_num but MISSING in new.
    # 15472, Willie Yee has SIDE DOOR in old address2 but MISSING in new.
    # 15478, Frank      has address2 Jackson, NJ old but Pomona with 2C in address2 in new
    # 15334, Sarah has blank for address2 and phone_num but MISSING for both in new (REPAIRED)
    # 15512, funny looking X in address.
    # order_to_debug = '15512'

    # this block loads 22 orders from #15397 to #15418. its good example to test processing of many orders in single query.
    # created_at_min = '2025-01-31'
    # created_at_max = '2025-02-01'
    # order_to_debug = None
    # product_type = ALL

    # 1/31/2026. this block used to test new donation field of Donor Name(s) in custom attribute. #17426 has Name(s) of Donor: Chaim and Rivka Shmuelowitz
    created_at_min = '2025-01-01'
    created_at_max = '2026-02-01'
    product_type = DONATION
    order_to_debug = None

    verbose = False
    orders = Orders(product_type,order_to_debug=order_to_debug,verbose=verbose)
    if orders.error:
        print(orders.error)
        return
    orders.shopifyLoad(created_at_min=created_at_min,created_at_max=created_at_max)

    msg = orders.error if orders.error else orders.show_dicts()
    print(msg)
    print(orders.dump_to_csv())

    #accessOrders = AccessOrders( sku_key,created_at_min,created_at_max=None, order_to_debug, verbose)

    return

def neafvendor_management_ss_and_invoices_to_console_from_orders(ind=12):

    from neaf_vendor import NEAFVendor
    neaf_year = '' # '2024'
    verbose = False

    created_at_min = None
    created_at_max = None
    order_to_debug = refund_examples[ind][2]

    # missing oberwerk donation value on s/s.
    # created_at_min = '2019-04-29'
    # created_at_max = created_at_min
    # XXX 2/18/2024. supporting a single order_to_debug works fine for Oberwerk since they only did one order. That won't work for other vendors.
    #                support multiple orders for single vendor like for Explore Scientific with
    #                order_to_debug = '13717|13712'
    # order_to_debug = '8948'
    # 12/16/2025. 17190|17193|17198|17206|17218 are 5 canceled orders for Joes half assed scope. working on bug fix to exclude them from further NEAF vendor processing.
    #order_to_debug = '17190|17193|17198|17206|17218'
    # 2/8/2026. Amateur Astronomers Association of Pittsburgh had 2 invoices in 2025, 15317|15705. They failed to merge into 1 company.

    # 2/1/2026. 17367, Remote Observatory. original order had 2 early bird premium. 1 refunded but 2 still showing on s/s and invoice.
    #           17371|17374, Takahashi. refund 2 standard booths in 17371, buy 2 premium in 17374

    order_to_debug = '17367'
    #order_to_debug = '17371|17374'
    #order_to_debug = '15317'
    #order_to_debug = '15317|15705' # Amateur Astronomers Assoc. of Pittsburgh
    #order_to_debug = '13443|13442|13441|13417'
    #order_to_debug = '15175|15400' # bob's knobs
    #order_to_debug = '15161|15376|16155' # "The Interstellar Collection, LLC" and "Brett Cohen" company names should be combined
    # for 17712 original order of neaf_vendor_booth_premium_from_standard_early_bird but before "My Company Name" added. I editted email from hqu@spectrumoi.com to hincequ@gmail.com.
    # combine with 17309 for 'Spectrum Optical Instruments'
    order_to_debug = '17712|17309'
    # #17377 of 'Khorovsky ent.inc dba Woodland hills camera', 2 premium booths. split into 2 companies with #19066, '10 Micron', neaf_vendor_booth_extra_ss_row
    #order_to_debug = '17377|19066'

    #order_to_debug = '17376' # 3/13/2026. has shitty extra badge name parsing where I confuse ',' and '/n' delimeters. repair.
    #order_to_debug = '13712|13717|14138' # 3/17/2026. I deleted block in NEAFVendor.get_nv_collections about hack for 'Explore Scientific' vs. 'Explore Scientific LLC'.
    #                                      I confirm with this test that block not needed and 'Explore Scientific LLC' is chosen.
    #order_to_debug = '19067|17376|19065|17712|17309|17377|19066' # 3/13/2026. 19067|19065|19066 are extra ss rows. 17712 is upgrade to premium of standrad order in 17309.


    # 7/8/2026. Spectrum Optical Instruments, it has 3 standard and 1 premium. it should be 2 standard and 2 premium when when neaf_vendor_booth_premium_from_standard_early_bird:1 applied.
    #order_to_debug = '17712|17309'
    # 7/9/2026. #17376 for astronomics, 3 premium, 1 standard. split into 3 companies with #19067, Sky Rover and #19065, Astro-Tech which both use sku neaf_vendor_booth_extra_ss_row.
    #           #17377 for Woodland Hills, 2 premium. split into 2 companies with #19066, 10 Micron which uses sku neaf_vendor_booth_extra_ss_row.
    order_to_debug = '19067|17376|19065|19066|17377|17712|17309'


    nv = NEAFVendor(neaf_year,created_at_min,created_at_max,order_to_debug,verbose)
    nv.shopifyLoad()
    if nv.error:
        print(nv.error)
    else:
        print(nv.output_nvt_csv('neaf_vendor'))
        #company_key = 'Australis'
        if not nv.nv_collections.vendor_invoices:
            invoice = f'nv.nv_collections.vendor_invoices is {nv.nv_collections.vendor_invoices}. No invoices created for order_to_debug:{order_to_debug}.'
        else:
            delim = ''
            for invoice in nv.nv_collections.vendor_invoices.values():
                print(delim + invoice)
                delim = '****************************************************************************************************************************************************\n'

    return

def neafvendor_invoice(company_key='Celestron',neaf_year=NEAF_YEAR_2026,as_pdf=True):
    nv = NEAFVendor(neaf_year=neaf_year)
    nv.shopifyLoad()
    if nv.error:
        print(nv.error)
        return
    target_companies,target_companies_text = nv.get_target_companies(company_key)
    if len(target_companies) != 1:
        print(target_companies_text)
        return
    target_company, target_company_invoice = nv.get_target_company_invoice(target_companies, '1')
    msg, subdir_path, fname = save_invoice(target_company,target_company_invoice,as_pdf=as_pdf)
    print(msg)
    return

def neafvendor_load(neaf_year=NEAF_YEAR_DEFAULT,verbose=False):
    neafVendor = NEAFVendor(neaf_year=neaf_year, verbose=verbose)
    if neafVendor.error:
        print(neafVendor.error + '\n' + neafVendor.msg)
        return
    neafVendor.shopifyLoad()
    if neafVendor.error:
        print(neafVendor.error)
    else:
        all_invoices = neafVendor.nv_collections.vendor_invoices
        i = 0
        print('\n**********   Display front of each element in neafVendor.nv_collections.vendor_invoices:   **********\n')
        for company,invoice in all_invoices.items():
            i += 1
            invoice_front = invoice.replace("\n",'')[118:264]
            msg = f'{i:>3}: {company[:40]:>40} -- {invoice_front}'
            print(msg)

    return

def tutorial_door_prize(override_day=SATURDAY,verbose=True):
    dp = DoorPrize(override_day=override_day,verbose=verbose)
    if dp.error:
        print('after DoorPrize(override_day=override_day, verbose=verbose):\ndp.error:\n{0}dp.msg:\n{1}'.format(dp.error,dp.msg))
        return
    dp.constantContactAndShopifyLoad()
    if dp.error:
        print('after dp.constantContactAndShopifyLoad():\ndp.error:\n{0}dp.msg:\n{1}'.format(dp.error,dp.msg))
        return
    print(dp.show_dicts_summary())
    return

def tutorial_door_prize_constant_contact_only(neaf_year = NEAF_YEAR_DEFAULT,override_day=SATURDAY, verbose=True):

    from date_filter_utils import calc_date_items_from_neaf_year_and_day
    from constant_contact import get_cc_door_prize_list

    created_at_max, neaf_day_of_week, neaf_other_day_of_week, error = calc_date_items_from_neaf_year_and_day(neaf_year, override_day)
    if error:
        print(error)
        return

    ccdpt_list, msg = get_cc_door_prize_list(neaf_year,neaf_day_of_week,verbose=verbose)
    #print(msg)

    if not ccdpt_list:
        print('\nNo Constant Contact door prize entries returned.')
        return

    print(f'\nConstant Contact returned {len(ccdpt_list)} door prize rows for neaf_year:{neaf_year}, neaf_day:{neaf_day_of_week}.')

    return

def tutorial_franks_spreadsheet(fname='C:\\Users\\jjmos\\OneDrive\\Desktop\\RAC AUGUST 2026 Membership.xlsx'):
    membership_dict,email_to_rmt_list_map,name_to_rmt_list_map,error,msg = load_franks_rac_membership_spreadsheet(fname)
    if error:
        print(f'ERROR:\n{error}')
    print(f'MSG:\n{msg}')
    return

def hspattendee_load(hsp_year=HSP_YEAR_DEFAULT):

    ha = HSPAttendees(hsp_year)
    if ha.error:
        print(ha.error + '\n' + ha.msg)
        return
    ha.shopifyAndFranksSpreadsheetLoad()

    if ha.error:
        print('\n-----------------ERROR----------------\n' + ha.error)
    print('\n---------------------------------\n' + ha.msg + '\n---------------------------------\n')

    ha.buildAndDisplaySales()
    if ha.error:
        print('\n-----------------ERROR----------------\n' + ha.error)

    return

def main():

    # 3/2/2024. the 3 functions in this block has been tested as of this date
    #neafvendor_management_ss_and_invoices_to_console_from_orders() # 8/31/2026. fix bug for Spectrum Optical were 3 standard + 1 premium and upgrade shows as 2 standard + 1 premium
    #neafvendor_invoice() #  ('Spectrum Optical Instruments',as_pdf=False)
    #neafvendor_load()
    #accesshopify_by_date_range_and_sku()
    #tutorial_door_prize()
    #tutorial_door_prize_constant_contact_only()
    #tutorial_franks_spreadsheet()
    hspattendee_load()

    return
main()

