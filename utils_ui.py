from tkinter import Frame,Label,Button,OptionMenu,StringVar,IntVar,Checkbutton,Entry,WORD,END,Text,Scrollbar
import tkinter.font

class STButton(object):
    def __init__(self,master,text,command,same_row=False):
        # TODO same_row doesn't work as intended. need to stick widgets on same row in new Frame

        self.bt = Button(master,text=text,command=command)

        if same_row:
            row = 0
            column = master.next_column
        else:
            row = master.next_row
            column = 0
        self.bt.grid(row=row,column=column)
        if same_row:
             master.next_column += 1
        else:
            master.next_row += 1
        return

class STWidgetDropDown(OptionMenu):
    def __init__(self,master,label_format,options,default_value=None,command=None,same_row=False):
        # TODO same_row doesn't work as intended. need to stick widgets on same row in new Frame
        self.label_format = label_format+'  ---  Change?'
        self.label = StringVar(master)
        if default_value is None:
            self.label.set(self.label_format%'')
        else: 
            self.label.set(self.label_format%default_value)
        self.value = StringVar(master)
        default_value = 'None' if default_value is None else default_value
        self.value.set(default_value)
        self.command = command
        OptionMenu.__init__(self, master, self.label,*options,command=self._command)

        if same_row:
            row = 0
            column = master.next_column
        else:
            row = master.next_row
            column = 0
        self.grid(row=row,column=column)
        if same_row:
             master.next_column += 1
        else:
            master.next_row += 1

        return 
    def _command(self,value):
        if self.command: 
            self.command(value)
        self.value.set(value) 
        self.label.set(self.label_format%value)
        return 
    def get(self):
        res = None if self.value.get()=='None' else self.value.get() 
        return res 

class STWidget(Frame):
    def __init__(self,master,label,width=None,check_box=False,same_row=False):
        Frame.__init__(self,master)
        if check_box:
            self.val = IntVar(self)
            self.check_box = Checkbutton(self, variable=self.val, onvalue=1, offvalue=0, text=label)
            self.check_box.grid(row=1,column=0) 
            self.label = None
            self.entry = None
        else: 
            self.val = StringVar(self)
            self.label = Label(self,text=label)
            self. label.grid(row=1,column=0) 
            self.entry = Entry(self,width=width,textvariable=self.val) 
            self.entry.grid(row=1,column=1) 
            self.check_box = None

        if same_row:
            row = 0
            column = master.next_column
        else:
            row = master.next_row
            column = 0
        self.grid(row=row,column=column)
        if same_row:
             master.next_column += 1
        else:
            master.next_row += 1

        return
    def get(self): 
        res = bool(self.val.get()) if self.check_box else self.val.get() 
        return res

    def clear_text(self):
        self.entry.delete(0,'end')
        
class STLargeResult(Frame): 

    def __init__(self, master, height=1, width=190):
        Frame.__init__(self, master)

        small_font = tkinter.font.Font(family="Courier", size=8)

        # Create scrollbars
        yscroll = Scrollbar(self, orient="vertical")
        xscroll = Scrollbar(self, orient="horizontal")

        # Plain Text widget (NOT ScrolledText) so we can have both scrollbars
        self.result = Text(
            self,
            height=height,
            width=width,
            wrap="none",                 # <-- critical: enables horizontal scrolling
            font=small_font,
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
        )

        # Wire scrollbars to Text widget
        yscroll.config(command=self.result.yview)
        xscroll.config(command=self.result.xview)

        # Layout inside this Frame
        self.result.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        # Make the text area expand with the frame
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Preserve your "next_row" placement convention
        self.grid(row=master.next_row, column=0, sticky="nsew")
        master.next_row += 1
        return


    def set(self,val):
        if val:
            val += '\n'
        else:
            val = ''
        self.result.insert(1.0,val)
        return
    def clear(self):
        self.result.delete('1.0',END)
        
class STFrame(Frame):
    def __init__(self,master,width,height):
        Frame.__init__(self,master,width=width,height=height)
        self.grid(row=master.next_row)
        master.next_row += 1
        self.next_column = 0
        return
       

