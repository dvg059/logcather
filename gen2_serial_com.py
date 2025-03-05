
#'''
#C:\Users\vagnod2\Documents\Medtronic\PowerStappler\python\gen2_serial_com.py
##DV dcb = GetCommState( self.handle ) fails, the port opens then GetCommState fails;
## 			I replaced it with win32file.DCB and I keep my own copy.C:\Users\vagnod2\Documents\Medtronic\PowerStappler\python>python gen2_serial_com.py
#************PortID: COM5
#************self.handle: <PyHANDLE:456>
#************ 11self.handle: <PyHANDLE:456>
#GetPortConfig:Error:["NameError: global name 'GetCommState' is not defined\n"] ,port(None)
#["NameError: global name 'GetCommState' is not defined\n"]
#Port Closed None
#Port Closed None
#
#C:\Users\vagnod2\Documents\Medtronic\PowerStappler\python>python gen2_serial_com.py
#************PortID: COM5
#************self.handle: <PyHANDLE:456>
#************ 11self.handle: <PyHANDLE:456>
#port 5, baud:115200, byte:8, parity:0, stopBits:1
#Port Closed None
#Port Closed None

import win32com.client
import win32file
import win32event
import pywintypes
import traceback
import string
import sys

import gen2_logging as log

oddparity =  [0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0]

def create_frame(sz = 0, cmd_id = 1, parm = None):
	if type(parm) is list:
		
		xmit_str = [0xAA, sz, 0x00,cmd_id ] + parm
		sz = len(xmit_str) +2
		xmit_str[1] = sz
		
	elif type(parm) is int:
		xmit_str = [0xAA, sz, 0x00, cmd_id, parm]
		
	else:
		xmit_str = [0xAA, sz, 0x00, cmd_id]
		
	crc = CRC16_Array(0, xmit_str)

	hi_byte = crc >> 8
	lo_byte = 0xff & crc

	xmit_str.append(lo_byte)
	xmit_str.append(hi_byte)
	return xmit_str
		

def GetCRC(crc = 0, frame= [0xAA, 0x06, 0x00, 0x01] ):
	for ch in frame:
		crc  = ch ^ crc16
	return crc


def int_to_byte(i_value):
	hbyte = i_value >> 8
	lbyte = (i_value & 0xff)
	return (lbyte, hbyte)
	
##cmd_ping = [0xAA, 0x06, 0x00, 0x01, 0x00, 0x19]	
def CRC16_Array(crc16In = 0, frame= [0xAA, 0x06, 0x00, 0x01]):

	for ch in frame:	

		data = (ch ^ (crc16In & 0xff)) & 0xff;
		crc16In >>= 8;

		if (oddparity[data & 0x0f] ^ oddparity[data >> 4]):
			crc16In ^= 0xc001

		data <<= 6
		crc16In ^= data
		data <<= 1
		crc16In ^= data

	return crc16In

#-----------------------------------------------------------------
class CSerialPort:
	'''
	SerialPort cbj: Open and configure a serial port
	'''
	def __init__(self,rawFrame=[], parsedFrame=[], status = 0, infoStr="Empty"):
		self.rawFrame    = rawFrame
		self.parsedFrame  =[]			#readable frame
		
		self.handle 		= None
		self.status      = status       #0 no frame, 1 frameComplete, 2 frameIncomplete, frameError

		self.timeStart   = None         #time stamp, when frame parsing started
		self.port   =  None
		self.baud   =  9600
		self.parity    = 'n'
		self.dataBit   = 8
		self.stopBit   = 1
		self.log_level = 0
	#==============================================================
	def WriteLog(self, stuff,level):
		if (level >= self.log_level):
			log.logging.debug( stuff)
			
		return
	##-------------------------------------------------------------
	def __del__(self):
		self.ClosePort()
	#-------------------------------------------------------------
	#-------------------------------------------------------------
	def ClosePort(self):
		#self.log.write("ClosePort : self.comm.PortOpen:%s" % self.comm.PortOpen)
		if self.IsPortOpen() == 1:
			self.port = None
			win32file.CloseHandle(self.handle)
#		self.WriteLog("Port Closed %s" % (self.port), 1)
	#--------------------------------------------------------------------------
	# ConfigPort
	#--------------------------------------------------------------------------
	def ConfigPort(self,port=1, baud=9600, parity="N", dataBit=8, stopBit=1, useThread=1):
		try:
			self.dcb = win32file.DCB()
			
			self.port = port
		
			#Normalize parity settings
			if parity == "e" or parity == "E":
				parity = win32file.EVENPARITY
		
			elif parity == "o" or parity == "O":
				parity = win32file.ODDPARITY
			else:
				parity = win32file.NOPARITY
			
			#Normalize dataBit Settings
			if stopBit == 2:
				stopBit = win32file.TWOSTOPBIT
			else:
				stopBit = win32file.ONESTOPBIT
	
			if int(port) < 10:
				port = "COM%s" % self.port
			else:
			   port = "\\\\.\\COM%s" % self.port
			   
			self.WriteLog("************PortID: %s" % port, 0)
			self.handle = win32file.CreateFile(port, win32file.GENERIC_READ | win32file.GENERIC_WRITE,
				0, # exclusive access
				None, # no security
				win32file.OPEN_EXISTING,
				win32file.FILE_ATTRIBUTE_NORMAL | win32file.FILE_FLAG_OVERLAPPED, 
				None)
				
			self.WriteLog("************win32file.CreateFile: Success self.handle: %s" % self.handle, 0)
			
			# Tell the port we want a notification on each char.
			# SetCommMask(self.handle, EV_RXCHAR)
			# Setup a 4k buffer
			win32file.SetupComm(self.handle, 4096, 4096)
			# Remove anything that was there
			win32file.PurgeComm(self.handle, win32file.PURGE_TXABORT | win32file.PURGE_RXABORT | win32file.PURGE_TXCLEAR | win32file.PURGE_RXCLEAR )
			# Setup for overlapped IO.
			timeouts = 100, 100, 1000, 0, 1000

			win32file.SetCommTimeouts(self.handle, timeouts)
			# Setup the connection info.
			
			# self.dcb = win32file.DCB()
			self.dcb = win32file.GetCommState( self.handle )
			self.dcb.BaudRate = baud
			self.dcb.ByteSize = 8
			self.dcb.Parity   = parity
			self.dcb.StopBits = stopBit
			self.dcb.fBinary = True
			

			win32file.SetCommState(self.handle, self.dcb)

			settings = self.GetPortConfig()
			self.WriteLog( "win32file.SetCommState: Success:", 0)

		except:
			self.port = None
