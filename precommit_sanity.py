from consts import NEAF_YEAR_DEFAULT,NEAF_ATTEND,MEMBERSHIP,CC_DOOR_PRIZE,NEAF_YEAR_2025,SATURDAY,NEAIC_ATTEND,NEAF_VENDOR,FAKE_TEST_KEY,FAKE_TEST_VALUE
from utils import showError
from graphql_utils import get_orders_cursor_items,get_url_and_headers,mutate_custom_attributes,load_and_adjust_custom_attributes
from neaf_vendor_utils import BADGE_ACTION,DELETE_PRIOR_EDIT_ACTION
from pdf_utils import build_winners_pdf
from neaf_vendor import NEAFVendor
from door_prize import DoorPrize
from orders import Orders

def neaf_vendor_and_badge_csv(neaf_year=NEAF_YEAR_DEFAULT,verbose=False):
    neafVendor = NEAFVendor(neaf_year=neaf_year, verbose=verbose)
    if neafVendor.error:
        print(neafVendor.error + '\n' + neafVendor.msg)
        return
    neafVendor.shopifyLoad()
    msg = neafVendor.output_nvt_csv('neaf_vendor')
    print('\n'+msg)
    msg = neafVendor.output_nvt_csv('neaf_company_badge')
    print('\n'+msg)
    return

def neaf_vendor_apply_edit():
    # XXX 4/2/2026. This function tests the processing of user edit entered from the NEAF Vendor Management app. Its based on the order #15264 from NEAF 2025
    #               for the USS Abraham Lincoln. The original order had 3 edits stored in the order customAttributes list:
    #               {'key': 'Delete_Original_Badge_Name_15264_1', 'value': 'Crewman Jessica Langer'}
    #               {'key': 'Badge_Name_15264_2', 'value': 'Civilian Laurie Zeilberger'}
    #               {'key': 'Badge_Name_15264_3', 'value': 'Civilian Michael Zeilberger'}
    #               I do a one-time and permanent injection using the inject_test_custom_attribute_by_order_num function in debug_shopify_graphql.py of a non-conforming edit:
    #               {'key': 'fake_test_key', 'value': 'fake_test_value'}
    #               This function then adds this edit item:
    #               {'key': 'Badge_Name_15264_4', 'value': 'Moshe Yisroel'}
    #               It then deletes same edit item. See todo comments below for text that should eventually be used in regression tests.

    def get_seq_no_of_item_to_delete(msg1):
        msg2 = msg1[:msg1.index(edit_item)]
        msg3 = msg2[msg2.rindex('_')+1:]
        seq_no_of_item_to_delete = msg3[:msg3.index('\'')]
        return seq_no_of_item_to_delete

    order_num = '15264'

    msg,order_id,success,customAttributes = load_and_adjust_custom_attributes(order_num,key=FAKE_TEST_KEY,value=FAKE_TEST_VALUE)
    print(msg)
    if success:
        success2,msg2 = mutate_custom_attributes(order_num, order_id, customAttributes)
        print(msg2)
        if not success2:
            raise Exception("mutate_custom_attributes failed. Get off your fat ass and fix.")

    neafVendor = NEAFVendor(neaf_year=NEAF_YEAR_2025,order_to_debug=order_num)
    if neafVendor.error:
        print(neafVendor.error + '\n' + neafVendor.msg)
        return
    neafVendor.shopifyLoad()
    if neafVendor.error:
        print(neafVendor.error)
        return

    target_companies,target_companies_text = neafVendor.get_target_companies('lincoln')
    target_company = target_companies[0]
    neafVendor.target_company = target_company
    msg = neafVendor.see_all_edit_items()
    # TODO 4/2/2026. use msg for regression
    print(msg)
    edit_item = 'Moshe Yisroel'
    msg1 = neafVendor.applyOrderNoteAttributeEdit(BADGE_ACTION,edit_item)
    # TODO 4/2/2026. use msg1 for regression
    print(msg1)
    seq_no_of_item_to_delete = get_seq_no_of_item_to_delete(msg1)
    neafVendor.shopifyLoad()
    if neafVendor.error:
        print(neafVendor.error)
        return
    neafVendor.target_company = target_company
    msg2 = neafVendor.applyOrderNoteAttributeEdit(DELETE_PRIOR_EDIT_ACTION, seq_no_of_item_to_delete)
    # TODO 4/2/2026. use msg2 for regression
    print(msg2)

    return

