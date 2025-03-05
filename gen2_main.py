import win32com.client

# import win32file
import threading
import time
import os
import random
import string
import queue
import gen2_serial_com as comm_port
import time
import gen2_cmds as gen2
import gen2_logging as log
import configparser as CP
import gen2_config_settings as gen2_config
import shutil
import traceback

parser = CP.ConfigParser()
parser.read(gen2_config.INI_FILE)


log.logging.debug(80 * ("*"))
localtime = time.asctime(time.localtime(time.time()))
log.logging.debug("localtime %s" % localtime)


BUF_SIZE = 1000
USB_MsgQueue = queue.Queue(BUF_SIZE)
USB_MsgToThrd = queue.Queue(BUF_SIZE)


MAX_NBR_CMDS = 200


def scan_usb():
    """
    scan_usb ports and return the port id thats connected to the coviden
    device
    """
    strComputer = "."

    objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
    objSWbemServices = objWMIService.ConnectServer(strComputer, "root\cimv2")

    colItems = objSWbemServices.ExecQuery("SELECT * FROM Win32_PnPEntity")
    usbs = []
    for objItem in colItems:

        if (objItem.Name != None) and objItem.name.find("SigniaPowerHandle") > -1:

            com_port = "%s" % "objItem.Name"
            port_num = (
                com_port.split()[1]
                .replace("(", "")
                .replace(")", "")
                .replace("COM", "")
                .replace("'", "")
            )
            usbs.append(port_num)

    return usbs


class Gen2Commands:
    def __init__(self):
        self.dct_cmds = {}
        self.dct_cmd_response = {}
        self.dct_cmds[gen2.SERIALCMD_PING] = (gen2.SERIALCMD_PING, "SERIALCMD_PING")
        self.dct_cmds[gen2.SERIALCMD_ENUM_INFO] = (
            gen2.SERIALCMD_ENUM_INFO,
            "SERIALCMD_ENUM_INFO",
        )
        self.dct_cmds[gen2.SERIALCMD_GET_VERSION] = (
            gen2.SERIALCMD_GET_VERSION,
            "SERIALCMD_GET_VERSION",
        )

        self.cmd_enum = gen2.SERIALCMD_LAST_CMD
        self.max_enum_cmds = None  # Set when handle response to enum cmd is
        self.SERIALCMD_DOPEN = None
        self.SERIALCMD_NEXT_FILE_NAME = None
        self.SERIALCMD_ENUM_INFO = None

        self.SERIALCMD_HARDWARE_VERSION = None
        self.SERIALCMD_GET_SERIALNUM = None

    def add_cmd(self, key=None, str=None):
        log.logging.debug("add_cmd: id: %s, str: %s" % (key, str))
        self.dct_cmds[key] = (key, str)


