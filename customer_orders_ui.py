
from tkinter import Tk,Frame,Label
from utils import build_startup_parameters
from utils_ui import STButton,STLargeResult,STWidget,STFrame,STWidgetDropDown
from customer_orders import CustomerOrders

from consts import HSP_YEAR_DEFAULT,HSP_YEAR_VALID

class CustomerOrdersUI(Frame):
    def __init__(self,master,argv):

        self.master = master
        self.width = self.master.winfo_screenwidth()
        self.height = self.master.winfo_screenheight()
        print('screen width:{0}, screen height:{1}'.format(self.width, self.height))
        self.argv = argv
        self.spt = build_startup_parameters(self.argv)

        self.next_row = 1
        self.next_column = 0
        master.title('Customer Orders')
        master.geometry('1235x550')
        Frame.__init__(self,master)
        self.grid()
        self._create_widgets()
        self.ha = None
        return

    def CustomerOrdersLoad(self):

        self.co = CustomerOrders()
        self.co.loadOrdersForCustomer(self.customer_search.get())

        if self.co.error:
            self.large_res.set(self.co.error)
            return

        self.large_res.set(self.co.msg)
        return

    def DisplayLineItems(self):

        if not self.co:
            self.large_res.set('Cannot display line items s/s. Load data first.')
            return

        self.co.displayLineItems()
        if self.co.error:
            self.large_res.set(self.co.error)

        return

    def Clear(self):
        self.large_res.clear()
        return

    def _create_widgets(self):
        self.l0 = Label(self,text='Customer Orders')
        self.l0.grid()

        width = 87
        vert_frame1 = STFrame(self,width,1)

        self.customer_search = STWidget(vert_frame1,'Customer search:',width=25,same_row=True)
        STButton(vert_frame1,text='LOAD CUSTOMER ORDERS (must do this first)',command=self.CustomerOrdersLoad,same_row=True)
        STButton(vert_frame1,text='Show line items s/s',command=self.DisplayLineItems,same_row=True)
        STButton(vert_frame1,text='Clear',command=self.Clear,same_row=True)

        self.large_res = STLargeResult(self,34,2 * width)

        return

def main(argv):
    top = Tk()
    dpui = CustomerOrdersUI(top,argv)
    dpui.mainloop()
    return