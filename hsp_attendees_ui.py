from tkinter import Tk,Frame,Label
from utils import build_startup_parameters
from utils_ui import STButton,STLargeResult,STWidget,STFrame,STWidgetDropDown
from hsp_attendees import HSPAttendees

from consts import HSP_YEAR_DEFAULT,HSP_YEAR_VALID,DEFAULT_NUM_HSP_RAFFLE_WINNERS

class HSPAttendeesUI(Frame):
    def __init__(self,master,argv):

        self.master = master
        self.width = self.master.winfo_screenwidth()
        self.height = self.master.winfo_screenheight()
        print('screen width:{0}, screen height:{1}'.format(self.width, self.height))
        self.argv = argv
        self.spt = build_startup_parameters(self.argv)

        self.next_row = 1
        self.next_column = 0
        self.hsp_year_entry = HSP_YEAR_DEFAULT
        master.title('HSP Attendees')
        master.geometry('1235x550')
        Frame.__init__(self,master)
        self.grid()
        self._create_widgets()
        self.ha = None
        return

    def ShopifyAndFranksSpreadsheetLoad(self):
        self.large_res.clear()
        self.ha = HSPAttendees(self.hsp_year_entry)
        if self.ha.error:
            self.large_res.set(self.ha.error)
            return
        self.ha.shopifyAndFranksSpreadsheetLoad()
        if self.ha.error:
            self.large_res.set(self.ha.error)
        else:
            self.large_res.set(self.ha.msg)
        return

    def _create_widgets(self):
        self.l0 = Label(self,text='HSP Attendees')
        self.l0.grid()

        width = 87
        vert_frame1 = STFrame(self,width,1)
        STButton(vert_frame1, text="SHOPIFY AND FRANK'S S/S LOAD (must do this first)", command=self.ShopifyAndFranksSpreadsheetLoad, same_row=True)
        STWidgetDropDown(vert_frame1,'HSP year: %5s',HSP_YEAR_VALID,default_value=HSP_YEAR_DEFAULT,command=self.HSPYearEntry,same_row=True)
        STButton(vert_frame1, text="Show s/s", command=self.BuildAndDisplaySales, same_row=True)
        self.num_raffle_winners = STWidget(vert_frame1,'# raffle winners:',width=2,default_value=DEFAULT_NUM_HSP_RAFFLE_WINNERS,same_row=True)
        STButton(vert_frame1, text="Pick raffle winners", command=self.PickRaffleWinners, same_row=True)
        STButton(vert_frame1,text='Clear Display',command=self.ClearDisplay,same_row=True)

        self.large_res = STLargeResult(self,34,2 * width)

        return

    def HSPYearEntry(self,val):
        self.hsp_year_entry = val
        return

    def BuildAndDisplaySales(self):

        if not self.ha:
            self.large_res.set('Cannot display s/s. Load data first.')
            return

        msg = self.ha.buildAndDisplaySales()
        self.large_res.set(msg)

        return

    def PickRaffleWinners(self):

        if not self.ha:
            self.large_res.set('Cannot pick raffle winners. Load data first.')
            return

        msg,error = self.ha.pick_raffle_winners(self.num_raffle_winners.get())
        if error:
            self.large_res.set(error+'\n')
        else:
            self.large_res.set(msg+'\n')

        return

    def ClearDisplay(self):
        self.large_res.clear()
        return

def main(argv):
    top = Tk()
    dpui = HSPAttendeesUI(top,argv)
    dpui.mainloop()
    return