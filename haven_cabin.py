
from datetime import datetime, timedelta
from consts import HSP_DATES
from graphql_queries import HAVEN_CABIN_PRODUCT
from graphql_utils import graphql_query

HAVEN_CABIN_PRODUCT_ID = 'gid://shopify/Product/7465806397522'
MAX_VARIANTS = 100

def bad_MD_date_msg(i,num_variants,title_curr):
    return f"Variant {i+1} out of {num_variants} of '{title_curr}' is invalid. Must be a valid date in M/D format."

def get_hspDatesTup_items(year):
    hsp_start = ''
    hsp_end = ''
    day_before_hsp = ''
    day_after_hsp = ''
    error = ''
    if year not in HSP_DATES:
        error = f"The current year of {year} has no entry in HSP_DATES imported from consts."
        return hsp_start,hsp_end,day_before_hsp,day_after_hsp,error
    hsp_start = datetime.strptime(HSP_DATES[year][0], '%Y-%m-%d').date()
    hsp_end = datetime.strptime(HSP_DATES[year][2], '%Y-%m-%d').date()
    day_before_hsp = hsp_start - timedelta(days=1)
    day_after_hsp = hsp_end + timedelta(days=1)
    return hsp_start,hsp_end,day_before_hsp,day_after_hsp,error

class HavenCabin(object):

    def __init__(self):

        self.error = ''
        self.msg = ''
        self.title = ''
        self.date_first = ''
        self.date_last = ''

        variables = {'id': HAVEN_CABIN_PRODUCT_ID}
        haven_cabin_product = HAVEN_CABIN_PRODUCT.replace('XXX', str(MAX_VARIANTS + 1))
        data = graphql_query(haven_cabin_product, variables)
        if 'product' not in data or not data['product']:
            self.error = f'Failed to load Haven Cabin product with id:{HAVEN_CABIN_PRODUCT_ID}.'
            return
        self.product = data['product']
        self.variants = self.product['variants']['nodes']
        num_variants =  len(self.variants)

        if num_variants == 0:
            self.error = f'Haven Cabin product with id:{HAVEN_CABIN_PRODUCT_ID} has no variants.'
            return
        if num_variants > MAX_VARIANTS:
            self.error = f'Haven Cabin product with id:{HAVEN_CABIN_PRODUCT_ID} has {num_variants} variants. Maximum allowed is MAX_VARIANTS:{MAX_VARIANTS}.'
            return

        self.title = self.product['title'].replace('<br>',', ')
        curr_year = datetime.now().year
        hsp_start, hsp_end, day_before_hsp, day_after_hsp, self.error = get_hspDatesTup_items(curr_year)
        if self.error:
            return

        prev_month = None
        prev_dt = None
        prev_title = None
        today = datetime.now()
        title_today = f'{today.month}/{datetime.now().day}'
        yesterday = today - timedelta(days=1)
        title_yesterday = f'{yesterday.month}/{yesterday.day}'
        found_todays_title = False
        found_yesterdays_title = False

        for i in range(num_variants):
            title_curr = self.variants[i]['title']
            if title_curr == title_today:
                found_todays_title = True
            if title_curr == title_yesterday:
                found_yesterdays_title = True
            if len(title_curr.split('/')) != 2:
                self.error = bad_MD_date_msg(i,num_variants,title_curr)
                return
            try:
                curr_month = int(title_curr.split('/')[0])
            except:
                self.error = bad_MD_date_msg(i,num_variants,title_curr)
                return
            if not(1<=curr_month<=12):
                self.error = bad_MD_date_msg(i,num_variants,title_curr)
                return

            if prev_month and (prev_month == 12 and curr_month == 1):
                curr_year += 1
                hsp_start, hsp_end, day_before_hsp, day_after_hsp, self.error = get_hspDatesTup_items(curr_year)
                if self.error:
                    return
            try:
                curr_dt = datetime.strptime(title_curr+'/'+str(curr_year), '%m/%d/%Y').date()
            except:
                self.error = bad_MD_date_msg(i,num_variants,title_curr)
                return
            if hsp_start <= curr_dt <= hsp_end:
                self.error = f"Variant {i+1} out of {num_variants} of '{title_curr}' is invalid. It lands on HSP dates {hsp_start.strftime('%Y-%m-%d')} to {hsp_end.strftime('%Y-%m-%d')}."
                return

            if prev_dt:
                # 9/27/2026. confirm curr_dt is one day after prev_dt
                if curr_dt == day_after_hsp:
                    if prev_dt != day_before_hsp:
                        self.error = f"Invalid Haven Cabin dates: {title_curr} is day after HSP ended. Prior variant should be day before HSP starts of " \
                                f"{day_before_hsp.strftime('%Y-%m-%d')} but it is {prev_title}."
                        return
                elif curr_dt - prev_dt != timedelta(days=1):
                    self.error = f'Invalid non-contiguous Haven Cabin dates: {prev_title} followed by variant {i+1} of {title_curr}.'
                    return

            prev_title = title_curr
            prev_month = curr_month
            prev_dt = curr_dt

        self.date_first = self.variants[0]['title']
        self.date_last = self.variants[-1]['title']
        self.msg = f"Loaded Haven Cabin Product '{self.title}' with {num_variants} date variants from {self.date_first} to {self.date_last}."
        if not found_todays_title or not found_yesterdays_title:
            self.msg += '\nWARNING: '
            if not found_todays_title:
                self.msg += f"Today's date of {title_today} is missing. "
            if not found_yesterdays_title:
                self.msg += f"Yesterday's date of {title_yesterday} is missing. "

        return