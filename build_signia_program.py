#build_signia_transfer_program
import os
import sys
import logging
import subprocess
import shutil
import zipfile
import time

APP_NAME = "signia_transfer_program"

def do_Log_catcher():
#    '''What it does Create a distrubtion package for log_catcher_install
#
#        How its done:
#            1: Compiles the log_cathcer  code into an exe using the setup.py util in the dir
#            2: Run the inno setup utility to create a distrubtion package
#
#        Sample execution:
#            C:\Users\vagnod2\Documents\Medtronic\PowerStappler\python\python\PYTHON_MCP\build_signia_program.py
#     '''
    try:

        print( "running setup.py to create %s_Installer.exe: dist\\" % (APP_NAME))


        p = os.popen(r"python setup.py py2exe")
        l =  p.read()


        print("-------------------------------")
        print("Excuting Inno Setup script signia_transfer_program.iss")
        #cmd = '"C:\\Program Files (x86)\\Inno Setup 5\\ISCC.exe" signia_transfer_program.iss'

        
        p = os.popen(r'"F:\\Program Files\\Inno Setup 6\\ISCC.exe" signia_transfer_program.iss')
        l =  p.read()


		

    except:
        print ("Unexpected error:", sys.exc_info()[0])
        raise		
        
if __name__ == "__main__":
    print ("Cur Dir is: %s" % os.getcwd())
    do_Log_catcher()
    