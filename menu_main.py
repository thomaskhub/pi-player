'''
This is the main menu using the Kivy frame work. All other Gui Elements
are added here. This code is also respnisble for setting up keyhandling
and key processing for all selectable elements in the GUI
'''
import logging
import os
import  http.server
import threading
import subprocess

from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.stacklayout import StackLayout
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition

import control_tree
import includes

from selectable_items import SelectableTabbedPanelHeader
from screensaver import ScreenSaver
from menu_settings import MenuSettings
from menu_video import FileList
from menu_osd import MenuOSD, OsdController
from menu_playlist import MenuPlaylist
from key_handler import KeyHandler
from dialog import DialogHandler
from menu_system import MenuSystem
from control_tree import selectId as selectId
import server

class IshaGui(StackLayout):
    '''This is the top object of the Gui'''
    osd = None

    def resize(self, widget, value):
        '''resize callback when width/height are chaning'''
        self.screens.height = Window.height - self.osd.height

    def __init__(self, **kwargs):
        super(IshaGui, self).__init__(**kwargs)

        self.osd = MenuOSD(id=str(selectId['osd']))
        self.screens = IshaPiScreens(osd=self.osd)

        self.screens.size_hint_y = None
        self.screens.height = Window.height - self.osd.height

        self.add_widget(self.screens)
        #TODO add this back:: self.add_widget(self.osd)

        self.bind(height=self.resize)

class IshaPiScreens(ScreenManager):
    '''
    The screen manager allows us to swith between multiple defined scrrens.
    This feature is used to implement:
        1: Main menu
        2: Screen Saver black screen
        3: OSD for videos
    '''
    menuOSD = None
    menuScreen = None
    menuScreenSaver = None
    menuOSDScreen = None
    osd = None

    def __init__(self, **kwargs):
        self.osd = kwargs.pop('osd', None)

        super(IshaPiScreens, self).__init__(**kwargs)

        self.transition = NoTransition()
        self.menuScreenSaver = Screen(name="blackscreen")
        self.menuScreen = Screen(name="main_menu")

        self.mainMenu = Menu(root=self, osd=self.osd)
        self.menuScreen.add_widget(self.mainMenu)
        self.add_widget(self.menuScreen)
        self.add_widget(self.menuScreenSaver)
        self.current = "main_menu"


