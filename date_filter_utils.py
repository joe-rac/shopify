# 2/26/2026. This module centralizes all logic related to:
#            created_at_min / created_at_max
#            NEAF year / NEAF day semantics
#            The classes AccessOrders, NEAFVendor and DoorPrize all inherit from AccessShopify and all need date filters when they load from shopify.

from datetime import datetime,date
from consts import NEAF_RELATED_PRODUCT_TYPES,NEAF_YEAR_DEFAULT,DONATION,MEMBERSHIP,NEAF_DATES,NEAF_YEAR_VALID,NEAF_YEAR_ALL,ERROR,SATURDAY,SUNDAY,NEAF_DAYS,DEFAULT_DAY
from utils import get_date,get_default_neaf_year,goodDateStr,appendMsg

def initialize_neaf_year(created_at_min,created_at_max,neaf_year):

    # 3/3/2025. called from AccessShopify.__init__

    error = ''
    neaf_year_normalized = ''

    if created_at_min:
        if not get_date(created_at_min):
            error = "created_at_min: '{0}' passed to AccessShopify.__init__ not in valid date form.".format(created_at_min)
            return neaf_year_normalized,error
    if created_at_max:
        if not get_date(created_at_max):
            error = 'created_at_max:{0} passed to AccessShopify.__init__ not in valid date form.'.format(created_at_max)
            return neaf_year_normalized,error
    if created_at_min and created_at_max and created_at_min > created_at_max:
        msg = 'created_at_min:{0} and created_at_max:{1} passed to AccessShopify.__init__ are invalid. created_at_min must be less than or equal to created_at_max.'
        error = msg.format(created_at_min,created_at_max)
        return neaf_year_normalized,error

    if not neaf_year and (created_at_min and created_at_max):
        # no need for neaf year if both min and max date exist.
        pass
    else:
        neaf_year = str(neaf_year) if neaf_year else NEAF_YEAR_DEFAULT
    nyr_default = get_default_neaf_year()
    nyr = ''
    if neaf_year.isdigit():
        nyr = int(neaf_year)
        if nyr < 2015 or nyr > nyr_default:
            error = 'neaf_year:{0} is invalid. Must be from {1} to {2}.'.format(nyr,2015,nyr_default)
    elif neaf_year and neaf_year not in NEAF_YEAR_VALID:
        error = f'neaf_year of {neaf_year}. Must be one of {NEAF_YEAR_VALID} or blank.'
    if error:
        return neaf_year_normalized,error
    if neaf_year == NEAF_YEAR_ALL:
        neaf_year_normalized = ''
    else:
        neaf_year_normalized = nyr

    if neaf_year and (created_at_min or created_at_max):
        error = f'neaf_year:{neaf_year}, created_at_min:{created_at_min} and created_at_max:{created_at_max} are incompatible. Either use neaf_year or created_at_min/created_at_max.'

    return neaf_year_normalized,error

def initialize_created_at_min_and_max(created_at_min, created_at_max, neaf_year):

    # 3/3/2025. called from AccessShopify.__init__
    
    error = ''

    if created_at_min:
        created_at_min_normalized,error = goodDateStr(created_at_min)
    else:
        created_at_min_normalized = '2014-10-01' if neaf_year == NEAF_YEAR_ALL else '{0}-10-01'.format(neaf_year-1)
    if created_at_max:
        created_at_max_normalized,error = goodDateStr(created_at_max)
    else:
        if neaf_year:
            created_at_max_normalized = '{0}-06-01'.format(neaf_year)
        else:
            now = datetime.now()
            created_at_max_normalized = '{0}-{1}'.format(now.year+1,now.strftime('%m-%d'))
    today = datetime.now().strftime('%Y-%m-%d')
    if created_at_max_normalized > today:
        created_at_max_normalized = today

    if created_at_min_normalized and created_at_max_normalized and created_at_min_normalized > created_at_max_normalized:
        error = f'created_at_min:{created_at_min_normalized} and created_at_max:{created_at_max_normalized} are incompatible. created_at_min must be less than or equal to created_at_max.'

    return created_at_min_normalized,created_at_max_normalized,error

