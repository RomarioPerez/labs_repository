import os
import asyncio
import Config.env as env
import getpass
import bcrypt

from Source import RemotePCManagerUI
from Source import RemotePCManager

async def main():
    ## Assuming that user information is contains in Config/env.py
    username = env.username
    password = env.password

    while True:
        aux_password = getpass.getpass("Write your password: ")
        if bcrypt.checkpw(aux_password.encode('utf8'), password.encode('utf8')):
            password = aux_password
            break;
        else:
            input("Incorrect password. Pulse enter to try again...")
    
    os.system('clear')
    ##

    mac_dict = env.mac_dict
    if os.path.exists(env.file_mac_ip):
        file_mac_ip = env.file_mac_ip           
    else:
        print("File with mac_ip address not found. Some function can not work correctly\n")
 
    manager = RemotePCManager.RemotePCManager(mac_dict, username, password,file_mac_ip)
    ui_manager = RemotePCManagerUI.RemotePCManagerUI(manager)
    
    await ui_manager.run()

if __name__ == "__main__":
    asyncio.run(main())