class Menu(StackLayout, TabbedPanel):
    '''This is the tab view pannel which will show all gui lements except the OSD'''
    selectableWidgets = {}
    tbHeads = []
    curId = 100
    lastId = None
    root = None
    screenSaver = None
    menuOSD = None
    serverSemaphore = threading.Semaphore()


    def _globalKeyHandler(self, keycode):
        """Key handler for global keys like volume up / volume down /mute etc."""

        if keycode[1] == "+":
            data = {}
            data['cmd'] = {'func':'volumeUp'}
            self._jsonCmdCallback(data)
            return

        if keycode[1] == "-":
            data = {}
            data['cmd'] = {'func':'volumeDown'}
            self._jsonCmdCallback(data)
            return

        if keycode[1] == "m":
            data = {}
            data['cmd'] = {'func':'muteToggle'}
            self._jsonCmdCallback(data)
            return

    _keyHandledMextId = False
    def _keyHanlder(self, cmdList):
        #cmdList is a list of dictonaries containing the command being executed
        #cmdList can be specified as None in control tree which means nothing to do
        if cmdList is None:
            return

        for cmd in cmdList:

            #Check if cmd is also a list, if so recursively we will execute
            #logging.debug("_keyHandler: going to execute command = {}".format(cmd))
            if isinstance(cmd, list):
                self._keyHanlder(cmd)
                continue

            #last entry, this will stop execution
            if 'nextid' in cmd and  not self._keyHandledMextId:
                self._keyHandledMextId = True
                self.curId = cmd['nextid']
                return

            if not all(k in cmd for k in ("id", "func")):
                cmd = "_keyHandler: You did not specify id/func for tree elemnt "
                cmd = cmd + "with id = {} ".format(self.curId)
                logging.error(cmd)
                return

            tmpId = cmd['id']
            func = cmd['func']

            #args attribute is optional, can be used when we want to pass something to callback
            args = {}
            if 'args' in cmd:
                args = cmd['args']

            #add user defined arguments of selectable widget to args passed to callback
            if self.selectableWidgets[tmpId].user is not None:
                for item in self.selectableWidgets[tmpId].user:
                    args[item] = self.selectableWidgets[tmpId].user[item]

            #Execute build in fucntions/object functions
            if func == "switch":#build-in-switch-tabpannel
                self.switch_to(self.selectableWidgets[tmpId], False)
            else:
                ret = getattr(self.selectableWidgets[tmpId], func)(args)

                if ret and 'true' in cmd: #execute ret functions if specified
                    self._keyHanlder(cmd['true'])

                if not ret and 'false' in cmd: #execute ret functions if specified
                    self._keyHanlder(cmd['false'])

	# This is not for enabling or disabling OSD but rather for playback
    # mode or non playback mode. When playback mode is over we should give control
    # back to the last selected element befor strting a video / audio /playlist
    def osdDisable(self, args):
        '''Switch control back to last element after OSD was displayed'''
        self.curId = self.lastId

    def osdEnable(self, args):
        '''Before switching to the OSD remember the current selected element'''
        self.lastId = self.curId
        self.curId = selectId['osd']


    # Callback function triggered by the key handler. This is triggered when
    #keyboard key is pressed.
    def _keyDown(self, keycode):
        '''Callback function for keyboard events. All key handling is done here.'''
        if self.screenSaver.active and self.screenSaver.ena:
            self.screenSaver.resetTime()
            return 0

        self.screenSaver.resetTime()

        msg = "Menu: Key Pressed [{}] ".format(keycode)
        msg = msg + "on element with curId = {}".format(self.curId)
        logging.debug(msg)

        self._globalKeyHandler(keycode)

        if keycode[1] in self.controlTree[self.curId]:
            self._keyHandledMextId = False #prepare keyHandler function
            self._keyHanlder(self.controlTree[self.curId][keycode[1]])
            return 0

        return -1

    def _findSelectableChildren(self, children):
        if not children:
            return

        for child in children:
            try:
                self._findSelectableChildren(child.children)
                if child and child.isSelectable:
                    self.selectableWidgets[int(child.id)] = child
            except Exception as allExceptions:
                pass



    def _onUpdateRunTime(self, value):
        self.osd.runtime.text = value

    def _warningPlay(self, args):
        logging.error("Warning: play somthing something something")


    def __init__(self, **kwargs):
        self.root = kwargs.pop('root', "None")
        self.osd = kwargs.pop('osd', "None")

        kwargs["do_default_tab"] = False #always disable the default tab
        super(Menu, self).__init__(**kwargs)

        tmp = KeyHandler()
        tmp.onPress = self._keyDown

        #Setup tabview for main menu
        self.tab_width = 150 + 10
        self.tab_height = 60


        self.selectableWidgets[selectId['settings']] = SelectableTabbedPanelHeader(
            id=str(selectId['settings']),
        )
        self.selectableWidgets[selectId['settings']].background_normal = "atlas://resources/img/pi-player/settings"
        self.selectableWidgets[selectId['settings']].background_down = "atlas://resources/img/pi-player/settings_select"

        self.selectableWidgets[selectId['videos']] = SelectableTabbedPanelHeader(
            id=str(selectId['videos']),
        )
        self.selectableWidgets[selectId['videos']].background_normal = "atlas://resources/img/pi-player/video"
        self.selectableWidgets[selectId['videos']].background_down = "atlas://resources/img/pi-player/video_select"


        self.selectableWidgets[selectId['music']] = SelectableTabbedPanelHeader(
            id=str(selectId['music']),
        )
        self.selectableWidgets[selectId['music']].background_normal = "atlas://resources/img/pi-player/music"
        self.selectableWidgets[selectId['music']].background_down = "atlas://resources/img/pi-player/music_select"


        self.selectableWidgets[selectId['playlist']] = SelectableTabbedPanelHeader(
            id=str(selectId['playlist']),
        )
        self.selectableWidgets[selectId['playlist']].background_normal = "atlas://resources/img/pi-player/playlist"
        self.selectableWidgets[selectId['playlist']].background_down = "atlas://resources/img/pi-player/playlist_select"

        self.selectableWidgets[selectId['system']] = SelectableTabbedPanelHeader(id=str(selectId['system']))

        self.selectableWidgets[selectId['system']].background_normal = "atlas://resources/img/pi-player/power"
        self.selectableWidgets[selectId['system']].background_down = "atlas://resources/img/pi-player/power_select"


        #for i in range(len(self.selectableWidgets)):
        self.add_widget(self.selectableWidgets[selectId['system']])
        self.add_widget(self.selectableWidgets[selectId['videos']])
        self.add_widget(self.selectableWidgets[selectId['music']])
        self.add_widget(self.selectableWidgets[selectId['playlist']])
        self.add_widget(self.selectableWidgets[selectId['settings']])

        self.selectableWidgets[selectId['settings']].content = MenuSettings()

        #Setup Video menu
        self.selectableWidgets[selectId['vFile']] = FileList(
            id=str(selectId['vFile']),
            rootdir=includes.config['video']['rootdir'],
            enaColor=includes.styles['enaColor0'],
            bar_width=10,
            size_hint=(1, None),
            size=(Window.width, Window.height),
            supportedTypes=includes.config['video']['types'],
            screenmanager=self.root,
            selectFirst=False,
            type="video"
        )
        self.selectableWidgets[selectId['videos']].content = self.selectableWidgets[selectId['vFile']]

        #Setup Audio menu
        self.selectableWidgets[selectId['mFiles']] = FileList(
            id=str(selectId['mFiles']),
            rootdir=includes.config['audio']['rootdir'],
            enaColor=includes.styles['enaColor0'],
            bar_width=10,
            size_hint=(1, None),
            size=(Window.width, Window.height),
            supportedTypes=includes.config['audio']['types'],
            screenmanager=self.root,
            selectFirst=False
        )
        self.selectableWidgets[selectId['music']].content = self.selectableWidgets[selectId['mFiles']]

        #Setup Playlist menu
        self.selectableWidgets[selectId['pFiles']] = MenuPlaylist(
            id=str(selectId['pFiles']),
            screenmanager=self.root
        )
        self.selectableWidgets[selectId['pFiles']].osdEnable = self.osdEnable
        self.selectableWidgets[selectId['pFiles']].osdDisable = self.osdDisable
        self.selectableWidgets[selectId['pFiles']].osdColorIndicator = self.osd.setColorIndicator
        self.selectableWidgets[selectId['playlist']].content = self.selectableWidgets[selectId['pFiles']]

        #Setup the menu for system notifications and system operations like shutdown
        self.menuSystem = MenuSystem()
        self.selectableWidgets[selectId['system']].content = self.menuSystem
        self.selectableWidgets[selectId['systemMsg']] = self.menuSystem.handler
        self.selectableWidgets[selectId['systemBtn']] = self.menuSystem.btn

        #Find all the children which are selectble and can be controlled by keyboard
        #TODO: If we simplify the settings menu then we can remove this. One ID per
        #window has been enought so far and we give the window itself the responsibility
        #Of selecting the right elements depending on key press. This makes the controll_tree
        #more simplistic and settings creen is anyway not proper
        self._findSelectableChildren(self.selectableWidgets[selectId['settings']].content.children)
