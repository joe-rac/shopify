from tkinter import Tk,Frame,Label
from utils import build_startup_parameters
from utils_ui import STButton,STLargeResult,STWidget,STFrame,STWidgetDropDown
from hsp_attendees import HSPAttendees

from consts import HSP_YEAR_DEFAULT,HSP_YEAR_VALID

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
        master.geometry('1425x525' if self.width >=1900 else '1000x350')
        Frame.__init__(self,master)
        self.grid()
        self._create_widgets()
        self.ha = None
        return

    def ShopifyAndFranksSpreadsheetLoad(self):
        self.large_res.clear()
        self.ha = HSPAttendees(self.hsp_year_entry,verbose=self.verbose.get(),order_to_debug=self.order_to_debug.get())
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

        width = 100 if self.width >= 1900 else 80
        vert_frame1 = STFrame(self,width,1)
        STButton(vert_frame1, text="SHOPIFY AND FRANK'S S/S LOAD (must do this first)", command=self.ShopifyAndFranksSpreadsheetLoad, same_row=True)
        STWidgetDropDown(vert_frame1,'HSP year: %5s',HSP_YEAR_VALID,default_value=HSP_YEAR_DEFAULT,command=self.HSPYearEntry,same_row=True)
        STButton(vert_frame1, text="Show s/s", command=self.BuildAndDisplaySales, same_row=True)
        self.order_to_debug = STWidget(vert_frame1, 'order_to_debug:', width=6, same_row=True)
        self.verbose = STWidget(vert_frame1, 'verbose', check_box=True, width=1, same_row=True)

        self.large_res = STLargeResult(self,30,2 * width)

        return

    def HSPYearEntry(self,val):
        self.hsp_year_entry = val
        return

    def BuildAndDisplaySales(self):

        if not self.ha:
            self.large_res.set('Cannot display s/s. Load data first.')
            return

        self.ha.buildAndDisplaySales()
        if self.ha.error:
            self.large_res.set(self.ha.error)

        return

def main(argv):
    top = Tk()
    dpui = HSPAttendeesUI(top,argv)
    dpui.mainloop()
    return