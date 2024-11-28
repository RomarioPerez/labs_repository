import asyncio
import asyncssh
import pexpect
import logging
from colorama import Fore, Style
from ipaddress import ip_address
import env
from blessed import Terminal

class RemotePCManager:
    def __init__(self, ip_list, username, password):
        self.username = username
        self.password = password
        self.ssh_timeout = 15
        self.command_timeout = 30
        self.logger = logging.getLogger(__name__)       
        
        self.ip_list = ip_list 
        self.ip_dict = {str(i+1): ip for i, ip in enumerate(self.ip_list)}

    def get_ip(self, identifier):
        """
        Obtiene la IP basada en el identificador proporcionado.
        El identificador puede ser la IP completa o el ID en la lista.
        """
        if identifier in self.ip_list:
            return identifier
        elif identifier in self.ip_dict:
            return self.ip_dict[identifier]
        else:
            raise ValueError(f"IP o ID no válido: {identifier}")

    def display_ips(self):
        """
        Muestra las IPs ordenadas con sus IDs correspondientes en 6 columnas.
        """
        ips = list(self.ip_dict.items())
        half = (len(ips) + 1) // 6
        #max_id_length = max(len(f"{i+1}") for i in range(len(ips)))  # Longitud máxima de IDs
        #max_ip_length = max(len(ip) for _, ip in ips)  # Longitud máxima de IPs
        
        for i in range(half):
            left = f"{ips[i][0]:>{max_id_length}}: {ips[i][1]:<{max_ip_length}}"
            right = f"{ips[i + half][0]:>{max_id_length}}: {ips[i + half][1]:<{max_ip_length}}" if i + half < len(ips) else ""
            print(f"{left}\t{right}")

    
    def display_ips_formatted(self):
        """
        Muestra las IPs ordenadas con sus IDs correspondientes en dos columnas.
        """
        ips = list(self.ip_dict.items())
        half = (len(ips) + 1) // 2  # Ajuste para manejar un número impar de IPs
        max_id_length = max(len(f"{i+1}") for i in range(len(ips)))  # Longitud máxima de IDs
        max_ip_length = max(len(ip) for _, ip in ips)  # Longitud máxima de IPs
        
        lines = []
        for i in range(half):
            left = f"{ips[i][0]:>{max_id_length}}: {ips[i][1]:<{max_ip_length}}"
            right = f"{ips[i + half][0]:>{max_id_length}}: {ips[i + half][1]:<{max_ip_length}}" if i + half < len(ips) else ""
            lines.append(f"{left}\t{right}")
        return "\n".join(lines)

    async def check_status(self, identifier, timeout=5):
        """Check the status of a specific IP."""
        ip = self.get_ip(identifier)
        id = next((k for k, v in self.ip_dict.items() if v == ip), None)
        try:
            await asyncio.wait_for(self._connect(ip), timeout)
            return f"{Fore.YELLOW}{id:>2}: {Fore.GREEN}{ip:>12}{Style.RESET_ALL}"
        except (asyncio.TimeoutError, asyncssh.Error, ConnectionRefusedError):
            return f'{Fore.YELLOW}{id:>2}: {Fore.RED}{ip:>12}{Style.RESET_ALL}'

    async def execute_command(self, identifier, command, timeout=10 ):
        """Execute a command on a specific IP."""
        ip = self.get_ip(identifier)
        timeout = timeout or self.command_timeout        
        try:
            print(f"Try connect to {ip}..")
            async with await asyncio.wait_for(self._connect(ip), self.ssh_timeout) as conn:
                sudo_command = f"echo {self.password} | sudo -S -p '' {command}"
                result = await conn.run(sudo_command, check=True)
                if result.stderr:
                    return f"Command executed on {ip} with errors:\nstderr: {result.stderr}"
                return f"Result from {ip}: {result.stdout}"
        except asyncio.TimeoutError:
            return f"Error: Connection to {ip} timed out."
        except Exception as e:
            return f"Error on {ip}: {e}"

    def open_shell(self, identifier):
        """Open an interactive shell on a specific IP."""
        ip = self.get_ip(identifier)
        try:
            print(f"Connecting to {ip}...")            
            print(f"-----------------------Remote session on {ip}...")            
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
                print("Error: Could not establish SSH connection. EOF received.")
                return
            elif i == 3:
                print("Error: Connection attempt timed out.")
                return
            
            child.expect(['$', '#'], timeout=30)  # Espera el prompt            
            child.interact()

        except pexpect.EOF:
            print(f"SSH connection to {ip} closed unexpectedly.")
        except pexpect.TIMEOUT:
            print(f"Timeout while connecting to {ip}.")
        except Exception as e:
            print(f"Error: Could not start shell on {ip}. {e}")
        finally:
            print(f"Disconnected from {ip}.")
    
    async def monitor_resources(self, identifier):
        """Monitor system resources (CPU, RAM, Disk) on a specific IP in real time."""
        ip = self.get_ip(identifier)
        try:
            async with await self._connect(ip) as conn:
                print(f"Monitoring resources on {ip} (Press Ctrl+C to stop)...")
                while True:
                    result = await conn.run('top -b -n 1 | head -n 10 && df -h | grep "^/" && free -h', check=True)
                    if result.stderr:
                        print(f"Error on {ip}: {result.stderr}")
                    else:
                        clear_screen()
                        print(f"Resource Usage on {ip}:\n")
                        print(result.stdout)
                    await asyncio.sleep(2)  # Refresh every 2 seconds
        except asyncio.TimeoutError:
            print(f"Error: Connection to {ip} timed out.")
        except Exception as e:
            print(f"Error on {ip}: {e}")

    async def _connect(self, ip):
        try:
            return await asyncssh.connect(ip, username=self.username, password=self.password, known_hosts=None)
        except Exception as e:
            raise ConnectionRefusedError(f"Could not connect to {ip}: {e}")

    async def check_all_statuses(self):
        """Check the status of all IPs in the list."""
        tasks = [self.check_status(ip) for ip in self.ip_list]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def execute_command_on_all(self, command):
        """Execute a command on all IPs in the list."""
        tasks = [self.execute_command(ip, command) for ip in self.ip_list]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def delete_files(identifier, directory):
        pass


