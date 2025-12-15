import sys
from neaf_vendor_console import main as neaf_vendor_main
from door_prize import main as door_prize_main
from search_and_mark import main as search_and_mark_main
from orders import main as orders_main

def main():
    while True:
        print('0: stop')
        print('1: NEAF Vendor Management Tool -- console mode')
        print('2: door prize app -- console mode')
        print('3: search and confirm app -- console mode')
        print('4: orders app -- console mode')
        optionstr = input('-----> ')
        if optionstr=='0':
            break
        if optionstr=='1':
            neaf_vendor_main(sys.argv)
            break
        if optionstr=='2':
            door_prize_main()
            break
        if optionstr=='3':
            search_and_mark_main()
            break
        if optionstr=='4':
            orders_main()
            break

        print("Invalid entry. You're not too bright. Are you?")
    return
main()