
import os
import tracemalloc
import tempfile
import random
from datetime import datetime,timedelta
from collections import namedtuple
from openpyxl import Workbook
from openpyxl.styles import Alignment

from consts import HSP_YEAR_DEFAULT,HSP,HSP_DATES,MEMBERSHIP,MISSING,DEFAULT_NUM_HSP_RAFFLE_WINNERS
from utils import load_franks_rac_membership_spreadsheet,appendMsg,show_and_save_namedtuple_collection_as_excel
from orders import Orders

HSP_ATTENDEE_FIELDS = 'name first_name last_name email expiration_date contribution starbq cabin raffle prv_tent platform order_nums created_at_latest comment'
HspAttendeeTup = namedtuple('HspAttendeeTup', HSP_ATTENDEE_FIELDS)

class HSPAttendees(object):

    def __init__(self,hsp_year=HSP_YEAR_DEFAULT):

        # 9/2/2026. call self.shopifyAndFranksSpreadsheetLoad() to load data.

        self.msg = ''
        self._error_cstr = ''
        self._error_load = ''
        self.membership_list = []
        self.email_to_rmt_list_map = {}
        self.name_to_rmt_list_map = {}
        self.raffle_tickets = []
        self.hat_list = []
        self.hsp_full_order_with_properties_dict = {}
        self.membership_full_order_with_properties_dict = {}

        self.contribution_total = 0
        self.starbq_total = 0
        self.cabin_total = 0
        self.raffle_total = 0
        self.prv_tent_total = 0
        self.platform_total = 0
        self.contribution_total_dollars = 0
        self.starbq_total_dollars = 0
        self.cabin_total_dollars = 0
        self.raffle_total_dollars = 0
        self.prv_tent_total_dollars = 0
        self.platform_total_dollars = 0
        self.total_dollars = 0
        self.num_distinct_raffle_emails = 0

        self.items_to_share_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'items_to_share')
        if not os.path.isdir(self.items_to_share_dir):
            self._error_cstr = f"items_to_share dir of {self.items_to_share_dir}. It must exist and is used to hold Frank's membership Excel files"
            return
        try:
            self.hsp_year = int(hsp_year)
        except:
            self._error_cstr = f"hsp_year:'{hsp_year}' passed to HSPAttendee.__init__ is invalid. It must be interpreted as an integer."
            return
        hspDates = HSP_DATES.get(self.hsp_year)
        if not hspDates:
            self._error_cstr = f"hsp_year:{self.hsp_year} passed to HSPAttendee.__init__ is invalid. Only supported years are {','.join(str(k) for k in HSP_DATES.keys())}."
            return
        self.created_at_max = (datetime.strptime(hspDates.hsp_end, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        self.created_at_min = f'{self.hsp_year}-01-01'
        self.created_at_min_membership = f'{self.hsp_year}-08-01'

        memory_usage = tracemalloc.get_traced_memory()
        print(f'memory usage at exit from HSPAttendee.__init__(...) : current:{memory_usage[0]}, peak:{memory_usage[1]}')

        return

    @property
    def error(self):
        error = ''
        # 9/22/2026. this is a subtle point that _error_load gets priority. thats because a type of load error is that load being called even though there is preexisting cstr error.
        #            load routine includes text of cstr error in it own error so no need to include cstr error here.
        if self._error_load:
            return self._error_load
        if self._error_cstr:
            error = self._error_cstr
        return error

    def buildAndDisplaySales(self):

        # 9/22/2026. create and open excel showing all HSP sales. if the user wants to save this excel it is their reponsibility to save it in a location of their choice.

        if self.error:
            return f"Cannot build and display HSP sales s/s because of preexisting error of\n'{self.error}'"
        if not len(self.hat_list):
            return 'Cannot build and display HSP sales s/s because no HSP sales data loaded.'

        msg = show_and_save_namedtuple_collection_as_excel(sorted(self.hat_list, key=lambda hat: hat.created_at_latest, reverse=True), description='HSP Attendees', column_is_text=('order_nums',))

        return msg

    def shopifyAndFranksSpreadsheetLoad(self):

        # 9/2/2026. analogous to the self.ShopifyLoad functions but also loads Frank's membership s/s.

        self._error_load = ''
        if self._error_cstr:
            self._error_load = f"Cannot load data because of pre-existing cstr error of '{self._error_cstr}'"
            return
        membership_file_full_path = os.path.join(self.items_to_share_dir,f'RAC AUGUST {self.hsp_year} Membership.xlsx')
        membership_list, email_to_rmt_list_map, name_to_rmt_list_map, self._error_load, msg = load_franks_rac_membership_spreadsheet(membership_file_full_path)

        self.msg = ''

        self.membership_list.clear()
        self.email_to_rmt_list_map.clear()
        self.name_to_rmt_list_map.clear()
        self.raffle_tickets.clear()
        self.hat_list.clear()
        self.hsp_full_order_with_properties_dict.clear()
        self.membership_full_order_with_properties_dict.clear()

        self.contribution_total = 0
        self.starbq_total = 0
        self.cabin_total = 0
        self.raffle_total = 0
        self.prv_tent_total = 0
        self.platform_total = 0
        self.contribution_total_dollars = 0
        self.starbq_total_dollars = 0
        self.cabin_total_dollars = 0
        self.raffle_total_dollars = 0
        self.prv_tent_total_dollars = 0
        self.platform_total_dollars = 0
        self.total_dollars = 0
        self.num_distinct_raffle_emails = 0

        self.membership_list.extend(membership_list)
        self.email_to_rmt_list_map.update(email_to_rmt_list_map)
        self.name_to_rmt_list_map.update(name_to_rmt_list_map)
        self.msg = appendMsg(self.msg,msg,print_new_msg=False)
        if self.error:
            return

        hsp_orders = Orders(HSP)
        if hsp_orders.error:
            self._error_load = hsp_orders.error
            return

        hsp_orders.shopifyLoad(created_at_min=self.created_at_min,created_at_max=self.created_at_max)
        self.msg = appendMsg(self.msg,hsp_orders.msg,print_new_msg=False)
        if hsp_orders.error:
            self._error_load = hsp_orders.error
            return
        self.hsp_full_order_with_properties_dict.update(hsp_orders.full_order_with_properties_dict)

        email_to_owpt_list_map = {}
        name_to_owpt_list_map = {}
        for owpt in self.hsp_full_order_with_properties_dict.values():

            key_email = owpt.email.lower()
            owpt_list = email_to_owpt_list_map.get(key_email,[])
            if not owpt_list:
                email_to_owpt_list_map[key_email] = owpt_list
            owpt_list.append(owpt)

            key_name = owpt.name.lower()
            owpt_list = name_to_owpt_list_map.get(key_name,[])
            if not owpt_list:
                name_to_owpt_list_map[key_name] = owpt_list
            owpt_list.append(owpt)

        self.msg += f"\n# distinct emails in HSP orders:{len(email_to_owpt_list_map)}, # distinct names in HSP orders:{len(name_to_owpt_list_map)}."
        if len(email_to_owpt_list_map) != len(name_to_owpt_list_map):
            self._error_load = f"MAJOR LOGIC FUCKUP. # distinct emails in HSP orders:{len(email_to_owpt_list_map)} does not equal # distinct names in HSP orders:{len(name_to_owpt_list_map)}"
            return

        # 9/4/2026. populate self.hat_list
        distinct_raffle_email = set()
        for key_email,owpt_list in email_to_owpt_list_map.items():

            # 9/4/2026. get membership expiration date
            rmt_list = self.email_to_rmt_list_map.get(key_email)
            if rmt_list:
                expiration_date = rmt_list[0].expiration_date
                for rmt in rmt_list:
                    if rmt.expiration_date > expiration_date:
                        expiration_date = rmt.expiration_date
            else:
                expiration_date = MISSING

            name = owpt_list[0].name
            first_name = owpt_list[0].first_name
            last_name = owpt_list[0].last_name
            email = owpt_list[0].email
            contribution = 0
            starbq = 0
            cabin = 0
            raffle = 0
            prv_tent = 0
            platform = 0
            contribution_dollars = 0
            starbq_dollars = 0
            cabin_dollars = 0
            raffle_dollars = 0
            prv_tent_dollars = 0
            platform_dollars = 0
            order_nums = ''
            created_at_latest = ''

            comment = ''
            found_attendee = False
            for owpt in owpt_list:

                onum = owpt.order_num
                toks = onum.split('-')
                if len(toks) == 2:
                    onum = toks[0]
                if not order_nums:
                    order_nums = onum
                else:
                    if onum not in order_nums.split('|'):
                        order_nums += '|' + onum

                if not created_at_latest:
                    created_at_latest = owpt.created_at
                else:
                    if owpt.created_at > created_at_latest:
                        created_at_latest = owpt.created_at

                if owpt.name not in name.split('|'):
                    name += '|' + owpt.name

                if owpt.sku == 'hsp_contribution':
                    found_attendee = True
                    contribution += owpt.quantity
                    contribution_dollars += int(owpt.paid)
                if owpt.sku == 'hsp_starbq':
                    found_attendee = True
                    starbq += owpt.quantity
                    starbq_dollars += int(owpt.paid)
                if owpt.sku.startswith('hsp_cabin_for_2_'):
                    found_attendee = True
                    cabin += owpt.quantity
                    cabin_dollars += int(owpt.paid)
                if owpt.sku.startswith('hsp_raffle_'):
                    raffle_num = owpt.quantity * int(owpt.sku.split('_')[-1])
                    raffle += raffle_num
                    distinct_raffle_email.add(owpt.email.lower())
                    for i in range(raffle_num):
                        order_num = owpt.order_num.split('-')[0]
                        created_at = owpt.created_at[:-3]
                        self.raffle_tickets.append((owpt.name,owpt.email,owpt.phone_num,owpt.address3,order_num,created_at,owpt.sku))
                    raffle_dollars += int(owpt.paid)
                if owpt.sku.startswith('hsp_prv_tent_'):
                    found_attendee = True
                    prv_tent += owpt.quantity
                    prv_tent_dollars += int(owpt.paid)
                if owpt.sku.startswith('hsp_platform_for_'):
                    found_attendee = True
                    platform += owpt.quantity
                    platform_dollars += int(owpt.paid)

            if not found_attendee:
                contribution = MISSING
                starbq = MISSING

            if isinstance(contribution,int):
                self.contribution_total += contribution
                self.contribution_total_dollars += contribution_dollars
            if isinstance(starbq,int):
                self.starbq_total += starbq
                self.starbq_total_dollars += starbq_dollars
            self.raffle_total += raffle
            self.raffle_total_dollars += raffle_dollars
            self.cabin_total += cabin
            self.cabin_total_dollars += cabin_dollars
            self.prv_tent_total += prv_tent
            self.prv_tent_total_dollars += prv_tent_dollars
            self.platform_total += platform
            self.platform_total_dollars += platform_dollars
            self.hat_list.append(HspAttendeeTup(name,first_name,last_name,email,expiration_date,contribution,starbq,cabin,raffle,prv_tent,platform,order_nums,created_at_latest,comment))

        self.total_dollars = self.contribution_total_dollars + self.starbq_total_dollars + self.raffle_total_dollars + self.cabin_total_dollars + self.prv_tent_total_dollars + \
                             self.platform_total_dollars
        self.num_distinct_raffle_emails = len(distinct_raffle_email)

        # 9/2/2026. XXX You might find it odd that we are loading membership orders when we are supposed to find membership expiration date in Frank's membership files.
        #               The reason we do this is that Frank's files are for end of August. If there are any late membership orders after that but before HSP this will pick them up.
        membership_orders = Orders(MEMBERSHIP)
        if membership_orders.error:
            self._error_load = membership_orders.error
            return
        membership_orders.shopifyLoad(created_at_min=self.created_at_min_membership,created_at_max=self.created_at_max)
        if membership_orders.error:
            self._error_load = membership_orders.error
            return
        self.membership_full_order_with_properties_dict.update(membership_orders.full_order_with_properties_dict)

        self.msg = appendMsg(self.msg,membership_orders.msg,print_new_msg=False)
        dt_str = datetime.now().strftime('%Y-%m-%d %#I:%M%p')
        msg_totals = f"HSP SALES TOTALS as of {dt_str}:\ncontribution:{self.contribution_total}, starbq:{self.starbq_total}, # raffle purchasers:{self.num_distinct_raffle_emails}, "\
                     f"raffle:{self.raffle_total}, cabin:{self.cabin_total}, prv_tent:{self.prv_tent_total}, platform:{self.platform_total}"
        msg_totals += f"\nHSP SALES TOTALS DOLLARS\ncontribution:${self.contribution_total_dollars}, starbq:${self.starbq_total_dollars}, raffle:${self.raffle_total_dollars},"\
                     f" cabin:${self.cabin_total_dollars}, prv_tent:${self.prv_tent_total_dollars}, platform:${self.platform_total_dollars}"
        msg_totals += f"\nTOTAL SALES: ${self.total_dollars}"
        print(msg_totals)
        self.msg = appendMsg(self.msg,msg_totals,print_new_msg=False)

        return

    def pick_raffle_winners(self, num_winners=DEFAULT_NUM_HSP_RAFFLE_WINNERS):
        msg = ''
        if self.error:
            return msg, f"Cannot pick raffle winner. First must repair preexisting error of\n'{self.error}'"
        if not self.hsp_full_order_with_properties_dict:
            return msg, 'Cannot pick raffle winner. No HSP data loaded.'
        if isinstance(num_winners,str):
            if not num_winners.isdigit():
                return msg, f'num_winners:{num_winners} is not an integer.'
            else:
                num_winners = int(num_winners)
        if not isinstance(num_winners,int):
            return msg, f"num_winners:{num_winners} is not an integer."
        if not (1 <= num_winners <= 10):
            return msg, f"num_winners:{num_winners} must be between 1 and 10."
        num_raffle_tickets = len(self.raffle_tickets)
        if num_raffle_tickets < num_winners:
            return msg, f'Cannot pick {num_winners} raffle winners. Only {num_raffle_tickets} raffle tickets sold.'
        if self.num_distinct_raffle_emails < num_winners:
            return msg, f'Requesting num_winners:{num_winners} but num_distinct_raffle_emails is only {self.num_distinct_raffle_emails}. num_winners must be <= num_distinct_raffle_emails.'

        raffle_tickets = self.raffle_tickets.copy()
        msg += f'{"Prize #":>7}{"random selection":>19}{"order #":>9}{"name":>30}{"email":>35}{"phone":>16}{"created_at":>18}{"sku":>16}'
        for i in range(num_winners):
            winner_ind = random.randrange(len(raffle_tickets))
            winner = raffle_tickets[winner_ind]
            msg += f'\n{f"#{i+1}":>7}{f"{winner_ind+1} out of {len(raffle_tickets)}":>19}{f"#{winner[4]}":>9}{winner[0]:>30}{winner[1]:>35}{winner[2]:>16}{str(winner[5]):>18}{winner[6]:>16}'
            winner_email = winner[1].lower()
            raffle_tickets = [rt for rt in raffle_tickets if rt[1].lower() != winner_email]

        return msg,''