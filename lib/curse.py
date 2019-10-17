import curses
#import random
#from time import sleep, time
import math

class ProgressBar:
    percent = 0

    def __init__(self, height, width, offset_y=0, offset_x=0):
        self.win = curses.newwin(height, width, offset_y, offset_x)
        self.height = height
        self.width = width

    def updateProgress(self, percent):
        self.percent = percent
        self.win.addstr(0,6-len(str(int(percent)))-3,"{}%".format(int(percent)))
        self.win.addch(0,5,"|")
        percent_to_paint = min(math.ceil((percent*(self.width-10))/100),self.width-10)
        self.win.addstr(0,6,"#"*percent_to_paint)
        self.win.addch(0,self.width-4,"|")
        if self.height > 1:
            self.win.addch(0,self.width-1,"\n")
        self.win.refresh()

class Text:
    def __init__(self, height, width, offset_y=0, offset_x=0, text=""):
        self.win = curses.newwin(height, width, offset_y, offset_x)
        self.height = height
        self.width = width
        self.win.addstr(0,0,text)
        self.win.refresh()

    def updateText(self, text, offset_y=0, offset_x=0):
        self.win.addstr(offset_y,offset_x,text)
        self.win.refresh()

class draw_curses:

    def __init__(self):
        self.stdscr = curses.initscr()
        curses.noecho() # don't show keyboard input
        curses.cbreak()

    def maxHeight(self):
        return self.stdscr.getmaxyx()[0]

    def maxWidth(self):
        return self.stdscr.getmaxyx()[1]

    def add_progress_bar(self, height, width, offset_y=0, offset_x=0):
        return ProgressBar(height, width, offset_y, offset_x)

    def add_text(self, height, width, offset_y=0, offset_x=0, text=""):
        return Text(height, width, offset_y, offset_x, text)

'''percent = 0
percent_1 = 0
draw = draw_curses()
progressBar_0 = draw.add_progress_bar(1,100,0,101)
progressBar_1 = draw.add_progress_bar(2,20,4,0)
txt = draw.add_text(1,50, text="XPTO")
random.seed(time())
while percent < 100 or percent_1 < 100:
    percent += random.randint(0,10)
    percent_1 += random.randint(0,10)
    percent = min(percent, 100)
    percent_1 = min(percent_1, 100)
    progressBar_0.updateProgress(percent)
    progressBar_1.updateProgress(percent_1)
    txt.updateText(text="XPTO"+str(percent))
    sleep(1)'''
