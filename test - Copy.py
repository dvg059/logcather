import win32com.client
import win32file
import threading
import time
import logging
import random
import string
import queue
import gen2_serial_com as comm_port
import time 
import dv_gen2_cmds as gen2


class myclass:
    def __init__(self):
        self.cmd_enum = 10

    def send_cmd(self, cmd_id):
        cmd_name = gen2.COMMAND_LIST[cmd_id][0]   #0 returns string name of command
        xmit_str = gen2.COMMAND_LIST[cmd_id][1]   #1 returns the the cmd list aa,01,02,etc, what is xmited from serial port
        
        if cmd_id == gen2.SERIALCMD_ENUM_INFO:
            self.cmd_enum = self.cmd_enum + 1
            cmd_str = [0xAA, 0x06, 0x00, 0x02, self.cmd_enum]
            crc = comm_port.CRC16_Array(0, cmd_str)
            hi_byte = crc >> 8
            lo_byte = 0xff & crc
            cmd_str.append(lo_byte)
            cmd_str.append(hi_byte)
            
if __name__ == "__main__":
    cl=myclass()
    cl.send_cmd(gen2.SERIALCMD_ENUM_INFO)