def calc_default_date_window_from_product_type(product_type):

    # 2/22/2026. XXX called from Order.__init__.
    #                this function solves difficult problem of coming up with default start and end dates for each product. You can imagine how hard that is
    #                considering RAC events all take place at different times of year.

    now = datetime.now()
    year = now.year
    month = now.month
    created_at_max = now.strftime('%Y-%m-%d')

    if product_type in NEAF_RELATED_PRODUCT_TYPES:
        created_at_min = f'{int(NEAF_YEAR_DEFAULT) - 1}-07-01'
    elif product_type in (DONATION,MEMBERSHIP):

        # 1/14/2026. Frank typically asks for prior year totals at the begining of the year so I arbitrarily use July 1 as cutover to this year.
        if month >= 7:
            created_at_min = f'{year}-01-01'
        else:
            created_at_min = f'{year-1}-01-01'
            created_at_max = f'{year-1}-12-31'

    elif 'hsp' in product_type:

        if month >= 4:
            created_at_min = f'{year}-04-01'
        else:
            created_at_min = f'{year-1}-04-01'

    elif 'rad' in product_type:
        if month >= 10:
            created_at_min = f'{year}-10-01'
        else:
            created_at_min = f'{year-1}-10-01'

    elif product_type == 'cc_door_prize':
        now_dt = now.date()
        now_date = now_dt.strftime("%Y-%m-%d")
        default_neaf_start_date = NEAF_DATES[int(NEAF_YEAR_DEFAULT)][0]
        default_neaf_end_date = NEAF_DATES[int(NEAF_YEAR_DEFAULT)][1]
        prior_neaf_start_date = NEAF_DATES[int(NEAF_YEAR_DEFAULT)-1][0]
        prior_neaf_end_date = NEAF_DATES[int(NEAF_YEAR_DEFAULT)-1][1]
        if now_date >= default_neaf_start_date:
            created_at_min = default_neaf_start_date
            created_at_max = default_neaf_end_date
        else:
            created_at_min = prior_neaf_start_date
            created_at_max = prior_neaf_end_date

    else:
        start_date = now - datetime.timedelta(days=370)
        created_at_min = start_date.strftime('%Y-%m-%d')
    return created_at_min,created_at_max

def calc_date_items_from_neaf_year_and_day(neaf_year,override_day):

    # 3/5/2026. XXX called from DoorPrize.__init__ .
    #               return neaf date, neaf day of week, other neaf day of week, error

    error = ''

    if override_day not in NEAF_DAYS:
        error = f'override_day:{override_day} is invalid. Must be one of NEAF_DAYS:{NEAF_DAYS}.'
        return None,None,None,error

    neaf_year = int(neaf_year)

    neaf_start = NEAF_DATES[neaf_year][0]
    neaf_start_date = date.fromisoformat(neaf_start)
    neaf_start_dow = neaf_start_date.strftime("%A")
    neaf_end = NEAF_DATES[neaf_year][1]
    neaf_end_date = date.fromisoformat(neaf_end)
    neaf_end_dow = neaf_end_date.strftime("%A")

    today_date = datetime.now().date()
    today_dow =  today_date.strftime("%A")
    today = today_date.strftime('%Y-%m-%d')
    if today_date < neaf_start_date:
        error = f"NEAF {neaf_year} doesn't start until {neaf_start_date} but today is {today}. Can't load NEAF {neaf_year} door prize data until it starts."
        return None,None,None,error

    if override_day == SATURDAY and neaf_start_dow != SATURDAY:
        error = f'override_day:{override_day} is inconsistent with NEAF start day of week:{neaf_start_dow} for NEAF day:{neaf_start}.'
        return None,None,None,error
    if override_day == SUNDAY and neaf_end_dow != SUNDAY:
        error = f'override_day:{override_day} is inconsistent with NEAF end day of week:{neaf_end_dow} for NEAF day:{neaf_end}.'
        return None,None,None,error

    if override_day == SATURDAY:
        return NEAF_DATES[neaf_year][0],override_day,neaf_end_dow,error
    elif override_day == SUNDAY:
        return NEAF_DATES[neaf_year][1],override_day,neaf_start_dow,error

    # 3/3/2026. override_day is DEFAULT_DAY beyond this point.

    if today == neaf_start:
        return today,neaf_start_dow,neaf_end_dow,error
    if today == neaf_end:
        return today,neaf_end_dow,neaf_start_dow,error

    error = f'override_day:{override_day} cannot determine NEAF date for today:{today}, {today_dow} which does not match NEAF dates {neaf_start}, {neaf_start_dow} or {neaf_end}, {neaf_end_dow}.'

    return None,None,None,error

