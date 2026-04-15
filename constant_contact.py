# -*- coding: utf-8 -*-
"""
Created on Thu Jan 01 12:02:46 2015

@author: joe1
"""

from collections import namedtuple
from socket import gethostname, gethostbyname
import json
# 7/8/2025 install with
#          pip install flask
#          use pip3 on mac
import os
import csv
import socket
import time
from datetime import date,datetime
import io
import requests
from flask import Flask, request, redirect
import urllib.parse
import webbrowser
from consts import MISSING,NEAF_YEAR_VALID,NEAF_DAYS,NEAF_DATES,NEAF_YEAR_DEFAULT,NEAF_YEAR_2025,DEFAULT_DAY,SATURDAY,SUNDAY,NEAF_YEAR_2026
from credentials import Credentials
from utils import RAC_DIR,writerow_UnicodeEncodeError,appendMsg,normalize_unicode_text
from date_filter_utils import parse_constant_contact_date_filter_args

from utils import convert_utc_to_local_datetime,remove_unicode

# TODO 2/27/2025. if for some crazy reason the function get_access_token_from_refresh_token() detects change of refresh token it will print message with new refresh_token and ask for change
#                 to this variable to new value. copilot leads me to believe a refresh token might last for 180 days so test this code prior to NEAF and update refresh_token here.
#                 Alternatively refresh_token might be so old that get_access_token_from_refresh_token fails with non-200 status code. On 12/11/2025 it failed with status_code 400.
#                 To generate new refresh_token do this:
#                 1) log into IONOS and set redirect of events1@rocklandastronomy.com to jjmoskowitz76@aol.com in order to get 6 digit code to log in to constant contact to get authorization code.
#                 2) run get_authorization_code() to get authorization code.
#                    The redirect url will popup Constant Constact login screen which will email 6 digit code to events1@rocklandastronomy.com.
#                    Redirect of that email will come back to jjmoskowitz76@aol.com.
#                 3) run exchange_authorization_code_for_access_token_and_refresh_token(...) to get access_token and refresh_token by passing in authorization code from step 1).
#                    access_token generated in this step can be ignored since prod code gets access token from refresh token in call to get_access_token_from_refresh_token().
refresh_token = Credentials().CC_REFRESH_TOKEN

CC_API_BASE = "https://api.cc.email/v3"
CC_DOOR_PRIZE_FIELDS = 'first_name last_name home_phone email_address modified_date'
CcDoorPrizeTup = namedtuple('CcDoorPrizeTup', CC_DOOR_PRIZE_FIELDS)

def find_free_port():
    # 2/28/2025. I abandoned this approach and have hard coded port as 8080 because I can set in advance in both this code and in
    #            Constant Contact https://app.constantcontact.com/pages/dma/portal/appList "My Applications" tab.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

# 2/28/2025. client_id and client_secret acquired from https://app.constantcontact.com/pages/dma/portal/appList in "My Applications" tab.
client_id = Credentials().CC_CLIENT_ID
client_secret = Credentials().CC_CLIENT_SECRET
port = 8080  # find_free_port() #
# 2/28/2025. the biggest trick copilot told me to get this working was to replace redirect_uri = f'http://localhost:{port}/callback' with value below and also
#            make same change in
redirect_uri = f'http://127.0.0.1:{port}/callback'
# 2/27/2025. this is LIST_ID for "NEAF_Door_Prize_Registration"
LIST_ID = Credentials().CC_NEAF_DOOR_PRIZE_REGISTRATION_LIST_ID
limit = 200

scope = "contact_data campaign_data offline_access"
state = "random_string"

