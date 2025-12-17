
from collections import namedtuple

# TODO 12/27/2024. this is temporary. leave it around for now and remove when we abandon rester api and migrate to GraphQL
USE_GRAPHQL = [False]

ADMIN_API_VERSION = '2024-10'

neafDatesTup = namedtuple('neafDatesTup','neaf_start neaf_end')
NEAF_DATES = {2015:neafDatesTup('2015-04-18','2015-04-19'),2016:neafDatesTup('2016-04-09','2016-04-10'),2017:neafDatesTup('2017-04-08','2017-04-09'),
              2018:neafDatesTup('2018-04-21','2018-04-22'),2019:neafDatesTup('2019-04-06','2019-04-07'),2020:neafDatesTup('2020-04-04','2020-04-05'),
              2021:neafDatesTup('2021-04-10','2021-04-10'),2022:neafDatesTup('2022-04-09','2022-04-10'),2023:neafDatesTup('2023-04-15','2023-04-16'),
              2024:neafDatesTup('2024-04-20','2024-04-21'),2025:neafDatesTup('2025-04-05','2025-04-06'),2026:neafDatesTup('2025-04-11','2025-04-12')}
# any NEAF vendor products ordered in this range are for the 2 virtual NEAFs in 2020 and 2021
VIRTUAL_NEAF_ORDER_RANGE = neafDatesTup('2020-03-01','2021-09-10')
CREATED_AT_MIN_COVID = '2019-11-01'
CREATED_AT_MAX_COVID = '2023-06-01'

# these consts are informational only. They are used on Apps->Manage private apps->Private apps page of shopify admin website at https://rockland-astronomy-club.myshopify.com/admin/apps/private .
# go there to set up new credentials
PRIVATE_APP_NAME = 'py_scripts'
PRIVATE_APP_NAME_2 = 'py_scripts2'
PRIVATE_APP_NAME_RW = 'py_scripts_rw'

# 12/8/2025. the credentials file will be in same dir as project but will be excluded from commit to github with .gitignore file
CREDENTIALS_FILE_NAME = 'credentials.txt'

SHOP_NAME = 'rockland-astronomy-club'

NEAF_MANAGMENT = 'neaf_management'
NEAF_FULL = 'neaf_full'
NEAF_RAW = 'neaf_raw'
NEAF_COMPANY_BADGE = 'neaf_company_badge'
VALID_USER_INPUT_FILE = NEAF_MANAGMENT+'.xlsx'
open_VALID_USER_INPUT_FILE = '~$'+VALID_USER_INPUT_FILE

MEMBERSHIP = 'membership'
DONATION = 'donation'
NEAF_ATTEND = 'neaf_attend'
NEAF_ATTEND_RAFFLE = 'neaf_attend_raffle'
NEAIC_ATTEND = 'neaic_attend'
NEAIC_EXHIBITOR = 'neaic_exhibitor'
RAD = 'rad'
HSP = 'hsp'
HSP_RAFFLE = 'hsp_raffle'
RLS = 'rls'
SSP = 'ssp'
DOOR_PRIZE = 'door_prize'
NEAF_ATTEND_DOOR_PRIZE = 'neaf_attend_door_prize'
MERCH = 'merch'
NEAF_VENDOR = 'neaf_vendor'
NEAF_SOLAR_STAR_PARTY = 'neaf_solar_star_party'
NEAF_VIRTUAL_DOORPRIZE = 'neaf_attend_virtual_door_prize'
TEST = 'test'
ADMIN = 'admin'
NUMBER_OF_DOORPRIZE_WINNERS = 20
NEAF_VIRTUAL_DOORPRIZE_DROPDOWN = '{0} and {1} raffle winners'.format(NEAF_VIRTUAL_DOORPRIZE,NUMBER_OF_DOORPRIZE_WINNERS)
ALL = 'all'
# TODO 9/4/2022. add to SKUS_TO_LOAD_DICT and PRODUCT_TYPES together. when adding a new product category add here and also in PRODUCT_TYPES in orders.py
SKUS_TO_LOAD_DICT = {
    DOOR_PRIZE:('neaf_attend_admit', 'neaic_attend_admission'),
    NEAF_ATTEND_DOOR_PRIZE:(NEAF_ATTEND_DOOR_PRIZE,),
    MERCH:('neaf_attend_merch',),
    NEAIC_ATTEND:(NEAIC_ATTEND,),
    NEAF_ATTEND:(NEAF_ATTEND,),
    NEAIC_EXHIBITOR:(NEAIC_EXHIBITOR,),
    NEAF_ATTEND_RAFFLE:(NEAF_ATTEND_RAFFLE,),
    NEAF_VENDOR:(NEAF_VENDOR,),
    NEAF_SOLAR_STAR_PARTY:(NEAF_SOLAR_STAR_PARTY,),
    MEMBERSHIP:('rac_membership','rac_magazine'),
    DONATION:('rac_donation','admin_donation'), # 12/29/2024. originally we used rac_donation but then I switched to admin_donation. Now its back to rac_donation.
    RAD:(RAD,),
    HSP:(HSP,),
    HSP_RAFFLE:(HSP_RAFFLE,),
    RLS:(RLS,),
    SSP:(SSP,),
    TEST:(TEST,),
    NEAF_VIRTUAL_DOORPRIZE:(NEAF_VIRTUAL_DOORPRIZE,),
    ADMIN:(ADMIN,),
    ALL:ALL
    }
