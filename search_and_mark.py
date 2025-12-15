import datetime
import os
from collections import namedtuple
from consts import NEAF_DATES,MERCH,MISSING
from utils import RAC_DIR,build_door_prize_cc_dict,show_dict,read_door_prize_file,get_target_dict
from utils import write_door_prize_file,DoorPrizeTup,get_default_neaf_year
from door_prize import DoorPrize
from constant_contact import get_cc_door_prize_list

LOGGING = [False]
SEARCH_AND_CONFIRM = 'search_and_confirm'
NEAF_ATTENDEE = 'neaf_attendee'
DOOR_PRIZE_CC = 'door_prize_cc'
SearchAndMarkDictsTup = namedtuple('SearchAndMarkDictsTup', 'neaf_attendee merch door_prize_cc confirmed msg_neaf_attendee msg_merch')

def show_hints():
    hints = '''
----------------------------------------------------------------------------------------------------------------------    
    
    Find orders in these 3 categories:
    1) All Shopify purchasers of NEAF and NEAIC admission.
    2) All Shopify purchasers of RAC Club Table merch. 
    3) All Door Prize entries in Constant Contact.      
       
    Source for 1) and 2) is webservice call to Shopify using 
    https://rockland-astronomy-club.myshopify.com/admin/orders.json
    Source for category 3) is Constant Contact api. 
    
    Orders found in 1) and 2) can be confirmed to have 1)picked up their NEAF tickets or 2)picked up their merchandise
    The purpose of the confirmation is to prevent them from invalidly gaining additional admission tickets or picking 
    up additional merchandise.

    Choose NEAF year. Defaults to calendar year.
    
    Of course it isn't that simple. Imagine someone buys 4 NEAF admits. They and 1 other show up and get 2 admission
    tickets. Then they come by hours later with the other 2 and ask for 2 more admits. What an ass pain.
          
---------------------------------------------------------------------------------------------------------------------    
    '''
    return hints

def show_paths_and_files(): 
    msg =  '---------------------------------------------------------------------------------------------------\n'
    msg += 'Directory for all RAC items:                '+RAC_DIR()+'\n'
    msg += 'Marked after being searched and selected:   '+os.path.join(RAC_DIR(),SEARCH_AND_CONFIRM+'.csv') + '\n'
    msg += '---------------------------------------------------------------------------------------------------\n'
    return msg
    
def show_dicts_summary(samdt):
    msg  = '-----------------------------------------------------\n'
    msg += 'neaf_attendee_dict size:{0}'.format(len(samdt.neaf_attendee))
    msg += 'merch_dict:{0}'.format(len(samdt.merch))
    msg += 'door_prize_cc_dict size:{0}'.format(len(samdt.door_prize_cc))
    msg += 'confirmed_dict:{0}'.format(len(samdt.confirmed))
    return msg    
    
def show_dicts(samdt):
    msg  = '-----------------------------------------------------\n'
    msg += show_dict(samdt.neaf_attendee,'neaf_attendee_dict')
    msg += show_dict(samdt.merch,'merch_dict')
    msg += show_dict(samdt.door_prize_cc,'door_prize_cc_dict')
    msg += show_dict(samdt.confirmed,'confirmed_dict')
    msg += show_dicts_summary(samdt)
    msg += '\n'
    return msg   
    
def get_samdt_dict(samdt,key):
    if key == NEAF_ATTENDEE:
        return samdt.neaf_attendee
    elif key == MERCH:
        return samdt.merch
    else:
        return samdt.door_prize_cc
        
def confirm_replace(samdt,key,dpt,confirmed):
    dpt = dpt._replace(CONFIRM_NOTE=confirmed)
    dpt_key = dpt.order_num
    target_dict = get_samdt_dict(samdt,key)
    target_dict[dpt_key] = dpt
    if confirmed:
        samdt.confirmed[dpt_key] = dpt
    else:
        # item that was previously confirmed has been unconfirmed so remove from search_and_confirm dict.
        del samdt.confirmed[dpt_key]
    # TODO 4/3/2023. we use same function for door prize but that needs to be fixed
    write_door_prize_file(samdt.confirmed, SEARCH_AND_CONFIRM)
    return      
    
