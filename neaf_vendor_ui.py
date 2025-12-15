import os
from tkinter import Tk,Frame,Label
from consts import NEAF_YEAR_VALID,NEAF_YEAR_DEFAULT
from utils import showError,build_startup_parameters,SMALL,MEDIUM,LARGE
from utils_ui import STButton,STWidgetDropDown,STLargeResult,STWidget,STFrame
from neaf_vendor_utils import VALID_EDIT_ACTIONS,BADGE_ACTION
from neaf_vendor import NEAFVendor,save_invoice

class NEAFManagementUI(Frame):

    def __init__(self,master,argv):
        self.master = master
        self.width = self.master.winfo_screenwidth()
        self.height = self.master.winfo_screenheight()
        print('screen width:{0}, screen height:{1}'.format(self.width,self.height))
        self.next_row = 1

        self.target_companies = []
        self.argv = argv
        self.spt = build_startup_parameters(self.argv)
        # 12/30/2022. must call self.ShopifyLoad() to set self.neafVendor to NEAFVendor object.
        self.neafVendor =  None
        self.target_company = ''
        self.target_company_invoice = ''
        self.neaf_year_entry = NEAF_YEAR_DEFAULT
        self.edit_action = BADGE_ACTION

        master.title('NEAF Vendor Managment Tools')
        # TODO 3/21/2023. this line added for debugging. remove when small windows layout is finished.
        #self.width = 1366

        if self.width < 1390:
            print('self.width:{0}. Most likely running on a club laptop which has a width of 1366.'.format(self.width))
            self.screen_size = SMALL
            master.geometry('1330x680')
        elif self.width > 1390 and self.width < 1880:
            print("self.width:{0}. Most likely running on Sarah's MAC which has a width of 1440.".format(self.width))
            self.screen_size = MEDIUM
            master.geometry('1425x700')
        else:
            print("self.width:{0}. Most likely running on a standard 1920 X 1080 monitor.".format(self.width))
            self.screen_size = LARGE
            master.geometry('1800x700')

        Frame.__init__(self,master)
        self.grid()
        self._create_widgets()
        self.neaf_year = None

        return

    def _create_widgets_small(self):

        vert_frame1 = STFrame(self,80,1)
        STButton(vert_frame1,text='Save NEAF Management s/s to csv',command=self.SaveNEAFManagementSS,same_row=True)
        STButton(vert_frame1,text='Save NEAF Company/Badge s/s to csv',command=self.SaveNEAFCompanyBadgeSS,same_row=True)
        STButton(vert_frame1, text='SHOPIFY LOAD (must do this first)', command=self.ShopifyLoad, same_row=True)
        STButton(vert_frame1, text='Re-build all companies from prior SHOPIFY LOAD', command=self.BuildFromPriorShopifyLoad, same_row=True)
        STButton(vert_frame1,text='Hints',command=self.ShowHints,same_row=True)
        STButton(vert_frame1,text='Show and Save all invoices',command=self.ShowAndSaveAllInvoices,same_row=True)
        STButton(vert_frame1,text='Save last invoice',command=self.SaveLastInvoice,same_row=True)
        STButton(vert_frame1,text='Save Vendor Sign-In Sheet',command=self.VendorSignInSheet,same_row=True)

        vert_frame2 = STFrame(self, 80, 1)
        STWidgetDropDown(vert_frame2,'NEAF year(covid is 2020-2023): %5s',NEAF_YEAR_VALID,default_value=NEAF_YEAR_DEFAULT,command=self.NeafYearEntry,same_row=True)
        STButton(vert_frame2,text='Clear Display',command=self.ClearDisplay,same_row=True)
        self.company_key = STWidget(vert_frame2,'Company key:',width=50,same_row=True)
        STButton(vert_frame2,text='Show invoice for company with requested key entered to left',command=self.ShowInvoiceForKey,same_row=True)
        self.item_number_of_company = STWidget(vert_frame2,'Company item number',width=4,same_row=True)
        vert_frame3 = STFrame(self,80,1)
        STButton(vert_frame3,text="Show invoice for 'Company item number' to upper right",command=self.ShowInvoiceForItemNumber,same_row=True)
        self.as_pdf = STWidget(vert_frame3,'Save Invoice as PDF',check_box=True,width=1,same_row=True)
        self.save_invoice_cutoff_date = STWidget(vert_frame3,'Save Invoice cutoff date:',width=10,same_row=True)
        STButton(vert_frame3,text='Save all invoices with last order after cutoff date',command=self.SaveInvoicesAfterCutoffDate,same_row=True)
        self.verbose = STWidget(vert_frame3, 'verbose', check_box=True, width=1, same_row=True)
        vert_frame4 = STFrame(self,80,1)

        msg = 'Choose an edit action:'
        STWidgetDropDown(vert_frame4, '{0}  %2s'.format(msg), VALID_EDIT_ACTIONS, default_value=BADGE_ACTION, command=self.EditAction, same_row=True)
        STButton(vert_frame4, text='Apply Edit', command=self.ApplyEdit, same_row=True)
        STButton(vert_frame4, text='See all badge and edit items', command=self.SeeAllEditItems, same_row=True)

        vert_frame5 = STFrame(self, 80, 1)
        self.edit_item = STWidget(vert_frame5, 'Edit Item:', width=210, same_row=True)

        self.large_res = STLargeResult(self,38,185)

        return

    def _create_widgets_medium(self):
        vert_frame1 = STFrame(self,100,1)
        STButton(vert_frame1,text='Save NEAF Management s/s to csv',command=self.SaveNEAFManagementSS,same_row=True)
        STButton(vert_frame1,text='Save NEAF Company/Badge s/s to csv',command=self.SaveNEAFCompanyBadgeSS,same_row=True)
        STButton(vert_frame1, text='SHOPIFY LOAD (must do this first)', command=self.ShopifyLoad, same_row=True)
        STButton(vert_frame1, text='Re-build all companies from prior SHOPIFY LOAD', command=self.BuildFromPriorShopifyLoad, same_row=True)
        STButton(vert_frame1,text='Hints',command=self.ShowHints,same_row=True)
        STButton(vert_frame1,text='Show and Save all invoices',command=self.ShowAndSaveAllInvoices,same_row=True)

        vert_frame2 = STFrame(self, 100, 1)
        STButton(vert_frame2,text='Save last invoice',command=self.SaveLastInvoice,same_row=True)
        STButton(vert_frame2,text='Save Vendor Sign-In Sheet',command=self.VendorSignInSheet,same_row=True)
        STWidgetDropDown(vert_frame2,'NEAF year(covid is 2020-2023): %5s',NEAF_YEAR_VALID,default_value=NEAF_YEAR_DEFAULT,command=self.NeafYearEntry,same_row=True)
        STButton(vert_frame2,text='Clear Display',command=self.ClearDisplay,same_row=True)
        self.company_key = STWidget(vert_frame2,'Company key:',width=50,same_row=True)

        vert_frame3 = STFrame(self,100,1)
        STButton(vert_frame3,text='Show invoice for company with requested key entered to left',command=self.ShowInvoiceForKey,same_row=True)
        self.item_number_of_company = STWidget(vert_frame3,'Company item number',width=4,same_row=True)
        STButton(vert_frame3,text='Show invoice for company with item number entered to left',command=self.ShowInvoiceForItemNumber,same_row=True)
        self.as_pdf = STWidget(vert_frame3,'Save Invoice as PDF',check_box=True,width=1,same_row=True)

        vert_frame4 = STFrame(self, 100, 1)
        self.save_invoice_cutoff_date = STWidget(vert_frame4,'Save Invoice cutoff date:',width=10,same_row=True)
        STButton(vert_frame4,text='Save all invoices with last order after cutoff date',command=self.SaveInvoicesAfterCutoffDate,same_row=True)
        self.verbose = STWidget(vert_frame4, 'verbose', check_box=True, width=1, same_row=True)

        vert_frame5 = STFrame(self, 100, 1)
        msg = 'Choose an edit action:'
        STWidgetDropDown(vert_frame5, '{0}  %2s'.format(msg), VALID_EDIT_ACTIONS, default_value=BADGE_ACTION, command=self.EditAction, same_row=True)
        STButton(vert_frame5, text='Apply Edit', command=self.ApplyEdit, same_row=True)
        STButton(vert_frame5, text='See all badge and edit items', command=self.SeeAllEditItems, same_row=True)

        vert_frame6 = STFrame(self, 100, 1)
        self.edit_item = STWidget(vert_frame6, 'Edit Item:', width=140, same_row=True)

        self.large_res = STLargeResult(self,60,250)

        return

    def _create_widgets_large(self):
        vert_frame1 = STFrame(self,100,1)
        STButton(vert_frame1,text='Save NEAF Management s/s to csv',command=self.SaveNEAFManagementSS,same_row=True)
        STButton(vert_frame1,text='Save NEAF Company/Badge s/s to csv',command=self.SaveNEAFCompanyBadgeSS,same_row=True)
        STButton(vert_frame1, text='SHOPIFY LOAD (must do this first)', command=self.ShopifyLoad, same_row=True)
        STButton(vert_frame1, text='Re-build all companies from prior SHOPIFY LOAD', command=self.BuildFromPriorShopifyLoad, same_row=True)
        STButton(vert_frame1,text='Hints',command=self.ShowHints,same_row=True)
        STButton(vert_frame1,text='Show and Save all invoices',command=self.ShowAndSaveAllInvoices,same_row=True)
        STButton(vert_frame1,text='Save last invoice',command=self.SaveLastInvoice,same_row=True)
        STButton(vert_frame1,text='Save Vendor Sign-In Sheet',command=self.VendorSignInSheet,same_row=True)
        STWidgetDropDown(vert_frame1,'NEAF year(covid is 2020-2023): %5s',NEAF_YEAR_VALID,default_value=NEAF_YEAR_DEFAULT,command=self.NeafYearEntry,same_row=True)
        STButton(vert_frame1,text='Clear Display',command=self.ClearDisplay,same_row=True)
        vert_frame2 = STFrame(self,100,1)
        self.company_key = STWidget(vert_frame2,'Company key:',width=50,same_row=True)
        STButton(vert_frame2,text='Show invoice for company with requested key entered to left',command=self.ShowInvoiceForKey,same_row=True)
        self.item_number_of_company = STWidget(vert_frame2,'Company item number',width=4,same_row=True)
        STButton(vert_frame2,text='Show invoice for company with item number entered to left',command=self.ShowInvoiceForItemNumber,same_row=True)
        vert_frame3 = STFrame(self,100,1)
        self.as_pdf = STWidget(vert_frame3,'Save Invoice as PDF',check_box=True,width=1,same_row=True)
        self.save_invoice_cutoff_date = STWidget(vert_frame3,'Save Invoice cutoff date:',width=10,same_row=True)
        STButton(vert_frame3,text='Save all invoices with last order after cutoff date',command=self.SaveInvoicesAfterCutoffDate,same_row=True)
        self.verbose = STWidget(vert_frame3, 'verbose', check_box=True, width=1, same_row=True)
        vert_frame4 = STFrame(self,100,1)

        msg = 'Choose an edit action:'
        STWidgetDropDown(vert_frame4, '{0}  %2s'.format(msg), VALID_EDIT_ACTIONS, default_value=BADGE_ACTION, command=self.EditAction, same_row=True)
        STButton(vert_frame4, text='Apply Edit', command=self.ApplyEdit, same_row=True)
        STButton(vert_frame4, text='See all badge and edit items', command=self.SeeAllEditItems, same_row=True)

        vert_frame5 = STFrame(self, 100, 1)
        self.edit_item = STWidget(vert_frame5, 'Edit Item:', width=250, same_row=True)

        self.large_res = STLargeResult(self,39,250)

        return

    def _create_widgets(self):
        if self.screen_size == SMALL:
            self._create_widgets_small()
        elif self.screen_size == MEDIUM:
            self._create_widgets_medium()
        else:
            self._create_widgets_large()
        return

    def neafVendorIsValid(self,label):
        if not self.neafVendor:
            self.large_res.set("Cannot run {0} because self.neafVendor is None. Expecting it to be a NEAFVendor object. Load with 'SHOPIFY LOAD (must do this first)' button.\n".format(label))
            return False
        return True

    def SaveNEAFManagementSS(self):
        if not self.neafVendorIsValid('SaveNEAFManagementSS'):
            return
        self.large_res.set(self.neafVendor.output_nvt_csv('neaf_management'))
        return

    def SaveNEAFCompanyBadgeSS(self):
        if not self.neafVendorIsValid('SaveNEAFCompanyBadgeSS'):
            return
        self.large_res.set(self.neafVendor.output_nvt_csv('neaf_company_badge'))
        return

    def ShopifyLoad(self):
        self.neafVendor =  NEAFVendor(neaf_year=self.neaf_year_entry,verbose=self.verbose.get())
        if self.neafVendor.error:
            self.large_res.set(showError(self.neafVendor.error) + '\n' + self.neafVendor.msg)
            return

        self.neafVendor.shopifyLoad()
        self.neaf_year = self.neafVendor.neaf_year

        if self.neafVendor.error:
            self.large_res.set(showError(self.neafVendor.error) + '\n' + self.neafVendor.msg)
            return
        else:
            self.large_res.set(self.neafVendor.msg)

        return

    def BuildFromPriorShopifyLoad(self):
        if not self.neafVendorIsValid('BuildFromPriorShopifyLoad'):
            return
        self.neafVendor.buildFromPriorShopifyLoad()
        if self.neafVendor.error:
            self.large_res.set('Failed running self.neafVendor.buildFromPriorShopifyLoad(). self.neafVendor.error is\n{0}.\n'.format(showError(self.neafVendor.error)))
        else:
            msg = \
            '''
            Reprocessed all companies with no reload from shopify. Edits were applied to raw shopify data from last full reload.
            '''
            self.large_res.set(msg)
        return

    def ShowHints(self):
        if not self.neafVendorIsValid('ShowHints'):
            return
        self.large_res.clear()
        self.large_res.set(self.neafVendor.show_hints(self.spt))
        return

    def ShowAndSaveAllInvoices(self):
        if not self.neafVendorIsValid('ShowAndSaveAllInvoices'):
            return
        self.large_res.clear()
        all_invoices_to_print,save_message_dummy = self.neafVendor.show_and_save_all_invoices(self.as_pdf.get())
        self.large_res.set(all_invoices_to_print)
        return

    def SaveLastInvoice(self):
        if not self.neafVendorIsValid('SaveLastInvoice'):
            return
        msg,subdir_path,fname = save_invoice(self.target_company,self.target_company_invoice,self.as_pdf.get())
        self.large_res.set(msg)
        return

    def VendorSignInSheet(self):
        if not self.neafVendorIsValid('VendorSignInSheet'):
            return
        self.large_res.set(self.neafVendor.save_vendor_sign_in_sheet())
        return

    def NeafYearEntry(self,val):
        self.neaf_year_entry = val
        return

    def ClearDisplay(self):
        self.large_res.clear()
        return

    # ********************************
    # self.company_key
    # ********************************

    def ShowInvoiceForKey(self):
        if not self.neafVendorIsValid('ShowInvoiceForKey'):
            return
        self.target_companies,target_companies_text = self.neafVendor.get_target_companies(self.company_key.get())
        if len(self.target_companies) == 1:
            self.large_res.clear()
            self.target_company,self.target_company_invoice = self.neafVendor.get_target_company_invoice(self.target_companies,'1')
            self.large_res.set(self.target_company_invoice)
        else:
            self.target_company = ''
            self.large_res.set(target_companies_text)
        return

    # ********************************
    # self.item_number_of_company
    # ********************************

    def ShowInvoiceForItemNumber(self):
        if not self.neafVendorIsValid('ShowInvoiceForItemNumber'):
            return
        self.target_company,self.target_company_invoice = self.neafVendor.get_target_company_invoice(self.target_companies,self.item_number_of_company.get())
        self.large_res.set(self.target_company_invoice)
        return

    # ********************************
    # self.as_pdf
    # ********************************

    # ********************************
    # self.save_invoice_cutoff_date
    # ********************************

    def SaveInvoicesAfterCutoffDate(self):
        if not self.neafVendorIsValid('SaveInvoicesAfterCutoffDate'):
            return
        self.large_res.clear()
        msg = self.neafVendor.save_all_requested_invoices_beyond_date(self.save_invoice_cutoff_date.get(),self.as_pdf.get())
        self.large_res.set(msg)
        return

    def EditAction(self,val):
        self.edit_action = val
        return

    # ********************************
    # self.edit_item
    # ********************************

    def ApplyEdit(self):
        if not self.neafVendorIsValid('ApplyEdit'):
            return
        msg = self.neafVendor.applyOrderNoteAttributeEdit(self.edit_action,self.edit_item.get())
        self.large_res.set(msg)
        return

    def SeeAllEditItems(self):
        if not self.neafVendorIsValid('SeeAllEditItems'):
            return
        self.large_res.set(self.neafVendor.see_all_edit_items())
        return


def main(argv):
    top = Tk()
    dpui = NEAFManagementUI(top,argv)
    dpui.mainloop()
    return

# TODO comment out calls to main before copying to RAC_share

# hoboken
#main(['c:\users\\family\Dropbox\RAC\py_scripts\\rac_launcher.py','jjmoskowitz76@gmail.com','pw:xxxxxx','cc:jjmoskowitz76@aol.com'])
# rockland
#main(['c:\users\\joe1\Dropbox\RAC\py_scripts\\rac_launcher.py','jjmoskowitz76@gmail.com','pw:xxxxxx','cc:jjmoskowitz76@aol.com'])

