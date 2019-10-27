import globals
from kivy.app import App
import kivy
from kivy.utils import get_color_from_hex as hexColor
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from select_listview import *
from menu_video import *
from kivy.core.window import Window
from kivy.graphics import Rectangle, Color, Line
from  subprocess import Popen, threading
import queue
import time


class MenuPlaylist(StackLayout, Select):
    _FILE_LIST = 0
    _JSON_LIST = 1
    mode = _FILE_LIST # mode 0 = json file fiew is selected, mode = 1 the list view of files in json are selected
    select = "json"
    pList = None
    workThread = None
    ctrlQueue = None


    def enable(self, args):#down
        if self.mode == self._FILE_LIST  and len(self.fileList.widgets) > 0:
            logging.info("enable/down")

            id = self.fileList.wId + 1

            if id == len(self.fileList.widgets):
                id = id - 1

            self.updateJsonFiles(self.fileList.widgets[id].text)
            ret = self.fileList.enable(None)

            return ret

        elif self.mode == self._JSON_LIST:


            self.files.enable(None)
            return False

    def disable(self,args):#up

        if self.mode == self._FILE_LIST and len(self.fileList.widgets) > 0:
            logging.info("disable/up")

            id = self.fileList.wId - 1
            if id < 0:
                id = 0


            self.updateJsonFiles(self.fileList.widgets[id].text)

            return self.fileList.disable(None)

        elif self.mode == self._JSON_LIST:
            self.files.disable({'disTop':False})
            return False

    def disableAll(self, args):
        for wid in self.fileList.widgets:
            wid.disable(None)


    def left(self, args):
        logging.debug("MenuPlayList: left called...")

        if self.mode == self._FILE_LIST:

            return True
        elif self.mode == self._JSON_LIST:
            self.mode = self._FILE_LIST

            for wid in self.files.widgets:
                wid.disable({'inc':False})
            self.files.wId = -1

            #self.fileList.enaColor = (1,0,0,1)
            tmpID = self.fileList.wId
            self.fileList.widgets[tmpID].label.color = self.fileList.enaColor
        pass

    def right(self,args):
        logging.info("rigth")
        #self.fileList.widgets[0].enaColor = [1,0,0,1]
        if self.mode == self._FILE_LIST and len(self.fileList.widgets) > 0:
            self.mode = self._JSON_LIST
            self.files.enable(None)

            tmpID = self.fileList.wId
            self.fileList.widgets[tmpID].label.color = [1,0.5,0.2,1]
        elif self.mode == self._JSON_LIST:
            pass

    def _validateJson(self,path):
        #check if number of eldn to the nodes, id must
        #accour in sequence without any gaps in between
        for i in range(len(self.pList)):
            msg = "PlayList:  id = {} / str(id) ={} / plist = {}\n".format(i, str(i), self.pList)
            logging.error(msg)
            if not (str(i) in self.pList):
                msg = "PlayList: playlist file ids not correct, stopped at id = {}\n".format(i)
                msg = msg + "\tplist = {} / i = {} \n".format(self.pList, i)
                msg = msg + "\tpath = {}".format(path)
                logging.error(msg)

                return -1

        i = 0
        for item in self.pList:
            if item != str(i):
                msg = "PlayList: playlist ids not in sequential order !\n"
                msg = msg + "\tpath = {}\n".format(path)
                msg = msg + "\tlist = {}\n".format(self.pList)
                msg = msg + "\t i = {}\n".format(i)
                logging.error(msg)
                return -2
            i = i + 1

        return 0


    def updateJsonFiles(self, text):
        path = os.path.join(globals.config[os.name]['playlist']['rootdir'], text)

        if os.path.isdir(path):
            return

        with open(path) as playFile:
            self.pList = json.load(playFile)

        if self._validateJson(path) < 0:
            logging.error("MenuPlaylist: the Json file for selected playlist is not correct")
            return

        self.files.layout.clear_widgets()
        self.files.wId = -1
        self.files.widgets = []



        for item in self.pList:
            logging.error("??????????????????: itm ;; {}".format(self.pList[item]['name']))
            self.files.add(self.pList[item]['name'], False)

        logging.error("??????????????????: number widget = {}".format(len(self.files.widgets)))


    '''
    This method will process when we press the enter key on the selected playlist.
    If we also have a specific file from the playlist selected we start playing
    from that file. This function will ensure that the last played element in
    the playlist is highlighted so that after a video is stopped we can continue
    from the same position. This function shoudl be triggered when the
    enter button is pressed while the playlist menu is active.


    The playlist is a json file which will be read with updateJsonFiles() when
    a playlist is selected. This will save the content of the playlist in a
    dictonary self.pList.

    The json file has multiple entries, where each entry starts with a id and
    then the content. The id specifies the order in which the files are being
    added to the playlist

    --> TODO: we need to change updateJsonFiles() function
    to parse the ids and rearanges them so we list them in the correct order
    independent in which order they are listed in the json file.


    The follwing example shows a playlist with a single entry, all
    paramters are case sensitive.

    {
      id:{
        "path":"mypath",
        "name": "muckel.wav",
        "post":"execute this before playback",
        "pre": "execute this after playback",
        "start":0,
        "end":0,
        "type":"audio"
      }
     }

    id:    this is an integer value defining the order in which files in playlist
            are played. It should be incremented sequentially without any gap in between
            The python app will check this and will not load the files of the json file

    path:   this is the absolute path to the media file
    name:   this is the name of the file, which will be displayed in the GUI
    pre:    here we can define a set of commands that shall be executed before a
            video starts.
                - BLACKSCREEN: will start the video on black screen, waiting for
                             for the user to press the 'enter/ok' button to start
                            playback
    post:   here we can define a set of commands that shall be executed after a
            video is played completely.
                - BLACKSCREEN: stop video on black screen,
                - PLAYNEXT: automatically plays the next file
    start: start the video from a specified time value in seconds. (not implemented yet)
    stop:  stop the video at the specified time in seconds         (not implemented yet)

    '''
    def _waitForCmd(self, key, value):
        while True:
            logging.debug("waiting for key [{}]/ value [{}]".format(key,value))

            while self.ctrlQueue.empty():
                time.sleep(0.25)
                continue

            cmd = self.ctrlQueue.get()
            logging.debug("cmd = {}".format(cmd))
            if key in cmd:
                logging.debug("key is in cmd")
                if cmd[key] == value:
                    logging.debug("key value match cmd")
                    return True



    def _processPlaylist(self):
        while True:
            time.sleep(0.25)
            logging.error("_processPlaylist: alive...")

            self._waitForCmd('key', 'enter') #blocks until  we got signal that playback is finished

            for item in self.pList:
                if int(item) < self.pListStartId:
                    continue

                
                if 'pre' in self.pList[item]:
                    logging.error("_processPlaylist: blackscreen in pre...")
                    if 'BLACKSCREEN' ==  self.pList[item]['pre']:
                        #TODO: We need to enable blackscrren here, how to do this? --> pass root to this as well?
                        self.screenmanager.current = "blackscreen"
                        self._waitForCmd('key', 'enter') #blocks until button has been pressed

                #Play the media file now...
                #Todo: How to access the player? Register player in init to local object?
                logging.debug("MenuPlayList: going to play file = {}".format(self.pList[item]['path']))
                self._waitForCmd('cmd', 'end') #blocks until  we got signal that playback is finished

                if 'post' in self.pList[item]:
                    logging.error("_processPlaylist: blackscreen in post...")
                    if 'BLACKSCREEN' ==  self.pList[item]['post']:
                        #TODO: We need to enable blackscrren here, how to do this? --> pass root to this as well?
                        self.screenmanager.current = "blackscreen"
                        self._waitForCmd('key', 'enter') #blocks until button has been pressed

                    elif 'PLAYNEXT' in self.pList[item]['post']: #just start processing the next entry of the playlist : NOTICE: the next element should not have BLACKSCRREN define in pre
                        continue


                if self.mode == self._JSON_LIST:
                    # self.files.widgets[int(item)].enable(None)
                    # self.files.widgets[int(item)-1].disable(None)
                    self.files.enable(None)

                globals.screenSaver.enable()



                logging.error("_processPlaylist: alive 1...")

            text = self.fileList.widgets[self.fileList.wId].text
            #self.updateJsonFiles(text)


        logging.error("_processPlaylist: dead...")

    def onPlayerEnd(self, args):
        self.ctrlQueue.put({'cmd':'end'})
        logging.debug("ßßßßßßßßßßßßßßßßß: enable screen saver again")


    def enter(self, args):
        logging.debug("MenuPlayList: enter callback...")


        if self.mode == self._FILE_LIST:
            if len(self.fileList.children) > 0:
                self.pListStartId = 0
                globals.screenSaver.disable()
                text = self.fileList.widgets[self.fileList.wId].text
                self.updateJsonFiles(text)
                self.ctrlQueue.put({'key':'enter'})

        elif self.mode == self._JSON_LIST:#remove all elements from the json object before current id
            logging.debug("MenuPlayList: mode = json...{}".format(self.files.wId))
            text = self.fileList.widgets[self.fileList.wId].text

            self.pListStartId = self.files.wId
            #self.updateJsonFiles(text)

            # for i in range(self.files.wId):
            #     logging.debug("MenuPlayList: try to pop..")
            #     #tmp = self.pList.pop(str(i))
            #     logging.debug("MenuPlayList:poped poped..")


            globals.screenSaver.disable()



            logging.debug("MenuPlayList: json list partial start.... {}...".format(self.pList))
            self.ctrlQueue.put({'key':'enter'})


    def __init__(self, **kwargs):


        self.id = kwargs.pop('id', None)
        self.screenmanager = kwargs.pop('screenmanager', None)
        super(MenuPlaylist,self).__init__(**kwargs)


        self.cols = 2
        self.rows = 2
        # self.padding = 0

        columnWidth0 = Window.width * 0.3
        columnWidth1 = Window.width-columnWidth0
        headerHeight = 20
        headerText0 = "[b]Playlists[/b]"
        headerText1 = "[b]Media Files[/b]"

        headerColor0 = hexColor('#5a5560')#
        headerColor1 = hexColor('#2d4159')#(0.5,0.5,0,1)

        enaColor0 = [0.5,0.5,1,1]
        enaColor1 = [1,0.5,0.2,1]

        self.header0 = self.header = SelectLabelBg(
            background_color = headerColor0,
            text_size=(columnWidth0-20,headerHeight),
            text=headerText0,
            halign="center",
            valign="middle",
            size_hint_y=None,
            size_hint_x=None,
            height=headerHeight,
            width=columnWidth0,
            id="-1",
            markup = True
        )
        self.add_widget(self.header0)

        self.header1 = self.header = SelectLabelBg(
            background_color = headerColor1,
            text_size=(columnWidth0-20,headerHeight),
            text=headerText1,
            halign="center",
            valign="middle",
            size_hint_y=None,
            size_hint_x=None,
            height=headerHeight,
            width=columnWidth1,
            id="-1",
            markup = True
        )

        self.add_widget(self.header1)



        self.fileList = FileList(
            id=str(int(self.id)+1),
            rootdir=globals.config[os.name]['playlist']['rootdir'],
            enaColor=enaColor0,
            bar_width=10,
            size_hint_x=None,
            width=columnWidth0,
            supportedTypes=globals.config[os.name]['playlist']['types'],
            screenmanager=self.screenmanager,
            fillerColor=headerColor0,
            showDirs=False,
            selectFirst=False
        )

        self.files = PlaylistJsonList(
            id=str(int(self.id) + 5000),
            enaColor=enaColor1,
            bar_width=10,
            size_hint_x=None,
            width=columnWidth1,
            fillerColor=headerColor1,
        )


        self.add_widget(self.fileList)
        self.add_widget(self.files)

        self.mode = self._FILE_LIST

        #Fill the select List View with elements from the first json file
        # logging.debug("MenuVideo: before widget list iteration... len = {}".format(self.fileList.widgets))
        # for item in self.fileList.widgets:
        #     logging.debug("MenuVideo: found item in widgets item = {}".format(item))
        #     if "..." in item.text:
        #         continue
        #     elif item.text.endswith('.json'): #TODO this is not nicely implemented,
        #         self.updateJsonFiles(item.text)

        self.workThread = threading.Thread(target = self._processPlaylist)
        self.workThread.setDaemon(True)
        self.workThread.start()
        self.ctrlQueue = queue.Queue()
