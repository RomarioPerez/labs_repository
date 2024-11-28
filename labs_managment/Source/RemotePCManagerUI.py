from colorama import Fore, Style, init
from .RemotePCManager import RemotePCManager
import os

class RemotePCManagerUI:
    def __init__(self, manager: RemotePCManager):
        self.manager = manager
        init(autoreset=True)  # Initialize colorama

    def print_menu(self):
        print(f"Remote PC Manager Menu:")
        print(f"1. Check status of all IPs")
        print(f"2. Execute command on IP's")
        print(f"3. Clean files on all IPs")     
        print(f"4. Open interactive shell on a specific IP")
        print(f"5. Monitor system resources on a specific IP")
        print(f"6. Internet conection disable")
        print(f"7. Update on all IPs")
        print(f"8. Power-on/off all IPs")
        print(f"9. Check relation ID|Mac|IP address")
        print(f"10. Clean terminal")
        print(f"11. Exit")

    def get_user_input_ids(self, prompt):
        list_ids = input(f"{Fore.YELLOW}{prompt}{Fore.WHITE}")
        list_ids = list_ids.split(",")        
        list_ids = [int(elemento) for elemento in list_ids if elemento.isdigit() and int(elemento) <= len(self.manager.mac_dict)]        
        return list_ids

    def get_user_input(self, prompt):
        return input(f"{Fore.YELLOW}{prompt}{Fore.WHITE}")

    def print_result(self, result):
        print(f"\n{Fore.GREEN}Result:{Style.RESET_ALL}")
        print(result)

    def print_error(self, error):
        print(f"\n{Fore.RED}Error:{Style.RESET_ALL} {error}")

    def format_status(self, status):
        id, ip, is_up = status
        color = Fore.GREEN if is_up else Fore.RED
        return f"{Fore.YELLOW}{id:>2}: {color}{ip:>12}{Style.RESET_ALL}"

    async def run(self):
        while True:
            self.print_menu()
            choice = self.get_user_input("Enter your choice: ")

            if choice == '1':
                statuses = await self.manager.check_all_statuses()
                formatted_statuses = [self.format_status(status) for status in statuses]
                self.print_result("\n".join(formatted_statuses))

            elif choice == '2':
                user_confirmation = input("Do you wish apply in all PCs? (y/n): ")
                if user_confirmation.lower() == 'n':
                    identifiers = self.get_user_input_ids("Enter the IDs (use ',' for various IDs: ")                
                    command = self.get_user_input("Enter the command to execute: ")
                    print("Executing in PC N°:",identifiers)
                    try:
                        for id in identifiers:
                            print(f"try in {id} {type(id )}")
                            result = await self.manager.execute_command(str(id), command)
                            self.print_result(result)
                    except ValueError as e:
                        self.print_error(str(e))
                elif user_confirmation.lower() == 'y':
                    command = self.get_user_input("Enter the command to execute on all IPs: ")
                    results = await self.manager.execute_command_on_all(command)
                    self.print_result("\n\n".join([f"{ip}:\n{result}" for ip, result in zip(self.manager.ip_list, results)]))
                else:
                    print("Invalid option. Operation cancelled.")

            elif choice == '3':
                
                command = "find /home/unimagdalena -type f -not -path \"/home/unimagdalena/.*\" -not -path \"/home/unimagdalena/.*/*\" -not -name \".*\" -exec rm -f {} \;"
                user_confirmation = input("Do you wish apply in all PCs? (y/n): ")
                if user_confirmation.lower() == 'n':
                    identifiers = self.get_user_input_ids("Enter the IDs. (use ',' for various IDs): ")
                    print(identifiers)
                    user_confirmation = self.get_user_input(f"Are you sure about it? (y/n): ")
                    if user_confirmation.lower() == 'y':
                        try:
                            for id in identifiers:
                                print(f"try in {id} {type(id )}")
                                result = await self.manager.execute_command(str(id), command)
                                self.print_result(result)
                        except ValueError as e:
                            self.print_error(str(e))
                    else:
                        print("Operation cancelled.")
                elif user_confirmation.lower() == 'y':
                    user_confirmation = self.get_user_input(f"Are you sure about it? (y/n): ")
                    if user_confirmation.lower() == 'y':
                        results = await self.manager.execute_command_on_all(command)
                        self.print_result("\n\n".join([f"{ip}:\n{result}" for ip, result in zip(self.manager.ip_list, results)]))                        
                    else:
                        print("Operation cancelled. ")
                else:
                    print("Unknow Error. ")

            elif choice == '4':
                identifier = self.get_user_input("Enter the IP or ID: ")
                print(f"\n{Fore.YELLOW}Opening shell to {identifier}. Use 'exit' to return to the menu.{Style.RESET_ALL}")
                try:
                    self.manager.open_shell(identifier)
                except ValueError as e:
                    self.print_error(str(e))

            elif choice == '5':
                identifier = self.get_user_input("Enter the IP or ID: ")
                print(f"\n{Fore.YELLOW}Monitoring resources. Press Ctrl+C to stop.{Style.RESET_ALL}\n")
                try:
                    async for resource_info in self.manager.monitor_resources(identifier):
                        print(resource_info)
                except ValueError as e:
                    self.print_error(str(e))
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}Monitoring stopped.{Style.RESET_ALL}")
            
            elif choice == '6':
                    user_confirmation = self.get_user_input(f"What do you want to do with web access? (on/off): ")
                    await self.manager.disable_internet(self.manager.mac_dict, user_confirmation)
            
            elif choice == '7':
                    command_list = ["sudo apt-get update","sudo apt-get upgrade -y","sudo apt-get autoremove -y"]
                    for command in command_list:
                        self.manager.execute_command_on_all(command)

            elif choice == '8':
                user_confirmation = self.get_user_input(f"What do you want? (on/off): ")
                if user_confirmation.lower() == "off":
                    command = f"poweroff"
                    results = await self.manager.execute_command_on_all(command)                         
                elif user_confirmation.lower() == "on":                    
                    self.manager.wake_all_pcs(self.manager.mac_dict)                    
                else:
                    print("Operation cancelled.")
            
            elif choice == '9':
                self.manager.extract_mac_from_ip(self.manager.mac_dict)
            
            elif choice == '10':
                os.system('clear')

            elif choice == '11' or choice.lower() == "exit":
                print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
                break
        
            else:
                self.print_error("Invalid option. Please choose again.")

            if choice != '10':
                input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
