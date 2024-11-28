import logging
import asyncio
import asyncssh
import os
from ipaddress import ip_address
import pexpect
import time
import subprocess
import json

class RemotePCManager:
    def __init__(self, mac_dict, username, password, file_mac_ip):
        self.username = username
        self.password = password
        self.file_mac_ip = file_mac_ip
        self.ssh_timeout = 15
        self.command_timeout = 30
        self.time_poweron = 0.3 # after tests, 0.3 seconds works the most of time even with one round only.
        self.logger = logging.getLogger(__name__)

        ##    
        if os.path.exists(self.file_mac_ip):
            with open(file_mac_ip,"r") as file_json:
                aux_dict = json.load(file_json)
                file_json.close()
                self.ip_list = list(aux_dict.values())
                self.ip_dict = {str(i+1): ip for i, ip in enumerate(self.ip_list)}
        else:
            print("IP address file not exits.\n")
        self.mac_dict = mac_dict
        ##
        
    def get_ip(self, identifier):
        if identifier in self.ip_list:
            return identifier
        elif identifier in self.ip_dict:
            return self.ip_dict[identifier]
        else:
            raise ValueError(f"IP o ID no válido: {identifier}")

    def get_mac(self, identifier):
        if identifier in self.mac_dict:
            return identifier
        else:
            raise ValueError(f"IP o ID no válido: {identifier}")

    async def check_status(self, identifier, timeout=5):
        ip = self.get_ip(identifier)
        id = next((k for k, v in self.ip_dict.items() if v == ip), None)
        try:
            await asyncio.wait_for(self._connect(ip), timeout)
            return id, ip, True
        except (asyncio.TimeoutError, asyncssh.Error, ConnectionRefusedError):
            return id, ip, False

    async def check_all_statuses(self):
        tasks = [self.check_status(ip) for ip in self.ip_list]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def execute_command(self, identifier, command, timeout=10):
        ip = self.get_ip(identifier)
        timeout = timeout or self.command_timeout        
        try:
            async with await asyncio.wait_for(self._connect(ip), self.ssh_timeout) as conn:
                sudo_command = f"echo {self.password} | sudo -S -p '' {command}"
                try:
                    result = await conn.run(sudo_command, check=True)
                    if result.stderr:
                        return f"Command executed on {ip} with errors:\nstderr: {result.stderr}\nstdout: {result.stdout}"
                    return f"Result from {ip}: {result.stdout}"
                except asyncssh.ProcessError as e:
                    return f"Error on {ip}: Command failed with exit status {e.exit_status}\n" \
                            f"stdout: {e.stdout}\n" \
                            f"stderr: {e.stderr}"
        except asyncio.TimeoutError:
            return f"Error: Connection to {ip} timed out."
        except asyncssh.Error as e:
            return f"SSH Error on {ip}: {str(e)}"
        except Exception as e:
            return f"Unexpected error on {ip}: {str(e)}\nType: {type(e).__name__}"

    async def execute_command_on_all(self, command):
        tasks = [self.execute_command(ip, command) for ip in self.ip_list]
        return await asyncio.gather(*tasks, return_exceptions=True)
        
    def open_shell(self, identifier):
        ip = self.get_ip(identifier)
        try:
            ssh_command = f'ssh {self.username}@{ip}'
            child = pexpect.spawn(ssh_command)                        
            i = child.expect(['password:', 'continue connecting (yes/no)?', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
            if i == 0:
                child.sendline(self.password)
            elif i == 1:
                child.sendline('yes')
                child.expect('password:')
                child.sendline(self.password)
            elif i == 2:
                return "Error: Could not establish SSH connection. EOF received."
            elif i == 3:
                return "Error: Connection attempt timed out."
            
            child.expect(['$', '#'], timeout=30)
            child.interact()
        except pexpect.EOF:
            return f"SSH connection to {ip} closed unexpectedly."
        except pexpect.TIMEOUT:
            return f"Timeout while connecting to {ip}."
        except Exception as e:
            return f"Error: Could not start shell on {ip}. {e}"

    async def monitor_resources(self, identifier):
        ip = self.get_ip(identifier)
        try:
            async with await self._connect(ip) as conn:
                while True:
                    result = await conn.run('top -b -n 1 | head -n 10 && df -h | grep "^/" && free -h', check=True)
                    if result.stderr:
                        yield f"Error on {ip}: {result.stderr}"
                    else:
                        yield f"Resource Usage on {ip}:\n\n{result.stdout}"
                    await asyncio.sleep(2)
        except asyncio.TimeoutError:
            yield f"Error: Connection to {ip} timed out."
        except Exception as e:
            yield f"Error on {ip}: {e}"

    async def _connect(self, ip):
        try:
            return await asyncssh.connect(ip, username=self.username, password=self.password, known_hosts=None)
        except Exception as e:
            raise ConnectionRefusedError(f"Could not connect to {ip}: {e}")
    
    def clean_IP(self,dir_IP):
        dir_IP = dir_IP.replace("'", "")
        dir_IP = dir_IP.replace("b", "")
        dir_IP = dir_IP.replace("\\n", "") # Proteger el back slash
        return dir_IP

    async def temp_execute_command_with_save_out(self, identifier, command, timeout=10):
        ip = self.get_ip(identifier)
        timeout = timeout or self.command_timeout        
        try:
            async with await asyncio.wait_for(self._connect(ip), self.ssh_timeout) as conn:
                sudo_command = f"echo {self.password} | sudo -S -p '' {command}"
                try:
                    result = await conn.run(sudo_command, check=True)
                    if result.stderr:
                        print(f"Command executed on {ip} with errors:\nstderr: {result.stderr}\nstdout: {result.stdout}")
                        return result.stdout 
                    print(f"Result from {ip}: {result.stdout}")
                    return result.stdout
                except asyncssh.ProcessError as e:
                    return f"Error on {ip}: Command failed with exit status {e.exit_status}\n" \
                            f"stdout: {e.stdout}\n" \
                            f"stderr: {e.stderr}"
        except asyncio.TimeoutError:
            return f"Error: Connection to {ip} timed out."
        except asyncssh.Error as e:
            return f"SSH Error on {ip}: {str(e)}"
        except Exception as e:
            return f"Unexpected error on {ip}: {str(e)}\nType: {type(e).__name__}"

    async def execute_command_on_all(self, command):
        tasks = [self.execute_command(ip, command) for ip in self.ip_list]
        return await asyncio.gather(*tasks, return_exceptions=True)   
       
    async def disable_internet(self, mac_dict, user_confirmation):
        ##
        dir_resolve_file = "/etc/resolv.conf"
        command = "less " + dir_resolve_file + " | grep nameserver"
        ##tasks = subprocess.run(str(command), shell=True, capture_output=True)
        result = await self.temp_execute_command_with_save_out(identifier= "1" ,command=command,timeout=10)
        print(result)
        aux = self.clean_IP(str(result))
        ##

        ## 
        if aux == "#nameserver 127.0.0.53":
            resolve_file_status = "offline"
        elif aux == "nameserver 127.0.0.53":
            resolve_file_status = "online"
        else:
            resolve_file_status = False
        ##

        if user_confirmation.lower() == "on":
            if resolve_file_status == "online":
                print("already enable web access")
            elif resolve_file_status == "offline":
                print("enabling web access")
                ##command = "sudo sed -i s/\"#nameserver 127.0.0.53\"/\"nameserver 127.0.0.53\"/ " + dir_resolve_file
            else:
                print("Unknow error")
        elif user_confirmation.lower() == "off":
            if resolve_file_status == "online":
                print("disabling web access")
                ##command = "sudo sed -i s/\"nameserver 127.0.0.53\"/\"#nameserver 127.0.0.53\"/ " + dir_resolve_file
                ##print(command)
            elif resolve_file_status == "offline":
                print("already disable web access")
            else:
                print("Unknow error")     
    
    def wake_all_pcs(self, mac_dict):
        for a in range(0,2):
            print("Round",a+1)
            for mac in mac_dict:
                if mac is not None:
                    print(f"Power-on PC with MAC: {mac}")
                    os.system(f"wakeonlan {mac}")
                    time.sleep(self.time_poweron)

    def extract_mac_from_ip(self,mac_dict):
        print("Mac's extraction init")
        temp_dir = {}
        '''os.system('echo "" > ' + self.file_mac_ip)
        i=1
        for mac in mac_dict:
            print(i)
            i+=1
            command = "arp -n | grep " + mac + " | awk '{print $1}'" 
            print("Command executed: ",command)
            tasks = subprocess.run(str(command), shell=True, capture_output=True)
            dir_IP = self.clean_IP(str(tasks.stdout))
            print(dir_IP)
            if dir_IP != "":
                temp_dir[mac] = dir_IP
            else:
                print("No se encontró la ARP")
                temp_dir[mac] = False
        file_json = open(self.file_mac_ip,"w")
        json.dump(temp_dir,file_json,indent=4)
        file_json.close()'''