def get_access_token_from_refresh_token():

    # 2/28/2025. new_access_token returned is gigantic. it's over 1000 chars long.

    token_url = "https://authz.constantcontact.com/oauth2/default/v1/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }

    try:
        response = requests.post(token_url, headers=headers, data=data)
    except Exception as ex:
        msg = f'\nFailure in get_access_token_from_refresh_token() calling requests.post(token_url, headers=headers, data=data).\nException:\n{ex}'
        print(f'{msg}\ntoken_url : {token_url}\nheaders : {headers}\ndata : {data}\n')
        msg += '\nSee more details in log.'
        raise Exception(msg)
    st = response.status_code
    if st != 200:
        msg = f'\nFailure in get_access_token_from_refresh_token(). requests.post(token_url, headers=headers, data=data) returned status_code:{st}. Must be 200 for success.'
        print(f'{msg}\ntoken_url : {token_url}\nheaders : {headers}\ndata : {data}\n')
        msg += '\nSee more details in log.'
        raise Exception(msg)

    token_data = response.json()
    new_access_token = token_data.get("access_token")
    new_refresh_token = token_data.get("refresh_token")

    if new_refresh_token != refresh_token:
        msg = '\n\nWARNING\n\n************************\nIn get_access_token_from_refresh_token() old refresh_token has changed to new value\n' + \
              'Update Credentials class variable for refresh_token in credentials.txt with this new refresh_token.'
        print(f'{msg}\nrefresh_token : {refresh_token}, new_refresh_token : {new_refresh_token}\n')
        msg += '\nSee more details in log.'
        raise Exception(msg)

    return new_access_token

def flatten_contacts(all_contacts):
    all_contacts_new = []
    for contact in all_contacts:
        contact_new = {}
        for k,v in contact.items():
            if isinstance(v,dict):
                for k1,v1 in v.items():
                    contact_new[k+':'+k1] = v1
            elif isinstance(v,list):
                for i,v1 in enumerate(v):
                    for k2,v2 in v1.items():
                        contact_new[k+':'+k2+':'+str(i)] = v2
            else:
                contact_new[k] = v
        all_contacts_new.append(contact_new)

    max_keys = []
    for contacts_new in all_contacts_new:
        keys = contacts_new.keys()
        if len(keys) > len(max_keys):
            max_keys = keys

    return max_keys,all_contacts_new

def get_constant_contact_door_prize_list(start_date):

    # 2/18/2026. TODO this function has been deprecated and is replaced by cc_export_contacts_as_rows.

    access_token = get_access_token_from_refresh_token()

    print('\nEntering get_constant_contact_door_prize_list(start_date={0}). get_access_token_from_refresh_token() returned access_token of size {1}.'.format(start_date,len(access_token)))

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # 2/28/2025. copilot says to include multiple items comma seperate them like this: "phone_numbers,addresses". I never tested that.
    params = {
        "include": "phone_numbers"
    }

    # new url for "NEAF_Door_Prize_Registration"
    base_url = "https://api.cc.email"  # Base URL for Constant Contact API
    next_link = f"{CC_API_BASE}/contacts?lists={LIST_ID}&limit={limit}&updated_after={start_date}T12:00:00Z"
    all_contacts = []

    i = 0
    while next_link:
        i += 1
        response = requests.get(next_link, headers=headers, params=params)
        if response.status_code != 200:
            msg = f'Failure in tutorial_api. response.status_code:{response.status_code}. Must be 200 for success.'
            print(f'\n{msg}\nresponse = requests.get(next_link, headers=headers, params=params)\nnext_link:\n{next_link}\nheaders:\n{headers}\nparams:\n{params}\n')
            raise Exception(f'{msg} See log for more details.')
        r_json = response.json()
        contact_list = r_json['contacts']
        all_contacts.extend(contact_list)
        print('Page {0}: Contact list of size {1} returned from this url:\n{2}'.format(i,len(contact_list),next_link))
        next_link = r_json.get('_links', {}).get('next', {}).get('href')
        if next_link:
            next_link = f"{base_url}{next_link}"

    # 2/28/2025. these last blocks sort results in reverse order by updated_at. its a good convenience when eyeballing the data but its not needed for functionality.

    updated_at_dict = {}
    for contact in all_contacts:
        updated_at = contact['updated_at']
        u_list = updated_at_dict.get(updated_at,[])
        if not u_list:
            updated_at_dict[updated_at] = u_list
        u_list.append(contact)

    sorted_keys =  sorted(updated_at_dict.keys(), reverse=True)
    all_contacts_new = []
    for key in sorted_keys:
        all_contacts_new.extend(updated_at_dict[key])

    print('Exiting get_constant_contact_door_prize_list with len(all_contacts_new):{0}\n'.format(len(all_contacts)))

    max_keys,all_contacts_new = flatten_contacts(all_contacts_new)

    return max_keys,all_contacts_new

