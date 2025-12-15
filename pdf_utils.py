# utiliites used to manage and disply pdf files

r'''
documentation on web said run
pip import fpdf
but it failed in hoboken, worked in rockland the 2nd time I tried. Instead I used
pip install fpdf
http://www.fpdf.org/en/doc/index.php   seems pretty good
http://cloford.com/resources/colours/500col.htm rgb values

Best documentation:
https://pyfpdf.readthedocs.org/en/latest/reference/FPDF/

wxPython seems to have tools to display pdfs and figure out what monitors are doing
http://stackoverflow.com/questions/22772968/python-pygtk-how-to-put-a-window-on-a-specific-display-monitor might help me use specific monitors

open tkinter window at specified point on display
http://stackoverflow.com/questions/3352918/how-to-center-a-window-on-the-screen-in-tkinter
http://stackoverflow.com/questions/17741928/python-tkinter-screen-width-and-height-secondary-display

doc for opening pdf by script
http://www.adobe.com/content/dam/Adobe/en/devnet/acrobat/pdfs/pdf_open_parameters.pdf

C:\Windows\System32\cmd.exe /c start "reader:"

'''

import os
from datetime import timedelta
from dateutil import parser
# install with
# pip install fpdf
from fpdf import FPDF
from utils import DOOR_PRIZE_WINNER,pdf_path,get_default_neaf_year

WINNERS_PER_ROW = 3
# use these 2 values to override screen dimensions derive from FPDF results
MIN_X = None
MAX_X = None
# page size is set bigger then it needs to be to fully fill screen
HEIGHT = 200
WIDTH = 350

def init_page():
    p = FPDF(orientation='L',format=(HEIGHT,WIDTH))
    p.set_fill_color(r=255, g=255,b=255)
    p.set_text_color(r=200,g=0,b=0)
    p.add_page()
    p.rect(0,0,1000,1000,style='F')
    return p

def get_page_geometry(p):
    min_x = p.get_x()
    min_y = p.get_y()
    p.set_xy(-1,-1)
    max_x = p.get_x()
    max_y = p.get_y()
    center_x = (max_x-min_x)/2
    comment = 'PAGE GEOMETRY: min_x {0} min_y {1} max_x {2} max_y {3} center_x {4}'.format(min_x,min_y,max_x,max_y,center_x)
    p.set_xy(min_x,min_x)
    return min_x,max_x,center_x,max_y,comment

def _cell(p,x,x_inc,text,ln=0):
    p.set_x(x)
    x += x_inc
    p.cell(1,6,text,align='C',ln=ln)
    return x

def show_an_hours_winners(p,min_x,max_x,hour,winners):
    p.set_text_color(r=238,g=180,b=34)
    _min_x =  MIN_X if MIN_X is not None else min_x # apply override to minimum x if applicable
    x = 2 * _min_x
    x_inc = (max_x-min_x)/(WINNERS_PER_ROW+1)
    x = _cell(p,x,x_inc,hour)
    p.set_text_color(r=0,g=0,b=255)
    cnt = 1
    i=0
    for winner in winners:
        i +=1
        ln = 1 if cnt == WINNERS_PER_ROW or i==len(winners) else 0
        x = _cell(p,x,x_inc,winner,ln=ln)
        if cnt == WINNERS_PER_ROW:
            x = _cell(p,2 * _min_x,x_inc,'')
            cnt = 1
        else:
            cnt += 1
    p.cell(10,3,'',align='C',ln=1)
    return

def build_doorprize_winner_pdf(all_winners):

    p = init_page()
    min_x,max_x,center_x,max_y,pg_comment = get_page_geometry(p)

    p.set_font('Arial','B',35)
    p.set_x(center_x-70)
    heading = 'NEAF {0} Door Prize Winners'.format(get_default_neaf_year())
    p.cell(140,20,heading,align='C',ln=1)
    p.set_y(p.get_y()+10)
    p.set_font('Arial','B',15)

    for (hour,winners) in all_winners:
        show_an_hours_winners(p,min_x,max_x,hour,winners)

    p.set_font('Arial','B',20)
    y = p.get_y()
    p.set_xy(center_x,y+15)
    p.set_text_color(r=0,g=200,b=100)
    p.cell(1,1,'Congratulations Winners',align='C')

    fname = pdf_path()
    p.output(fname,'F')
    # 4/8/2023. displaying the pdf doesn't seem to work well anymore. it freezes the app. force the user to open each pdf manually after building it with 'Build Winners PDF'.
    #os.system(fname)
    #os.startfile(fname)
    comment = 'pdf path:{0}\n{1}'.format(fname,pg_comment)
    return comment

def get_hour(CONFIRM_NOTE):
    picked_at = CONFIRM_NOTE.split()[-1]
    dt = parser.parse(picked_at)
    dt = dt + timedelta(minutes = 30)
    hour_int = dt.hour
    hour = 'Noon' if dt.strftime("%I%p") == '12PM' else dt.strftime("%I%p")
    hour = hour[1:] if hour[0:1] == '0' else hour
    return hour,hour_int

def build_winners_pdf(dp_src_winner):

    # first kill prior running pdf display before building new file
    os.system('taskkill /f /im AcroRd32.exe')

    all_winners_dict = {}
    for dpt in list(dp_src_winner.values()):
        winner = dpt.name
        hour,hour_int = get_hour(dpt.CONFIRM_NOTE)
        all_winners_item = all_winners_dict.get(hour_int,(hour,[]))
        if not all_winners_item[1]:
            all_winners_dict[hour_int] = all_winners_item
        all_winners_item[1].append(winner)
    all_winners = []
    for hour_int,all_winners_item in all_winners_dict.items():
        all_winners.append(all_winners_item)
    comment = build_doorprize_winner_pdf(all_winners)
    return comment

def main():
    all_winners = [
        ('10AM',['Joe Moskowitz','Sarah Colker','Jarred Donkersley','David Brotherston','Emily Moskowitz']),
        ('11AM',['Robert Johnson','Babak Sedehi','Tom Peters']),
        ('Noon',['manfred bruenjes','Linda Shore','Mia Ishikawa','Serguei Antonov','Robert Kolbet','Jeff Simon','Lawrence Faltz']),
        ('1PM',['Csaba Bereczki','Ms. Dominik Schwarz','Brian Deis']),
        ('2PM',['Noelyn Rodney','David Ho','Lucretia Darrah']),
        ('3PM',['manfred bruenjes','Linda Shore','Mia Ishikawa']),
        ('4PM',['manfred bruenjes','Linda Shore','Mia Ishikawa','Serguei Antonov','Robert Kolbet','Jeff Simon','Lawrence Faltz']),
        ('5PM',['manfred bruenjes','Linda Shore','Mia Ishikawa','Serguei Antonov','Robert Kolbet']),
        ('6PM',['manfred bruenjes','Linda Shore','Mia Ishikawa','Serguei Antonov','Robert Kolbet','Jeff Simon'])
        ]
    comment = build_doorprize_winner_pdf(all_winners)
    print(comment)
    return
# comment out main before copying to RAC_share
#main()
