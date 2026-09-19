
from collections import namedtuple
import tempfile
import os
from utils import appendMsg
from graphql_utils import get_order_nums_from_customer_search
from orders import Orders
from openpyxl import Workbook

CUSTOMER_FIELDS = 'displayName email phone street city state zip country'
CustomerTup = namedtuple('CustomerTup', CUSTOMER_FIELDS)
LINE_ITEM_FIELDS = 'order_num created_at name phone_num sku quantity paid'
LineItemTup =  namedtuple('LineItemTup', LINE_ITEM_FIELDS)

class CustomerOrders(object):

    def __init__(self):
        self.error = ''
        self.msg = ''
        self.cust_str = ''
        self.customers = []
        self.orders = []
        self.line_items = []
        self.sku_to_quantity_map = {}

        return

    def _ordersForCustomerSummary(self):

        summary = f"For search string '{self.cust_str}' found {len(self.customers)} customer record(s) and {len(self.orders)} order(s).\n\n"

        summary += 'Customers:\n'
        summary += f'{"displayName":<18}{"email":<30}{"phone":<14}{"street":<30}{"city":<15}{"state":<12}{"zip":<12}{"country":<20}\n'

        for ct in self.customers:
            summary += f'{str(ct.displayName):<18}{str(ct.email):<30}{str(ct.phone):<14}{ct.street:<30}{ct.city:<15}{ct.state:<12}{ct.zip:<12}{ct.country:<20}\n'

        summary += '\nOrders:\n'
        summary += ','.join(str(order_num) for order_num in self.orders)

        return summary

    def _loadOrders(self):
        order_to_debug = '|'.join([str(o) for o in self.orders])
        # TODO 9/8/2026. Passing order_to_debug to the constructor is a hack. Its only purpose is that existing gating code in the constructor takes a different path
        #                than when product_type is set but order_to_debug is missing. Most likely fix is simple: allow product_type=None to replace the existing gating logic
        #                based on the existence of order_to_debug, and then remove order_to_debug from the constructor. Discussed with ChatGPT; fix after HSP.
        orders = Orders(None,order_to_debug=order_to_debug)
        if orders.error:
            self.error = orders.error
            return
        orders.shopifyLoad(order_to_debug=order_to_debug)
        if orders.error:
            self.error = orders.error
            return
        self.msg = appendMsg(self.msg,orders.msg,print_new_msg=False)

        products = [orders.order_dict[k] for k in sorted(orders.order_dict.keys(),key=lambda k: tuple(int(x) for x in k.split('-')),reverse=True)]
        for pr in products:
            self.line_items.append(LineItemTup(pr.order_num,pr.created_at,pr.name,pr.phone_num,pr.sku,pr.quantity,pr.paid))
            quantity_tot = self.sku_to_quantity_map.get(pr.sku,0)
            self.sku_to_quantity_map[pr.sku] = quantity_tot + pr.quantity

        self.msg = appendMsg(self.msg,f'Total of {len(self.line_items)} line items over {len(self.sku_to_quantity_map)} distinct skus.',print_new_msg=False)
        qps_str = f"Quantities per sku: {','.join(f'{sku}:{quantity}' for sku,quantity in self.sku_to_quantity_map.items())}"
        max_line_len = 150

        items = qps_str.split(',')
        lines = []
        line = ''
        for item in items:
            if line and len(line) + len(item) + 1 > max_line_len:
                lines.append(line)
                line = item
            else:
                line += (',' if line else '') + item
        if line:
            lines.append(line)

        qps_str = '\n'.join(lines)
        self.msg = appendMsg(self.msg,f"{qps_str}",print_new_msg=False)

        return

    def loadOrdersForCustomer(self,cust_str):

        self.customers.clear()
        self.orders.clear()
        self.line_items.clear()
        self.sku_to_quantity_map.clear()
        self.cust_str = cust_str
        order_nums,customers = get_order_nums_from_customer_search(cust_str)
        order_nums = [int(o) for o in order_nums]
        order_nums.sort(reverse=True)
        self.orders.extend(order_nums)
        for cu in customers:
            ad = cu['defaultAddress']
            if ad:
                st = ad['address1'] + ', ' + ad['address2'] if ad['address2'] else ad['address1']
                city = ad['city']
                state = ad['province']
                zip = ad['zip']
                country = ad['country']
            else:
                st = ''
                city = ''
                state = ''
                zip = ''
                country = ''
            ct = CustomerTup(cu['displayName'],cu['email'],cu['phone'],st,city,state,zip,country)
            self.customers.append(ct)

        self.msg = appendMsg(self.msg,self._ordersForCustomerSummary(),print_new_msg=False)

        self._loadOrders()

        return
    def displayLineItems(self):

        fd,fname = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)

        wb = Workbook()
        ws = wb.active
        ws.title = 'Line Items'

        ws.append(LineItemTup._fields)
        ws.freeze_panes = 'A2'

        for line_item in self.line_items:
            ws.append(line_item)

        for column_cells in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            ws.column_dimensions[column_cells[0].column_letter].width = max_length + 2

        wb.save(fname)
        os.startfile(fname)

        return