def print_ccDoorPrizeTup_list(ccdpt_list):
    cnt=0
    cnt_max = 0
    name_max = 0
    email_max = 0
    phone_max = 0
    for ccdpt in ccdpt_list:
        cnt += 1
        cnt_max = len(str(cnt)) if len(str(cnt))>cnt_max else cnt_max
        name = ccdpt.first_name+' '+ccdpt.last_name
        name_max = len(name) if len(name)>name_max else name_max
        email_max = len(ccdpt.email_address) if len(ccdpt.email_address)>email_max else email_max
        phone_max = len(ccdpt.home_phone) if len(ccdpt.home_phone)>phone_max else phone_max
    fmt = '{{:{0}d}}: {{:{1}s}}    {{:{2}s}}  {{:{3}s}}  {{:{4}s}}'.format(cnt_max,name_max,email_max,phone_max,19)
    cnt=0
    for ccdpt in ccdpt_list:
        cnt += 1
        print(fmt.format(cnt,ccdpt.first_name+' '+ccdpt.last_name,ccdpt.email_address,ccdpt.home_phone,ccdpt.modified_date))
    return   

def convert_cc_res_to_ccDoorPrizeTup_list(rows):
    # only return items less than or equal to neaf_end_date
    ccdpt_list = []

    # remove unicode
    cc_res = remove_unicode(rows)

    for cc_dict in cc_res:
        first_name = cc_dict.get(CC_FIRST_NAME) or MISSING
        last_name = cc_dict.get(CC_LAST_NAME) or ''
        phone_home = cc_dict.get(CC_PHONE_HOME) or ''
        phone_mobile = cc_dict.get(CC_PHONE_MOBILE) or ''
        phone = phone_mobile or phone_home
        email_address = cc_dict.get(CC_EMAIL_ADDRESS)
        modified_date = cc_dict.get(CC_UPDATED_AT) # [:19]
        modified_date = modified_date[:19]
        ccdpt = CcDoorPrizeTup(first_name, last_name, phone, email_address, modified_date)
        ccdpt_list.append(ccdpt)
    return ccdpt_list        

def build_raw_cc_to_csv(cc_res_keys,cc_res):
    fname = os.path.join(RAC_DIR(),'door_prize','raw_cc.csv')

    os.makedirs(os.path.dirname(fname),exist_ok=True)
    try:
        with open(fname,'w',encoding="utf-8-sig") as csv_file:
            wr = csv.writer(csv_file,  quoting=csv.QUOTE_ALL, lineterminator='\n') # delimiter=' ',quotechar='|', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            wr.writerow(cc_res_keys)
            for res in cc_res:
                ntrow = []
                for col in cc_res_keys:
                    ntrow.append(res.get(col))

                writerow_UnicodeEncodeError(wr,ntrow)
    except Exception as ex:
        error = appendMsg(f'\nConstant Contact raw data dump to csv failed with exception:\n{ex}')
        return '',error
    return appendMsg(f'Constant Contact raw data dump of {len(cc_res)} rows, {len(cc_res_keys)} columns at {fname}.'),''

