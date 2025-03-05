import wx
import wx.grid
import gen2_main as handle
import gen2_logging as log
import time
import os
import  traceback
import wx.adv
import configparser as CP
import gen2_config_settings as gen2_config




parser = CP.ConfigParser()
parser.read(gen2_config.INI_FILE)


log.logging.debug( 80*('*') )
localtime = time.asctime( time.localtime(time.time()) )
log.logging.debug("localtime %s" % localtime)

'''
Dominic Vagnone:

Log cather gui interface
08/09/2021: Added SetLogFile Destination File->SetDestinationZipFile. User can now select where the destination zip archive goes.
'''

APP_NAME = "SIGNIA_TRANSFER_PROGRAM"
VERSION = "1.002"
DV_DEBUG = True


log.logging.debug( 80*('*') )
localtime = time.asctime( time.localtime(time.time()) )
log.logging.debug("localtime %s" % localtime)

# Some classes to use for the notebook pages.  
QUE_MSG_TIMEOUT = 40       #max amount of time bettween handle messages
ID_ADDR = 1000
ID_EXIT = ID_ADDR+1
ID_FIND_HANDLE = ID_ADDR+2
ID_SET_DESTINATION = ID_ADDR+3
ID_HELP        = ID_ADDR+4
ID_ABOUT        = ID_ADDR+5


ID_STATE_UPDATING      ="Update"
ID_STATE_INITIALIZE    = "Initialize"
ID_STATE_ACRHCIVING    = "Archiving"
ID_STATE_ENDED          = "Ended"
ID_STATE_TIMEOUT        = "Timeout"


GRID_COLS_NAMES =  ["USB\nPORT", "STATUS", "SERIAL\nNUMBER", "HARDWARE \nVER", "FIRE\nCOUNT", "PROCEDURE\nCOUNT"]
GRID_COLS_WIDTHS = [80, 220, 250, 90, 70,80]



#-------------------------------        
class TextPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        t = wx.StaticText(self, -1, "This is a PageOne object", (20,20))

 #------------------------------------
class MyGrid(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, -1)
        self.nbr_cols = len(GRID_COLS_NAMES)
        self.CreateGrid(0,self.nbr_cols)
        
        self.SetColLabelSize(50)
#                attrib.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD))
#        attrib.SetAlignment(wx.ALIGN_CENTER, wx.ALIGN_BOTTOM)
#        self.SetDaultFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD) )
        self.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_BOTTOM)
#        self.CreateGrid(9, 3)

        for ii in  range(self.nbr_cols):
            self.SetColLabelValue(ii, GRID_COLS_NAMES[ii])
            self.SetColSize (ii, GRID_COLS_WIDTHS[ii])
            
 #------------------------------------
class NoteBook(wx.Notebook):
    def __init__(self, parent, id):
        wx.Notebook.__init__(self, parent, id)

        self.parent = parent
        style = wx.NB_TOP
        self.parent = parent
        #self.usbs_in_use=[]
        self.dct_port={}