def confirm_dpt(samdt,key,dpt):
    confirmed = datetime.datetime.now().strftime('{0}*Confirmed:%m-%dT%H:%M:%S')
    confirmed = confirmed.format(key)
    confirm_replace(samdt,key,dpt,confirmed)
    return
         
def unconfirm_dpt(samdt,key,dpt):
    confirm_replace(samdt,key,dpt,None)
    return    
    
def confirm_or_unconfirm(key,target_dict,samdt,c_or_u):
    if not target_dict:
        # no items selected so nothing to confirm or unconfirm
        return 'No items selected for confirm or unconfirm'
    if not c_or_u.startswith(('c','u')):
        return 'c_or_u of {0} passed to confirm_or_unconfirm is invalid. Must be of form c<item#> or u<item#>'.format(c_or_u)
    confirm = True if c_or_u.startswith('c') else False
    confirm_str = 'confirm' if confirm else 'unconfirm'
    if len(target_dict)==1 and len(c_or_u)==1:
        # no need to force user to pick index of choice if there is only 1 option
        c_or_u += '1'
    choice = c_or_u[1:]
    if not choice.isdigit():
        return 'Item # of {0} to {1} is invalid. Must be a valid line #.'.format(choice,confirm_str)
    ichoice = int(choice)
    if ichoice<1 or ichoice>len(target_dict):
        return 'Item # of {0} to {1} is invalid. Must be between 1 and {2}.'.format(choice,confirm_str,len(target_dict))
    dpt_key = sorted(target_dict.keys())[ichoice-1] 
    dpt = target_dict[dpt_key]
    if confirm:
        confirm_dpt(samdt,key,dpt)
    else:
        unconfirm_dpt(samdt,key,dpt)
    return 'Item # {0} has been {1}ed.'.format(choice,confirm_str)   
    
def search_and_display(samdt,samdt_key,search_for):
    target_dict,msg = get_target_dict(search_for,samdt,samdt_key)
    if not target_dict:
        # just in case the item being searched for was updated very recently build the dict again
        samdt = get_search_and_mark_dicts()
        target_dict,msg = get_target_dict(search_for,samdt,samdt_key)
    target_str="Searching for '{0}' in {1} group. Found {2} items.\n".format(search_for,samdt_key,len(target_dict))
    target_str += show_dict(target_dict,'items to be confirmed or unconfirmed') 
    return samdt,target_dict,samdt_key,target_str
    
def apply_confirm(samdt):
    errors = ''
    for key,dpt in samdt.confirmed.items():
        toks = dpt.CONFIRM_NOTE.split('*')
        target_dict_key = toks[0]
        CONFIRM_NOTE = toks[1]
        target_dict = get_samdt_dict(samdt,target_dict_key)
        target_dpt = target_dict.get(dpt.order_num)
        if target_dpt:
            target_dpt = target_dpt._replace(CONFIRM_NOTE=CONFIRM_NOTE)
            target_dict[dpt.order_num] = target_dpt
        else:
            errors += 'item {0} was marked as confirmed but key of {1} does not exist in target_dict.\n'.format(dpt,key)
    print(errors)
    return
    
def inject_neaf_attendee(neaf_attendee_dict):
    # find a free key. start guessing at 1.
    free_key = 1
    while True:
        if not neaf_attendee_dict.get(str(free_key)):
            break
        free_key += 1
    last_key = str(free_key)
    created_at = '{0}-04-04T21:59:58-05:00'.format(get_default_neaf_year())
    dpt = DoorPrizeTup(order_num=last_key, order_id=MISSING, created_at=created_at, name='Blossom Moskowitz', phone_num=None,email=' ', sku='neaf_attend_admit_2day', quantity=1, CONFIRM_NOTE=None)
    neaf_attendee_dict[last_key] = dpt                
    return    
    
def get_search_and_mark_dicts(weekend_day,verbose):
    # TODO 4/3/2023. we use same function for door prize but that needs to be fixed
    confirmed_dict,fname = read_door_prize_file(SEARCH_AND_CONFIRM, verbose)
    doorPrizeMerch = DoorPrize(sku_key=MERCH,verbose=LOGGING[0])
    merch_dict = doorPrizeMerch.raw
    msg_merch = doorPrizeMerch.msg
    #msg_merch,merch_dict = build_door_prize_dict_from_shopify(sku_key='merch', verbose=LOGGING[0])
    doorPrizeNeafAttendee = DoorPrize(verbose=LOGGING[0])
    neaf_attendee_dict = doorPrizeMerch.raw
    msg_neaf_attendee = doorPrizeNeafAttendee.msg
    #msg_neaf_attendee,neaf_attendee_dict = build_door_prize_dict_from_shopify(verbose=LOGGING[0])
    inject_neaf_attendee(neaf_attendee_dict)
    ndt = NEAF_DATES[get_default_neaf_year()]
    ccdpt_list = get_cc_door_prize_list(ndt.neaf_start,ndt.neaf_end,verbose=verbose)
    door_prize_cc_dict,door_prize_cc_reject_dict = build_door_prize_cc_dict(ccdpt_list,neaf_attendee_dict,weekend_day,verbose=verbose,use_both_days=True)
    samdt = SearchAndMarkDictsTup(neaf_attendee_dict, merch_dict, door_prize_cc_dict, confirmed_dict, msg_neaf_attendee, msg_merch)
    apply_confirm(samdt)
    return samdt
   
def process_option(optionstr):
    search_for = None
    c_or_u = None
    if optionstr.startswith(('1s*','2s*','3s*')):
        search_for = optionstr[3:]   
        optionstr = optionstr[:1]
        return int(optionstr),search_for,c_or_u 
    if optionstr.startswith(('c','u')):
        c_or_u = optionstr   
        option = 11 
        return option,search_for,c_or_u   
    if not optionstr.isdigit():
        return -1,search_for,c_or_u  
    option = int(optionstr)
    if option<0 or option>10:
        return -1,search_for,c_or_u          
    return option,search_for,c_or_u   
    
def main():    
    target_dict = {}
    samdt_key,samdt,c_or_u = [None] * 3
    samdt = get_search_and_mark_dicts()
    if samdt.msg_merch:
        print('msg_merch:{0}'.format(samdt.msg_merch))
    if samdt.msg_neaf_attendee:
        print('msg_neaf_attendee:{0}'.format(samdt.msg_neaf_attendee))
    while True:
        print('\n\n4:show_dicts    5:debug on     6:debug off    7:hints    8:show paths and files   '+\
            '9:refresh data  10:show targets')
        msg = '0:stop  1s*<...>:search NEAF attendees  2s*<...>:search merch purchasers  3s*<...>:search door prize entrants  c<item#>:confirm  u<item#>:unconfirm\n\n-----> '
        optionstr = input(msg)
        option,search_for,c_or_u = process_option(optionstr)
        if option == -1: 
            print('Choice not valid. Try again.')
            continue 
        if not option: 
            break
                 
        if option == 1:
            samdt,target_dict,samdt_key,target_str = search_and_display(samdt,NEAF_ATTENDEE,search_for)
            print(target_str)
            continue
        if option == 2:
            samdt,target_dict,samdt_key,target_str = search_and_display(samdt,MERCH,search_for)
            print(target_str)
            continue
        if option == 3:
            samdt,target_dict,samdt_key,target_str = search_and_display(samdt,DOOR_PRIZE_CC,search_for)
            print(target_str) 
            continue        
        if option == 4:
            print(show_dicts(samdt))
            continue  
        if option == 5:
            LOGGING[0] = True
            continue
        if option == 6:
            LOGGING[0] = False
            continue     
        if option == 7:
            print((show_hints()))
            continue    
        if option == 8:
            print(show_paths_and_files())   
            continue 
        if option == 9:
             samdt = get_search_and_mark_dicts()
             print(show_dicts(samdt))
             continue    
        if option == 10:
             print(show_dict(target_dict,'items to be confirmed or unconfirmed')) 
             continue                    
        if option == 11:  
            message = confirm_or_unconfirm(samdt_key,target_dict,samdt,c_or_u)
            print(message)
            continue

    return   

#main()
        