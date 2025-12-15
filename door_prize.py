import csv
import os
import datetime
import random
import tracemalloc
from consts import NEAF_DATES,DOOR_PRIZE,USE_GRAPHQL,NEAF_ATTEND_DOOR_PRIZE
from utils import RAC_DIR,build_door_prize_cc_dict,get_weekend_day,DEFAULT_DAY,DICT_DELIMITER_FRONT,delta_on_date_str
from utils import show_dict,read_door_prize_file,DOOR_PRIZE_HEADER,write_door_prize_file,DoorPrizeSrcDicts,DoorPrizeResDicts
from utils import show_paths_and_files_dp,DOOR_PRIZE_WINNER,get_default_neaf_year,DoorPrizeTup,ERROR,SATURDAY,SUNDAY
from orders import Orders
from graphql_utils import get_url_and_headers
from pdf_utils import build_winners_pdf
from constant_contact import get_cc_door_prize_list
from access_shopify import AccessShopify,NEAF_YEAR_DEFAULT

def get_random_in_range(max_num):
    winner = random.randint(0, max_num - 1)
    return winner


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

    def __init__(self,neaf_year=NEAF_YEAR_DEFAULT,sku_key=DOOR_PRIZE,override_day=DEFAULT_DAY,order_to_debug=None,verbose=False):

        created_at_min = None
        created_at_max = None

        # TODO uncomment these variable to debug a prior years NEAF
        #neaf_year = None
        #created_at_min = '2018-08-01'
        #created_at_max = '2019-05-01'
        super(DoorPrize, self).__init__(neaf_year,created_at_min,created_at_max,order_to_debug,verbose)
        if self.error:
            return
        if not self.neaf_year:
            # even if created_at_min,created_at_max are set we still need neaf_year to lookup actual days of neaf.
            self.neaf_year = int(self.created_at_min[0:4]) + 1

        # sku_key can also be MERCH. example is in search_and_mark
        self.sku_key = sku_key
        # 12/30/2022. this function populates self.raw from self.rawOrdersTupList which was built in shopifyOrdersFromHttps.

        self.dpSrc = None
        self.dpRes = None
        self.prev_load_time = None
        self.fname = None
        self.weekend_day = get_weekend_day(override_day)
        if self.weekend_day == ERROR:
            self.error = 'override_day:{0} is invalid. Must be set to Saturday or Sunday if weekday.'.format(override_day)

        # I found 37 entries in CC list named NEAF_Door_Prize_Registration from 3/2/2023. they shouldn't be there since only way names should get in that list is on NEAF show days
        # when attendees register. I asked Mies if he knows how names got in there and he said "I have no idea". I'll just ignore that day.
        self.cc_dates_to_ignore = ['2023-03-02','2023-03-11','2023-03-12']

        return

    def build_eligible_door_prize_dict(self,door_prize_winner_dict, door_prize_cc_dict, door_prize_dict):
        door_prize_eligible_dict = {}
        door_prize_reject_dict = {}
        for k, v in door_prize_cc_dict.items():
            if door_prize_winner_dict.get(k):
                continue
            door_prize_eligible_dict[k] = v
        other_day = SUNDAY if self.weekend_day == SATURDAY else SATURDAY
        for k, v in door_prize_dict.items():
            if door_prize_winner_dict.get(k) or other_day.lower() in v.sku.lower():
                if other_day.lower() in v.sku.lower():
                    door_prize_reject_dict[k] = v
                continue
            door_prize_eligible_dict[k] = v
        return door_prize_eligible_dict, door_prize_reject_dict

    def constantContactAndShopifyLoad(self):

        # 12/30/2022. load from shopify and populate all in-memory representations needed for full functionality.

        self.msg = ''
        now = datetime.datetime.now()
        if self.prev_load_time:
            # a reload can be forced by passing in prev_load_time as None.
            minutes = (now - self.prev_load_time).total_seconds() / 60.
            if minutes < 15.0:
                # if last load was less than 15 minutes ago skip load and use last results.
                plt = self.prev_load_time.strftime('%H:%M:%S')
                self.msg = 'Inside constantContactAndShopifyLoad(...) skipping re-load of data because last load was less than 15 minutes ago. It was {0:.1f} minutes ago at {2}.'
                self.msg = self.msg.format(minutes, plt)
                print(self.msg)
                return

        if self.error:
            self.error = 'Cannot run DoorPrize.shopifyLoad(). DoorPrize has pre-existing error:\n{0}'.format(self.error)
            return
        # 12/30/2022. shopifyOrdersFromHttps populates self.rawOrdersTupList with raw shopify data from their webservice.
        if USE_GRAPHQL[0]:
            self.shopifyOrdersFromGraphQL()
        else:
            self.shopifyOrdersFromHttps()
        if self.error:
            self.error = 'Failure in DoorPrize.shopifyLoad().\n{0})'.format(self.error)
            return

        # 12/30/2022. convertShopifyOrdersToRacOrders populates self.raw from self.rawOrdersTupList which was built in shopifyOrdersFromHttps.
        self.convertShopifyOrdersToRacOrders()

        door_prize_winner_dict, self.fname = read_door_prize_file(DOOR_PRIZE_WINNER, self.verbose)
        door_prize_dict = self.raw

        ndt = NEAF_DATES[self.neaf_year]
        # As convenience when debugging start looking in Constant Contact 10 weeks before NEAF. this way I can test this app shortly before NEAF starts.
        start_date = delta_on_date_str(ndt.neaf_start, -70)
        ccdpt_list = get_cc_door_prize_list(start_date, ndt.neaf_end, verbose=self.verbose)
        door_prize_cc_dict, door_prize_cc_reject_dict, cc_dates_to_ignore_cnt = build_door_prize_cc_dict(ccdpt_list, self.raw, self.weekend_day, self.cc_dates_to_ignore, self.verbose)

        door_prize_eligible_dict, door_prize_reject_dict = self.build_eligible_door_prize_dict(door_prize_winner_dict,door_prize_cc_dict,door_prize_dict)
        self.dpSrc = DoorPrizeSrcDicts(door_prize_winner_dict, door_prize_cc_dict, door_prize_cc_reject_dict, cc_dates_to_ignore_cnt, door_prize_dict)
        self.dpRes = DoorPrizeResDicts(door_prize_eligible_dict, door_prize_reject_dict)
        self.prev_load_time = datetime.datetime.now()

        print('memory usage at exit from DoorPrize.constantContactAndShopifyLoad after all loading is done : {0}'.format(tracemalloc.get_traced_memory()))
        return

    def verifyLoaded(self,label):
        if not self.raw:
            self.msg = 'Failed running DoorPrize.{0}. No data loaded for this DoorPrize object. Call DoorPrize.constantContactAndShopifyLoad() running this function.'.format(label)
            return False
        self.msg = ''
        return True

    def show_dicts_summary(self):
        msg = '-----------------------------------------------------\n'
        msg += 'DoorPrize.dpSrc.cc size:{0}\n'.format(len(self.dpSrc.cc))
        msg += 'DoorPrize.dpSrc.cc_reject size:{0}\n'.format(len(self.dpSrc.cc_reject))
        msg += 'DoorPrize.dpSrc.cc_dates_to_ignore_cnt:{0}\n'.format(self.dpSrc.cc_dates_to_ignore_cnt)
        msg += 'DoorPrize.dpSrc.shopify size:{0}\n'.format(len(self.dpSrc.shopify))
        msg += 'DoorPrize.dpRes.reject size:{0}\n'.format(len(self.dpRes.reject))
        msg += 'DoorPrize.dpRes.eligible size:{0}\n'.format(len(self.dpRes.eligible))
        msg += 'DoorPrize.dpSrc.winner size:{0}\n'.format(len(self.dpSrc.winner))
        msg += '-----------------------------------------------------\n'
        return msg

    def show_dicts(self):
        if not self.verifyLoaded('show_dicts'):
            return self.msg
        msg = show_dict(self.dpSrc.cc, 'DoorPrize.dpSrc.cc')
        msg += show_dict(self.dpSrc.cc_reject, 'DoorPrize.dpSrc.cc_reject')
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
        2) All Door Prize entries in Constant Contact.       Acquired from Constant Contact api.
        3) Prior winners in file door_prize_winner.csv and are excluded from future drawings.

        Exclude any entries in item 2) with email addresses that match item 1).

        3:choose_day option only used for debugging. Don't use it during NEAF.

        door_prize_reject_dict consists of Shopify entrants that do not belong in the days door prize drawing.
        For example if you have Shopify sku of neaf_attend_admit_saturday and its Sunday you will be in reject dict.
        
        created_at_max:{1}, created_at_min:{2}, neaf_year:{3}, neaf_year_raw:{4}, weekend_day:{5}
        # CC eligible entries:{6}   # CC entries rejected because wrong weekend day:{7}   CC Dates To Ignore:{8}   # of CC entries on Dates to Ignore:{9}
        # eligible Shopify and CC entries:{10}   # CC and Shopify entries rejected because wrong weekend day:{11}   
        # Door Prize Winners:{12}

    ---------------------------------------------------------------------------------------------------------------------    
        '''

        webservice_name = get_url_and_headers()[0] if USE_GRAPHQL[0] else 'https://rockland-astronomy-club.myshopify.com/admin/orders.json'
        hints += '\n' + show_paths_and_files_dp()
        hints = hints.format(webservice_name,self.created_at_max, self.created_at_min, self.neaf_year, self.neaf_year_raw, self.weekend_day,
                             len(self.dpSrc.cc), len(self.dpSrc.cc_reject), self.cc_dates_to_ignore, self.dpSrc.cc_dates_to_ignore_cnt,
                             len(self.dpRes.eligible),len(self.dpRes.reject),len(self.dpSrc.winner))

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
            msg = 'Failure in get_random_index(...) . get_random_in_range(max_num-1={1}) returned {0} but door_prize_eligible_dict has size of {2}. Fix this bug.'
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

    def append_to_door_price_winner_dict(self,door_prize_winner_dict, order_num, door_prize_cc_dict, door_prize_dict):
        dpt_cc = door_prize_cc_dict.get(order_num)
        dpt_door_prize = door_prize_dict.get(order_num)
        dpt = dpt_cc or dpt_door_prize
        if not dpt:
            msg = 'Failure adding key of {0} to door_prize_winner_dict of ' + \
                  'size {1}. Its missing from door_prize_cc_dict of size {1} and door_prize_dict of size ' + \
                  '{2}'
            input(msg.format(order_num, len(door_prize_winner_dict), len(door_prize_cc_dict), len(door_prize_dict)))
            raise Exception
        dpt_orig = door_prize_winner_dict.get(order_num)
        if dpt_orig:
            msg = 'Failure adding key of {0} to door_prize_winner_dict of ' + \
                  'size {1}. It already exists in door_prize_winner_dict.'
            input(msg.format(order_num, len(door_prize_winner_dict)))
            raise Exception
        # use CONFIRM_NOTE as place to store time winner chosen. Thats useful for ui.
        CONFIRM_NOTE = 'Winner chosen {0}'.format(datetime.datetime.now().strftime('%m/%d %H:%M:%S'))
        dpt = dpt._replace(CONFIRM_NOTE=CONFIRM_NOTE)
        door_prize_winner_dict[order_num] = dpt
        return

    def adjustEligibleForWinner(self,order_num):
        self.append_to_door_price_winner_dict(self.dpSrc.winner, order_num, self.dpSrc.cc, self.dpSrc.shopify)
        write_door_prize_file(self.dpSrc.winner, DOOR_PRIZE_WINNER)
        door_prize_eligible_dict, door_prize_reject_dict = self.build_eligible_door_prize_dict(self.dpSrc.winner, self.dpSrc.cc, self.dpSrc.shopify)
        return door_prize_eligible_dict, door_prize_reject_dict

    def pick_and_show_winner(self):
        if not self.verifyLoaded('pick_and_show_winner'):
            return self.msg
        winner, order_num, dpt = self.pick_winner()
        msg = '{0}  Winner is number {1} out of {2} eligible. Name:{3} Order#:{4} sku:{5} {6}'
        wtime = datetime.datetime.now().strftime('%H:%M:%S')
        msg = msg.format(wtime, winner, len(self.dpRes.eligible), dpt.name, order_num, dpt.sku, dpt.created_at)
        door_prize_eligible_dict, door_prize_reject_dict = self.adjustEligibleForWinner(order_num)
        self.dpRes._replace(eligible=door_prize_eligible_dict,reject=door_prize_reject_dict)
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

    def valid_dp(dp,label):
        if not dp:
            print("Cannot run '{0}' option. First run '0:CC and Shopify Load' and build DoorPrize object.".format(label))
            return False
        return True

    dp = None
    override_day = DEFAULT_DAY
    verbose = False
    valid_inputs = ['0','1','2','3','4','5','6','7','8','9','10','11','12']
    while True:
        print('\n\n12:stop')
        print('\n\n5:verbose True    6:verbose False    7:hints    8:show paths and files    9:get_random_index   10 <search item>   11:get random number 0 to 99')
        msg =     '0:CC and Shopify Load   1:pick_winner   2:build winners pdf   3:show_dicts    4:choose_day(sat, sun, def)\n-----> '
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
            msg = show_paths_and_files_dp()
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
            dp.shopifyAndConstantContactLoad()
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
            print(build_winners_pdf(dp.dpSrc.winner))
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

def tutorial_door_prize(override_day=SATURDAY,use_graphql=True,verbose=True):
    USE_GRAPHQL[0] = use_graphql
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
#tutorial_door_prize()