<<<<<<< HEAD
        self._findSelectableChildren(self.selectableWidgets[selectId['videos']].content.children)
        self.selectableWidgets[selectId['osd']] = OsdController() #TODO: see if this ican be remover :: self.osd
=======
>>>>>>> remote-keyboard

        #TODO: this OSD should be replaced by a different version of OSD wich
        #only shows the volume indicator. Maybe we can implement an option
        #which replaces all buttons with a label as a placeholder
        self.selectableWidgets[selectId['osd']] = self.osd


        #Get the globally defined controll tree used for processing keystrokes
        self.controlTree = control_tree.CONTROL_TREE

        #set the first Tab to be selected, which is the system tab
        self.curId = selectId['system'] # set start id

        #
        # Dynamic modifications to the controll tree if needed
        #
        #do not allow down press on empty list
        if len(self.selectableWidgets[selectId['mFiles']].layout.children) <= 0:
            self.controlTree[2]['down'] = None

        #Try to enable the start widget
        try:
            self.selectableWidgets[self.curId].enable(None)
        except Exception as allExceptions:
            logging.error("Menu: cannot find default widget...")

        #setup the screen saver and also make it available as global object
        self.screenSaver = ScreenSaver(self.root, "blackscreen", "main_menu")
        self.screenSaver.enable()
        includes.screenSaver = self.screenSaver

        #set player callbacks
        includes.player.onPlayEnd = self.selectableWidgets[selectId['pFiles']].onPlayerEnd
        includes.player._onUpdateRunTime = self._onUpdateRunTime

<<<<<<< HEAD
        #Setup OSD callback for passing enter command to playlist
        # self.osd.onPlaylistEnter = self.selectableWidgets[selectId['pFiles']].enter
        # self.osd.btnPlay.onEnter =  self.selectableWidgets[selectId['pFiles']].play
        # self.osd.btnPause.onEnter =  self.selectableWidgets[selectId['pFiles']].pause
        # self.osd.btnPrevious.onEnter =  self.selectableWidgets[selectId['pFiles']].previous
        # self.osd.btnNext.onEnter =  self.selectableWidgets[selectId['pFiles']].next
        # self.osd.btnStop.onEnter =  self.selectableWidgets[selectId['pFiles']].abort

