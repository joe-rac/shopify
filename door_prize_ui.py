from tkinter import Tk,Frame,Label
from utils import NEAF_DAYS,DEFAULT_DAY,show_paths_and_files_dp,showError
from utils_ui import STButton,STWidgetDropDown,STLargeResult,STFrame,STWidget
from door_prize import DoorPrize,build_winners_pdf

class DoorPrizeUI(Frame):
    def __init__(self,master):
        self.master = master
        self.next_row = 1
        self.neaf_day = DEFAULT_DAY
        self.dp = None

        master.title('Door Prize')
        master.geometry('1330x635')
        Frame.__init__(self,master)
        self.grid()
        self._create_widgets()
        self.verbose = False
        return

    def _create_widgets(self):
        self.l0 = Label(self,text='Choose a Door Prize function')
        self.l0.grid()

        vert_frame1 = STFrame(self,100,1)
        STButton(vert_frame1, text='Load Data (must do this first)', command=self.ConstantContactAndShopifyLoad, same_row=True)
        STButton(vert_frame1,text='Pick Winner',command=self.PickWinner,same_row=True)
        STButton(vert_frame1,text='Build Winners PDF',command=self.BuildWinnersPdf,same_row=True)
        vert_frame2 = STFrame(self,100,1)
        STButton(vert_frame2,text='Show all door prize data',command=self.ShowData,same_row=True)
        STWidgetDropDown(vert_frame2,'Choose override NEAF Day: %8s',NEAF_DAYS,default_value=DEFAULT_DAY,command=self.ChooseNEAFDay,same_row=True)
        STWidgetDropDown(vert_frame2,'Verbose: %3s', ('True','False'), default_value='False', command=self.Verbose, same_row=True)
        STButton(vert_frame2,text='Hints',command=self.Hints,same_row=True)
        STButton(vert_frame2,text='Show Paths and Files',command=self.ShowPathsAndFiles,same_row=True)
        STButton(vert_frame2,text='Get Random Index',command=self.GetRandomIndex,same_row=True)
        STButton(vert_frame2,text='Clear Results',command=self.ClearResults,same_row=True)
        self.searchItem = STWidget(vert_frame2, 'Item:', width=20, same_row=True)
        STButton(vert_frame2, text='Search', command=self.SearchForItem, same_row=True)

                  
        self.small_res = STLargeResult(self,5,172)
        self.large_res = STLargeResult(self,33,187)
        
        return

    def doorPrizeObjectLoaded(self,label):
        if not self.dp:
            self.large_res.set("Cannot execute the option '{0}' until the option of 'Load Date (must do this first)' is run.".format(label))
            return False
        return True

    def PickWinner(self):
        if not self.doorPrizeObjectLoaded('PickWinner'):
            return
        self.small_res.set(self.dp.pick_and_show_winner())
        return
    def BuildWinnersPdf(self):
        if not self.doorPrizeObjectLoaded('BuildWinnersPdf'):
            return
        self.small_res.set(build_winners_pdf(self.dp.dpSrc.winner))
        return
    def ConstantContactAndShopifyLoad(self):
        self.dp = DoorPrize(override_day=self.neaf_day,verbose=self.verbose)
        if self.dp.error:
            self.large_res.set(showError(self.dp.error) + '\n' + self.dp.msg)
            return
        self.dp.constantContactAndShopifyLoad()
        self.large_res.set(self.dp.msg  + '\n' + self.dp.show_dicts_summary())
        return    
    def ShowData(self):
        if not self.doorPrizeObjectLoaded('ShowData'):
            return
        self.large_res.clear()
        self.large_res.set(self.dp.show_dicts())
        return  
    def ChooseNEAFDay(self,val):
        self.neaf_day = val
        return
    def Verbose(self, val):
        if val == 'True':
            self.verbose = True
        else:
            self.verbose = False
        return        
    def Hints(self):
        if not self.doorPrizeObjectLoaded('Hints'):
            return
        self.large_res.clear()
        self.large_res.set(self.dp.show_hints_dp())
        return    
    def ShowPathsAndFiles(self):
        self.small_res.set(show_paths_and_files_dp())
        return
    def GetRandomIndex(self):
        if not self.doorPrizeObjectLoaded('GetRandomIndex'):
            return
        self.large_res.set(self.dp.show_random_index())
        return  
    def ClearResults(self):
        self.small_res.clear()
        self.large_res.clear()
        return
    def SearchForItem(self):
        if not self.doorPrizeObjectLoaded('SearchForItem'):
            return
        self.large_res.clear()
        self.large_res.set(self.dp.search_for_item(self.searchItem.get()))
        return

        
def main():
    top = Tk()
    dpui = DoorPrizeUI(top)
    dpui.mainloop()
    return

# comment out main before trying to use with rac_launcher.
#main()
