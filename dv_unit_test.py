
import win32com.client
import win32file
import threading
import time
import logging
import random
import string
import Queue
import gen2_serial_com as com_port
import signia_transfer_program as stp
import time 
import gen2_cmds as gen2
import gen2_main
import gen2_config_settings as gen2_config
import unittest
import os
import ConfigParser as CP

rcv =  [170, 39, 0, 2, 64, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 71,69, 84, 95, 67, 79, 78, 78, 69, 67, 84, 69, 68, 0, 237, 176,\
170, 37, 0, 2, 65, 83, 69, 82, 73, 65, 76, 67, 77,68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 71, 69, 84, 95, 65, 68, 68, 82, 69, 83, 83, 0, 109, 83,\
170, 36, 0, 2, 66, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 71, 69, 84, 95, 83, 84, 65, 84, 85, 83, 0, 22, 124,\
170, 38, 0, 2, 67, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87,73, 82, 69, 95, 87, 82, 73, 84, 69, 95, 77, 69, 77, 79, 82, 89, 0, 149, 65,
170, 37, 0, 2, 68, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69,95, 82, 69, 65, 68, 95, 77, 69, 77, 79, 82, 89, 0, 6, 252,\
170, 32, 0, 2, 69, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 71, 69, 84, 95, 73, 68, 0, 142, 143,\
170, 32, 0, 2, 70, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 83, 69, 84, 95, 73, 68, 0, 209, 206,\
170, 38, 0, 2, 71, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 67, 76, 69, 65, 82, 95, 65, 76, 76, 95, 73, 68, 0, 198, 166,\
170, 33, 0, 2, 72, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 68, 73, 83, 65, 66, 76, 69, 0, 101, 188,\
170, 37, 0, 2, 73, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 85, 80, 76, 79, 65, 68, 95, 70, 65, 75, 69, 0, 96, 163,\
170, 27, 0, 2, 74, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 82, 85, 78, 95, 77, 79, 84, 79, 82, 0, 85, 71,\
170, 33, 0, 2, 75, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 67, 79, 77, 77, 95, 84, 69, 83, 84, 95, 83, 69, 84, 85, 80, 0, 81, 65]

exptd_rcv = [[170, 39, 0, 2, 64, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 71, 69, 84, 95, 67, 79, 78, 78, 69, 67, 84, 69, 68, 0, 237, 176],\
 [170, 37, 0, 2, 65, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 71, 69, 84, 95, 65, 68, 68, 82, 69, 83, 83, 0, 109, 83],\
 [170, 36, 0, 2, 66, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 71, 69, 84, 95, 83, 84, 65, 84, 85, 83, 0, 22, 124],\
 [170, 38, 0, 2, 67, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 87, 82, 73, 84, 69, 95, 77, 69, 77, 79, 82, 89, 0, 149, 65],\
 [170, 37, 0, 2, 68, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 82, 69, 65, 68, 95, 77, 69, 77, 79, 82, 89, 0, 6, 252],\
 [170, 32, 0, 2, 69, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 71, 69, 84, 95, 73, 68, 0, 142, 143],\
 [170, 32, 0, 2, 70, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 83, 69, 84, 95, 73, 68, 0, 209, 206],\
 [170, 38, 0, 2, 71, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 67, 76, 69, 65, 82, 95, 65, 76, 76, 95, 73, 68, 0, 198, 166],\
 [170, 33, 0, 2, 72, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 68, 73, 83, 65, 66, 76, 69, 0, 101, 188],\
 [170, 37, 0, 2, 73, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 85, 80, 76, 79, 65, 68, 95, 70, 65, 75, 69, 0, 96, 163],\
 [170, 27, 0, 2, 74, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 82, 85, 78, 95, 77, 79, 84, 79, 82, 0, 85, 71],\
 [170, 33, 0, 2, 75, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 67, 79, 77, 77, 95, 84, 69, 83, 84, 95, 83, 69, 84, 85, 80, 0, 81, 65]]


rcv2=[170, 60, 0, 22, 32, 32, 50, 50, 52, 55, 48, 58, 32, 65, 114, 99, 104, 105, 118, 105, 110, 103, 32, 100, 105, 114, 101, 99, 116, 111,\
114, 121, 32, 92, 100, 97, 116, 97, 92, 100, 97, 116, 97, 95, 48, 48, 48, 49, 48, 49, 92, 48, 48, 48, 49, 50, 48, 0, 45, 144]
 
