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
import socket
from flask import Flask, request, redirect
import urllib.parse
import requests
import webbrowser
from consts import MISSING
from credentials import Credentials

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
# 2/27/2025. this is list_id for "NEAF_Door_Prize_Registration"
list_id = Credentials().CC_NEAF_DOOR_PRIZE_REGISTRATION_LIST_ID
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

    response = requests.post(token_url, headers=headers, data=data)
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

def get_constant_contact_door_prize_list(start_date):

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
    next_link = f"{base_url}/v3/contacts?lists={list_id}&limit={limit}&updated_after={start_date}T12:00:00Z"
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

    return all_contacts_new

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
    fmt = '{{:{0}d}}: {{:{1}s}} -- {{:{2}s}}  {{:{3}s}}  {{:{4}s}}'.format(cnt_max,name_max,email_max,phone_max,19)
    cnt=0
    for ccdpt in ccdpt_list:
        cnt += 1
        print(fmt.format(cnt,ccdpt.first_name+' '+ccdpt.last_name,ccdpt.email_address,ccdpt.home_phone,ccdpt.modified_date))
    return   

def convert_cc_res_to_ccDoorPrizeTup_list(neaf_end_date,cc_res):
    # only return items less than or equal to neaf_end_date
    ccdpt_list = []

    # remove unicode
    cc_res = remove_unicode(cc_res)

    for cc_dict in cc_res:
        first_name = cc_dict.get('first_name') or MISSING
        last_name = cc_dict.get('last_name') or ''
        home_phone = ''
        for phone_number in cc_dict.get('phone_numbers',[]):
            if phone_number.get('create_source') == 'Contact':
                home_phone = phone_number.get('phone_number')
                break
        email_address = cc_dict.get('email_address',{}).get('address')
        modified_date = cc_dict.get('updated_at') # [:19]
        # date is in UTC format. remove_unicode to local datetime
        modified_date = convert_utc_to_local_datetime(modified_date)
        modified_date = modified_date[:19]
        ccdpt = CcDoorPrizeTup(first_name, last_name, home_phone, email_address, modified_date)
        if modified_date[:modified_date.index('T')] <= neaf_end_date:
            ccdpt_list.append(ccdpt)
    return ccdpt_list        
    
def get_cc_door_prize_list(neaf_start_date,neaf_end_date,verbose=False):
    # TODO 3/2/2025. remove verbose arg. no longer used.
    cc_res = get_constant_contact_door_prize_list(neaf_start_date)
    ccdpt_list = convert_cc_res_to_ccDoorPrizeTup_list(neaf_end_date,cc_res)
    return ccdpt_list        
   
def test_cc(neaf_start_date = None,verbose = False):

    # 2/28/2025. this function tests the public interface to Constant Contact which is get_cc_door_prize_list.

    #neaf_start_date = '2014-12-01' good for testing door prize list
    #neaf_start_date = '2014-01-01' good for testing dummy SSP 2013 list
    neaf_end_date = '2025-04-06'
    ccdpt_list = get_cc_door_prize_list(neaf_start_date,neaf_end_date,verbose)
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

def tutorial_api():

    # 2/28/2025. this function tests this get_constant_contact_door_prize_list which is a fairly raw representation of what Constant Contact returns
    #            from its web api. The only adjustment is a sort in reverse order by updated_at. That's a good convenience when eyeballing the results.

    start_date = '2024-12-01'
    all_contacts = get_constant_contact_door_prize_list(start_date)

    return

if __name__ == "__main__":
    tutorial_api()
    #get_access_token_from_refresh_token()

    # run test_cc in console or uncomment next line and run here
    # in order to import this file must comment out next line
    #test_cc('2020-01-25')

    # TODO 2/27/2025. get the auth code passed to exchange_authorization_code_for_access_token_and_refresh_token(...) by first running get_authorization_code()
    #get_authorization_code()
    #exchange_authorization_code_for_access_token_and_refresh_token(auth_code='qjFJLw1jSUwb2dtutyC6d2xcwKbeU-pBAVhYeGVgaI8')

    