#        self.dct_port =  {'status':'my state', 'serial_num': None, 'port_num': None, 'row': None, "thread_ptr":None, "last_update":None}  # the port id is the key
        self.my_que_msg = []    #list of queue msgs from threads
        
        try:
            self.Do_ReadINI_File()
            log.logging.debug("NoteBook: self.serial_nbr_file: %s" % self.serial_nbr_file)
            self.parser_serial_nbr = CP.ConfigParser()
            self.parser_serial_nbr.read( self.serial_nbr_file)
        
        except:
            log.logging.debug( "Traceback %s" % traceback.format_exc() )

        
        
        # create the page windows as children of the notebook
        self.my_grid = MyGrid(self)
        # add the pages to the notebook with the label to show on the tab
        self.AddPage(self.my_grid, "Handle-Status")

        self.com_status_txt = TextPage(self)
        self.AddPage(self.com_status_txt, "Communications Status")
        self.task_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.On_task_timer, self.task_timer)
        self.task_timer.Start(1000)
        
    #---------------------------
    def Do_ReadINI_File(self):
        '''
            Read the ini file, reset variables from INI file
            
        '''
        parser.read(gen2_config.INI_FILE)
 
        if parser.has_option("files",gen2_config.LOG_FILE_DESTINIATION_OPTION):
            self.log_destination = parser.get("files",gen2_config.LOG_FILE_DESTINIATION_OPTION)
        else:
            self.log_destination = "C:\\Users\\"
            gen2_config.Update_IniFile(gen2_config.INI_FILE, parser, section="files",  option=gen2_config.LOG_FILE_DESTINIATION_OPTION, value=self.log_destination)
            
        #ensure the dest_dir is terminated with correclty    
        if self.log_destination[-1] != "\\":
            self.log_destination = self.log_destination + "\\"
        
        if parser.has_option("files",gen2_config.HISTORY_FILE_OPTION):
            self.history_file = parser.get("files",gen2_config.HISTORY_FILE_OPTION)
        else:
            self.history_file = "C:\\Users\\signia_transfer_program.ini"
            gen2_config.Update_IniFile(gen2_config.INI_FILE, parser, section="files",  option=gen2_config.HISTORY_FILE_OPTION, value=self.history_file)



        if parser.has_option("files", gen2_config.SERIAL_NBR_FILE_OPTION):
            self.serial_nbr_file = parser.get("files",gen2_config.SERIAL_NBR_FILE_OPTION)
        else:
            self.serial_nbr_file = "serial_nbr_file.ini"
            gen2_config.Update_IniFile(gen2_config.INI_FILE, parser, section="files",  option=gen2_config.SERIAL_NBR_FILE_OPTION, value = self.serial_nbr_file)


        self.parent.status_bar.SetStatusText("Log Dir: " + self.log_destination, 0)
    #---------------------------
    def Do_AddNewUBSPort(self, port):
        '''
            Add the given port to the grid and our internal dictionary of ports
            Handle isnt communicating therfore : serial_num, hardware_ver aren't available,
            They should show up in the Update  messages
        '''
        self.my_grid.AppendRows(1)
        new_row = self.my_grid.GetNumberRows() -1
        self.my_grid.SetRowSize(new_row, 60)
        # attrib = wx.grid.GridCellAttr()

        # attrib.SetFont(wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD))
        # attrib.SetAlignment(wx.ALIGN_CENTER, wx.ALIGN_BOTTOM)
        # self.my_grid.SetRowAttr(new_row, attrib)
        
        if not self.dct_port.get(port):
            self.dct_port[port] = {'status':"New Connection",  "serial_num": None, 
                                   "port_num": port, "row": new_row,\
                                    "last_update":time.time(),\
                                    "last_log_file":None,\
                                    "hardware_ver":None, "state":ID_STATE_INITIALIZE}  # the port id is the key


            self.dct_port[port]["thread_ptr"] = handle.ProducerThread(name='HandleCommunications_%s' % port,\
                                                    port_num = port, log_dest = self.log_destination,\
                                                    history_file = self.history_file,  config_parser = self.parser_serial_nbr)
            
            self.dct_port[port]["thread_ptr"].start()
            #write the new port the grid, start the thread, the thread handle will report its serial  number first
            self.WriteGrid( new_row , self.dct_port[port], None, None )
        else:
            log.logging.debug("Do_AddNewUBSPort Error: duplicate key: %s " % (self.dct_port[port]))
            
            
    #---------------------------
    def Do_ProcessQueueMsg(self):
        '''
            Iterate thru the msg, set the grids background color to match the message 
            Write the lastest msgs to the gird, port, nbr logs, serial_num
        '''
        try:
        
            while len(self.my_que_msg ) > 0:
                mbx_msg = self.my_que_msg.pop(0)
                log.logging.debug("Do_ProcessQueueMsg: new mbx_msg %s" % mbx_msg)
                
                nbr_logs_downloaded = mbx_msg["status"]["nbr_logs"]
                serial_num  =   mbx_msg["status"]["serial_num"]
                hardware_ver =  mbx_msg["status"]['hardware_ver']
                cur_log_name =  mbx_msg["status"]['log_name']
                
                port        = mbx_msg["port_num"]
                new_msg     = mbx_msg["msg"]
                

                
                dest_dir     = mbx_msg["dest_dir"]
                total_log_count = mbx_msg["total_log_count"]
                
# {'status':  {  'stat': None,   'log_name': '\\data\\data_000001\\000023\\eventLog.txt', 
#             'hardware_ver': '1.0', 'serial_num': '7BF8F1C000000E5', 'offset': 0, 
#             'nbr_logs': 162, 'history': []   },
 
