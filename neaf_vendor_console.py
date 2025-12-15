from utils import build_startup_parameters
from consts import NEAF_MANAGMENT,NEAF_FULL,NEAF_RAW,NEAF_COMPANY_BADGE,NEAF_YEAR_DEFAULT
from neaf_vendor_utils import get_neaf_year
from neaf_vendor import NEAFVendor,save_invoice,set_as_pdf

# 4/13/2020. previously this file was named neaf_vendor.py but I wanted to free up the file to hold NEAFVendor class that was previously in access_shopify.py .

def get_option(raw_input_str):
    valid_inputs = ['0','1','2','3','4','5','6','7','8','9','10','11','12','13','15','16','17','18','19','20','21','22']
    inputs_with_args = ['8','9','14','15','16','17','20','22']
    option = None
    toks = raw_input_str.split()
    if not toks:
        print('Nothing entered. Try again')
        return None,None
    optionstr = toks[0]
    option_args = ' '.join(toks[1:]) if len(toks)>1 else None
    if optionstr in inputs_with_args and not option_args:
        print('This option needs an argument. Try again.')
        return None,None
    if optionstr not in inputs_with_args and option_args:
        print('This option cannot have needs an argument. Try again.')
        return None,None
    if optionstr not in valid_inputs:
        print('Choice not valid. Try again.')
        return None,None
    option = int(optionstr)
    return option,option_args

def main(argv):

    import faulthandler
    faulthandler.enable()

    target_companies = []
    spt = build_startup_parameters(argv)
    neaf_year = NEAF_YEAR_DEFAULT
    neafVendor = None
    target_company = ''
    target_company_invoice = ''
    as_pdf = False
    verbose = False
    while True:
        print('\n\n22 save invoices as pdf files:y/n')
        print('21:dump company_badge list to csv')
        print('14:<cur|all|YYYY>:NEAF Year                          15 <date>:save all requested invoices greater than date')
        print('12:save last selected invoice                        13:create Vendor Sign-In sheet')
        print('10:show and save all invoices                        11:show dicts(probably does not work)')
        print('8 <key>:show invoice for company with this key       9 <item>:If 8 returned more than 1 invoice choose item')
        print('5:verbose on                                         6:verbose off                         7:hints')
        print('2:SHOPIFY LOAD (must do this first)                  3:dump full NeafVendorTup to csv    4:dump raw NeafVendorTup to csv')
        print('0:stop                                               1:dump NEAF Management s/s to csv')
        msg = '-----> '
        raw_input_str = input(msg)
        option,option_args = get_option(raw_input_str)
        if option is None:
            continue
        if option == 0:
            break
        if option == 2:
            spt = build_startup_parameters(argv)
            neafVendor = NEAFVendor(neaf_year,verbose=verbose)
            neafVendor.shopifyLoad()
        if option == 5:
            verbose = True
            continue
        if option == 6:
            verbose = False
            continue

        if not neafVendor:
            msg = 'Do this option first -- 2:SHOPIFY LOAD (must do this first)'
            print(msg)
            continue

        if option == 7:
            msg = neafVendor.show_hints(spt)
            print(msg)
        if option == 8:
            target_companies,target_companies_text = neafVendor.get_target_companies(option_args)
            print(target_companies_text)
            if len(target_companies) == 1:
                target_company,target_company_invoice = neafVendor.get_target_company_invoice(target_companies,'1')
                print(target_company_invoice)
        if option == 9:
            target_company,target_company_invoice = neafVendor.get_target_company_invoice(target_companies,option_args)
            print(target_company_invoice)
        if option == 1:
            print(neafVendor.output_nvt_csv(NEAF_MANAGMENT))
        if option == 3:
            print(neafVendor.output_nvt_csv(NEAF_FULL))
        if option == 4:
            print(neafVendor.output_nvt_csv(NEAF_RAW))
        if option == 21:
            print(neafVendor.output_nvt_csv(NEAF_COMPANY_BADGE))

        if option == 11:
            print(neafVendor.show_neaf_vendor_dicts())
            continue
        if option == 10:
            all_invoices_to_print,save_message_dummy = neafVendor.show_and_save_all_invoices(as_pdf)
            print(all_invoices_to_print)
            continue
        if option == 12:
            msg,subdir_path,fname = save_invoice(target_company,target_company_invoice,as_pdf)
            print(msg)
        if option == 22:
            as_pdf,msg = set_as_pdf(as_pdf,option_args)
            print(msg)
        if option == 13:
            print(neafVendor.save_vendor_sign_in_sheet())
        if option == 14:
            neaf_year = get_neaf_year(option_args)
        if option == 15:
            msg = neafVendor.save_all_requested_invoices_beyond_date(option_args,as_pdf)
            print(msg)

    return

# comment out main when launching from rac_launcher_console.py

# hoboken
#main(['c:\users\\family\Dropbox\RAC\py_scripts\\rac_launcher.py','jjmoskowitz76@gmail.com','pw:xxxxxx','cc:jjmoskowitz76@aol.com'])
# rockland
main('xxx') # ['c:\users\\joe1\Dropbox\RAC\py_scripts\\rac_launcher.py']