class ProducerThread(threading.Thread):
    def __init__(
        self,
        group=None,
        target=None,
        name=None,
        args=(),
        kwargs=None,
        verbose=None,
        port_num=None,
        log_dest=None,
        history_file=None,
        config_parser=None,
    ):
        super(ProducerThread, self).__init__()
        self.target = target
        self.name = name
        self.history_file = history_file
        self.dct_mcp_dir = {"dirs": ["\\data"], "cur_dir": None, "dest_dir": log_dest}

        self.dct_dm_use_counts = (
            {}
        )  # Use counts parameters for SERIALCMD_GET_PARAMETERS

        self.periodic_update = time.time()  # Send a periodic msg, heat_beat
        self.dct_mcp_dir["fin_dirs"] = []

        self.end_thread_request = False  # end_thread_request, timer_get_file_data detect the end of thread after waiting for get_file_xfer to complete
        self.timer_get_file_data = None

        self.my_port = None
        self.port_num = port_num
        if self.port_num != None:
            # caller supplied a port num, lets use it
            self.my_port = comm_port.CSerialPort()
            self.my_port.log_level = 1
            #        port_num = '4'
            self.my_port.ConfigPort(
                port=self.port_num,
                baud=115200,
                parity="N",
                dataBit=8,
                stopBit=1,
                useThread=1,
            )
            log.logging.debug(
                "#1 Com port is open: GetPortConfig() " + self.my_port.GetPortConfig()
            )
        else:
            # No port num supplied, try an found a port
            self.scan_usb()

        MAX_TIMEOUTS = 10
        self.count = 0
        self.time_outs = []
        self.gen2_obj = Gen2Commands()
        self.log_files = []  # list of logs on handle.
        self.dct_file_xfer = {
            "log_name": None,
            "offset": 0,
            "stat": None,
            "history": [],
            "serial_num": "",
            "hardware_ver": None,
            "nbr_logs": 0,
        }
        self.handle_data = []

        self.serial_nbr_parser = config_parser
        log.logging.debug(
            "ProducerThread: __init__: name:%s, self.serial_nbr_parser:sections:%s"
            % (self.name, self.serial_nbr_parser.sections())
        )
        self.resume_log = None

        self.file_offset = 0000  # fileoffset used in get file data cmd
        log.logging.debug(
            "Thread Initialize: USB port:%s, log_destination: %s"
            % (self.port_num, self.dct_mcp_dir["dest_dir"])
        )

    # -------------------------------------
    def SaveHandleFileNm(self, pth):
        """
        SaveHandleFileNm:  exptd to be called from OnGetNextFile:
        as it returns handle file names
        """

        self.log_files.append(pth)

    # -------------------------------------
    def Do_ResumeLogCheck(self, resume_log=None):
        try:
            if resume_log == None:
                resume_log = self.resume_log

            if self.resume_log != None:  # 1: check if the resume log defined
                if (
                    self.resume_log in self.log_files
                ):  # 2: if resume_log is defined and is in our list of logs
                    pos = self.log_files.index(
                        self.resume_log
                    )  # 3 Get the position of the resume log

                    log.logging.debug(
                        "Do_ResumeLogCheck: cur log list %s, nbr_logs(%s), pos(%s)"
                        % (self.log_files[0], len(self.log_files), pos)
                    )

                    if pos > 0:
                        self.log_files = self.log_files[
                            pos - 1 :
                        ]  # delete all log files before the resumet log.
                        log.logging.debug(
                            "Do_ResumeLogCheck: updated log list %s, nbr_logs(%s), pos(%s)"
                            % (
                                self.log_files[0],
                                len(self.log_files),
                                self.log_files.index(self.resume_log),
                            )
                        )

        except:
            log.logging.debug("%s" % traceback.format_exc())
            log.logging.debug("Do_ResumeLogCheck: failed to retrieve last log")

        finally:
            self.resume_log = None

    # -------------------------------------
    def OnDopen(self, frame, dct):
        # the mcp sends over files in the dir defined in the DOPEN cmd,
        #
        if frame[4] == frame[5] == 0:
            cmd_nxt_file = self.get_cmd_id("SERIALCMD_NEXT_FILE_NAME")
            self.send_cmd(cmd_nxt_file)
        else:
            log.logging.debug("SERIALCMD_DOPEN Error code: %s, " % dct.values())

    # -------------------------------------
    def GetCurHandleFileNm(self):
        return self.dct_file_xfer["log_name"]

    # -------------------------------------
    def SaveHandleData(self, frame):
        """
        SaveHandleData: save the handle data, later write to file
        only called in SERIALCMD_GET_FILE_DATA
        """
        self.handle_data = self.handle_data + frame

    # ------------------------------------
    def GetCurLogFileNm(self):
        """
        GetCurLogFileNm: return path/nm of
        log file for SERIALCMD_GET_FILE_DATA
        """
        return self.dct_file_xfer["log_name"]

    # -------------------------------------
    def CreateHandleFile(self):
        """
        CreateHandleFile:  SERIALCMD_GET_FILE_DATA has finished
        receiving data for file, save the log file
        """
        dd = self.dct_file_xfer[
            "serial_num"
        ]  # reformat bytes to string 49, 55, 53, 52, 49, 56, 48, 56, 48, 48, 48, 48, 48, 48, 69, 52
        #        handle_log = "C:\\Users\\vagnod2\\Documents\\" + dd + "\\" + self.dct_file_xfer['log_name']    #\data\data_000001\000001\eventLog.gen2Log
        handle_log = (
            self.dct_mcp_dir["dest_dir"] + dd + "\\" + self.dct_file_xfer["log_name"]
        )
        log_pth = os.path.dirname(handle_log)

        try:
            os.stat(log_pth)
        except:
            os.makedirs(log_pth)

        #        log.logging.debug("CreateHandleFile: log_path: %s" % log_pth )
        fh = open(handle_log, "w+")

        fh.write("".join(map(chr, self.handle_data)))
        fh.close()

        self.dct_file_xfer["nbr_logs"] = self.dct_file_xfer["nbr_logs"] + 1

        self.handle_data = []

    #        print("CreateHandleFile: Success %s" % handle_log)

    # -------------------------------------
    def GetCurMCPDir(self):
        """
        return the dir sent in the last DOPEN command
        """
        return self.dct_mcp_dir["cur_dir"]

    # -------------------------------------
    def GetNextHandleFileNm(self):
        """
        called when starting SERIALCMD_GET_FILE_DATA with a new
        file handle,
        """
        self.Do_ResumeLogCheck()
        if len(self.log_files) > 0:
            self.dct_file_xfer["log_name"] = self.log_files.pop(0)

            #            print "self.dct_file_xfer['log_name'] " + self.dct_file_xfer['log_name']
            # remeber the logs we parsed
            #            self.dct_file_xfer['history'].append( self.dct_file_xfer['log_name'] )
            self.file_offset = 0000

        else:
            self.dct_file_xfer["log_name"] = None

        return self.dct_file_xfer["log_name"]

    # -------------------------------------
    def GetNextMCPDir(self):
        """
        Manages the dirs that havent been req, that have been requested and currently being requested
        """
        cur_dir = None

        if len(self.dct_mcp_dir["dirs"]) > 0:

            cur_dir = self.dct_mcp_dir["dirs"].pop(0)

            self.dct_mcp_dir["fin_dirs"].append(cur_dir)
            # add this to the dir we already requested
            self.dct_mcp_dir["cur_dir"] = cur_dir

        return cur_dir

    # -------------------------------------
    def AddMCPDir(self, new_dir):
        """
        SerialCmdGetNextFile returned a dir name
        if its in the list return false donot add the dir neme
        if its noe int the list return true add it to the list
        """
        if len(new_dir) < 4:
            return False

        for cc in ["..", "\\."]:
            if cc in new_dir:
                return False

        for dd in self.dct_mcp_dir["dirs"]:
            if dd == new_dir:
                return False

        self.dct_mcp_dir["dirs"].append(new_dir)
        #        log.logging.debug("AddMCPDir: %s" % (new_dir) )
        return True

    # -------------------------------------
    def scan_usb(self):
        """
        scan_usb ports and return the port id thats connected to the coviden
        device
        """

        strComputer = "."

        objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        objSWbemServices = objWMIService.ConnectServer(strComputer, "root\cimv2")

        colItems = objSWbemServices.ExecQuery("SELECT * FROM Win32_PnPEntity")

        for objItem in colItems:

            if (objItem.Name != None) and objItem.name.find("SigniaPowerHandle") > -1:

                com_port = "%s" % "objItem.Name"
                port_num = (
                    com_port.split()[1]
                    .replace("(", "")
                    .replace(")", "")
                    .replace("COM", "")
                    .replace("'", "")
                )

                self.my_port = comm_port.CSerialPort()
                self.my_port.log_level = 1
                self.my_port.ConfigPort(
                    port=port_num,
                    baud=115200,
                    parity="N",
                    dataBit=8,
                    stopBit=1,
                    useThread=1,
                )
                log.logging.debug(
                    "#1 Com port is open: GetPortConfig() "
                    + self.my_port.GetPortConfig()
                )

        if self.my_port == None:
            log.logging.debug("scan_usb: Serial Port Not open " + ("*" * 80))

    # -------------------------------------
    # look up a cmd id from the given name return cmd id
    def get_cmd_id(self, name):
        for ky in self.gen2_obj.dct_cmds.keys():
            if (
                name.strip() == self.gen2_obj.dct_cmds[ky][1].strip()
            ):  # expted dct format dct[cmd_id] = (cmd_id, name)
                return ky
        return None

    # -------------------------------------
    # send a cmd out to port
    def send_cmd(self, cmd_id, data=""):
        # cmd_name = gen2.COMMAND_LIST[cmd_id][0]   #0 returns string name of command
        xmit_str = gen2.COMMAND_LIST[cmd_id][
            1
        ]  # 1 returns the the cmd list aa,01,02,etc, what is xmited from serial port

        cmd_name = self.gen2_obj.dct_cmds[cmd_id][1]
        if cmd_name in [
            "SERIALCMD_HARDWARE_VERSION",
            "SERIALCMD_GET_SERIALNUM",
            "SERIALCMD_NEXT_FILE_NAME",
            "SERIALCMD_GET_VERSION",
        ]:
            xmit_str = comm_port.create_frame(6, cmd_id)

        elif cmd_name == "SERIALCMD_GET_PARAMETERS":
            frm = [data]
            sz = len(frm) + 6

            xmit_str = comm_port.create_frame(sz, cmd_id, frm)
            log.logging.debug("SERIALCMD_GET_PARAMETERS: xmit_str %s" % xmit_str)

        elif cmd_name == "SERIALCMD_GET_FILE_DATA":
            xmit_str = comm_port.create_frame(6, cmd_id)
            log.logging(
                "SERIALCMD_GET_FILE_DATA ERROR (cmd_id:%s), (data:%s" % (cmd_id, data)
            )
            # self.file_offset = self.file_offset + 990

            # frm = [ self.file_offset & 255,  self.file_offset >> 8,  self.file_offset >> 16,  self.file_offset >> 24] + map(ord,data)  + [00]
            # sz = len(frm) + 6  #1byte start, 2byte sz, 1 byte cmd_id, 2byte crc = 6 bytes
            # xmit_str = comm_port.create_frame(sz, cmd_id, frm)

        elif cmd_name == "SERIALCMD_DOPEN":
            frm = map(ord, data) + [00]

            sz = len(frm) + 6
            xmit_str = comm_port.create_frame(sz, cmd_id, frm)

        elif cmd_id == gen2.SERIALCMD_ENUM_INFO:

            if self.gen2_obj.max_enum_cmds == None:
                xmit_str = comm_port.create_frame(
                    7, gen2.SERIALCMD_ENUM_INFO, self.gen2_obj.cmd_enum
                )
                self.gen2_obj.cmd_enum = self.gen2_obj.cmd_enum + 1
            else:
                log.logging.debug(
                    "\n\nSend:SERIALCMD_ENUM_INFO not sent,.max_enum_cmds exceeded: %s\n"
                    % (self.gen2_obj.max_enum_cmds)
                )

        elif cmd_name == "SERIALCMD_GET_FILE_ATTRIB":
            # frm = map(ord,data)+[00]
            frm = map(ord, "\\01000287.tar") + [0]  # [170, 8, 0, 60, 197, 2, 235, 86]

            sz = len(frm) + 6
            xmit_str = comm_port.create_frame(sz, cmd_id, frm)

        self.DoXmit(cmd_name, xmit_str)

    # -------------------------------------
    def DoXmit(self, cmd_name, xmit_str):

        self.my_port.xmitBuf(xmit_str)
        log.logging.debug("%s -> %s" % (cmd_name, xmit_str))

    # -------------------------------------
    # ----------- Run Thread monitors serial port
    def run(self):
        self.send_cmd(gen2.SERIALCMD_PING)
        ping_cmd_timeout = time.time()

        self.send_cmd(gen2.SERIALCMD_GET_VERSION)
        self.send_cmd(gen2.SERIALCMD_ENUM_INFO)

        self.count = 1
        remainder = []

        while self.my_port.IsPortOpen() == True:
            if self.Do_EndThreadRequest() == True:
                self.my_port.ClosePort()
                log.logging.debug("Exiting thread: ")
                return

            self.GetQueueMsg()

            if abs(time.time() - self.periodic_update) > 10.0:  # 5.0:
                # Periodically send an upadate message 5 s
                self.SendQueueMsg("Update")
                self.periodic_update = time.time()

            # cmd_ping = [AA, 06, 00, 01, 00, 19]
            xmit_cmd = None
            cmd_nm = None
            cmd_id = None
            frame_sz = None

            # Check if we get a response
            self.my_port.addToRxdBuf()

            # chars was recvd

            if len(self.my_port.parsedFrame) > 0:

                # Convert the parsed frame to int. ['0xaa','0x12'.] to [170,16]
                pf = remainder + map(eval, self.my_port.parsedFrame)
                if remainder != []:
                    log.logging.debug("\t\n%s remainder added: " % pf)
                remainder = []

                cmd_id = pf[3]
                frame_sz = len(pf)

                log.logging.debug(
                    "\nFrame Recv: cmd_id: %s frame_sz: %s" % (cmd_id, frame_sz)
                )
                log.logging.debug("\tFrame Recv: %s" % str(pf))

                self.count = self.count + 1
                last_rcv = time.time()

                # if the command is in the command list and the entry is filled in display it

                if frame_sz > 1:
                    if pf[0] != (gen2.START_CHAR):
                        log.logging.debug(
                            "log.logging.debug\tParsedFrame  Missing Start Char"
                        )

                    else:
                        msg_sz = pf[1] + (pf[2] * 256)
                        msg_timeout = time.time()

                        # the frame is missing data wait for the rest of the msg to arrive
                        while msg_sz > len(pf):
                            self.my_port.addToRxdBuf()

                            # log.logging.debug("msg_sz: %s, frame_sz: %s" % (msg_sz,frame_sz) )
                            if len(self.my_port.parsedFrame) > 0:
                                pf = pf + map(eval, self.my_port.parsedFrame)
                                # log.logging.debug("pf: %s" % pf)

                            if abs(time.time() - msg_timeout) > 5:
                                log.logging.debug(80 * "*")
                                log.logging.debug(
                                    "Error: Msg Timeout waiting for rest of frame"
                                )
                                exit()

                        frames_remainder = gen2.extract_frames(pf)  # list of frames.
                        # returns a list of fully parsed frames, and any partial/remainder frames
                        # save the remainder frames and stick them onto the beginig of the next frame.

                        frames = frames_remainder[0]
                        remainder = frames_remainder[1]
                        if remainder == None:
                            remainder = []

                        # if len(remainder) > 0:
                        # log.logging.debug("ParsedFrame: Remaining frame:%s\n" % remainder )

                        for frame in frames:

                            if frame[0] != gen2.START_CHAR:
                                log.logging.debug("Missing Start Char Error %s" % frame)
                                pass

                            elif frame[0] == gen2.START_CHAR:
                                if not self.IsCRCValid(frame):
                                    log.logging("Bad CRC Error: %s" % f)
                                    pass

                                cmd_id_rcv = frame[3]

                                if cmd_id_rcv == gen2.SERIALCMD_ENUM_INFO:
                                    # process ENUM cmd, if the response is "" then the cmd is over,
                                    # if the enum cmd has data
                                    # --   save the add_cmd  name and assoc id
                                    # --   send another enum request
                                    #
                                    # if the enum has no data /  frame = ""
                                    # - - set enum done flag, Send DOPEN cmd

                                    log.logging.debug(
                                        "\tParsedFrame rcv: SERIALCMD_ENUM_INFO recevd \n"
                                    )
                                    dct = gen2.format_frame(frame)

                                    if dct["frame"] == "":
                                        # Recvd SERIAL_ENUM_RESP with null response, No cmds left to add
                                        if self.gen2_obj.max_enum_cmds == None:

                                            self.gen2_obj.max_enum_cmds = frame[4]

                                            # log.logging.debug("\t #2: EnumCmd Done: ParsedFrame rcv: SERIALCMD_ENUM_INFO Max cmds recvd %s\n" % (self.gen2_obj.max_enum_cmds) )
                                            # All the cmds are enumerated, lets get a list of directories, this kicks off the getnext file cmd-resp

                                            cmd_id_get_serial = self.get_cmd_id(
                                                "SERIALCMD_GET_SERIALNUM"
                                            )
                                            # ask for serial number before asking for dir.
                                            if cmd_id_get_serial != None:
                                                self.send_cmd(cmd_id_get_serial)

                                            cmd_id_get_param = self.get_cmd_id(
                                                "SERIALCMD_GET_PARAMETERS"
                                            )
                                            self.send_cmd(
                                                cmd_id_get_param, gen2.DP_PARAM_USAGE
                                            )

                                    else:
                                        # Save the Gen2 handle response SERIAL_ENUM its a Handle returns a cmdid and its name,
                                        # add cmd name string and id to the dict and send another enum cmd
                                        self.gen2_obj.add_cmd(frame[4], dct["frame"])

                                        # cmd_dct_resp = gen2.extract_frames(pf)
                                        self.send_cmd(gen2.SERIALCMD_ENUM_INFO)

                            if self.gen2_obj.max_enum_cmds == None:
                                # Dont do any other processing till al cmds are enumerated.
                                pass

                            elif self.gen2_obj.dct_cmds.has_key(cmd_id_rcv):
                                # we just recv a cmd, process it
                                cmd_name = self.gen2_obj.dct_cmds[cmd_id_rcv][1]

                                dct = gen2.format_frame(frame)
                                # id:50,     frame:"001./tar0005.tar"

                                # update the cmd_dct with the associated frame data
                                self.gen2_obj.dct_cmd_response[cmd_id_rcv] = {
                                    "cmd_name": cmd_name,
                                    "response": frame,
                                }

                                # log.logging.debug("\tParsedFrame rcv_1: %s recvd, %s\n" % (cmd_name, dct) )

                                if cmd_name == "SERIALCMD_HARDWARE_VERSION":
                                    self.dct_file_xfer["hardware_ver"] = "%s.%s" % (
                                        frame[4],
                                        frame[5],
                                    )
                                    log.logging.debug(
                                        "\tParsedFrame rcv SERIALCMD_HARDWARE_VERSION: %s \t %s"
                                        % (cmd_name, dct)
                                    )

                                elif cmd_name == "SERIALCMD_GET_FILE_ATTRIB":
                                    log.logging.debug(
                                        "\tParsedFrame rcv SERIALCMD_GET_FILE_ATTRIB: %s \t %s"
                                        % (cmd_name, dct)
                                    )

                                elif cmd_name == "SERIALCMD_GET_SERIALNUM":
                                    log.logging.debug(
                                        "\tParsedFrame rcv SERIALCMD_GET_SERIALNUM: %s \t %s"
                                        % (cmd_name, frame)
                                    )
                                    self.OnGetSerialNum(cmd_name, frame)

                                elif cmd_name == "SERIALCMD_DOPEN":
                                    self.OnDopen(frame, dct)
                                    # the mcp sends over files in the dir defined in the DOPEN cmd,

                                elif cmd_name == "SERIALCMD_NEXT_FILE_NAME":
                                    self.OnGetNextFile(frame, dct)

                                elif cmd_name == "SERIALCMD_GET_FILE_DATA":
                                    self.OnGetFileData(frame, dct)

                                elif cmd_name == "SERIALCMD_GET_PARAMETERS":
                                    self.OnGetParameters(frame, dct)
                                    log.logging.debug(
                                        "\tParsedFrame rcv SERIALCMD_GET_PARAMETERS: frame: %s "
                                        % frame
                                    )

                                elif cmd_name == "SERIALCMD_GET_VERSION":
                                    self.OnGetVersion(frame, dct)
                                    self.dct_file_xfer["software_version"] = "%s.%s" % (
                                        frame[4],
                                        frame[5],
                                    )
                                    log.logging.debug(
                                        "\tParsedFrame rcv SERIALCMD_GET_VERSION: frame: %s "
                                        % frame
                                    )

            # Periodically send out these commands
            if abs(ping_cmd_timeout - time.time()) > 15:
                self.send_cmd(gen2.SERIALCMD_PING)
                ping_cmd_timeout = time.time()
                if self.gen2_obj.max_enum_cmds != None:
                    # All cmds have been returned, now send cmds we know about

                    for name in [
                        "SERIALCMD_HARDWARE_VERSION",
                        "SERIALCMD_GET_SERIALNUM",
                    ]:
                        cmd_id = self.get_cmd_id(name)
                        if self.gen2_obj.dct_cmd_response.has_key(cmd_id) == False:
                            #
                            if cmd_id != None:
                                self.send_cmd(cmd_id)

        return

    # -------------------------------------
    def IsCRCValid(self, frame):
        """
        return true if the given frame has valid crc
        return false the given frame has invalid crc
        """
        crc_val = comm_port.CRC16_Array(0, frame[:-2])
        if (crc_val & 0xFF) == frame[-2] and (crc_val >> 8) & 0xFF == frame[-1]:
            return True

        else:
            log.logging.debug("IsCRCValid Error: InvalidCRC: %s" % frame)
            return False

    # -------------------------------------
    def OnGetParameters(self, frame, dct):
        """
        handle has responded to SERIALCMD_GET_PARAMETERS
        response is dependent on the index 19 is get params
        exptd: frame  [170, 16, 0, 116, 19, 127, 13, 0, 231, 3, 4, 0, 231, 3, 102, 236]
                  <star_char><loByte SZ><hiByte Sz>> <cmd_id> <index response>
        """
        cmd_id_get_param = self.get_cmd_id("SERIALCMD_GET_PARAMETERS")
        if len(frame) > 12:

            if frame[4] == gen2.DP_PARAM_USAGE and frame[3] == cmd_id_get_param:

                self.dct_dm_use_counts["fire_count"] = frame[6] + frame[7] * 256
                self.dct_dm_use_counts["fire_limit"] = frame[8] + frame[9] * 256

                self.dct_dm_use_counts["procedure_count"] = frame[10] + frame[11] * 256
                self.dct_dm_use_counts["prodedure_limit"] = frame[12] + frame[12] * 256

    # -------------------------------------
    def OnGetSerialNum(self, name, frame):
        # handle has resonded to SERIAL_CMD_GET_SERIAL_NUM
        """
        [170, 17, 0, 111, 67, 49, 54, 65, 65, 76, 48, 48, 48, 52, 0, 24, 219]
        """
        if self.dct_file_xfer["serial_num"] == "":
            self.dct_file_xfer["serial_num"] = "".join(
                map(chr, frame[4:-3])
            )  # 2byte crc + 1 byte null term

            # handle_history = HandleHistory(self.history_file)
            # if handle_history.get_handle_history( self.dct_file_xfer["serial_num"] ) != None:

            log.logging.debug("OnGetSerialNum %s " % (self.dct_file_xfer["serial_num"]))

            """
                From the ini file check we lost communications during a log file xfer during an update.
            """
            resume_log = None
            try:
                log.logging.debug(
                    "self.serial_nbr_parser.sections(): %s"
                    % self.serial_nbr_parser.sections()
                )
                if self.serial_nbr_parser.has_option(
                    self.dct_file_xfer["serial_num"], "last_log"
                ):  # my serial nbr has last_log defined in the ini file
                    resume_log = self.serial_nbr_parser.get(
                        self.dct_file_xfer["serial_num"], "last_log"
                    )
                    log.logging.debug(
                        "OnGetSerialNum: status: %s "
                        % self.serial_nbr_parser.get(
                            self.dct_file_xfer["serial_num"], "status"
                        )
                    )

                    if self.serial_nbr_parser.has_option(
                        self.dct_file_xfer["serial_num"], "status"
                    ):
                        # parser has my serial nbr last state wias update, this means we died b4  log transfer finished

                        if (
                            self.serial_nbr_parser.get(
                                self.dct_file_xfer["serial_num"], "status"
                            )
                            == "Update"
                        ):
                            self.resume_log = resume_log
            except:
                log.logging.debug("Traceback %s" % traceback.format_exc())
                self.resume_log = None

            log.logging.debug("OnGetSerialNum: last_log status : %s " % self.resume_log)

            # wait till we have serial number before sending the msg, ask for serial number after enumeration

            log.logging.debug("Start Do_SerialCmdDopen Enum")
            self.SendQueueMsg("Starting File Xfer")

            if self.Do_SerialCmdDopen() == None:
                log.logging.debug("Do_SerialCmdDopen: No Directories")

    # -------------------------------------
    def OnGetNextFile(self, frame, dct):
        """
        The handle has send SERIALCMD_NEXT_FILE_NAME
        example file return.
        [170, 21, 0, 50, 0, 0, 3, 1, 109, 111, 116, 101, 115, 116, 46, 107, 118, 102, 0, 81, 160]
        """
        # SERIALCMD_NEXT_FILE_NAME response with 00 which means the no more files in the dir,
        #   send a dopen cmd to  a new dir
        err_code = frame[4] * frame[5] * 256
        attrib = frame[6]
        file_type = frame[7]
        fname = frame[8:-3]  # 2byte crc and null term

        if frame[4] == frame[5] == 00:
            # no error cdoe
            cur_dir = self.GetCurMCPDir()  # current dir were working on
            if frame[8] == 00:
                self.Do_SerialCmdDopen()  # no file name returned, check for additional dir

            else:
                # ask for another file,
                cmd_nxt_file = self.get_cmd_id("SERIALCMD_NEXT_FILE_NAME")
                self.send_cmd(cmd_nxt_file)

                pth = cur_dir + "\\" + "".join(map(chr, fname))
                #                log.logging.debug("SERIALCMD_NEXT_FILE_NAME add file:(attrib: %s), (file_type: %s),  (pth: %s)" % (attrib, file_type, pth) )

                if attrib == 0x03:
                    # attrib 03 means its a file.
                    # pth = string.strip(pth)
                    self.SaveHandleFileNm(pth)
                    # self.log_files.append(pth)

                elif attrib == 67:
                    self.AddMCPDir(pth)

        else:
            log.logging.debug(
                "SERIALCMD_NEXT_FILE_NAME Error code: %s, %s" % (frame[4], frame[5])
            )

    # -------------------------------------
    def GetQueueMsg(self):
        item = None
        if not USB_MsgToThrd.empty():
            item = USB_MsgToThrd.get()
            log.logging.debug(
                "Getting "
                + str(item)
                + " : "
                + str(USB_MsgToThrd.qsize())
                + " items in queue"
            )

            if "Exit" in str(item):
                print("Exit msg recvd")

                log.logging.debug("GetQueueMsg: ExitResponse %s" % (str(item)))
                self.end_thread_request = True
                self.timer_get_file_data = time.time()  # added -2 sec speed up the exit
                self.SendQueueMsg("ExitResponse: ")
                return True

            if "SendUpdate" in str(item):
                log.logging.debug("GetQueueMsg: UpdateResponse")
                self.SendQueueMsg("UpdateResponse: %s" % handle_log)

        return item

    # -------------------------------------
    def SendQueueMsg(self, msg):
        log.logging.debug("SendQueueMsg: %s" % msg)
        for ii in range(1):
            if not USB_MsgQueue.full():

                # dct={ "name":self.name, "port_num":self.port_num, "serial_num":self.dct_file_xfer["serial_num"],\
                # "msg":msg, "nbr_logs":self.dct_file_xfer["nbr_logs"], "dest_dir":self.dct_mcp_dir["dest_dir"], \
                # "hardware_ver": self.dct_file_xfer["hardware_ver"], "use_counts": self.dct_dm_use_counts }
                dct = {
                    "status": self.dct_file_xfer,
                    "use_counts": self.dct_dm_use_counts,
                    "dest_dir": self.dct_mcp_dir["dest_dir"],
                    "msg": msg,
                    "last_log": self.name,
                    "port_num": self.port_num,
                    "total_log_count": len(self.log_files),
                }

                #                "nbr_logs":len(self.dct_file_xfer['history']), "dest_dir":self.dct_mcp_dir["dest_dir"], "msg":msg}

                USB_MsgQueue.put(dct)

                log.logging.debug(
                    "Putting "
                    + str(dct)
                    + " : "
                    + str(USB_MsgQueue.qsize())
                    + " items in queue"
                )
                return True

            else:
                time.sleep(0.1)
                log.logging.debug("SendQueueMsg retry %s: que is full" % ii)

        log.logging.debug("SendQueueMsg Error : que is full (%s)" % (ii))
        return False

    # -------------------------------------
    def OnGetFileData(self, frame, dct):
        """
        The handle has responded to SERIALCMD_GET_FILE_DATA.
        - If an error code recvd
            then quit

        - If the returned data size is < 990
            bytes then were done with this data transfer
            save the file,
            ask for another file.

        - if the returned size is 990
            then send SERIALCMD_GET_FILE_DATA for the same file


        """
        #        log.logging.debug( ("SERIALCMD_GET_FILE_DATA\n\t Error code: %s, %s") % (frame[4],frame[5]) )

        if frame[4] == frame[5] == 0:
            # no error detected
            self.timer_get_file_data = time.time()
            log.logging.debug(
                "\t File Offset: %s, %s, %s, %s"
                % (frame[6], frame[7], frame[8], frame[9])
            )
            log.logging.debug("\t Block Return size: %s, %s " % (frame[10], frame[11]))
            self.SaveHandleData(frame[12:])

            if (frame[10] + frame[11] * 256) < 990:
                # file transer complete, save the file ask for another
                log.logging.debug(
                    "SERIALCMD_GET_FILE_DATA file complete :%s"
                    % (self.GetCurHandleFileNm())
                )

                self.CreateHandleFile()

                handle_fn = self.GetNextHandleFileNm()
                if handle_fn != None:
                    # okay that went well lets do it again
                    self.Do_SendGetFileData(handle_fn)

                else:
                    self.end_thread_request = True
                    # self.my_port.ClosePort()
                    # for fn in self.dct_file_xfer['history']:
                    # print "self.dct_file_xfer['history'] - %s " % fn

            else:
                # file xfer still in progress, save data, ask for more.
                self.Do_SendGetFileData(self.GetCurHandleFileNm())

        else:
            log.logging.debug(
                "SERIALCMD_GET_FILE_DATA Error code :  frame[4]: %s, frame[5]: %s"
                % (frame[4], frame[5])
            )

    # -------------------------------------
    def Do_EndThreadRequest(self):
        """
        Check if thread needs to end, no more file transfer taking place more then 10 secs

        """
        if (self.end_thread_request == True) and abs(
            self.timer_get_file_data - time.time()
        ) > 30:
            log.logging.debug("SERIALCMD_GET_FILE_DATA: Done")
            self.SendQueueMsg("Done")

            # Zip up the log destingation dir
            return True
        else:
            return False

    # -------------------------------------
    def Do_SerialCmdDopen(self):
        """
        Send a dopen cmd for the next dir in the list
            return the size of the list, 0 signals calling
            routine were done.
        """

        mcp_dir = self.GetNextMCPDir()

        if mcp_dir != None:
            log.logging.debug("SERIALCMD_DOPEN for  %s" % self.GetCurMCPDir())

            cmd_id = self.get_cmd_id("SERIALCMD_DOPEN")
            self.send_cmd(cmd_id, mcp_dir)

        else:
            # '''        HEY THE FILES ARE BEING RETURNED
            # 1: TRY GETTING FILE DATA FOR TXT AND RDF
            # 2: TRY MULTIPLE HANDLES.
            # log.logging.debug("Do_SerialCmdDopen Done")
            # '''
            #
            handle_fn = self.GetNextHandleFileNm()
            if handle_fn != None:
                self.Do_SendGetFileData(handle_fn)

            else:
                log.logging.debug(
                    "Do_SerialCmdDopen ;) ALL HAIL THE END %s" % 80 * ("*")
                )

            # for fn in self.log_files:
            # log.logging.debug("filelist: %s" % fn)

        return mcp_dir

    # -------------------------------------
    def Do_SendGetFileData(self, file_name=None):

        if file_name == None:
            log.logging.debug("Do_SendGetFileData Error: No File name")
            print("Do_SendGetFileData Error" + 80 * ("*"))
            exit()

        cmd_id = self.get_cmd_id("SERIALCMD_GET_FILE_DATA")

        frm = (
            [
                self.file_offset & 255,
                0xFF & (self.file_offset >> 8),
                0xFF & (self.file_offset >> 16),
                0xFF & (self.file_offset >> 24),
            ]
            + map(ord, file_name)
            + [00]
        )

        sz = len(frm) + 6  # 1byte start, 2byte sz, 1 byte cmd_id, 2byte crc = 6 bytes
        xmit_str = comm_port.create_frame(sz, cmd_id, frm)

        self.file_offset = self.file_offset + 990
        self.DoXmit("SERIALCMD_GET_FILE_DATA", xmit_str)
        #        time.sleep(0.1) ##DV
        return xmit_str