async def main():
    ip_list = env.ip_list
    username = env.username
    password = env.password

    manager = RemotePCManager(ip_list, username, password)
    term = Terminal()

    def clear_screen():
        print(term.clear)

    def print_menu():
        with term.location(0, term.height - 11):
            print(term.clear_eos + "\nOptions:")            
            print("1. Check status of all IPs")
            print("2. Execute command on a specific IP")
            print("3. Execute command on all IPs")
            print("4. Delete specific file types recursively in a directory on a specific IP")
            print("5. Open interactive shell on a specific IP")
            print("6. Monitor system resources on a specific IP")
            print("7. Exit")

    def print_content(content):
        with term.location(0, 1):
            print(term.clear_eos + content)

    while True:        
        print_menu()
        with term.cbreak(), term.hidden_cursor():
            choice = term.inkey()
        

        if choice == '1':            
            statuses = await manager.check_all_statuses()
            num_pcs = len(ip_list)
            lines = []            
            for i in range(0, num_pcs, env.pcs_by_line):
                line = "\t".join(statuses[i:i + env.pcs_by_line][::-1])
                lines.append(line)            
            print_content("\n".join(lines))
                 


        elif choice == '2':
            clear_screen()
            with term.location(0, 1):
                identifier = input("Enter the IP or ID: ")
                command = input("Enter the command to execute: ")
            try:
                result = await manager.execute_command(identifier, command)
                print_content(result)
            except ValueError as e:
                print_content(str(e))

        elif choice == '3':
            clear_screen()
            with term.location(0, 10):
                command = input("Enter the command to execute on all IPs: ")
            results = await manager.execute_command_on_all(command)
            results_str = "\n".join([str(result) for result in results])
            print_content(results_str)

        elif choice == '4':
            with term.location(0, term.height - 10):
                identifier = input("Enter the IP or ID: ")
                directory = input("Enter the directory path: ")
            try:
                result = await manager.delete_files(identifier, directory)
                print_content(result)
            except ValueError as e:
                print_content(str(e))

        elif choice == '5':
            with term.location(0, term.height - 10):
                identifier = input("Enter the IP or ID: ")
            try:
                await asyncio.get_event_loop().run_in_executor(None, manager.open_shell, identifier)
            except ValueError as e:
                print_content(str(e))

        elif choice == '6':
            with term.location(0, term.height - 10):
                identifier = input("Enter the IP or ID: ")
            try:
                await manager.monitor_resources(identifier)
            except ValueError as e:
                print_content(str(e))

        elif choice == '7':
            print_content("Exiting...")
            break

        else:
            print_content("Invalid option. Please choose again.")

if __name__ == "__main__":
    asyncio.run(main())





