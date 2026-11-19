import csv
import os
import datetime
import random
import tracemalloc
import requests
import io
import re
from openpyxl import Workbook
from collections import namedtuple
from consts import NEAF_DATES,DOOR_PRIZE,DEFAULT_DAY,SATURDAY,SUNDAY,NEAF_YEAR_DEFAULT,MISSING
from credentials import Credentials
from utils import RAC_DIR,build_door_prize_sf_dict,DICT_DELIMITER_FRONT,convert_utc_to_local_datetime
from utils import show_dict,read_door_prize_file,DOOR_PRIZE_HEADER,write_door_prize_file,DoorPrizeSrcDicts,DoorPrizeResDicts
from utils import show_paths_and_files_dp,DOOR_PRIZE_WINNER,DoorPrizeTup,appendMsg
from date_filter_utils import calc_date_items_from_neaf_year_and_day,get_neaf_dates_from_neaf_year_and_day
from graphql_utils import get_url_and_headers
from pdf_utils import build_winners_pdf
from access_shopify import AccessShopify

SF_DOOR_PRIZE_FIELDS = 'createdAt type formInstanceId email firstName lastName phoneNumber'
SfDoorPrizeTup = namedtuple('SfDoorPrizeTup', SF_DOOR_PRIZE_FIELDS)

def get_random_in_range(max_num):
    winner = random.randint(0, max_num - 1)
    return winner

def get_sf_door_prize_entries_by_date_range(created_at_min, created_at_max):

    # 10/15/2026. get all door prize entries, in requested date range, created by Shopify Form(sf) named 'NEAF Door Prize Entry' with form ID 1175570.
    #             url for form is https://rockland-astronomy-club.myshopify.com/pages/neaf-door-prize-entry .

    def date_valid(dt,date_name):
        error = ''
        try:
            datetime.datetime.strptime(dt, '%Y-%m-%d')
        except:
            error = f"{date_name} of {dt} not string in valid form of YYYY-MM-DD."
        return error

    msg = ''
    error = ''
    sf_door_prize_list = []
    error = date_valid(created_at_min,'created_at_min')
    if error:
        return sf_door_prize_list,msg,error
    error = date_valid(created_at_max,'created_at_max')
    if error:
        return sf_door_prize_list,msg,error
    if created_at_min > created_at_max:
        error = f"created_at_min:{created_at_min} and created_at_max:{created_at_max} are incompatible. created_at_min must be less than or equal to created_at_max."
        return sf_door_prize_list,msg,error
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    if created_at_min > today_str:
        error = f"created_at_min:{created_at_min} is invalid. Must be less than or equal to today of {today_str}."
        return sf_door_prize_list,msg,error

    sheet_id = Credentials().GOOGLE_SHEETS_NEAF_DOOR_PRIZE_ID

    try:
        html = requests.get(f'https://docs.google.com/spreadsheets/d/{sheet_id}/edit').text
        sheet_name = re.search(r'<title>(.*?)</title>', html).group(1)
    except:
        error = 'Failed loading html representation of NEAF Door Prize entry google sheet.'
        return sf_door_prize_list,msg,error

    msg = f"Load '{sheet_name}' and parse all entries from {created_at_min} and {created_at_max}."

    url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0'
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as ex:
        error = f'Failed loading NEAF Door Prize Google Sheet.\n{ex}'
        return sf_door_prize_list,msg,error
    rows = list(csv.DictReader(io.StringIO(response.text)))
    for row in rows:
        gsdp = SfDoorPrizeTup(**row)
        createdAt = convert_utc_to_local_datetime(gsdp.createdAt)
        if not (created_at_min <= createdAt[:10] <= created_at_max):
            continue
        gsdp = gsdp._replace(createdAt=createdAt)
        sf_door_prize_list.append(gsdp)
    msg += '\n' + f"Loaded {len(rows)} rows. {len(sf_door_prize_list)} rows are within date range and will be returned."

    return sf_door_prize_list,msg,error