# --------------------------------------------


# --------------------------------------------------
def Do_LogFileZip(
    item={
        "nbr_logs": 0,
        "dest_dir": None,
        "serial_num": None,
    }
):
    """
    create a zipfile if none is present
    """
    ret_val = False
    if item["nbr_logs"] <= 0:
        log.logging.debug("Do_LogFileZip Error: no log files created:")
        return ret_val

    elif item["dest_dir"]:
        fname = os.path.join(
            item["dest_dir"], item["serial_num"]
        )  # example: C:\\Users\\vagnod2\\Documents\\7541808000000E4.zip'

        #        if os.path.exists(fname+".zip") == False:
        log.logging.debug("Do_LogFileZip: Create zip file : %s" % fname)

        zip_result = shutil.make_archive(fname, "zip", fname)
        log.logging.debug("Do_LogFileZip zip_result: %s" % zip_result)
        time.sleep(0.5)
        ret_val = True

    return ret_val


# ------------------------------------
def SendMsgToThrd(thrd_msg={"msg": None, "serial_num": None, "port_num": None}):
    """SendMsgToThrd, retry twice,"""

    log.logging.debug("SendMsgToThrd: %s " % (thrd_msg))
    dct = {}
    for ii in range(1):
        if not USB_MsgToThrd.full():

            dct["msg"] = thrd_msg["msg"]  # exptd text like "Exit"

            dct["serial_num"] = thrd_msg["serial_num"]
            dct["port_num"] = thrd_msg["port_num"]
            USB_MsgToThrd.put(dct)

            log.logging.debug(
                "Putting "
                + str(dct)
                + " : "
                + str(USB_MsgToThrd.qsize())
                + " items in queue"
            )
            return True
        else:
            time.sleep(0.1)
            log.logging.debug("SendMsgToThrd retry %s: que is full" % ii)

    log.logging.debug("SendMsgToThrd Error : que is full (%s)" % (ii))
    return False