def parse_constant_contact_date_filter_args(neaf_year, neaf_day):

    msg = ''
    msg_ex = ''
    neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow = (None,) * 7

    msg_front = 'In get_cc_door_prize_list'
    if neaf_year not in NEAF_YEAR_VALID:
        msg_ex = f"{msg_front} passed in value of neaf_year:{neaf_year} not in NEAF_YEAR_VALID:{NEAF_YEAR_VALID}."
        return neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex
    if neaf_day not in NEAF_DAYS:
        msg_ex = f"{msg_front} passed in value of neaf_day:{neaf_year} not in NEAF_DAYS:{NEAF_DAYS}."
        return neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex
    neaf_year_int = int(neaf_year)
    neaf_year_default_int = int(NEAF_YEAR_DEFAULT)
    if neaf_year_int > neaf_year_default_int:
        msg_ex = f"{msg_front} neaf_year:{neaf_year} is greater then NEAF_YEAR_DEFAULT:{NEAF_YEAR_DEFAULT}. That's a major fuckup. Current implementation does not support that."
        return neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex

    neaf_start = NEAF_DATES[int(neaf_year)].neaf_start
    neaf_end = NEAF_DATES[int(neaf_year)].neaf_end
    neaf_start_date = date.fromisoformat(neaf_start)
    neaf_end_date = date.fromisoformat(neaf_end)
    diff_neaf_days = (neaf_end_date - neaf_start_date).days
    if diff_neaf_days != 1:
        msg_ex = f"{msg_front} neaf_start:{neaf_start} neaf_end:{neaf_end} implied by neaf_year:{neaf_year} have diff_neaf_days:{diff_neaf_days}. Must be 1."
        return neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex
    today_date = datetime.now().date()
    diff_to_neaf_start = (neaf_start_date - today_date).days
    if diff_to_neaf_start > 0:
        msg_ex = f"{msg_front} neaf_start:{neaf_start} is in the future from today_date:{today_date}. There is no use case for NEAF to be in the future."
        return neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex

    today = today_date.strftime('%Y-%m-%d')
    neaf_start_dow = neaf_start_date.strftime('%A')
    neaf_end_dow = neaf_end_date.strftime('%A')
    if neaf_day != DEFAULT_DAY and neaf_year == NEAF_YEAR_DEFAULT and (today == neaf_start_date or today == neaf_end_date):
        msg_ex = f"{msg_front} neaf_year:{neaf_year} equals NEAF_YEAR_DEFAULT:{NEAF_YEAR_DEFAULT}, today:{today} is one of neaf_start:{neaf_start} or neaf_end:{neaf_end}.\n" + \
                 f"That means we are running live during NEAF. neaf_day:{neaf_day} is invalid during NEAF. It must be DEFAULT_DAY:{DEFAULT_DAY} and we use calendar day of week for neaf_day."
        return neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex

    neaf_start_mon = neaf_start_date.strftime('%B')
    neaf_end_mon = neaf_start_date.strftime('%B')
    if neaf_year != NEAF_YEAR_DEFAULT:
        if neaf_start_mon != 'April' or neaf_end_mon != 'April':
            msg_ex = f"{msg_front} neaf_start_mon:{neaf_start_mon}, neaf_end_mon:{neaf_end_mon} are invalid for neaf_year:{neaf_year}.\n" + \
                     f"Only neaf_year of NEAF_YEAR_DEFAULT:{NEAF_YEAR_DEFAULT} can have NEAF days not in April and only for testing purposes."
            return neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex
        if neaf_start_dow != SATURDAY or neaf_end_dow != SUNDAY:
            msg_ex = f"{msg_front} neaf_start_dow:{neaf_start_dow}, neaf_end_dow:{neaf_end_dow} are invalid for neaf_year:{neaf_year}.\n" + \
                     f"Only neaf_year of NEAF_YEAR_DEFAULT:{NEAF_YEAR_DEFAULT} can have NEAF days of week not on weekend and only for testing purposes."
            return neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex

    if neaf_year == NEAF_YEAR_DEFAULT:
        if neaf_start_mon != 'April' or neaf_end_mon != 'April':
            msg = appendMsg(msg,f'WARNING: NEAF days of {neaf_start} and {neaf_end} are not both in April. Thats because we are running in TEST mode, not PROD mode.')
        if neaf_start_dow != SATURDAY or neaf_end_dow != SUNDAY:
            msg = appendMsg(msg,f'WARNING: NEAF start day of week:{neaf_start_dow} and NEAF end day of week:{neaf_end_dow} are not {SATURDAY} and {SUNDAY}.')
            msg = appendMsg(msg,'         Thats because we are running in TEST mode, not PROD mode.')

    return neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex