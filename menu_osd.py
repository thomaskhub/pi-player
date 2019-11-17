'''
This is the implementation of the media players on screen display
to control the playback of the media files. The main object
is the MenuOSD() class which can be added to Kivy gui applications.

This creates a 50px high button bar, under under it a 5px high
border which color can be changed to display different states of
the software, e.g. the color could be changed to differentiate
between screen saver black screen and waiting for user inout during
playlist processing.
'''
import queue
import threading
import requests
import time
import os
import logging
from multiprocessing.connection import Client
import pickle
import json

from kivy.uix.stacklayout import StackLayout
from kivy.uix.label import Label
from kivy.app import App
from kivy.core.window import Window


from selectable_items import Select, SelectButton, SelectLabel, SelectLabelBg
import includes
from volume_widget import VolumeIndicator
from ipc import Ipc
from selectable_items import Select
from key_handler import KeyHandler


class OsdController(Select):
    def enable(self, args):
        self.ipc.sendCmd({'cmd':'osdTop'},  includes.config['ipcWmPort'])
        self.ipc.sendCmd({'cmd':{'func':'resetCnt'}}, includes.config['ipcOsdPort'])

    def disable(self, args):
        self.ipc.sendCmd({'cmd':'osdBackground'}, includes.config['ipcWmPort'])

    def left(self, args):
        self.ipc.sendCmd({'cmd':'osdTop'},  includes.config['ipcWmPort'])
        self.ipc.sendCmd({'cmd':{'func':'resetCnt'}}, includes.config['ipcOsdPort'])
        self.ipc.sendCmd({'cmd':{'func':'left'}}, includes.config['ipcOsdPort'])

    def right(self, args):
        self.ipc.sendCmd({'cmd':'osdTop'},  includes.config['ipcWmPort'])
        self.ipc.sendCmd({'cmd':{'func':'resetCnt'}}, includes.config['ipcOsdPort'])
        self.ipc.sendCmd({'cmd':{'func':'right'}}, includes.config['ipcOsdPort'])

    def enter(self, args):
        self.ipc.sendCmd({'cmd':'osdTop'},  includes.config['ipcWmPort'])
        self.ipc.sendCmd({'cmd':{'func':'resetCnt'}}, includes.config['ipcOsdPort'])
        self.ipc.sendCmd({'cmd':{'func':'enter'}}, includes.config['ipcOsdPort'])

    def __init__(self):
        self.ipc = Ipc()

class MenuOSD(StackLayout, Select):
    '''On Screen Display (fixed height 50px (button height) + 5px (status border))'''
    btnPrevious = None
    btnNext = None
    btnPlay = None
    btnPaus = None
    btnStop = None
    volume = None
    colorIndicator = None
    id = None
    gap = None
    timeStep = 0.1
    thread = None
    idleCounter = 0
    #ena = True
    active = False
    ctrlQueue = None
    wId = 0
    enableDone = False
    widgets = []
    isSelectable = True

    _jsonCmdCallback = None
    cmdServer = None

    def _cmdServer(self):
        cmdServer = Ipc()
        cmdServer.serverInit(includes.config['ipcOsdPort'])

        while True:
            data = cmdServer.serverGetCmd()
            logging.error("Test001: OSD_cmdServer: data = {}".format(data))
            if 'cmd' in data:
                cmd = data['cmd']

                if cmd['func'] == "muteToggle":
                    self.muteToggle(None)

                elif cmd['func'] == "volumeUp":
                    self.volumeUp(None)

                elif cmd['func'] == "volumeDown":
                    self.volumeDown(None)

                elif cmd['func'] == "left":
                    self.left(None)

                elif cmd['func'] == "right":
                    self.right(None)

                elif cmd['func'] == "enter":
                    self.enter(None)

                elif cmd['func'] == "resetCnt":
                    self._resetCnt()


    def setColorIndicator(self, color):
        '''Set the color of the 5px high indicator border at the bottom of OSD'''
        self.colorIndicator.background_color = color

    def onEnterPlay(self, args):
        data = {}
        data['cmd'] = {'func':'play'}
        self._jsonCmdCallback(data)

    def onEnterPause(self, args):
        '''Callback function which needs to be set by parent to execute pause fct of player'''
        data = {}
        data['cmd'] = {'func':'pause'}
        self._jsonCmdCallback(data)

    def onEnterPrevious(self, args):
        '''called when previous button on OSD is pressed'''
        data = {}
        data['cmd'] = {'func':'previous'}
        self._jsonCmdCallback(data)

    def onEnterNext(self, args):
        '''called when next button on OSD is pressed'''
        data = {}
        data['cmd'] = {'func':'next'}
        self._jsonCmdCallback(data)

    def onEnterStop(self, args):
        '''This function is executed when we hit stop'''
        self.disable(None)

        data = {}
        data['cmd'] = {'func':'stop'}

        self._jsonCmdCallback(data)

    def _worker(self):
        logging.debug("MenuOSD: thread called...")

        while True:
            time.sleep(self.timeStep)
            self.idleCounter = self.idleCounter + self.timeStep

            if self.volume.muteState:
                continue

            #just limit the counter value
            if self.idleCounter > includes.config['settings']['osdTime'] and self.isVisible:
                self.idleCounter = includes.config['settings']['osdTime'] + 1
                self.wId = 0
                for wid in self.widgets:
                    wid.disable(None)

                self.isVisible = False
                self.osdCtrl.disable(None)


            if not self.ctrlQueue.empty():

                cmd = self.ctrlQueue.get()
                if cmd['cmd'] == 'resetCnt':
                    self.idleCounter = 0
                    self.isVisible = True


    def left(self, args):
        '''Logic to select next OSD element to the left from currently selected item'''

        if not self.isVisible:
            self.enable(None)
            self.wId = 0
            self.widgets[self.wId].enable(None)
            return

        self._resetCnt()

        if self.wId < len(self.widgets) and self.wId >= 0:
            if self.wId > 0:
                self.widgets[self.wId].disable(None)

            self.wId = includes.clipInt(self.wId - 1, min=0, max=4)
            self.widgets[self.wId].enable(None)

    def right(self, args):
        '''Logic to select next OSD element to the right from currently selected item'''
        if not self.isVisible:
            self.enable(None)
            self.wId = 0
            self.widgets[self.wId].enable(None)

            return

        self._resetCnt()

        if self.wId < len(self.widgets):
            self.widgets[self.wId].disable(None)

            self.wId = includes.clipInt(self.wId + 1, min=0, max=4)
            self.widgets[self.wId].enable(None)

    def _resetCnt(self):
        self.ctrlQueue.put({'cmd':'resetCnt'})


    def enable(self, args):
        self._resetCnt()
        return

    def disable(self, args):
        #self.ctrlQueue.put({'cmd':'invisible'})
        self.osdCtrl.disable(None)


    def enter(self, args):
        '''
            If OSD is visible enter will activate button press, otherwise
            enter will be forwarded to playlist controller
        '''
        if self.isVisible:
            logging.error("Thomas MenuOSD: wid = {}".format(self.wId))
            self.widgets[self.wId].onEnter(args)
        else:
            #when OSD is not active, enter button will be forwareded to the player
            #this is used to switch to the next media file in playlist mode
            if self.onPlaylistEnter is not None:
                self.onPlaylistEnter(None)

    def changeSize(self, widget, value):
        '''resize the child attributes if widht or height changes'''
        winCenter = int(Window.width / 2)
        winBoundaryLeft = winCenter - int(self.runtime.width / 2)
        winBoundaryRight = winCenter + int(self.runtime.width / 2)

        self.gap0.width = winBoundaryLeft-(5*50)
        self.gap.width = Window.width-winBoundaryRight-60

    def volumeUp(self, args):
        '''Increase the audio volume'''
        self._resetCnt()
        self.volume.volumeUp()

    def volumeDown(self, args):
        '''Decrease the audio volume'''
        self._resetCnt()
        self.volume.volumeDown()

    def muteToggle(self, args):
        '''Mute/unmute the audio'''
        self._resetCnt()
        self.volume.muteToggle()

    def _addAllWidgets(self):
        '''Add all widgets to the OSD and hide them with opacity = 0'''
        self.widgets.append(self.btnPause)
        self.widgets.append(self.btnPlay)
        self.widgets.append(self.btnStop)
        self.widgets.append(self.btnPrevious)
        self.widgets.append(self.btnNext)

        for wid in self.widgets:
             self.add_widget(wid)


        self.add_widget(self.gap0)
        self.add_widget(self.runtime)
        self.add_widget(self.gap)
        self.add_widget(self.volume)

    def __init__(self, **kwargs):
        self.id = kwargs.pop('id', None)

        if self.id is None:
            logging.error("MenuOSD: id not defined...")
            return

        self.id = int(self.id)

        super(MenuOSD, self).__init__()

        self.btnPrevious = SelectButton(
            imgPath="atlas://resources/img/pi-player/previous",
            size_hint_y=None,
            size_hint_x=None,
            height=50,
            width=50,
            id=str(3)
        )

        self.btnNext = SelectButton(
            imgPath="atlas://resources/img/pi-player/next",
            size_hint_y=None,
            size_hint_x=None,
            height=50,
            width=50,
            id=str(0)
        )

        self.btnPlay = SelectButton(
            imgPath="atlas://resources/img/pi-player/play",
            size_hint_y=None,
            size_hint_x=None,
            height=50,
            width=50,
            id=str(1),

        )


        self.btnPause = SelectButton(
            imgPath="atlas://resources/img/pi-player/pause",
            size_hint_y=None,
            size_hint_x=None,
            height=50,
            width=50,
            id=str(2)
        )

        self.btnStop = SelectButton(
            imgPath="atlas://resources/img/pi-player/stop",
            size_hint_y=None,
            size_hint_x=None,
            height=50,
            width=50,
            id=str(3)
        )


        self.runtime = SelectLabel(
            size_hint_y=None,
            size_hint_x=None,
            height=50,
            width=200,
            id=str(3),
            text="00:00:23"
        )

        winCenter = int(Window.width / 2)
        winBoundaryLeft = winCenter - int(self.runtime.width / 2)
        winBoundaryRight = winCenter + int(self.runtime.width / 2)


        self.gap0 = Label(
            size_hint_y=None,
            size_hint_x=None,
            height=50,
            width=winBoundaryLeft-(5*50),
            #background_color=(1,0,1,0.5)
        )

        self.gap = Label(
            size_hint_y=None,
            size_hint_x=None,
            height=50,
            #background_color=(0,1,1,0.5),
            width=Window.width-winBoundaryRight-60
        )


        self.volume = VolumeIndicator(
            incVal=1,
            size_hint=(None, None),
            width=50,
            height=50,
            radius=15,
            bgColor=includes.colors['gray'],
            color=includes.colors['oldblue'],
            value=0,
            mode='line'
        )

        self._addAllWidgets()

        #add a colored 5px indicator bar at the bottom of the OSD to show status
        self.colorIndicator = SelectLabelBg(
            # height=50,#includes.styles['pListIndiactorHeight'],
            # size_hint_y=None,
            size_hint_x=None,
            width=Window.width,
            background_color=includes.colors['black'],
            id="-1",
            text=""
        )

        self.add_widget(self.colorIndicator)

        self.height = 50 + 5
        self.size_hint_y = None

        self.bind(size=self.changeSize)
        self.isVisible = False

        #Thread and queue handling
        self.ctrlQueue = queue.Queue()
        self.thread = threading.Thread(target=self._worker)
        self.thread.setDaemon(True)
        self.thread.start()

        self.wId = 0
        self.osdCtrl = OsdController()

        self.btnPlay.onEnter =  self.onEnterPlay
        self.btnPause.onEnter =  self.onEnterPause
        self.btnPrevious.onEnter =  self.onEnterPrevious
        self.btnNext.onEnter = self.onEnterNext
        self.btnStop.onEnter =  self.onEnterStop

        #Server setup to control GUI elements on the OSD such as the volume indicator
        if int(self.id) < 0:
            self.serverTr = threading.Thread(target=self._cmdServer)
            self.serverTr.setDaemon(True)
            self.serverTr.start()

        # logging.error("THOMAS: setup key handler")
        # self.keyHandler = KeyHandler()
        # self.keyHandler.onPress = self._onPress

    #
    # Keyboard management
    # #
    # def _onPress(self, args):
    #     loggin.error("Key pressed menu osd.....")
    #     #if self.keyboardEnabled:
    #     scancode = args[1]
    #
    #     if scancode == 'left':
    #         self.osd.left(None)
    #
    #     elif scancode == 'right':
    #         self.osd.right(None)
    #
    #     elif scancode == 'enter':
    #         self.osd.enter(None)


class OSDMain(App):



    def jsonCmdCallback(self, data):
        ip = includes.config['httpServerIp']['ip']
        port = includes.config['httpServerIp']['port']

        url = 'http://{}:{}'.format(ip, port)
        logging.error("Request: url = {}".format(url))
        req = requests.post(url, data=json.dumps(data))

        if req.status_code != 200:
            logging.error("jsonCmdCallback: crequest error:: ret val = {}".format(req.status_code))

    '''This is just a Kivy app for testing the OSD on its own - do not rely on this!'''
    def build(self):
        self.osd = MenuOSD(id="-1")
        self.osd._jsonCmdCallback = self.jsonCmdCallback
        return self.osd


#If we start OSD as standalone we use http request to control functions
if __name__ == "__main__":
    main = OSDMain()
    #Window.size = (Window.width, 50)
    main.run()