# ------------------------------------
def DoUpdateMsg(thrd_msg):
    print("Update: Msg: %s" % thrd_msg)
    log.logging.debug("Update Msg from handle: %s" % thrd_msg)


# ------------------------------------
def DoStartMsg(thrd_msg):
    """
    recevd start msg from serial thread

    """
    if "Start" in thrd_msg["msg"]:
        log.logging.debug(
            "Checking for duplicate SerialNum: %s, PortNum: %s"
            % (thrd_msg["serial_num"], thrd_msg["port_num"])
        )
        print(
            "\tChecking for duplicate Serial Num: %s on Port: %s"
            % (thrd_msg["serial_num"], thrd_msg["port_num"])
        )

        # if this serial number is already in the history file, tell thread to and stop close the port
        csv_hist = handle_history.get_handle_history(thrd_msg["serial_num"])

        if csv_hist != None and 1 == 0:  # disable the duplicate handle
            log.logging.debug("Duplicate SerialNum found: %s " % (csv_hist))
            # close the thread we already ran this
            log.logging.debug(
                "\tDuplicate SerialNum found request exit: SerialNum: %s,  PortNum: %s "
                % (thrd_msg["serial_num"], thrd_msg["port_num"])
            )

            dct = {}
            dct["msg"] = "Exit"
            dct["serial_num"] = thrd_msg["serial_num"]
            dct["port_num"] = thrd_msg["port_num"]

            USB_MsgToThrd.put(dct)

        else:
            log.logging.debug(
                "Serial Xfer Inprogress: SerialNum: %s, Port:%s "
                % (thrd_msg["serial_num"], thrd_msg["port_num"])
            )
            print(
                "\tNew Serial Num starting Xfer SerialNum: %s on Port: %s"
                % (thrd_msg["serial_num"], thrd_msg["port_num"])
            )


