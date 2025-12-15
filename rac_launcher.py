import sys
import os
import faulthandler
from utils import USE_GRAPHQL
from neaf_vendor_ui import main as neaf_vendor_ui_main
from door_prize_ui import main as door_prize_ui_main
from search_and_mark_ui import main as search_and_mark_ui_main
from orders_ui import main as orders_ui_main
import tracemalloc

def main():
    if os.name != 'nt':
        print("Change of plans. It's too much of an ass pain to support anything but windows. os.name:'{0}' is not supported. Must be 'nt'.".format(os.name))
    faulthandler.enable()
    tracemalloc.start()
    tracemalloc.start()
    USE_GRAPHQL[0] = True
    print('At entrance to main() in rac_launcher we have current:{0}, peak:{1} from tracemalloc.get_traced_memory()'.format(*tracemalloc.get_traced_memory()))

    while True:

        print('0: stop')
        print('1: NEAF Vendor Management Tool')
        print('2: door prize app')
        print('3: search and confirm app')
        print('4: orders app')
        optionstr = input('-----> ')
        if optionstr=='0':
            break
        if optionstr=='1':
            print('memory usage in rac_launcher before launch of neaf_vendor_ui:{0}'.format(tracemalloc.get_traced_memory()))
            neaf_vendor_ui_main(sys.argv)
            break
        if optionstr=='2':
            door_prize_ui_main()
            break  
        if optionstr=='3':
            search_and_mark_ui_main()
            break
        if optionstr=='4':
            orders_ui_main(sys.argv)
            break

        print("Invalid entry. You're not too bright. Are you?")
    return
main()