def neaf_vendor_all_invoices(neaf_year=NEAF_YEAR_DEFAULT,as_pdf=False,verbose=False):
    neafVendor = NEAFVendor(neaf_year=neaf_year, verbose=verbose)
    if neafVendor.error:
        print(neafVendor.error + '\n' + neafVendor.msg)
        return
    neafVendor.shopifyLoad()
    if neafVendor.error:
        print(neafVendor.error)
    else:
        all_invoices_to_print,save_message = neafVendor.show_and_save_all_invoices(as_pdf)
        print(save_message)

    return

def orders_neaf_attendee_csv(verbose=False,order_to_debug=None):
    orders = Orders(NEAF_ATTEND,verbose=verbose,order_to_debug=order_to_debug)
    orders.shopifyLoad()
    print(orders.dump_to_csv())
    return

def orders_neaf_vendor_csv(verbose=False,order_to_debug=None):
    orders = Orders(NEAF_VENDOR,verbose=verbose,order_to_debug=order_to_debug)
    orders.shopifyLoad()
    print(orders.dump_to_csv())
    return

def orders_rac_membership_csv(verbose=False,order_to_debug=None):
    orders = Orders(MEMBERSHIP,verbose=verbose,order_to_debug=order_to_debug)
    orders.shopifyLoad()
    print(orders.dump_to_csv())
    return

def orders_raw_cc_door_prize_csv(verbose=False, order_to_debug=None):
    orders = Orders(CC_DOOR_PRIZE,verbose=verbose,order_to_debug=order_to_debug)
    orders.shopifyLoad()
    print(orders.dump_to_csv())
    return

def NEAF_YEAR_PRIOR():
    return str(int(NEAF_YEAR_DEFAULT)-1)
def door_prize_entrants_csv(verbose=False):
    #dp = DoorPrize(neaf_year=NEAF_YEAR_PRIOR(),override_day=SATURDAY,verbose=verbose)
    dp = DoorPrize(verbose=verbose)
    if dp.error:
        print(showError(dp.error) + '\n' + dp.msg)
        return
    dp.constantContactAndShopifyLoad()
    msg = dp.show_dicts_summary()
    msg2 = dp.show_hints_dp()
    print(f'\nshow_dicts_summary results:\n\n{msg}\n\nshow_hints_dp results:\n\n{msg2}')
    return

def door_prize_pdf(pick_n_winners=3,verbose=False):
    dp = DoorPrize(neaf_year=NEAF_YEAR_PRIOR(),override_day=SATURDAY,verbose=verbose)
    if dp.error:
        print(showError(dp.error) + '\n' + dp.msg)
        return
    dp.constantContactAndShopifyLoad()
    msgs = []
    for i in range(0,pick_n_winners):
        msgs.append(dp.pick_and_show_winner())
    print('\n'.join(msgs))
    comment = build_winners_pdf(dp.dpSrc.winner,dp.neaf_year,dp.neaf_day_of_week)
    print(comment)
    return

def create_full_and_incremental_neaic_report():

    verbose = False
    product_type = NEAIC_ATTEND
    created_at_min = '2026-03-16' # None # '2024-01-01'
    created_at_max = '2026-03-16' # None
    order_to_debug = None

    orders = Orders(product_type, order_to_debug=order_to_debug, verbose=verbose)

    # 3/2/2026. Its not neccesary to call this function here since its called inside orders.neaic_attendee_dump_to_csv but its convenience to see
    #           how this important function behaves.
    neaic_last_order, file_with_neaic_last_order,error = orders.get_latest_neaic_order_number()
    print(f'Call to orders.get_latest_neaic_order_number() returnes\nneaic_last_order:{neaic_last_order}\nfile_with_neaic_last_order:{file_with_neaic_last_order}\nerror:{error}\n')

    orders.shopifyLoad(created_at_min=created_at_min, created_at_max=created_at_max, order_to_debug=order_to_debug)

    if orders.error:
        print(orders.error)
    else:
        print('\n********** GENERATE INCREMENTAL NEAIC ATTENDEE CSV **********\n')
        msg = orders.neaic_attendee_dump_to_csv(incremental_since_last_run=True)
        print(msg)
        print('\n********** GENERATE FULL NEAIC ATTENDEE CSV **********\n')
        msg = orders.neaic_attendee_dump_to_csv(incremental_since_last_run=False)
        print(msg)

    return


def main():
    neaf_vendor_and_badge_csv(NEAF_YEAR_DEFAULT)
    #neaf_vendor_apply_edit()
    #neaf_vendor_all_invoices()
    #orders_neaf_attendee_csv()
    #orders_neaf_vendor_csv()
    #orders_rac_membership_csv()
    #orders_raw_cc_door_prize_csv()
    #door_prize_entrants_csv()
    #door_prize_pdf()
    #create_full_and_incremental_neaic_report()
    return
main()