# 1/26/2026. these columns on left edge of raw Constant Contact csv
CC_EMAIL_ADDRESS = 'Email address'
CC_FIRST_NAME = 'First name'
CC_LAST_NAME = 'Last name'
CC_PHONE_HOME = 'Phone - home'
CC_PHONE_MOBILE = 'Phone - mobile'
CC_EMAIL_UPDATE_SOURCE = 'Email update source' # if 'contact' last update came from the signup page
CC_SOURCE_NAME = 'Source Name' # if 'Website sign-up form' last update came from the signup page
CC_CREATED_AT = 'Created At' # time stamp when first created. it doesn't change even if edits.
CC_UPDATED_AT = 'Updated At' # time stamp of last edit on this contact
CC_NAME_OF_ASTRONOMY_CLUB = 'Name of Astronomy Club'
CC_COLS = [CC_EMAIL_ADDRESS,CC_FIRST_NAME,CC_LAST_NAME,CC_PHONE_HOME,CC_PHONE_MOBILE,CC_EMAIL_UPDATE_SOURCE,CC_SOURCE_NAME,CC_CREATED_AT,CC_UPDATED_AT,CC_NAME_OF_ASTRONOMY_CLUB]

def cc_export_contacts_as_rows(poll_interval_sec=2.0, timeout_sec=300.0):
    """
    Simulate Constant Contact UI export:
      1) POST /v3/activities/contact_exports
      2) Poll the activity until state == "completed"
      3) GET the results as text/csv
      4) Parse CSV in-memory and return a list of dict rows

    Returns:
      rows: list of dict, where dict keys are the CSV header names (as CC emits them).

    Notes:
      - The CSV header names are typically humanized (e.g. "Email Address", "Source Name").
      - Phone number columns in the CSV may be "Phone Number" / "Phone Number Type" (CC-controlled).
      - This is the reliable way to get Source Name ("Website sign-up form") if your account/export supports it.
    """

    access_token = get_access_token_from_refresh_token()
    headers_json = {"Authorization": f"Bearer {access_token}","Accept": "application/json","Content-Type": "application/json"}

    # 1) Create export activity
    create_url = f"{CC_API_BASE}/activities/contact_exports"
    body = {"list_ids": [LIST_ID]}

    rows = []
    error = ''
    msg = f'Submit request for Constant Contact csv data of requests.post(create_url, headers=headers_json, json=body, timeout=30)\nwith create_url:{create_url}, body:{body}'
    msg = appendMsg(msg)
    r = requests.post(create_url, headers=headers_json, json=body, timeout=30)
    r.raise_for_status()
    activity = r.json()

    # These are relative hrefs like "/v3/activities/<id>" and "/v3/contact_exports/<file_export_id>"
    activity_href = activity["_links"]["self"]["href"]
    results_href = activity["_links"]["results"]["href"]

    activity_url = "https://api.cc.email" + activity_href
    results_url = "https://api.cc.email" + results_href

    # 2) Poll activity until completed
    deadline = time.time() + timeout_sec
    cnt = 0
    elapsed_time = 0
    while True:
        cnt += 1
        msg = appendMsg(msg,f'Polling for completion of Constant Contact csv data at {activity_url}. elapsed time:{elapsed_time} secs')
        rr = requests.get(activity_url, headers=headers_json, timeout=30)
        rr.raise_for_status()
        activity = rr.json()
        state = activity.get("state")

        if state == "completed":
            msg =  appendMsg(msg,f'Polling complete after {elapsed_time} secs.')
            break

        if state == "failed":
            error = f"Constant Contact export failed running {activity_url}: {activity.get('activity_errors')}"
            msg = appendMsg(msg,error)
            break

        if time.time() > deadline:
            error = f"Constant Contact export timed out running {activity_url} after {timeout_sec} seconds; last_state={state}"
            msg = appendMsg(msg,error)
            break

        elapsed_time += poll_interval_sec
        time.sleep(poll_interval_sec)

    # 3) Download CSV
    headers_csv = {"Authorization": f"Bearer {access_token}","Accept": "text/csv"}
    csv_resp = requests.get(results_url, headers=headers_csv, timeout=60)
    csv_resp.raise_for_status()
    msg = appendMsg(msg,f'Downloaded csv data from {results_url}.')

    # 4) Parse CSV into list of dict rows
    text = csv_resp.content.decode("utf-8", errors="replace")
    f = io.StringIO(text, newline="")
    reader = csv.DictReader(f)

    bad_row_cnt = 0
    for nrows,row in enumerate(reader):

        # 1/26/2026. this block re-orders items in row and places items in CC_COLS first
        nr = {}
        for cc in CC_COLS:
            if cc in row:
                nr[cc] = normalize_unicode_text(row[cc])
        for k,v in row.items():
            if k not in nr:
                nr[k] = normalize_unicode_text(row[k])

        if not nr[CC_EMAIL_ADDRESS] or not nr[CC_FIRST_NAME] or not nr[CC_LAST_NAME]:
            bad_row_cnt += 1
        else:
            rows.append(nr)

    fieldnames = reader.fieldnames
    msg = appendMsg(msg,f'Downloaded {nrows + 1} rows, {len(fieldnames)} cols. Deleted {bad_row_cnt} rows missing email or name, {len(rows)} returned.')

    return fieldnames,rows,msg,error
