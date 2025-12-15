from tkinter import Tk,Frame,Label
from utils_ui import STButton,STWidgetDropDown,STLargeResult,STWidget
from utils import DEFAULT_DAY
from search_and_mark import show_hints,show_paths_and_files,show_dicts,get_search_and_mark_dicts,NEAF_ATTENDEE,MERCH,DOOR_PRIZE_CC
from search_and_mark import search_and_display,confirm_or_unconfirm

SEARCH_IN = ('NEAF Attendees','RAC Merchandise Purchasers','Constant Contact Door Prize Entrants')   

class SearchAndMarkUI(Frame):
    def __init__(self,master):
        self.master = master
        self.next_row = 1
        self.next_column = 0
        self.verbose = False
        self.weekend_day = DEFAULT_DAY
        self.samdt = get_search_and_mark_dicts(self.weekend_day,self.verbose)
        self.samdt_key = NEAF_ATTENDEE
        self.search_for = None
        self.target_dict = {}
        self.c_or_u = None
        master.title('Search and Confirm')
        master.geometry('1140x690')
        Frame.__init__(self,master)
        self.grid()
        self._create_widgets()
        return
    def _create_widgets(self):
        self.l0 = Label(self,text='Choose a Search and Confirm function')
        self.l0.grid()
 
        STWidgetDropDown(self,'Search in %36s',SEARCH_IN,default_value=SEARCH_IN[0],command=self.SearchIn)
        self.search_for = STWidget(self,'Search for this item:',width=50)
        STButton(self,text='Search Now',command=self.SearchNow)
        self.target_str = STLargeResult(self,8,157)  
        self.confirm_or_unconfirm = STWidget(self,'Item # to Confirm or Unconfirm:',width=30)
        STButton(self,text='Confirm',command=self.ConfirmItem)
        STButton(self,text='Unconfirm',command=self.UnconfirmItem)
        self.message = STLargeResult(self,2,100)        
        STButton(self,text='Show all search and confirm data',command=self.ShowData)   
        self.large_res = STLargeResult(self,10,157) 
        STButton(self,text='Refresh Data',command=self.RefreshData)
        STButton(self,text='Hints',command=self.Hints)
        STButton(self,text='Show Paths and Files',command=self.ShowPathsAndFiles)
        STButton(self,text='Clear Results',command=self.ClearResults)
        STWidgetDropDown(self,'Verbose: %3s',('Off','On'),default_value='off',command=self.Debugging)
           
        return

    def SearchIn(self,val):
        if val == SEARCH_IN[0]:
            self.samdt_key = NEAF_ATTENDEE
        elif val == SEARCH_IN[1]:
            self.samdt_key = MERCH
        else:
            self.samdt_key = DOOR_PRIZE_CC
        return
    def SearchNow(self):
        self.samdt,self.target_dict,self.samdt_key,target_str = search_and_display(self.samdt,self.samdt_key,self.search_for.get())
        self.target_str.clear()
        self.target_str.set(target_str)
        return 
    def ConfirmOrUnconfirm(self,val,confirm):
        cstr = 'c' if confirm else 'u'
        self.c_or_u = cstr+val
        self.message.clear()
        self.message.set(confirm_or_unconfirm(self.samdt_key,self.target_dict,self.samdt,self.c_or_u))
        return             
    def ConfirmItem(self):
        self.ConfirmOrUnconfirm(self.confirm_or_unconfirm.get(),True)
        return     
    def UnconfirmItem(self):
        self.ConfirmOrUnconfirm(self.confirm_or_unconfirm.get(),False)
        return 
    def ShowData(self):
        self.large_res.clear()
        self.large_res.set(show_dicts(self.samdt))
        return          
    def RefreshData(self):
        self.samdt = get_search_and_mark_dicts(self.weekend_day,self.verbose)
        self.ClearResults()
        self.large_res.set(show_dicts(self.samdt))
        return   
    def Hints(self):
        self.large_res.clear()
        self.large_res.set(show_hints())
        return      
    def ShowPathsAndFiles(self):
        self.large_res.clear()
        self.large_res.set(show_paths_and_files())
        return        
    def ClearResults(self):
        self.target_str.clear()
        self.message.clear()
        self.large_res.clear()
        return 
    def Debugging(self,val):
        if val == 'On':
            LOGGING[0] = True
        else:
            LOGGING[0] = False    
        return                       

def main():
    top = Tk()
    dpui = SearchAndMarkUI(top)
    dpui.mainloop()
    return

# comment out call to main before copying to RAC_share
#main()