# --------------------------------------------
if __name__ == "__main__":

    usbs_in_use = []
    dct_thrds = {99999: None}
    if parser.has_option("files", "destination"):
        log_destination = parser.get("files", "destination")
    else:
        log_destination = "C:\\Users\\"

    if parser.has_option("files", "history"):
        history_file = parser.get("files", "history")
    else:
        history_file = "C:\\Users\\signia_transfer_program. csv"

    print(history_file)

    print(log_destination)
    handle_history = gen2_config.HandleHistory(history_file)
    my_msg = []
    while True:
        while not USB_MsgQueue.empty():
            item = USB_MsgQueue.get()
            my_msg.append(item)
            # '''
        if len(my_msg) > 0:
            item = my_msg.pop(0)

            log.logging.debug(
                "New: msg: %s, serial_num: %s, port: %s "
                % (item["msg"], item["serial_num"], item["port_num"])
            )
            if "Start" in item["msg"]:
                DoStartMsg(item)

            elif "Update" in item["msg"]:
                DoUpdateMsg(item)

            elif "Done" in item["msg"]:
                if item["port_num"] in usbs_in_use:
                    SendMsgToThrd(
                        {
                            "msg": "Exit",
                            "port_num": item["port_num"],
                            "serial_num": item["serial_num"],
                        }
                    )

                    Do_LogFileZip(item)

                if dct_thrds.has_key(item["port_num"]):
                    dct_thrds[item["port_num"]].stop()

                    del dct_thrds[item["port_num"]]

            # (MainThread) Getting name:Gen2Communications_7	, port_num:7	, serial_num:16AAK0094	,  msg:Done: 2146 file xfered	 : 0 items in queue

        usbs = scan_usb()
        for usb_port in usbs:
            if usb_port not in usbs_in_use:
                usbs_in_use.append(usb_port)

                print("new handle attached %s" % usb_port)
                dct_thrds[usb_port] = ProducerThread(
                    name="Gen2Communications_%s" % usb_port,
                    port_num=usb_port,
                    log_dest=log_destination,
                    history_file=history_file,
                )
                dct_thrds[usb_port].start()

#                time.sleep(2)

#        time.sleep(5)