def get_cc_door_prize_list(neaf_year,neaf_day,raw_cc_to_csv=False,verbose=False):

    # 2/24/2026. call the Constant Contact csv download api with cc_export_contacts_as_rows.
    #            Then transform those results to list of CcDoorPrizeTup(ccdpt_list) with convert_cc_res_to_ccDoorPrizeTup_list.
    #            If date of cc row is inconsistent with NEAF day specified by neaf_year and neaf_day do not include in ccdpt_list.

    neaf_year = str(neaf_year)
    neaf_year_int,neaf_year_default_int,today,neaf_start,neaf_end,neaf_start_dow,neaf_end_dow,msg,msg_ex = parse_constant_contact_date_filter_args(neaf_year, neaf_day)
    if msg_ex:
        raise Exception(msg_ex)

    fieldnames,rows,msg2,error = cc_export_contacts_as_rows()
    msg = appendMsg(msg,msg2)

    if raw_cc_to_csv:
        msg2,error = build_raw_cc_to_csv(fieldnames,rows)
        msg = appendMsg(msg,msg2,print_new_msg=False)

    # 2/18/2026. trim raw cc result down to requested NEAF year and NEAF days
    day_of_week_counts = {}
    rows_dict = {}

    # 2/23/2026. XXX this block sets all additional filtering logic based on neaf_year and neaf_day.

    updated_at_valid_days = []
    if neaf_year_int == neaf_year_default_int and today in (neaf_start,neaf_end):
        # 2/19/2026. XXX this is block we take during actual PROD runs on days of NEAF. We also can take this block when testing with dummy values of neaf days default.
        updated_at_valid_days.extend([today])
    else:
        if neaf_day == DEFAULT_DAY:
            updated_at_valid_days.extend([neaf_start,neaf_end])
        elif neaf_day == SATURDAY:
            updated_at_valid_days.append(neaf_start)
        elif neaf_day == SUNDAY:
            updated_at_valid_days.append(neaf_end)

    for row in rows:
        updated_at = row[CC_UPDATED_AT]
        updated_at_date = updated_at[:10]

        if updated_at_date in updated_at_valid_days:
            dow = date.fromisoformat(updated_at_date).strftime('%A')
            count = day_of_week_counts.get(dow,0)
            day_of_week_counts[dow] = count + 1
            rows_dict[updated_at] = row

    rows_new = [rows_dict[k] for k in sorted(rows_dict)]
    # 2/25/2026. this was ChatGPTs clever idea. I hope I can mentally retain it but I doubt I can.
    has_weekday = bool(set(day_of_week_counts) - {SATURDAY, SUNDAY})
    if has_weekday:
        msg2 = 'WARNING: RUNNING IN TEST MODE. NEAF start and end days of week not Saturday and Sunday.\n' +\
               f"neaf_start_dow:{neaf_start_dow} has {day_of_week_counts.get(neaf_start_dow,0)} rows and {neaf_end_dow} has {day_of_week_counts.get(neaf_end_dow,0)} rows."
        msg = appendMsg(msg,msg2)
    uavd = ' - '.join(updated_at_valid_days)
    counts_str = ', '.join([f"{k}:{v}" for k,v in day_of_week_counts.items()])
    msg = appendMsg(msg,f"After applying filter using neaf_year:{neaf_year}, neaf_day:{neaf_day}, ({uavd}) row cnt reduced from {len(rows)} to {len(rows_new)} with {counts_str}.")

    ccdpt_list = convert_cc_res_to_ccDoorPrizeTup_list(rows_new)
    return ccdpt_list,msg

