# hook-custom-path.py
import sys
import os

if hasattr(sys, '_MEIPASS'):
    exe_dir = os.path.dirname(sys.executable)
    
    distribute_dir = os.path.dirname(os.path.dirname(exe_dir))
    
    new_internal_path = os.path.join(distribute_dir, 'Vista3D-dist')
    
    sys._MEIPASS = os.path.abspath(new_internal_path)
    
    sys.path.insert(0, sys._MEIPASS)