def build_raw_sf_to_excel(sf_door_prize_list):
    fname = os.path.join(RAC_DIR(),'door_prize','raw_sf.xlsx')
    os.makedirs(os.path.dirname(fname),exist_ok=True)

    try:
        wb = Workbook()
        ws = wb.active
        ws.title = 'NEAF Door Prize'
        ws.append(SF_DOOR_PRIZE_FIELDS.split())
        for sfdpt in sf_door_prize_list:
            ws.append(list(sfdpt))
        wb.save(fname)

    except Exception as ex:
        error = appendMsg(f"\nShopify Form 'NEAF Door Prize Entry' raw data dump to Excel failed with exception:\n{ex}")
        return '',error

    return appendMsg(f"Shopify Form 'NEAF Door Prize Entry' raw data dump of {len(sf_door_prize_list)} rows, {len(SF_DOOR_PRIZE_FIELDS.split())} columns at {fname}."),''

def get_sf_door_prize_list(neaf_year, neaf_day, raw_sf_to_excel=False, verbose=False):

    # 10/16/2026 XXX this function is public interface to return all door prize entries create with Shopify Form named 'NEAF Door Prize Entry' with form ID 1175570.
    #                url for form is https://rockland-astronomy-club.myshopify.com/pages/neaf-door-prize-entry .

    neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex = \
        get_neaf_dates_from_neaf_year_and_day(neaf_year, neaf_day, 'get_sf_door_prize_list')
    if msg_ex:
        return [],msg,msg_ex

    sf_door_prize_list,msg,error = get_sf_door_prize_entries_by_date_range(neaf_start,neaf_end)
    if error:
        return [],msg,error
    if raw_sf_to_excel:
        msg2,error = build_raw_sf_to_excel(sf_door_prize_list)
        msg = appendMsg(msg,msg2,print_new_msg=False)

    return sf_door_prize_list,msg,error

class DoorPrize(AccessShopify):

    def append_to_shopifyTup_dict(self,dpt_dict,sct):

        # 1/15/2023. append_to_shopifyTup_dict is implemented in each class that derives from AccessShopify and is responsible for much of the polymorphism of this class heirarchy.
        #            so far the classes AccessOrders, DoorPrize and NEAFVendor implement append_to_shopifyTup_dict.
        #            append_to_shopifyTup_dict sums all the line items in sct to orders under st_dict

        for quan in range(0, sct.quantity):
            key = sct.order_num if quan==0 else sct.order_num+'-'+str(quan+1)
            dpt = DoorPrizeTup(key, sct.order_id, sct.created_at, sct.name, sct.phone_num, sct.email, sct.sku, sct.quantity, None)
            dpt_dict[key] = dpt
        return

    def __init__(self,neaf_year=NEAF_YEAR_DEFAULT,override_day=DEFAULT_DAY,order_to_debug=None,verbose=False):

        created_at_min = None
        created_at_max = None

        # TODO uncomment these variable to debug a prior years NEAF
        #neaf_year = None
        #created_at_min = '2018-08-01'
        #created_at_max = '2019-05-01'
        super(DoorPrize, self).__init__(neaf_year,created_at_min,created_at_max,order_to_debug,verbose)
        if self.error:
            return

        self.sku_key = DOOR_PRIZE
        # 12/30/2022. this function populates self.raw from self.rawOrdersTupList which was built in shopifyOrdersFromHttps.

        self.dpSrc = DoorPrizeSrcDicts({}, {}, {}, {})
        self.dpRes = DoorPrizeResDicts({}, {})
        self.prev_load_time = None
        self.fname = None

        self.created_at_max,self.neaf_day_of_week,self.neaf_other_day_of_week,self.error = calc_date_items_from_neaf_year_and_day(self.neaf_year,override_day)

        return

    def build_eligible_door_prize_dict(self,door_prize_winner_dict, door_prize_sf_dict, door_prize_dict):
        door_prize_eligible_dict = {}
        door_prize_reject_dict = {}
        for k, v in door_prize_sf_dict.items():
            if door_prize_winner_dict.get(k):
                continue
            door_prize_eligible_dict[k] = v
        other_dow = self.neaf_other_day_of_week.lower()
        for k, v in door_prize_dict.items():
            if door_prize_winner_dict.get(k) or other_dow in v.sku.lower() or MISSING in v.name:
                # 3/5/2026. example satisfying 'MISSING in v.name' clause is #16499 for NEAF year:2025, NEAF day of week:Saturday.
                #           v.name is 'MISSING MISSING' because user paid by Tap & Chip on Saturday but no personal info available.
                door_prize_reject_dict[k] = v
                continue
            door_prize_eligible_dict[k] = v
        return door_prize_eligible_dict, door_prize_reject_dict

    def sFAndShopifyLoad(self):

        # 10/16/2022. load from Shopify Form named 'NEAF Door Prize Entry' with form ID 1175570 and standard shopify NEAF orders and populate
        #             all in-memory representations needed for full functionality.

        self.msg = ''
        now = datetime.datetime.now()
        if self.prev_load_time:
            # a reload can be forced by passing in prev_load_time as None.
            minutes = (now - self.prev_load_time).total_seconds() / 60.
            if minutes < 15.0:
                # if last load was less than 15 minutes ago skip load and use last results.
                plt = self.prev_load_time.strftime('%H:%M:%S')
                self.msg = 'Inside sFAndShopifyLoad(...) skipping re-load of data because last load was less than 15 minutes ago. It was {0:.1f} minutes ago at {1}.'
                self.msg = self.msg.format(minutes, plt)
                print(self.msg)
                return

        if self.error:
            self.error = 'Cannot run DoorPrize.sFAndShopifyLoad(). DoorPrize has pre-existing error:\n{0}'.format(self.error)
            return
        # 12/30/2022. shopifyOrdersFromHttps populates self.rawOrdersTupList with raw shopify data from their webservice.
        self.shopifyOrdersFromGraphQL()
        if self.error:
            self.error = 'Failure in DoorPrize.sFAndShopifyLoad().\n{0})'.format(self.error)
            return

        # 12/30/2022. convertShopifyOrdersToRacOrders populates self.raw from self.rawOrdersTupList which was built in shopifyOrdersFromHttps.
        self.convertShopifyOrdersToRacOrders()

        door_prize_winner_dict, self.fname = read_door_prize_file(DOOR_PRIZE_WINNER, self.neaf_year, self.neaf_day_of_week, self.verbose)
        door_prize_dict = self.raw

        # 10/15/2026: XXX IMPORTANT:
        #                 Time/day filtering for shopify form data from 'NEAF Door Prize Entry' happens only in get_sf_door_prize_list(...).
        #                 Do not duplicate that filtering in build_door_prize_sf_dict() or anywhere else.
        sfdpt_list,msg,self.error = get_sf_door_prize_list(self.neaf_year, self.neaf_day_of_week, verbose=self.verbose)
        if self.error:
            return

        door_prize_sf_dict, door_prize_sf_reject_dict = build_door_prize_sf_dict(sfdpt_list, self.raw, self.verbose)

        door_prize_eligible_dict, door_prize_reject_dict = self.build_eligible_door_prize_dict(door_prize_winner_dict,door_prize_sf_dict,door_prize_dict)

        for trg,src in ((self.dpSrc.winner,door_prize_winner_dict),(self.dpSrc.sf,door_prize_sf_dict),(self.dpSrc.sf_reject,door_prize_sf_reject_dict),(self.dpSrc.shopify,door_prize_dict)):
            trg.clear()
            trg.update(src)

        for trg,src in ((self.dpRes.eligible, door_prize_eligible_dict),(self.dpRes.reject, door_prize_reject_dict)):
            trg.clear()
            trg.update(src)

        self.prev_load_time = datetime.datetime.now()

        print('memory usage at exit from DoorPrize.sFAndShopifyLoad after all loading is done : {0}'.format(tracemalloc.get_traced_memory()))
        return

    def verifyLoaded(self,label):
        if not self.raw:
            self.msg = 'Failed running DoorPrize.{0}. No data loaded for this DoorPrize object. Call DoorPrize.sFAndShopifyLoad() running this function.'.format(label)
            return False
        self.msg = ''
        return True

    def show_dicts_summary(self):
        msg = '-----------------------------------------------------\n'
        msg += 'DoorPrize.dpSrc.sf size:{0}\n'.format(len(self.dpSrc.sf))
        msg += 'DoorPrize.dpSrc.sf_reject size:{0}\n'.format(len(self.dpSrc.sf_reject))
        msg += 'DoorPrize.dpSrc.shopify size:{0}\n'.format(len(self.dpSrc.shopify))
        msg += 'DoorPrize.dpRes.reject size:{0}\n'.format(len(self.dpRes.reject))
        msg += 'DoorPrize.dpRes.eligible size:{0}\n'.format(len(self.dpRes.eligible))
        msg += 'DoorPrize.dpSrc.winner size:{0}\n'.format(len(self.dpSrc.winner))
        msg += '-----------------------------------------------------\n'
        return msg

    def show_dicts(self):
        if not self.verifyLoaded('show_dicts'):
            return self.msg
        msg = show_dict(self.dpSrc.sf, 'DoorPrize.dpSrc.sf')
        msg += show_dict(self.dpSrc.sf_reject, 'DoorPrize.dpSrc.sf_reject')
        msg += show_dict(self.dpSrc.shopify, 'DoorPrize.dpSrc.shopify')
        msg += show_dict(self.dpRes.reject, 'DoorPrize.dpRes.reject')
        msg += show_dict(self.dpRes.eligible, 'DoorPrize.dpRes.eligible')
        msg += show_dict(self.dpSrc.winner, 'DoorPrize.dpSrc.winner')
        msg += self.show_dicts_summary()
        return msg

    def show_hints_dp(self):
        hints = '''
    ----------------------------------------------------------------------------------------------------------------------    

        Winners determined by 3 sources:
        1) All NEAF and NEAIC purchases online from Shopify can be acquired by
           webservice call to Shopify using {0}
        2) All Door Prize entries in Shopify form named 'NEAF Door Prize Entry'. Acquired from Google Sheet api.
        3) Prior winners in file {1}.csv and are excluded from future drawings.

        Exclude any entries in item 2) with email addresses that match item 1).

        3:choose_day option only used for debugging. Don't use it during NEAF.

        door_prize_reject_dict consists of Shopify entrants that do not belong in the days door prize drawing.
        For example if you have Shopify sku of neaf_attend_admit_saturday and its Sunday you will be in reject dict.
        
        created_at_max:{2}, created_at_min:{3}, neaf_year:{4}, neaf_year_raw:{5}, neaf_day_of_week:{6}
        # SF eligible entries:             {7:4}    # SF entries rejected:            {8:4} 
        # eligible Shopify and SF entries: {9:4}    # SF and Shopify entries rejected:{10:4}   
        # Door Prize Winners:              {11:4}

    ---------------------------------------------------------------------------------------------------------------------    
        '''

        webservice_name = get_url_and_headers()[0]
        hints += '\n' + show_paths_and_files_dp(self.neaf_year,self.neaf_day_of_week)
        hints = hints.format(webservice_name,  DOOR_PRIZE_WINNER.format(neaf_year=self.neaf_year, neaf_day_of_week=self.neaf_day_of_week),
                             self.created_at_max, self.created_at_min, self.neaf_year, self.neaf_year_raw, self.neaf_day_of_week,
                             len(self.dpSrc.sf), len(self.dpSrc.sf_reject),
                             len(self.dpRes.eligible),len(self.dpRes.reject),
                             len(self.dpSrc.winner))

        return hints

    def search_for_item(self, searchItem):
        if not self.verifyLoaded('search_for_item'):
            return self.msg
        msg = self.show_dicts()
        sItem = searchItem.lower().replace(' ', '')
        res = ''
        current_section = ''
        last_current_section_used = ''
        for line in msg.split('\n'):
            current_section = line if line.startswith(DICT_DELIMITER_FRONT) else current_section
            if sItem in line.lower().replace(' ', ''):
                # we have found item of interest. if its in a new section print that section
                if current_section != last_current_section_used:
                    res += current_section + '\n'
                res += line + '\n'
                last_current_section_used = current_section
        res = "Requested item of '{0}' not found".format(searchItem) if not res else res
        return res

    def get_random_index(self):
        if not self.verifyLoaded('get_random_index'):
            return None
        max_num = len(self.dpRes.eligible)
        winner = get_random_in_range(max_num)
        if winner < 0 or winner >= len(self.dpRes.eligible):
            msg = 'Failure in get_random_index(...) . get_random_in_range(max_num-1={1}) returned {0} but door_prize_eligible_dict has size of {1}. Fix this bug.'
            input(msg.format(max_num, len(self.dpRes.eligible)))
            raise Exception
        return winner

    def pick_winner(self):
        if not self.verifyLoaded('get_random_index'):
            return (None,None,None)
        winner = self.get_random_index()
        order_num = sorted(self.dpRes.eligible.keys())[winner]
        dpt = self.dpRes.eligible[order_num]
        winner += 1
        return (winner, order_num, dpt)

    def append_to_door_price_winner_dict(self,door_prize_winner_dict, order_num, door_prize_sf_dict, door_prize_dict):
        dpt_sf = door_prize_sf_dict.get(order_num)
        dpt_door_prize = door_prize_dict.get(order_num)
        dpt = dpt_sf or dpt_door_prize
        if not dpt:
            msg = 'Failure adding key of {0} to door_prize_winner_dict of '\
                  'size {1}. Its missing from door_prize_sf_dict of size {1} and door_prize_dict of size '\
                  '{2}'
            input(msg.format(order_num, len(door_prize_winner_dict), len(door_prize_sf_dict), len(door_prize_dict)))
            raise Exception
        dpt_orig = door_prize_winner_dict.get(order_num)
        if dpt_orig:
            msg = 'Failure adding key of {0} to door_prize_winner_dict of size {1}. It already exists in door_prize_winner_dict.'
            input(msg.format(order_num, len(door_prize_winner_dict)))
            raise Exception
        # use CONFIRM_NOTE as place to store time winner chosen. Thats useful for ui.
        CONFIRM_NOTE = 'Winner chosen {0}'.format(datetime.datetime.now().strftime('%m/%d %H:%M:%S'))
        dpt = dpt._replace(CONFIRM_NOTE=CONFIRM_NOTE)
        door_prize_winner_dict[order_num] = dpt
        return

    def adjustEligibleForWinner(self,order_num):
        self.append_to_door_price_winner_dict(self.dpSrc.winner, order_num, self.dpSrc.sf, self.dpSrc.shopify)
        write_door_prize_file(self.dpSrc.winner, DOOR_PRIZE_WINNER, self.neaf_year, self.neaf_day_of_week)
        door_prize_eligible_dict, door_prize_reject_dict = self.build_eligible_door_prize_dict(self.dpSrc.winner, self.dpSrc.sf, self.dpSrc.shopify)
        return door_prize_eligible_dict, door_prize_reject_dict

    def pick_and_show_winner(self):
        if not self.verifyLoaded('pick_and_show_winner'):
            return self.msg
        winner, order_num, dpt = self.pick_winner()
        msg = '{0}  Winner is number {1} out of {2} eligible. Name:{3} Order#:{4} sku:{5} {6}'
        wtime = datetime.datetime.now().strftime('%H:%M:%S')
        msg = msg.format(wtime, winner, len(self.dpRes.eligible), dpt.name, order_num, dpt.sku, dpt.created_at)
        door_prize_eligible_dict, door_prize_reject_dict = self.adjustEligibleForWinner(order_num)
        self.dpRes.eligible.clear()
        self.dpRes.eligible.update(door_prize_eligible_dict)
        self.dpRes.reject.clear()
        self.dpRes.reject.update(door_prize_reject_dict)
        return msg

    def show_random_index(self):
        if not self.verifyLoaded('show_random_index'):
            return self.msg
        winner = self.get_random_index()
        msg = 'winner:{0} selected. Range was 0 to len(DoorPrize.dpRes.eligible) - 1:{1}.'
        msg = msg.format(winner, len(self.dpRes.eligible) - 1)
        return msg

def validDoorPrizeFile(fname,verbose):
    dpFile = os.path.join(RAC_DIR(),fname)
    reader = csv.reader(open(dpFile))
    try:
        fields = next(reader)
    except Exception as ex:
        if verbose:
            msg = 'In validDoorPrizeFile failure processing {0}. Exception raised executing reader.next().\nAssume this file is invalid. Exception is\n{1}'
            input(msg.format(fname,ex))    
        return False
    if len(fields) != len(DOOR_PRIZE_HEADER):
        return False
    for field in fields:
        if field not in DOOR_PRIZE_HEADER:
            return False
    return True                

def choose_day(override_day):
    if not override_day:
        return DEFAULT_DAY
    elif override_day.lower().startswith('sat'):
        return SATURDAY
    elif override_day.lower().startswith('sun'):
        return SUNDAY
    return DEFAULT_DAY

def main():

    def valid_dp(label,dp):
        if not dp:
            print("Cannot run '{0}' option. First run '0:SF and Shopify Load' and build DoorPrize object.".format(label))
            return False
        return True

    dp = None
    override_day = DEFAULT_DAY
    verbose = False
    valid_inputs = ['0','1','2','3','4','5','6','7','8','9','10','11','12']
    while True:
        print('\n\n12:stop')
        print('\n\n5:verbose True    6:verbose False    7:hints    8:show paths and files    9:get_random_index   10 <search item>   11:get random number 0 to 99')
        msg =     '0:SF and Shopify Load   1:pick_winner   2:build winners pdf   3:show_dicts    4:choose_day(sat, sun, def)\n-----> '
        optionstr = input(msg)
        toks = optionstr.split()
        optionstr = toks[0]
        optionArgs = ' '.join(toks[1:]) if len(toks)>1 else None
        if optionstr not in valid_inputs:
            print('Choice not valid. Try again.')
            continue 
        option = int(optionstr)
        if option == 12:
            break
        if option == 4:
            override_day = choose_day(optionArgs)
            continue
        if option == 5:
            verbose = True
            continue
        if option == 6:
            verbose = False
            continue     
        if option == 7:
            if not valid_dp('7:hints',dp):
                continue
            msg = dp.show_hints_dp()
            print(msg)
            continue    
        if option == 8:
            msg = show_paths_and_files_dp(dp.neaf_year, dp.neaf_day_of_week)
            print(msg)
            continue
        if option == 9:
            if not valid_dp('9:get_random_index',dp):
                continue
            msg = dp.show_random_index()
            print(msg)
            continue
        if option == 10:
            if not valid_dp('10 <search item>',dp):
                continue
            msg = dp.search_for_item(optionArgs)
            print(msg)
            continue
        if option == 11:
            winner = get_random_in_range(99)
            msg = 'winner:{0} selected. Range was 0 to 99'
            msg = msg.format(winner)
            print(msg)

            continue

        if option == 0:

            dp = DoorPrize(override_day=override_day,verbose=verbose)
            dp.sFAndShopifyLoad()
            if dp.error:
                print(dp.error)

        if option == 3:
            if not valid_dp('3:show_dicts',dp):
                continue
            print(dp.show_dicts())
            continue
        if option == 2:
            if not valid_dp('2:build winners pdf',dp):
                continue
            print(build_winners_pdf(dp.dpSrc.winner,dp.neaf_year,dp.neaf_day_of_week))
            continue
        if option == 1:
            if not valid_dp('1:pick_winner',dp):
                continue
            msg = dp.pick_and_show_winner()
            print(msg)
            continue
    return

# comment out next call to main before copying to RAC_share. uncomment only for testing.
#main()

