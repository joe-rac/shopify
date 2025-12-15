import os
from tkinter import Tk,Frame,Label
from utils import build_startup_parameters
from utils_ui import STButton,STLargeResult,STWidget,STFrame,STWidgetDropDown
from orders import Orders

class OrdersUI(Frame):
    def __init__(self,master,argv):
        # install win32api with
        # pip install pywin32

        self.master = master
        self.width = self.master.winfo_screenwidth()
        self.height = self.master.winfo_screenheight()
        print('screen width:{0}, screen height:{1}'.format(self.width, self.height))
        self.argv = argv
        self.spt = build_startup_parameters(self.argv)

        self.next_row = 1
        self.next_column = 0
        self.orders = None
        self.product_type = Orders.PRODUCT_TYPES[0]
        self.number_of_address_rows = '1'
        master.title('Orders')
        master.geometry('1820x690' if self.width >=1900 else '1420x690')
        Frame.__init__(self,master)
        self.grid()
        self._create_widgets()
        return

    def _create_widgets(self):
        self.l0 = Label(self,text='Choose an Order Management function')
        self.l0.grid()

        width = 125 if self.width >= 1900 else 100
        vert_frame1 = STFrame(self,width,1)
        STButton(vert_frame1, text='SHOPIFY LOAD (must do this first)', command=self.ShopifyLoad, same_row=True)
        self.option = STWidget(vert_frame1, 'Option:', width=50, same_row=True)
        STButton(vert_frame1,text='Order by search(enter search word)',command=self.orders_by_search,same_row=True)
        self.created_at_min = STWidget(vert_frame1,'created_at_min(YYYY-MM-DD):',width=10,same_row=True)
        self.created_at_max = STWidget(vert_frame1, 'created_at_max(YYYY-MM-DD):', width=10, same_row=True)
        self.order_to_debug = STWidget(vert_frame1, 'order_to_debug:', width=6, same_row=True)

        vert_frame2 = STFrame(self,width,1)
        STButton(vert_frame2, text='NEAIC attendee report (full), Dump to csv', command=self.neaic_attendee_dump_to_csv_full, same_row=True)
        STButton(vert_frame2, text='NEAIC attendee report (incremental), Dump to csv', command=self.neaic_attendee_dump_to_csv_incremental, same_row=True)
        STButton(vert_frame2,text='Dump to csv',command=self.dump_to_csv,same_row=True)
        STButton(vert_frame2,text='Dump to csv - 1 line per item',command=self.dump_to_csv_1_line_per_item,same_row=True)
        STButton(vert_frame2,text='Show dicts',command=self.show_dicts,same_row=True)
        STButton(vert_frame2,text='Debug on',command=self.debug_on,same_row=True)
        STButton(vert_frame2,text='Debug off',command=self.debug_off,same_row=True)
        STButton(vert_frame2,text='Hints',command=self.show_hints,same_row=True)
        STButton(vert_frame2,text='Clear Screen',command=self.clear_screen,same_row=True)
        self.verbose = STWidget(vert_frame2, 'verbose', check_box=True, width=1, same_row=True)

        vert_frame3 = STFrame(self,width,1)

        STWidgetDropDown(vert_frame3,'# of Address rows: %1s',('1','2','3'),default_value='1',command=self.NumberOfAddressRows,same_row=True)
        STWidgetDropDown(vert_frame3,'Choose product type: %13s', Orders.PRODUCT_TYPES, default_value=Orders.PRODUCT_TYPES[0], command=self.ProductType, same_row=True)

        self.large_res = STLargeResult(self,40,2 * width)

        return

    def orderObjectLoaded(self,label):
        if not self.orders:
            self.large_res.set("Cannot execute the option '{0}' until the option of 'SHOPIFY LOAD (must do this first)' is run.".format(label))
            return False
        return True

    def clear_screen(self):
        self.large_res.clear()
        return

    def orders_by_search(self):
        if not self.orderObjectLoaded('orders_by_search'):
            return
        self.large_res.set(self.orders.orders_by_search(self.option.get()))
        return

    def neaic_attendee_dump_to_csv_full(self):
        if not self.orderObjectLoaded('neaic_attendee_dump_to_csv'):
            return
        self.large_res.set(self.orders.neaic_attendee_dump_to_csv())
        return
    def neaic_attendee_dump_to_csv_incremental(self):
        if not self.orderObjectLoaded('neaic_attendee_dump_to_csv'):
            return
        self.large_res.set(self.orders.neaic_attendee_dump_to_csv(incremental_since_last_run=True))
        return
    def dump_to_csv(self):
        if not self.orderObjectLoaded('dump_to_csv'):
            return
        self.large_res.set(self.orders.dump_to_csv())
        return
    def dump_to_csv_1_line_per_item(self):
        if not self.orderObjectLoaded('dump_to_csv_1_line_per_item'):
            return
        self.large_res.set(self.orders.dump_to_csv_1_line_per_item())
        return
    def show_dicts(self):
        if not self.orderObjectLoaded('show_dicts'):
            return
        self.large_res.set(self.orders.show_dicts())
        return
    def show_hints(self):
        if not self.orderObjectLoaded('show_hints'):
            return
        self.large_res.set(self.orders.show_hints())
        return
    def debug_on(self):
        if not self.orderObjectLoaded('debug_on'):
            return
        self.orders.logging = True
        return
    def debug_off(self):
        if not self.orderObjectLoaded('debug_off'):
            return
        self.orders.logging = False
        return

    def ShopifyLoad(self):
        self.orders = Orders(self.product_type,number_of_address_rows=self.number_of_address_rows,verbose=self.verbose.get(),order_to_debug=self.order_to_debug.get())
        self.orders.shopifyLoad(created_at_min=self.created_at_min.get(),created_at_max=self.created_at_max.get())
        if self.orders.error:
            self.large_res.set(self.orders.error)
        else:
            self.large_res.set(self.orders.show_dicts())
        return

    def NumberOfAddressRows(self,val):
        self.number_of_address_rows = val
        return
    def ProductType(self, val):
        self.product_type = val
        return


def main(argv):
    top = Tk()
    dpui = OrdersUI(top,argv)
    dpui.mainloop()
    return

# comment out call to main before copying to RAC_share
#main()