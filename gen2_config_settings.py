import  configparser as CP
import gen2_logging as log

INI_FILE = "signia_transfer_program.ini"

LOG_FILE_DESTINIATION_OPTION  = "destination"

HISTORY_FILE =        "handle_history.csv"        #csv file that has date, serialnbr for each handle.
HISTORY_FILE_OPTION = "history"
SERIAL_NBR_FILE_OPTION_ENABLE = "EnableSerialNbr"         #the section name that has the serial n 
SERIAL_NBR_FILE_OPTION = "serial_nbr_status"


#SERIAL_NBR_FILE_DEFAULT =           "serial_nbr_ini_file"       #ini file: last known status of the handle while downloading logs, each serial number is a section

#---- Update the log file setting in the ini
def Update_IniFile(ini_file, parser, section="files",  option=None, value=None):
    ''' '''
    ret_val = None
    log.logging.debug("Update_IniFile: %s, section: %s, option: %s, value: %s" % (ini_file, section, option, value ) )
    try:
        if (parser.has_section(section) == False):
            parser.add_section(section)
        
        #write new value to section
        if (option != None) and (value != None):
            parser.set(section, option, value)
        
        ini_fp = open(ini_file,"w+")
        parser.write(ini_fp)
        ini_fp.close()
        ret_val = True
            
    except:
        log.logging.debug( "Traceback %s" % traceback.format_exc() )
        ret_val = None
     
    finally:
        return ret_val
        
#--------------------------------------------
class HandleHistory:
    def __init__(self, csv_file = HISTORY_FILE):
        self.file_name = csv_file
        self.read_csv_file()
        
        pass
    
    #--------------------------------------------------
    def add_handle(self, handle_row=["datetime, serial_num, nbr_logs"]):
        '''
            add the given row to the csv file
            -return True on success
            -return False on failure
        '''
        ret_val = False
        for row in handle_row:
            serial_num = row.split(",")[1]      
            
            #search key on serial num 
            if self.get_handle_history(serial_num) == None:
                self.write_csv_file(self.file_name, handle_row)
                return True
        
        return ret_val
    
    #--------------------------------------------------
    #--------------------------------------------------
    def get_handle_history(self, serial_nbr=""):
        ret_val = None
        try:
            self.lines = self.read_csv_file()
            for line in self.lines:
                srl_nbr = line.split(",")
                if len(srl_nbr) > 2:
                    if serial_nbr in line.split(",")[1] and len(serial_nbr) == len(line.split(",")[1] ):
                        #serial nbr exist in history,
                        ret_val = line
                        break

        except:
            log.logging.debug("HandleHistory: is_handle_in_history")
        
        
        finally:
            return ret_val
    #--------------------------------------------------
    def read_csv_file(self, fname=None):
        if fname == None:
            fname = self.file_name
            
        lines = None
        try:
            os.stat(fname)
        except:
            self.write_csv_file(fname)

        with open(fname,"r+") as history_file:
            lines = history_file.readlines()
            
        return lines
    
    #--------------------------------------------------
    def write_csv_file(self, fname = None, rows= [] ):
        if fname == None:
            fname = self.file_name
            
        with open(fname,"a+") as history_file:
            for row in rows:
                row = row + "\n"
                history_file.write(row) 