def cc_test(neaf_year = NEAF_YEAR_2026, neaf_day = DEFAULT_DAY, verbose = False):

    # 2/28/2025. this function tests the public interface to Constant Contact which is get_cc_door_prize_list.

    ccdpt_list,msg = get_cc_door_prize_list(neaf_year,neaf_day,raw_cc_to_csv=True,verbose=verbose)
    print_ccDoorPrizeTup_list(ccdpt_list)
    return

def get_authorization_code():

    # 2/22/2025. this code came from copilot with prompt:
    #            I'm trying to get the authorization code from my desktop python program. what should I use for my YOUR_REDIRECT_URI

    app = Flask(__name__)

    @app.route('/')
    def index():
        print('Inside index() making call to redirect(authorization_url) with\nauthorization_url:{0}\n'.format(authorization_url))
        return redirect(authorization_url)

    @app.route('/callback')
    def callback():

        print('entering callback()')
        state = request.args.get('state')
        auth_code = request.args.get('code')
        print("request.args.get('code'):\n{0}\nrequest.args.get('state'):\n{1}".format(auth_code, state))

        if auth_code:
            print(f"Authorization code: {auth_code}")
            return f'Authorization code: {auth_code}', 200
        else:
            print("request.args.get('code') returned None. Failed to find Authorization code")
            return 'No authorization code found', 400

    #authorization_url = f'https://oauth2.constantcontact.com/oauth2/oauth/siteowner/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}'
    authorization_url = (
        f"https://authz.constantcontact.com/oauth2/default/v1/authorize"
        f"?client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
        f"&scope={scope}&response_type=code&state={state}"
    )
    open_url = f'http://localhost:{port}'
    print('\ncalling webbrowser.open(open_url) with\nopen_url:\n{0}\nauthorization_url:{1}\n'.format(open_url,authorization_url))
    print('When Constant Contact authorization login screen opens enter\nAccount:\ninfo@nasociety.org\nPassword:\nrac2023$constant\n')

    if __name__ == '__main__':
        webbrowser.open(open_url)
        print('calling app.run(port=port) with\nport:\n{0}'.format(port))
        app.run(port=port)
        print('DONE app.run(port=port) with\nport:\n{0}'.format(port))

    return

def exchange_authorization_code_for_access_token_and_refresh_token(auth_code=None):


    token_url = "https://authz.constantcontact.com/oauth2/default/v1/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'code': auth_code,
        'redirect_uri': redirect_uri
    }
    print(r'\nInside exchange_authorization_code_for_access_token() making requests.post(token_url, data=data) call with\ntoken_url:\{0}\ndata:\n{1}\n'.format(token_url, data))

    response = requests.post(token_url, headers=headers, data=data)

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        print(f'response.status_code: {response.status_code}\nAccess Token:\n{access_token}\nRefresh Token:\n{refresh_token}')
    else:
        print(f'Error: {response.status_code}')
        print(response.json())
    return


if __name__ == "__main__":
    pass
    # get_access_token_from_refresh_token()

    # run test_cc in console or uncomment next line and run here
    # in order to import this file must comment out next line
    cc_test()

    # TODO 2/27/2025. get the auth code passed to exchange_authorization_code_for_access_token_and_refresh_token(...) by first running get_authorization_code()
    #get_authorization_code()
    #exchange_authorization_code_for_access_token_and_refresh_token(auth_code='qjFJLw1jSUwb2dtutyC6d2xcwKbeU-pBAVhYeGVgaI8')


    