dct_cmds = {1: 'SERIALCMD_PING',2: "SERIALCMD_ENUM_INFO",  3: "SERIALCMD_GET_VERSION",     4:  "SERIALCMD_BOOT_ENTER",5:  "SERIALCMD_BOOT_QUIT",\
6:  "SERIALCMD_FLASH_ERASE",    7:  "SERIALCMD_FLASH_WRITE",8: "SERIALCMD_FLASH_READ",      9: "SERIALCMD_SET_VERSION",\
44:"SERIALCMD_STATUS_DATA",     45:"SERIALCMD_STATUS_START", 46: 'SERIALCMD_STATUS_STOP',    47:'SERIALCMD_DOPEN', 48:'SERIALCMD_DCLOSE',\
49:'SERIALCMD_FOPEN',           50:'SERIALCMD_FCLOSE',       51: "SERIALCMD_NEXT_FILE_NAME",  52:'SERIALCMD_CREATE_DIRECTORY', 53:'SERIALCMD_CREATE_DIRECTORY',\
54: 'SERIALCMD_FORMAT_FILESYSTEM', 55: 'SERIALCMD_DELETE_DIRECTORY', 56: 'SERIALCMD_DELETE_FILE', 57:'SERIALCMD_RENAME_FILE',   58: 'SERIALCMD_SET_FILE_NAME',\
59: 'SERIALCMD_GET_FILE_DATA', 60: 'SERIALCMD_SET_FILE_DATA', 61: 'SERIALCMD_GET_FILE_ATTRIB'}




def decode_frame(s='aa 28 00 xx xx 64 61 74 61 5c 64 61 74 61 5f 30 30 30 30 30 31 5c 30 30 30 30 30 32 5c 61 72 63'):
    ll = lambda x: '0x'+x               #exptd: ['0xaa', '0x28', '0x00', '0x3c', '0x5c', '0x64', '0x61', '0x74', 
    frm = map(eval,map(ll,s.split()))   #exptd: [170, 40, 0, 60, 92, 100, 97, 116, 97, 92, 100, 97, 116, 97, 
    

    if dct_cmds.has_key( frm[3] ):
        cmd = dct_cmds[frm[3]]
    else:
        cmd = "unknown cmd: %s " % frm[3]
    
    print "(%s/ %s) %s, payload: %s" % ( frm[3], hex(frm[3]), cmd, map(chr,frm[4:sz-5]))
    

def decode_file(lines=[]):
    '''
        lines is the output of readlines from a text file (mem dump from a communicatios sesion, r232 spy).
        its an array of strings, each element ends in \n. 
        it needs to be converted into numbers so I can parse it.
    '''
    ll = lambda x: '0x'+x               #exptd: ['aa 06 00 01 00 19 aa 06 00 01 00 19 aa 06 00 01\n', '00 19 aa 06 00 01 ... 06\n']
    frm = string.join(lines)            
    frm.replace('\\n',"")               #exptd: 'aa 06 00 01 00 19 aa 06 00 01 00 19 aa 06 00 01 00 19 aa 06 00 01 00 06'
    frm = map(eval,map(ll,frm.split())) #exptd: [170, 6, 0, 1, 0, 25, 170, 6, 0, 1, 0, 25, 170, 6, 0, 1, 0, 25, 170, 6, 0, 1, 0, 25, 170, 6, 0, 1, 0, 25, 170, 6]

    
    ii = 0
    frm = frm[:1000]
    fh = open("xx.txt", "w")
    while ii + 3 < len(frm):
           
        if frm[ii] == 0xaa:
            sz = frm[ii+1] + frm[ii+2] * 255
            
            if dct_cmds.has_key( frm[3] ):
                cmd = dct_cmds[frm[3]]
            else:
                cmd = "unknown cmd: %s " % frm[3]
            
            payload = frm[ii:ii+sz]
            pyld = map(chr, frm[ii+3:ii+sz])
            pyld = "".join(pyld)
            l = ( "(%s/ %s) %s, payload: %s" % ( frm[3], hex(frm[3]), cmd, pyld) )
            fh.write(l) +"\t*\t"+ payload + "\n"
            print l
        else:
            sz = 1
        
        ii = ii + sz
        
    fh.close()
       
    return
class MyMockObj:
    def __init__(self):
        self.dct_cmds ={}
        
   