NEAF_RELATED_PRODUCT_TYPES = (NEAF_ATTEND, NEAF_VENDOR, NEAIC_ATTEND,NEAIC_EXHIBITOR)
# 1/15/2023. NEAF Vendor Management Tool queries for neaf_year of 'covid' are different. 'covid' means NEAF 2023 but sum together all NEAF vendor orders from 2020, 2021, 2022 and 2023.
# however exclude the following NEAF Vendor purchases for virtual NEAFs of 2020 and 2021.
COVID_NEAF_VENDOR_SKUS_TO_EXCLUDE = ('neaf_vendor_booth_virtual_already_registered','neaf_vendor_booth_virtual')
# 1/30/2022. unfortunately I carelessly didn't create seperate skus for these products when they were for virtual NEAF.
# exclude them only in date range VIRTUAL_NEAF_ORDER_RANGE.
COVID_NEAF_VENDOR_SKUS_TO_EXCLUDE_CONDITIONALLY = ('neaf_vendor_sponsor_logo_and_link','neaf_vendor_sponsor_ad_and_link')

SHOPIFY_COMMON_FIELDS = 'order_id order_num created_at canceled_at note note_attributes customer total_discounts discount_codes discount_allocations name first_name last_name email '+\
                        'default_address province_code country_code phone_num sku quantity refund_note refund_created_at line_item'
# ShopifyCommonTup is a fairly raw representation of a single line_item in a single order_num. there will be duplicate order items across different line_items in same order.
ShopifyCommonTup = namedtuple('ShopifyCommonTup', SHOPIFY_COMMON_FIELDS)
RawOrdersTup = namedtuple('RawOrdersTup','page raw_orders_count orders')

NEAF_YEAR_ALL = 'all' # all years since 2015
NEAF_YEAR_2015 = '2015'
NEAF_YEAR_2016 = '2016'
NEAF_YEAR_2017 = '2017'
NEAF_YEAR_2018 = '2018'
NEAF_YEAR_2019 = '2019'
NEAF_YEAR_COVID = 'covid' # 2020 to 2023
NEAF_YEAR_2024 = '2024'
NEAF_YEAR_2025 = '2025'
NEAF_YEAR_2026 = '2026'
NEAF_YEAR_VALID = (NEAF_YEAR_ALL,NEAF_YEAR_2015,NEAF_YEAR_2016,NEAF_YEAR_2017,NEAF_YEAR_2018,NEAF_YEAR_2019,NEAF_YEAR_COVID,NEAF_YEAR_2024,NEAF_YEAR_2025,NEAF_YEAR_2026)

# TODO 1/15/2022. after NEAF 2023 change NEAF_YEAR_DEFAULT for neaf_year back to latest NEAF_YEAR_<year> to pick up current year. for now default of NEAF_YEAR_COVID means sum together
#  all NEAF Vendors orders from 2020, 2021, 2022 and 2023.
NEAF_YEAR_DEFAULT = NEAF_YEAR_2026 # NEAF_YEAR_COVID

MISSING = 'MISSING'
ERROR = 'ERROR'
REFUND = 'REFUND'
FAILED_REFUND = 'FAILED_REFUND'
DECLINED = 'DECLINED'
N_A = 'N/A'