#			err=traceback.format_exception_only(sys.exc_type,sys.exc_value) 
			etype, evalue, tb = sys.exc_info()
			self.WriteLog((traceback.format_exception_only(etype, evalue)),0)

	#-------------------------------------------------------------
	#-------------------------------------------------------------
	def addToRxdBuf(self):
		
		tmp=""
		txt  = []
		#self.rxdBuf = []

		if self.IsPortOpen() != 1:
			return

		ov = pywintypes.OVERLAPPED()
		ov.hEvent = win32event.CreateEvent(None,0,0,None)
		flags, comstat = win32file.ClearCommError( self.handle )      
		
		self.rawFrame = []
		self.parsedFrame=[]
		rc, self.rawFrame = win32file.ReadFile( self.handle, comstat.cbInQue,ov)
#		wait = win32event.WaitForSingleObject(ov.hEvent, 100)
		wait = win32event.WaitForSingleObject(ov.hEvent, 0)
		
		self.WriteLog("addToRxdBuf: rc: %s: self.rawFrame %s" % (rc, self.rawFrame), 0 )
		self.WriteLog("addToRxdBuf: comstat.cbInQue: %s" % (comstat.cbInQue),0 )
		
		if (comstat.cbInQue >0):

			self.WriteLog("Data Recived",0)
			
			for x in self.rawFrame:
				self.parsedFrame.append("0x%x" % (ord(x)))
#				self.parsedFrame.append(ord(x))
		
		self.WriteLog("%s Bytes Received, Frame: %s" % (comstat.cbInQue, self.parsedFrame),0 )
		
	#-------------------------------------------------------------
	#-------------------------------------------------------------
	def IsPortOpen(self):
		#self.log.write("IsPortOpen():%s" % (self.comm.PortOpen) )
		if self.port  == None:
			return None
		else:
			 return True
	#-------------------------------------------------------------
	#-------------------------------------------------------------
	def GetPortConfig(self):
		try:
			
			dcb = win32file.GetCommState( self.handle )
			self.WriteLog( "GetPortConfig:  dcb: %s" % dcb, 0)
			settings = "port %s, " % self.port
			settings = settings + "baud:%s, "   % dcb.BaudRate
			settings = settings + "byte:%s, "   % dcb.ByteSize
			settings = settings + "parity:%s, " % dcb.Parity
			settings = settings + "stopBits:%s "    % (dcb.StopBits + 1)

		except:
			self.port = None
			etype, evalue, tb = sys.exc_info()
			self.WriteLog((traceback.format_exception_only(etype, evalue)),0)
            
            
            
            
            
#			err=traceback.format_exception_only(sys.exc_type,sys.exc_value) 
#			self.WriteLog( "GetPortConfig:Error:%s ,port(%s)" % (err, self.port), 1 )
			settings="%s" % etype

		return settings
		
	#-------------------------------------------------------------
	#-------------------------------------------------------------			
	def xmitBuf(self,frame):
		try:
			s=""
			for x in frame:
				s=s+chr(x)

			ov = pywintypes.OVERLAPPED()
			ov.hEvent = win32event.CreateEvent(None,0,0,None)
			flags, comstat = win32file.ClearCommError( self.handle )      
			self.WriteLog("flags: %s, comstat: %s" % (flags, comstat), 0)
			win32file.WriteFile( self.handle, s,ov)
			wait = win32event.WaitForSingleObject(ov.hEvent, win32event.INFINITE)# might have to change this from INIFINITE

		except:
			s = "Cannot Open Serial Port %s" % self.port
			self.WriteLog(s,1)

			self.port = None
			etype, evalue, tb = sys.exc_info()
			self.WriteLog((traceback.format_exception_only(etype, evalue)),0)		
#--------------------- main -----------------------
if __name__ == '__main__':
	my_port = CSerialPort()

#	my_port.ConfigPort(port=5,   baud=460800, parity="N", dataBit=8, stopBit=1, useThread=1)
	my_port.ConfigPort(port = 5, baud=115200, parity="N", dataBit=8, stopBit=1, useThread=1)
	#PING AA 06 00 01 00 19
	ping = [0xAA, 0x06, 0x00, 0x01, 0x00, 0x19]
	
	my_port.xmitBuf(ping)
	my_port.addToRxdBuf()
	print ("%s\n" % my_port.rawFrame)
	print (my_port.GetPortConfig())                           
	my_port.ClosePort()

    
    