class MyMockThreadObj(gen2_main.ProducerThread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        pass
        # th.ProducerThread.__init__(self, group=None, target=None, name=None,
                 # args=(), kwargs=None, verbose=None):




class TestUM(unittest.TestCase):
 
    def setUp(self):

        self.thrd = MyMockThreadObj()
        

        pass
    
    def test_iniFile(self):
        '''
            Test ini file creation and reading
        '''
        #Update_IniFile(section="files",  option=None, value=None):
        
        parser = CP.ConfigParser()
        parser.read(gen2_config.INI_FILE)

        self.serial_nbr_file = "serial_nbr_file.ini"
        if parser.has_option("files", gen2_config.SERIAL_NBR_FILE_OPTION):
            self.serial_nbr_file = parser.get("files",gen2_config.SERIAL_NBR_FILE_OPTION)
            
        self.parser_serial_nbr = CP.ConfigParser()
        self.parser_serial_nbr.read( self.serial_nbr_file)

#        print "self.parser_serial_nbr: %s" % self.parser_serial_nbr.sections()
        
        
        ret_val = gen2_config.Update_IniFile("files", "last_log", "\\data\\data_000001\\000023\\eventLog.txt")
  
  #     stp.Do_CheckForPortTimouts
 #       self.assertTrue(ret_val != None)

        
    def test_ProducerThread(self):
            self.thrd_obj = MyMockThreadObj()
            frm = [170, 21, 0, 50, 0, 0, 3, 1, 48, 48, 48, 48, 53, 52, 46, 116, 97, 114, 0, 15, 168]
            
            self.assertTrue( self.thrd_obj.IsCRCValid(frm), True)
            
    def test_format_frame(self):
        frame = [170, 21, 0, 50, 0, 0, 3, 1, 48, 48, 48, 48, 53, 52, 46, 116, 97, 114, 0, 15, 168]
        dct = gen2.format_frame(frame)
        exptd_dct = {'frame': '\\x03\\x01000054.tar', 'id': 50}
        self.assertDictEqual(dct, exptd_dct)
    
        serail_frame= [170, 17, 0, 111, 67, 49, 54, 65, 65, 76, 48, 48, 48, 52, 0, 24, 219]
        dct = gen2.format_frame(serail_frame)
        print "dct: %s " % dct
    
    def test_Gen2_Default(self):
        
        'Check the default values in the dictionary'
        
        dct_g2cmd = gen2_main.Gen2Commands().dct_cmds

        self.assertEqual(dct_g2cmd[gen2.SERIALCMD_PING], (gen2.SERIALCMD_PING, "SERIALCMD_PING"))
        self.assertEqual(dct_g2cmd[gen2.SERIALCMD_ENUM_INFO],  (gen2.SERIALCMD_ENUM_INFO, "SERIALCMD_ENUM_INFO") )
        self.assertEqual(dct_g2cmd[gen2.SERIALCMD_GET_VERSION], (gen2.SERIALCMD_GET_VERSION,"SERIALCMD_GET_VERSION"))
        

    def test_Gen2_extract_frames(self):
        '''
            A raw frame is passed into extract frames
			extract_frames 
	    returns a tuple[0] a list of complete frames
            returns a tuple[1] a list of incomplet frames
		'''
        
	#happy path: completed frames no reminder
        frames_remainder  = gen2.extract_frames(rcv)
        #expt compltd_frames frames_remainder[0], no remaining frames 
        self.assertEqual(frames_remainder[0], exptd_rcv)
        self.assertEqual(frames_remainder[1], None)


	#test incomplete raw frames:
        rcv_incmplt = [1170, 39, 0, 2, 64, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 79, 78, 69, 87, 73, 82, 69, 95, 71,69, 84, 95, 67, 79, 78, 78, 69, 67, 84, 69, 68, 0, 237]
        frames_remainder  = gen2.extract_frames(rcv_incmplt)
        self.assertEqual(frames_remainder[0],[])
        self.assertEqual(frames_remainder[1],rcv_incmplt)   #check no completed frames only incomplete frame.


        
	#test both complete and incomplete frames
        #add incomplete frame to list
        tfrm = [170, 27, 0, 2, 74, 83, 69, 82, 73, 65, 76, 67, 77, 68, 95, 82, 85, 78, 95, 77, 79, 84, 79, 82, 0, 85, 71]
        #create an incomplet frame an tack  it onto the good frame.
        recv_incmplt = rcv + tfrm[:-5]
        
        frames_remainder  = gen2.extract_frames(recv_incmplt)
        self.assertEqual(frames_remainder[0], exptd_rcv)
        #the partial frame is the remainder
        self.assertEqual(frames_remainder[1],tfrm[:-5])
        
        #Test short frame parseing, no remainder
        tfrm = [170, 7, 0, 1, 9, 216, 250]
        frames_remainder  = gen2.extract_frames(tfrm)
        self.assertEqual(frames_remainder[0], [tfrm])
        self.assertEqual(frames_remainder[1],None)
        
        #Test Long and short raw_frame
        raw_frame = [170, 34, 0, 22, 32, 32, 32, 57, 51, 50, 53, 58, 32, 77, 79, 84, 73, 79, 78, 32, 73, 78, 32, 80, 82, 79, 71, 82, 69, 83, 83, 0, 203, 125, 170, 48, 0, 22, 32, 32, 32, 57, 51, 50, 54, 58, 32, 65, 100, 97, 112, 116, 101, 114, 44, 32, 83, 116, 114, 97, 105, 110, 32, 71, 97, 117, 103, 101, 32, 69, 114, 114, 111, 114, 32, 61, 32, 49, 57, 0, 203, 45, 170, 12, 0, 109, 32, 0, 108, 36, 0, 0, 149, 95, 170, 12, 0, 109, 126, 0, 109, 36, 0, 0, 153, 221]
        frames_remainder  = gen2.extract_frames(raw_frame)
        exptd_frame = [[170, 34, 0, 22, 32, 32, 32, 57, 51, 50, 53, 58, 32, 77, 79, 84, 73, 79, 78, 32, 73, 78, 32, 80, 82, 79, 71, 82, 69, 83, 83, 0, 203, 125], [170, 48, 0, 22, 32, 32, 32, 57, 51, 50, 54, 58, 32, 65, 100, 97, 112, 116, 101, 114, 44, 32, 83, 116, 114, 97, 105, 110, 32, 71, 97, 117, 103, 101, 32, 69, 114, 114, 111, 114, 32, 61, 32, 49, 57, 0, 203, 45], [170, 12, 0, 109, 32, 0, 108, 36, 0, 0, 149, 95], [170, 12, 0, 109, 126, 0, 109, 36, 0, 0, 153, 221]]
        self.assertEqual(frames_remainder[0],exptd_frame)
        
        self.assertEqual(frames_remainder[1],None)
    
        # test crc
        frame = [170, 60, 0, 22, 32, 32, 50, 50, 52, 55, 48, 58, 32, 65, 114, 99, 104, 105, 118, 105, 110, 103, 32, 100, 105, 114, 101, 99, 116, 111, 114, 121, 32, 92, 100, 97, 116, 97, 92, 100, 97, 116, 97, 95, 48, 48, 48, 49, 48, 49, 92, 48, 48, 48, 49, 50, 48, 0, 45, 144]

        crc_value = com_port.CRC16_Array(0,frame[:-2])
        self.assertEqual(crc_value & 0xff, frame[-2], "lowbyte of crc is bad")       #verify lowbyte
        self.assertEqual( (crc_value >> 8) & 0xff, frame[-1], "hibyte of crc is bad" ) #verify hibyte
        
        #test bad crc
        crc_value = crc_value +1
        self.assertNotEqual(crc_value & 0xff, frame[-2], "exptd not equal")       #verify lowbyte
    

    #--------------------------------------------
    #--------------------------------------------
    #--------------------------------------------
    def test_Do_LogFileZip(self):    
        item = {'name': 'Gen2Communications_18', 'port_num': '18', 
                        'serial_num': '7541808000000E4', 
                        'dest_dir': 'C:\\Users\\vagnod2\\Documents\\', 
                        'nbr_logs': 0, 
                        'msg': 'Starting File Xfer'}
    
    
        gen2_main.Do_LogFileZip(item)
        
    #--------------------------------------------
    #--------------------------------------------
    
    
    def test_History (self):
        '''
            Test creating a new history.
            Writing records to a csv file
            Reading back records.
            Searching records.
        '''
        tmp_hist = "tmp.csv"

        
        if os.path.exists(tmp_hist):
            #start off with an empty file for testing
            os.remove(tmp_hist)
            
        hist = gen2_config.HandleHistory(tmp_hist)   #should create new csv file
        
        # hist.add_handle(["datetime,serial_num,nbr_logs"])
        handle_entrys =  ["Sun Aug 21 06:58:58 2019,754180000E4,2888", "Mon Jul 21 06:58:58 2019,4180000E4,22228", "Sun Aug 21 06:58:58 2019,75418,2333"]
            
        #add entries to the CSV file.
        hist.add_handle(handle_entrys)         
            
        for ii in range(len(handle_entrys)):
            expt_ser_num = handle_entrys[ii].split(",")[1]   #extract the records and see if they match, exptd: "Sun Aug 21 06:58:58 2019,754180000E4, 2888"
            
            #retrive records to the csv file
            act_ser_num = hist.get_handle_history(expt_ser_num)                 
            act_ser_num = act_ser_num.split(",")[1]            
            self.assertEqual(act_ser_num, expt_ser_num)
        
        
        handle_enties_bad =  ["Sun Aug 21 06:58:58 2019,B754180000E4,2888", "Mon Jul 21 06:58:58 2019,4180000E,22228", "Sun Aug 21 06:58:58 201,74418,2333"]
        for ii in range(len(handle_enties_bad)):
            #check a non-existant/bad serial number, should return None
            bad_serial_num = handle_enties_bad[ii].split(",")[1]
            
            bad_ser_num_resp = hist.get_handle_history(bad_serial_num) 
            
            self.assertEqual(bad_ser_num_resp, None)
            
        
        
        if os.path.exists(tmp_hist):
            #start off with an empty file for testing
            os.remove(tmp_hist)
            
    def test_ComPort(self):
        #test short frame len 6, cmd id 1
        frame = com_port.create_frame(6,1)
        self.assertEqual(frame, [170, 6, 0, 1, 0, 25])

        
        #test using list parm
        frm = map(ord,"..\\settings")+[00]
        cmd_id =46
        sz = len(frm) + 6
        frame = com_port.create_frame(sz, cmd_id, frm)
        self.assertEqual(frame, [170, 18, 00, 46,  46, 46, 92, 115, 101, 116, 116, 105, 110,  103, 115,  0, 108,  154])
        
        #test usning single parm
        cmd_id = 116
        data = 01
        frm = [data]
        sz = 7 #start of frame, loByte SZ, HiByte SZ, 
        frame = com_port.create_frame(sz, cmd_id, frm)
        self.assertEqual(frame, [170, 07, 00, 116, 01, 255, 172])
        

def Do_UnitTest():
    unittest.main()

def Do_DecodeComText():
    fn = "C:\\Users\\vagnod2\\Documents\\Medtronic\\PowerStappler\\python\\python\\PYTHON_MCP\\dv_mcp_rd_wr_download.txt"
    fn = "cm.txt"
    fh = open(fn,"r")
    
    lines = fh.readlines()
    fh.close()
    print decode_file(lines)
    
def Do_CSV_File():

    hist = gen2_main.HandleHistory()
    # hist.add_handle(["datetime,serial_num,nbr_logs"])
    for ii in ["Sun Aug 21 06:58:58 2019,754180000E4,2888", "Mon Jul 21 06:58:58 2019,4180000E4,22228", "Sun Aug 21 06:58:58 2019,75418,2333"]:
        hist.add_handle([ii])
    
    
    print "history: " + str(hist.get_handle_history("75418"))
    # gen2_main.write_csv_file("my_csv.csv", [ "Sun Jul 21 06:58:58 2019,7541808000000E4,2816"])
    # print gen2_main.read_csv_file("my_csv.csv")
    
    # if os.pagen2_main.exists("xyz.txt"):
        # os.remove("xyz.txt")
    # print gen2_main.read_csv_file("xyz.txt")


    # csv_row =  "%s,%s,%s" %  (time.ctime(), "1234566", 211112)
    
    # gen2_main.write_csv_file("my_csv.csv",[csv_row])
    # print gen2_main.read_csv_file("my_csv.csv")

#----------------------------

if "__main__" ==  __name__:

    print "1: Do MCP unit test:\n2: Do_DecodeCommTxt \n3: Do_CSV_File"
    action = raw_input("")


    if action == "1":
        Do_UnitTest()
        
    elif action == "2":
        Do_DecodeComText()
    
    elif action == "3":
        Do_CSV_File()
    else:
        print "Unknown action"


        
        