=======
>>>>>>> remote-keyboard
        #Setup video/audio view callbacks
        tmp = self.selectableWidgets[selectId['pFiles']].startVirtualSingle
        self.selectableWidgets[selectId['vFile']]._onEnterPlayer = tmp
        self.selectableWidgets[selectId['mFiles']]._onEnterPlayer = tmp

        #webserver for remote control
        self._cmdInitCallbackHandler()
        self.serverThread = threading.Thread(target=self._jsonServer)
        self.serverThread.setDaemon(True)
        self.serverThread.start()

        self.osd._jsonCmdCallback = self._jsonCmdCallback
        self.osd.onPlaylistEnter = self.selectableWidgets[selectId['pFiles']].enter


        #Set default system values such as volume etc.
        data = {}
        data['cmd'] = {'func':'setVolume', 'args':'100'}
        self._jsonCmdCallback(data)

    #---------------------------------------------------------------------------
    # Callback functions for contriling the system like the player etc.
    #---------------------------------------------------------------------------
    def _cmdMuteToggle(self, args):
        self.osd.volume.muteToggle() #TODO: This should not be in OSD as we have OSD and dummy osd....
        subprocess.run(['amixer', 'sset', '\'Master\'', str(self.osd.volume.value), '> /dev/null'])

    def _cmdSetVolume(self, args):
        try:
            self.osd.volume.value = int(args)
            subprocess.run(['amixer', 'sset', '\'Master\'', str(self.osd.volume.value), '> /dev/null'])
        except TypeError as e:
            logging.error("setVolume: " + str(e))

    def _cmdVolumeUp(self, args):
         self.osd.volumeUp(None) #TODO: This should not be in OSD as we have OSD and dummy osd....
         subprocess.run(['amixer', 'sset', '\'Master\'', str(self.osd.volume.value), '> /dev/null'])

    def _cmdVolumeDown(self, args):
         self.osd.volumeDown(None) #TODO: This should not be in OSD as we have OSD and dummy osd....
         subprocess.run(['amixer', 'sset', '\'Master\'', str(self.osd.volume.value), '> /dev/null'])

    def _cmdInitCallbackHandler(self):
        self.funcList = {}
        self.funcList['muteToggle'] = {'call':self._cmdMuteToggle, 'args':None}
        self.funcList['setVolume'] = {'call':self._cmdSetVolume, 'args':None}
        self.funcList['volumeUp'] = {'call':self._cmdVolumeUp, 'args':None}
        self.funcList['volumeDown'] = {'call':self._cmdVolumeDown, 'args':None}
        self.funcList['play'] = {'call':self.selectableWidgets[selectId['pFiles']].play, 'args':None}
        self.funcList['pause'] = {'call':self.selectableWidgets[selectId['pFiles']].pause, 'args':None}
        self.funcList['previous'] = {'call':self.selectableWidgets[selectId['pFiles']].previous, 'args':None}
        self.funcList['next'] = {'call':self.selectableWidgets[selectId['pFiles']].next, 'args':None}
        self.funcList['stop'] = {'call':self.selectableWidgets[selectId['pFiles']].abort, 'args':None}


    def _jsonCmdCallback(self, data):
        """
        This function is the only function that has control over the application
        As this is the http server callback where recieved json commands will be
        passed towards. All other modules should request functions via the json
        rpc server with local socket connection. This way handling race conditions
        remote and local control will be eaiser.

        This is thread save so it cannot only be called from the server but from
        all components within the main menu if they want to. For example "+", "-"
        and mute button are calling this function so volume can potentially be set with less
        latency.

        TODO: The old OSD will be replaced by a shadow OSD which only contains the
              volumen widget as of now.
        TODO: Remove all OSD callbacks and implement the corresponding functionality
             with the webinterface.
         """
        self.serverSemaphore.acquire()
        if includes.isRemoteCtrlCmd(data): # check if valid command or not
            cmd = data['cmd']

            if 'args' in cmd:
                args = cmd['args']
            else:
                args = None

            self.funcList[cmd['func']]['call'](args)

            ret = {}
            ret['status'] = "ok"

            self.serverSemaphore.release()
            return ret


    def _jsonServer(self):
        ip = includes.config['httpServerIp']['ip']
        port = includes.config['httpServerIp']['port']
        self.httpd = http.server.HTTPServer((ip, int(port)), server.WebServer)
        server.cmdCallback = self._jsonCmdCallback

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.httpd.server_close()