#             'name': 'HandleCommunications_5', 
#             'total_log_count': 5655, 'port_num': '5', 'msg': 'Update', 
#             'use_counts': { 'procedure_count': 8, 'prodedure_limit': 59367, 'fire_count': 51, 'fire_limit': 999 }, 
#             'dest_dir': 'C:\\Users\\vagnod2\\Documents\\'}
 
                attr = wx.grid.GridCellAttr()
                log.logging.debug("self.dct_port: %s" % self.dct_port)
                
                
                if serial_num == None or len(serial_num) < 3:
                    raise Exception('Do_ProcessQueueMsg: error in serial nbr: (%s)' % (serial_num))
                
                if self.dct_port.has_key(port):   
                    '''
                    exptd msg 
                     {'name': 'HandleCommunications_18', 'port_num': '18', 'serial_num': '7541808000000E4', 'nbr_logs': 3307, 'dest_dir': 'C:\\Users\\vagnod2\\Documents\\', 'msg': 'Update'}

                    '''
                    unknown_msg = True
                    
                    if "Update" in new_msg:
                        self.dct_port[port]["last_update"] = time.time() #remeber last time port was updated
                        self.dct_port[port]["state"] = ID_STATE_UPDATING
                        self.dct_port[port]["last_log_file"] = cur_log_name

                        
                        gen2_config.Update_IniFile(self.serial_nbr_file, self.parser_serial_nbr, serial_num, "last_log", cur_log_name)
                        gen2_config.Update_IniFile(self.serial_nbr_file, self.parser_serial_nbr, serial_num,"status", ID_STATE_UPDATING)
                        
                        attr.SetBackgroundColour(wx.GREEN)
                        status = "Waiting for download: %s\n Logs downloaded: %s" % (total_log_count, nbr_logs_downloaded)


                        # self.WriteGrid( self.dct_port[port]["row"],\
                        # {"port_num":self.dct_port[port]["port_num"],  "status":"Okay to disconnect" % mbx_msg["nbr_logs"],\
                        # "serial_num":mbx_msg["serial_num"],  "hardware_ver":mbx_msg["hardware_ver"]}, attr )

                    elif "Starting" in new_msg:
                        self.dct_port[port]["last_update"] = time.time() #remeber last time port was updated
                        self.dct_port[port]["state"] = ID_STATE_INITIALIZE
                        self.dct_port[port]["last_log_file"] = ""
                        

                        status = "Handle Searching for logs:\n (%s) found" % total_log_count
                    
                    
                    elif "Done" in new_msg:
                        self.dct_port[port]["last_update"] = time.time() #remeber last time port was updated
                        self.dct_port[port]["state"] = ID_STATE_ACRHCIVING        
                        self.dct_port[port]["last_log_file"] = ""

                        gen2_config.Update_IniFile(self.serial_nbr_file, self.parser_serial_nbr, serial_num, "last_log", "")
                        gen2_config.Update_IniFile(self.serial_nbr_file, self.parser_serial_nbr, serial_num, "status", ID_STATE_ACRHCIVING)
                      
                        handle.Do_LogFileZip(  {"nbr_logs": nbr_logs_downloaded, "dest_dir":dest_dir,  "serial_num":serial_num} ) 
                        attr.SetBackgroundColour(wx.LIGHT_GREY)
                        status = "Log files achived/zipped\n waiting disconnect"
                        
                        handle.SendMsgToThrd({"msg":"Exit", "port_num":port, "serial_num":serial_num} )


                        #rember file is completed an zipped
                        
                        log.logging.debug("Done localtime: serial_num:%s, %s" % (serial_num, time.time()) )
 
                    elif "ExitResponse" in new_msg:
                        attr.SetBackgroundColour(wx.LIGHT_GREY)
                        self.dct_port[port]["state"] = ID_STATE_ENDED  
                        status = "Communications has ended"
                        # self.WriteGrid( self.dct_port[port]["row"],\
                        # {"port_num":self.dct_port[port]["port_num"],  "status":"Okay to disconnect" % mbx_msg["nbr_logs"],\
                        # "serial_num":mbx_msg["serial_num"],  "hardware_ver":mbx_msg["hardware_ver"]}, attr ) 
                        gen2_config.Update_IniFile(self.serial_nbr_file, self.parser_serial_nbr, serial_num, "last_log", "")
                        gen2_config.Update_IniFile(self.serial_nbr_file, self.parser_serial_nbr, serial_num, "status", ID_STATE_ENDED)
                      

                    else:
                        assert(new_msg == "XYZ")
                        log.logging.debug("Do_ProcessQueueMsg: Error Unknown msg from thread: %s" % mbx_msg)
                        attr.SetBackgroundColour(wx.RED)
 

                    self.WriteGrid( self.dct_port[port]["row"],\
                        {"port_num":self.dct_port[port]["port_num"],  "status":"%s" % status,\
                        "serial_num":serial_num,  "hardware_ver":hardware_ver}, mbx_msg ,attr ) 

                else:
                    log.logging.debug("Do_ProcessQueueMsg: Unknown Key : %s" % mbx_msg)
                    

        except:
            log.logging.debug( "Traceback %s" % traceback.format_exc() )

        

    #---------------------------
    def WriteGrid( self,row,  dct={"port_num":None, "status":None, "serial_num":None, "hardware_ver":None}, dct_usage=None,attrib=None ):
        if attrib == None:
            attrib = wx.grid.GridCellAttr()

        attrib.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD))
        attrib.SetAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)

        self.my_grid.SetRowAttr(row, attrib)
        
        self.my_grid.SetCellValue(row,0, str( dct["port_num"]) )
        self.my_grid.SetCellValue(row,1, str( dct["status"]) )
        self.my_grid.SetCellValue(row,2, str( dct["serial_num"]) )
        self.my_grid.SetCellValue(row,3, str( dct["hardware_ver"]) )
        
        if dct_usage != None:
            if dct_usage["use_counts"].has_key("fire_count"):
                self.my_grid.SetCellValue(row,4, str( dct_usage["use_counts"]["fire_count"]) )
            
            if dct_usage["use_counts"].has_key("procedure_count"):
                self.my_grid.SetCellValue(row,5, str( dct_usage["use_counts"]["procedure_count"]) )

    #---------------------------
    def Do_ScanForNewConnection(self):
        '''
            Do_ScanForNewConnection: Scan the usb ports
            Check each port and see if its new
        '''
        log.logging.debug( "Do_ScanForNewConnection:start" )
        usbs = handle.scan_usb()
        if DV_DEBUG:
            usbs=["10"]
            log.logging.debug( "Do_ScanForNewConnection:start" )
            
        for usb_port in usbs:
            if usb_port not in self.dct_port.keys():
            
                new_usb_port = "".strip(usb_port)
                
                self.Do_AddNewUBSPort(usb_port)
    #---------------------------
    def Do_CheckForQueueMsg(self):
        
        log.logging.debug("Do_CheckForQueueMsg USB_MsgQueue size %s" % str(handle.USB_MsgQueue.qsize()) ) 
 
        try:
            while not handle.USB_MsgQueue.empty():
                item = handle.USB_MsgQueue.get()
                self.my_que_msg.append(item)
        except:
            log.logging.debug("%s" % traceback.format_exc() ) 

        log.logging.debug("Do_CheckForQueueMsg : my_que_msg size %s"  %  len( self.my_que_msg) )
        
    #---------------------------
    def Do_CheckForPortTimouts(self, time_out_parm=QUE_MSG_TIMEOUT):
        '''
            iterate thru the handles check update msgs.
        '''
        for key in self.dct_port.keys():
            if (self.dct_port[key]["last_update"] == None):
                self.dct_port[key]["last_update"] = time.time()
            
            

            if (self.dct_port[key]["state"] == ID_STATE_UPDATING):
                #skip timeout process for handles that have ended or are archiving
                lst_update = self.dct_port[key]["last_update"]
                log.logging.debug("lst_update: %s" % lst_update )
                
                row = self.dct_port[key]["row"]
                                        

                
                #put an * as heartbeat indicator
                txt = self.my_grid.GetCellValue(row, 0)
                txt = txt.strip()
                txt = txt.replace("*","")
                
                mark = "" if(int(time.time()) & 0x02) else "*"
                self.my_grid.SetCellValue(row, 0, txt + " " +mark)
                
                
                if abs(lst_update - time.time()) > time_out_parm:
                    if self.dct_port[key]["state"] != ID_STATE_TIMEOUT:
                        self.dct_port[key]["state"] = ID_STATE_TIMEOUT
                        
                        attrib = wx.grid.GridCellAttr()
                        attrib.SetBackgroundColour(wx.YELLOW)
               
                        attrib.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD))
                        attrib.SetAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
                        
                        self.my_grid.SetRowAttr(row, attrib)
                        
                        txt = self.my_grid.GetCellValue(row, 0)

                        self.my_grid.SetCellValue(row, 0, "Timeout\n"+txt)
                        log.logging.debug("Do_CheckForPortTimouts: Error timeout %s" % self.dct_port[key])

                    
     #                   if not (self.dct_port[key]["serial_num"] == None): 
                        # gen2_config.Update_IniFile(self.serial_nbr_file,  self.parser_serial_nbr, self.dct_port[key]["serial_num"], "status", "timeout")
                        # gen2_config.Update_IniFile(self.serial_nbr_file,  self.parser_serial_nbr, self.dct_port[key]["serial_num"], "last_log", self.dct_port[key]["last_log_file"])
                        
                    
                        # self.WriteGrid( self.dct_port[key]["row"], {"port_num":self.dct_port[key]["port_num"],    "status":"Not Responding",\
                                                            # "serial_num":self.dct_port[key]["serial_num"], "hardware_ver":self.dct_port[key]["hardware_ver"]}, None,attrib   )

    #---------------------------
    def On_task_timer(self, evt):
        try:
     #       start_time = time.time()
            log.logging.debug("On_task_timer: %s" % time.asctime( time.localtime(time.time()) ))
            self.Do_ScanForNewConnection()
            self.Do_CheckForQueueMsg()       
     #      log.logging("total time: %s" % abs(time.time() - start_time()) )
            self.Do_ProcessQueueMsg()
            self.Do_CheckForPortTimouts()
            
        except:
            log.logging.debug( "Traceback %s" % traceback.format_exc() )
