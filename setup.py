#c:\Python27\python setup.py py2exe
from distutils.core import setup
import py2exe
import os
MFC_DIR="mfc_dir"
mfcfiles = [os.path.join(MFC_DIR, i) for i in ["mfc90.dll", "mfc90u.dll", "mfcm90.dll", "mfcm90u.dll", "Microsoft.VC90.MFC.manifest"]] 
data_files = [("Microsoft.VC90.MFC", mfcfiles),]
setup(windows=['signia_transfer_program.py'],data_files = data_files,
     options={'py2exe': {"dll_excludes": ["mswsock.dll", "MSWSOCK.dll"]}}
     )

