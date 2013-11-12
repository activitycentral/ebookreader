import os
import subprocess
import platform
import env_settings

from gi.repository import GConf
from sugar3 import mime

DISABLE_SECURITY = GConf.Client.get_default().get_bool('/desktop/ebookreader/disable_security')

def get_path_bin():
    bin_path = 'bin/binario'
    if "arm" in platform.machine():
        bin_path = "bin/binario_arm"
    return os.path.join(env.SUGAR_ACTIVITY_ROOT, bin_path)

def is_file_encrypted(filepath):
    if DISABLE_SECURITY is True:
        return False

    filepath = filepath.replace('file://', '')
    mimebook = mime.get_for_file(filepath)
    return (mimebook == 'application/x-ceibal')

def decrypt_and_return_path_of_decrypted_file(filepath):
    filepath = filepath.replace('file://', '')
    if is_file_encrypted(filepath) is False:
        return filepath
    try:
        process = subprocess.Popen([get_path_bin(), filepath, str(os.getpid())], stdout=subprocess.PIPE)
        output, unused_err = process.communicate()
    except:
        return None
    return "file://" + str(output)