#---------------------------            
#---------------------------            
class MainFrame(wx.Frame):
    def __init__(self,size=(600,450)):
        wx.Frame.__init__(self, None, title=APP_NAME)
		# #Add a menu bar to the frame
        self.CreateMenuBar()

        vboxSz = wx.BoxSizer(wx.VERTICAL)

        # Create Button Bar,
        btnSz = self.CreateBtnBar()
        
        #Add btns to the sizer, 
        vboxSz.Add(btnSz,0, wx.EXPAND)

        
        
        self.status_bar = wx.StatusBar(self)
        self.status_bar.SetStatusText("Greetings from status bar")
        
        self.status_bar.SetFieldsCount(3)
        self.status_bar.SetStatusWidths([400, 100, 100])
        # Create a notebook
        self.nb = NoteBook(self,-1)
        
        #Add notebook and Status_bar to the sizer

        vboxSz.Add(self.nb,1,  wx.EXPAND|wx.ALL|wx.NORTH,2)
        vboxSz.Add(self.status_bar,0,wx.EXPAND)
        
        self.SetSizer(vboxSz)
        
            
            
    def CreateMenuBar(self):
		#Add a menu bar to the frame
#        box = wx.BoxSizer(wx.VERTICAL)
          #--- Create menu bar
        mb = wx.MenuBar()
        
        #---- Create File Menu items that attach to menu bar, Quit, about
        file_menu = wx.Menu()
        
        #wx.Menu attach to the menu bar.,
        #each wx.Menu has items, 
        file_menu_items = [(ID_FIND_HANDLE, "&Find"), (ID_SET_DESTINATION, "&SetDestinationZipFile"), (ID_EXIT, '&Exit')]

        for id_txt in file_menu_items:
            evt_id, evt_txt = id_txt
            
            item = wx.MenuItem(file_menu, evt_id, evt_txt)
            self.Bind(wx.EVT_MENU, self.OnMainMenuSelect, item)
            file_menu.Append(item)
                
        mb.Append(file_menu, "&File")
        
        
        #Add help item to main menu
        help_menu = wx.Menu()
        help_menu_items = [(ID_HELP, '&Help'), (ID_ABOUT, '&About')]
        for id_txt in help_menu_items:
            evt_id, evt_txt = id_txt
            log.logging.debug("help Menu: id:%s, txt:%s" % (evt_id, evt_txt) )
            
            item = wx.MenuItem(help_menu, evt_id, evt_txt)
            self.Bind(wx.EVT_MENU, self.OnMainMenuSelect, item)
            help_menu.Append(item)
        
        mb.Append(help_menu, '&Help')
        
        self.SetMenuBar(mb)
    
    def CreateBtnBar(self):
        #Add NewFile button for logger
        #grdSz = wx.GridSizer(rows=1, cols=2, vgap=3, hgap=3)
        hboxSz = wx.BoxSizer(wx.HORIZONTAL)

        self.BtnNewLogFile_Id=wx.ID_ANY
        self.BtnLogFileSaveAs_Id=wx.ID_ANY
        self.BtnToggleLog_ON_Id=wx.ID_ANY
        self.BtnToggleLog_OFF_Id=wx.ID_ANY
        
        #Create Hub Button Bar---------------------
        #create btns and arannge them in horiz line,
        #assign each btn text and mapp it to the OnClick Event handler

        # btnBar = [(self.BtnNewLogFile_Id,"CreateNewLogFile","new_file.png","Create New Log File"),
                  # (self.BtnLogFileSaveAs_Id,"Log File Dest","save_1.png","Save handle log destination")]
        btnBar = [ (self.BtnLogFileSaveAs_Id,"Log File Dest","save_1.png","Save handle log destination")]

        for b in range(len(btnBar)):
            btn_id,txt,pic,toolTip = btnBar[b]
            # bmp = wx.Bitmap(pic, wx.BITMAP_TYPE_PNG)
            # mask = wx.Mask(bmp, wx.BLUE)
            # bmp.SetMask(mask)
            newBtn = wx.Button(self, btn_id, txt)           
            
            
            self.Bind(wx.EVT_BUTTON, self.OnBtnClick,newBtn)
            newBtn.SetToolTip(toolTip)
            hboxSz.Add(newBtn,0,wx.ALIGN_LEFT,1)
            
        return hboxSz
        
    def OnMainMenuSelect(self, evt):
        log.logging.debug("OnMainMenuSelect: %s" % evt.GetId())
        
        if evt.GetId() == ID_EXIT:
            self.Destroy()
            log.logging.debug( "ID_EXIT selected")
        
        elif evt.GetId() == ID_SET_DESTINATION:
            log.logging.debug("ID_SET_DESTINATION")
            self.OnLogFileSel()
        
        elif evt.GetId() == ID_FIND_HANDLE:
             log.logging.debug( "ID_FIND_HANDLE selected")
            
        elif evt.GetId() == ID_HELP:
            log.logging.debug( 'ID_HELP selected')
        
        elif evt.GetId() == ID_ABOUT:
            log.logging.debug("ID_ABOUT: %s" % ID_ABOUT)
            self.Do_OnAbout(self)
        
    #---------------------------------------------
    def Do_OnAbout(self, evt):
        aboutInfo = wx.adv.AboutDialogInfo()
        aboutInfo.SetName(APP_NAME)
        aboutInfo.SetVersion(VERSION)
        aboutInfo.SetDescription("Automatically detects, connects and downloads logs \n\
        from Signia Handles\n")
        
        aboutInfo.SetCopyright("(Copyright Medtronics) 2021")
       # aboutInfo.SetWebSite("http:#myapp.org")
        aboutInfo.AddDeveloper("Dominic Vagnone")

        wx.adv.AboutBox(aboutInfo)

        # Then we call wx.AboutBox giving it that info object




    #---------------------------------------------
    def OnBtnClick(self, evt):
        if evt.GetId() == self.BtnNewLogFile_Id:
            log.logging.debug( " you preset New log btn")

            
        
        elif evt.GetId() == self.BtnLogFileSaveAs_Id:
            self.OnLogFileSel()
        
        else:
            log.logging.debug( " I don't know what you pressed")
    

    def OnLogFileSel(self):
        #update log file dir location
        dlg = wx.DirDialog(self, "Choose a directory:",
                          style=wx.DD_DEFAULT_STYLE
                           #| wx.DD_DIR_MUST_EXIST
                           #| wx.DD_CHANGE_DIR
                           )

        # Show the dialog and retrieve the user response.
        # If it is the OK response, update logfile path
        # .
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            new_path = dlg.GetPath()
            log.logging.debug("new_path: %s" % new_path)
            
            #Write the new log file destination to the ini then reread the ini file
            gen2_config.Update_IniFile(gen2_config.INI_FILE, parser, section="files",  option=gen2_config.LOG_FILE_DESTINIATION_OPTION, value=new_path)
            self.nb.Do_ReadINI_File()


        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()
    
#----------------------------
# Every wxWindows application must have a class derived from wxApp
class MyApp(wx.App):

    # wxWindows calls this method to initialize the application
    def OnInit(self):
        log.logging.debug("Start")
        # Create an instance of our customized Frame class
        self.main_frame = MainFrame()
        self.main_frame.SetSize((900,600))

        self.main_frame.Show()
        return True
    
    def OnExit(self):
        ''' close window via system menu'''
        
        log.logging.debug("ExitAPP") #XXChange debug level 
        self.Destroy()
        return 0;
        
 
    
    
#----------------------------
if __name__ == "__main__":

    app = MyApp(0)     # Create an instance of the application class
    app.MainLoop()     # Tell it to start processing events

