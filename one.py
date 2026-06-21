import os
import subprocess
import psutil
import socket
import shutil
import platform
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk
from datetime import datetime
import threading

class ShellGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Shell Forces - Terminal")
        self.root.configure(bg="#2b2b2b")
        self.root.geometry("900x600")
        
      
        self.command_history = []
        self.history_index = 0
        
       
        self.aliases = {}
        
        
        self.create_widgets()
        
        
        self.display_team_info()
        
        
        self.update_directory_display()

    def create_widgets(self):
       
        main_frame = tk.Frame(self.root, bg="#2b2b2b")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
       
        self.output_display = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, bg="#282c34", fg="#abb2bf", 
                                                        font=("Consolas", 11), insertbackground="#abb2bf")
        self.output_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output_display.config(state=tk.DISABLED)
        
     
        cmd_frame = tk.Frame(main_frame, bg="#2b2b2b")
        cmd_frame.pack(fill=tk.X, padx=5, pady=5)
        
       
        self.dir_display = tk.Label(cmd_frame, text="", bg="#2b2b2b", fg="#61afef", anchor="w", font=("Consolas", 11))
        self.dir_display.pack(side=tk.TOP, fill=tk.X)
        
      
        prompt_label = tk.Label(cmd_frame, text="myOS> ", bg="#2b2b2b", fg="#61afef", font=("Consolas", 11))
        prompt_label.pack(side=tk.LEFT)
        
        self.cmd_entry = tk.Entry(cmd_frame, bg="#282c34", fg="#abb2bf", insertbackground="#abb2bf", 
                                 font=("Consolas", 11), relief=tk.FLAT, bd=2)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cmd_entry.focus_set()
        
       
        button_frame = tk.Frame(main_frame, bg="#2b2b2b")
        button_frame.pack(fill=tk.X, pady=5)
        
        buttons = [
            ("Help", lambda: self.execute_command("help")),
            ("Clear", lambda: self.execute_command("clear")),
            ("System Info", lambda: self.execute_command("system")),
            ("Disk Space", lambda: self.execute_command("disk")),
            ("File Explorer", self.open_file_explorer)
        ]
        
        for text, command in buttons:
            btn = tk.Button(button_frame, text=text, command=command, bg="#3e4451", fg="#abb2bf",
                            relief=tk.FLAT, padx=10, font=("Consolas", 10))
            btn.pack(side=tk.LEFT, padx=5)
        
       
        self.cmd_entry.bind("<Return>", self.process_command)
        self.cmd_entry.bind("<Up>", self.history_up)
        self.cmd_entry.bind("<Down>", self.history_down)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_file_explorer(self):
        folder = filedialog.askdirectory(initialdir=os.getcwd())
        if folder:
            self.execute_command(f"cd {folder}")

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit the shell?"):
            self.root.destroy()

    def write_to_output(self, text, color=None):
        self.output_display.config(state=tk.NORMAL)
        if color:
            self.output_display.tag_configure(color, foreground=color)
            self.output_display.insert(tk.END, text, color)
        else:
            self.output_display.insert(tk.END, text)
        self.output_display.see(tk.END)
        self.output_display.config(state=tk.DISABLED)

    def clear_output(self):
        self.output_display.config(state=tk.NORMAL)
        self.output_display.delete(1.0, tk.END)
        self.output_display.config(state=tk.DISABLED)

    def update_directory_display(self):
        self.dir_display.config(text=f"Current Directory: {os.getcwd()}")

    def display_team_info(self):
        team_name = "Shell Forces"
        project_name = " Shell Project"
        welcome_msg = f"\nWelcome to {project_name} by {team_name}\n"
        self.write_to_output(welcome_msg, "#61afef")
        self.write_to_output("Type 'help' to see available commands\n\n", "#98c379")

    def history_up(self, event):
        if not self.command_history:
            return "break"
        if self.history_index > 0:
            self.history_index -= 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self.command_history[self.history_index])
        return "break"

    def history_down(self, event):
        if not self.command_history:
            return "break"
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self.command_history[self.history_index])
        else:
            self.history_index = len(self.command_history)
            self.cmd_entry.delete(0, tk.END)
        return "break"

    def process_command(self, event=None):
        command = self.cmd_entry.get().strip()
        if not command:
            return
        
      
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
   
        self.write_to_output(f"myOS> {command}\n", "#61afef")
        
    
        self.cmd_entry.delete(0, tk.END)
        
      
        if command.lower() in ["exit", "quit"]:
            self.write_to_output("Exiting shell...\n", "#98c379")
            self.root.after(1000, self.root.destroy)
        else:
            threading.Thread(target=self.execute_command, args=(command,), daemon=True).start()

    def execute_command(self, command):
        """Execute shell commands"""
        try:
            if command.lower() in ["exit", "quit"]:
                return  
                
            elif command == "ls":
                self.list_files()
                
            elif command.startswith("cd "):
                path = command[3:].strip()
                self.change_directory(path)
                
            elif command.startswith("mkdir "):
                name = command[6:].strip()
                self.create_directory(name)
                
            elif command.startswith("rm "):
                filename = command[3:].strip()
                self.delete_file(filename)
                
            elif command == "ps":
                self.list_processes()
                
            elif command.startswith("kill "):
                self.kill_process(command[5:].strip())
                
            elif command.startswith("cp "):
                parts = command[3:].split(maxsplit=1)
                if len(parts) == 2:
                    self.copy_file(parts[0], parts[1])
                else:
                    self.write_to_output("Error: cp requires source and destination\n", "#e06c75")
                    
            elif command.startswith("mv "):
                parts = command[3:].split(maxsplit=1)
                if len(parts) == 2:
                    self.move_file(parts[0], parts[1])
                else:
                    self.write_to_output("Error: mv requires source and destination\n", "#e06c75")
                    
            elif command.startswith("view ") or command.startswith("cat "):
                filename = command.split(maxsplit=1)[1].strip()
                self.view_file(filename)
                
            elif command.startswith("create ") or command.startswith("touch "):
                filename = command.split(maxsplit=1)[1].strip()
                self.create_file(filename)
                
            elif command == "pwd":
                self.show_current_directory()
                
            elif command.startswith("find "):
                self.find_file(command[5:].strip())
                
            elif command == "disk":
                self.check_disk_space()
                
            elif command == "system":
                self.system_info()
                
            elif command == "ip":
                self.show_ip()
                
            elif command == "clear":
                self.clear_output()
                
            elif command.startswith("recent "):
                try:
                    n = int(command.split()[1])
                    self.recent_files(n)
                except (ValueError, IndexError):
                    self.write_to_output("Error: Please provide a valid number.\n", "#e06c75")
                    
            elif command.startswith("alias "):
                self.set_alias(command[6:])
                
            elif command.startswith("run "):
                self.run_alias(command[4:].strip())
                
            elif command == "aliases":
                self.list_aliases()
                
            elif command == "history":
                self.show_history()
                
            elif command == "help":
                self.show_help()
                
            else:
                
                self.execute_system_command(command)
                
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")
        
        
        self.update_directory_display()
        

    
    def list_files(self):
        """List files in the current directory."""
        try:
            files = os.listdir()
            if not files:
                self.write_to_output("Directory is empty.\n")
                return
                
       
            self.write_to_output("\nFiles and directories:\n", "#98c379")
            for file in files:
                if os.path.isdir(file):
                    self.write_to_output(f"📁 {file}/\n", "#61afef")
                elif os.path.isfile(file):
                    
                    if file.endswith(('.py', '.java', '.cpp', '.c', '.js')):
                        self.write_to_output(f"📄 {file}\n", "#c678dd")
                    elif file.endswith(('.txt', '.md', '.log')):
                        self.write_to_output(f"📄 {file}\n", "#98c379")
                    else:
                        self.write_to_output(f"📄 {file}\n")
            self.write_to_output("\n")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def change_directory(self, path):
        """Change to a specified directory."""
        try:
            os.chdir(path)
            self.write_to_output(f"Changed directory to: {os.getcwd()}\n")
        except FileNotFoundError:
            self.write_to_output("Error: Directory not found!\n", "#e06c75")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def create_directory(self, name):
        """Create a new directory."""
        try:
            os.mkdir(name)
            self.write_to_output(f"Directory '{name}' created successfully.\n", "#98c379")
        except FileExistsError:
            self.write_to_output("Error: Directory already exists!\n", "#e06c75")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def delete_file(self, filename):
        """Delete a file with confirmation."""
        result = messagebox.askquestion("Confirm Delete", f"Are you sure you want to delete '{filename}'?", icon='warning')
        if result != 'yes':
            self.write_to_output("File deletion canceled.\n")
            return
            
        try:
            if os.path.isdir(filename):
                shutil.rmtree(filename)
            else:
                os.remove(filename)
            self.write_to_output(f"File '{filename}' deleted successfully.\n", "#98c379")
        except FileNotFoundError:
            self.write_to_output("Error: File or directory not found!\n", "#e06c75")
        except PermissionError:
            self.write_to_output("Error: Access denied. Try running as administrator.\n", "#e06c75")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def list_processes(self):
        """List running processes."""
        self.write_to_output("\nRunning Processes:\n", "#98c379")
        self.write_to_output("PID\tProcess Name\n", "#61afef")
        self.write_to_output("=" * 30 + "\n")
        
        try:
            for process in psutil.process_iter(['pid', 'name']):
                self.write_to_output(f"{process.info['pid']}\t{process.info['name']}\n")
        except Exception as e:
            self.write_to_output(f"Error retrieving processes: {e}\n", "#e06c75")
        self.write_to_output("\n")

    def kill_process(self, pid):
        """Terminate a process by PID"""
        try:
            pid = int(pid)
            process = psutil.Process(pid)
            process_name = process.name()
            
            result = messagebox.askquestion("Confirm Termination", 
                                           f"Are you sure you want to terminate process {pid} ({process_name})?", 
                                           icon='warning')
            if result != 'yes':
                self.write_to_output("Process termination canceled.\n")
                return
                
            process.terminate()
            self.write_to_output(f"Process {pid} ({process_name}) terminated.\n", "#98c379")
        except psutil.NoSuchProcess:
            self.write_to_output(f"Error: No process with PID {pid} found.\n", "#e06c75")
        except ValueError:
            self.write_to_output("Error: Invalid PID. Please enter a number.\n", "#e06c75")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def copy_file(self, src, dest):
        """Copy a file or directory"""
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dest)
            else:
                shutil.copy(src, dest)
            self.write_to_output(f"File '{src}' copied to '{dest}'.\n", "#98c379")
        except FileNotFoundError:
            self.write_to_output(f"Error: File '{src}' not found.\n", "#e06c75")
        except PermissionError:
            self.write_to_output(f"Error: Permission denied for '{src}'. Try running as administrator.\n", "#e06c75")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def move_file(self, src, dest):
        """Move a file or directory."""
        try:
            shutil.move(src, dest)
            self.write_to_output(f"File '{src}' moved to '{dest}'.\n", "#98c379")
        except FileNotFoundError:
            self.write_to_output(f"Error: File '{src}' not found.\n", "#e06c75")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def view_file(self, filename):
        """Display contents of a file."""
        try:
            with open(filename, 'r') as file:
                content = file.read()
                self.write_to_output(f"\n--- Contents of {filename} ---\n", "#98c379")
                self.write_to_output(content + "\n")
                self.write_to_output(f"--- End of {filename} ---\n\n", "#98c379")
        except FileNotFoundError:
            self.write_to_output("Error: File not found!\n", "#e06c75")
        except UnicodeDecodeError:
            self.write_to_output("Error: Cannot display binary file content.\n", "#e06c75")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def create_file(self, filename):
        """Create an empty file."""
        try:
            with open(filename, 'w') as file:
                pass
            self.write_to_output(f"File '{filename}' created successfully.\n", "#98c379")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def system_info(self):
        """Display system information."""
        self.write_to_output("\nSystem Information:\n", "#98c379")
        self.write_to_output(f"OS: {platform.system()} {platform.release()}\n")
        self.write_to_output(f"CPU: {platform.processor()}\n")
        self.write_to_output(f"Architecture: {platform.architecture()[0]}\n")
        self.write_to_output(f"Python: {platform.python_version()}\n")
        self.write_to_output(f"RAM: {round(psutil.virtual_memory().total / (1024**3), 2)} GB\n")
        
       
        cpu_usage = psutil.cpu_percent(interval=1)
        self.write_to_output(f"CPU Usage: {cpu_usage}%\n")
        
      
        ram = psutil.virtual_memory()
        self.write_to_output(f"RAM Usage: {round(ram.used / (1024**3), 2)} GB ({ram.percent}%)\n")
        
        self.write_to_output("\n")

    def show_current_directory(self):
        """Display current working directory."""
        self.write_to_output(f"Current Directory: {os.getcwd()}\n")

    def find_file(self, filename):
        """Search for a file recursively."""
        self.write_to_output(f"Searching for '{filename}'...\n")
        found = False
        for root, dirs, files in os.walk(os.getcwd()):
            if filename in files:
                self.write_to_output(f"Found: {os.path.join(root, filename)}\n", "#98c379")
                found = True
        
        if not found:
            self.write_to_output("File not found!\n", "#e06c75")

    def check_disk_space(self):
        """Display disk usage information."""
        try:
            total, used, free = shutil.disk_usage("/")
            self.write_to_output("\nDisk Space:\n", "#98c379")
            self.write_to_output(f"Total: {total // (2**30)} GB\n")
            self.write_to_output(f"Used: {used // (2**30)} GB\n")
            self.write_to_output(f"Free: {free // (2**30)} GB\n")
            
           
            used_percent = (used / total) * 100
            self.write_to_output(f"Used: {used_percent:.1f}%\n\n")
        except Exception as e:
            self.write_to_output(f"Error checking disk space: {e}\n", "#e06c75")

    def recent_files(self, n=5):
        """Show the N most recently modified files."""
        try:
            files = [(f, os.path.getmtime(f)) for f in os.listdir() if os.path.isfile(f)]
            files.sort(key=lambda x: x[1], reverse=True)
            
            self.write_to_output(f"\n{n} Most Recently Modified Files:\n", "#98c379")
            for i, (file, mtime) in enumerate(files[:n], 1):
                date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                self.write_to_output(f"{i}. {file} (Modified: {date_str})\n")
            self.write_to_output("\n")
        except Exception as e:
            self.write_to_output(f"Error: {e}\n", "#e06c75")

    def set_alias(self, command):
        """Create command alias."""
        parts = command.partition('=')
        if parts[1] == '=':
            name, actual_command = parts[0].strip(), parts[2].strip()
            self.aliases[name] = actual_command
            self.write_to_output(f"Alias set: {name} -> {actual_command}\n", "#98c379")
        else:
            self.write_to_output("Invalid alias format! Use: alias name = 'command'\n", "#e06c75")

    def run_alias(self, name):
        """Execute alias command."""
        if name in self.aliases:
            command = self.aliases[name]
            self.write_to_output(f"Running alias '{name}': {command}\n", "#61afef")
            self.execute_command(command)
        else:
            self.write_to_output(f"Alias '{name}' not found.\n", "#e06c75")

    def list_aliases(self):
        """Display all saved aliases."""
        if not self.aliases:
            self.write_to_output("No aliases set.\n")
        else:
            self.write_to_output("\nSaved Aliases:\n", "#98c379")
            for name, command in self.aliases.items():
                self.write_to_output(f"{name} -> {command}\n")
            self.write_to_output("\n")

    def show_ip(self):
        """Display network details."""
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            self.write_to_output("\nNetwork Information:\n", "#98c379")
            self.write_to_output(f"Hostname: {hostname}\n")
            self.write_to_output(f"IP Address: {ip_address}\n\n")
           
            try:
                import urllib.request
                external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
                self.write_to_output(f"External IP: {external_ip}\n\n")
            except:
                pass
                
        except Exception as e:
            self.write_to_output(f"Error retrieving network info: {e}\n", "#e06c75")
    
    def compile_and_run(self, lang, filename):
        try:
            if lang == "c":
                compile_command = f"gcc {filename} -o output"
                run_command = "./output"
            
            elif lang == "cpp":
                compile_command = f"g++{filename} -o output"
                run_command = "./output"
            
            elif lang == "java":
                compile_command = f"javac{ filename}"
                run_command = f"java Temp" 
            
            subprocess.check_output(compile_command,shell=True, stderr = subprocess.STDOUT, text=True)

            output = subprocess.check_output(run_command, shell=True, stderr=subprocess.STDOUT, text=True)

            self.write_to_output(f"\nOutput: \n{output}", "#98c379")
        
        except subprocess.CalledProcessError as e:
            self.write_to_output(f"Compilation/Execution Error:\n{e.output}","#e06c75")

    def show_history(self):
        """Show command history."""
        self.write_to_output("\nCommand History:\n", "#98c379")
        for i, cmd in enumerate(self.command_history, 1):
            self.write_to_output(f"{i}: {cmd}\n")
        self.write_to_output("\n")

    def show_help(self):
        """Display available commands and their descriptions."""
        self.write_to_output("\nAvailable commands:\n", "#98c379")
        
        commands = [
            ("ls", "List files in current directory"),
            ("cd <dir>", "Change Directory"),
            ("mkdir <name>", "Create directory"),
            ("rm <file>", "Delete file (with confirmation)"),
            ("ps", "List running processes"),
            ("kill <pid>", "Terminate a process (with confirmation)"),
            ("cp <source> <destination>", "Copy file"),
            ("mv <source> <destination>", "Move file"),
            ("pwd", "Display current working directory"),
            ("view/cat <file>", "View contents of a file"),
            ("create/touch <file>", "Create a new file"),
            ("disk", "Show disk usage"),
            ("system", "Show system information"),
            ("ip", "Show IP address and network details"),
            ("clear", "Clear the terminal screen"),
            ("recent <N>", "Show N most recently modified files"),
            ("find <file>", "Search for a file recursively"),
            ("alias <name>=<command>", "Set a custom command alias"),
            ("run <alias>", "Execute an alias command"),
            ("aliases", "List all defined aliases"),
            ("history", "Show commands history"),
            ("help", "Show this help message"),
            ("exit/quit", "Exit the shell")
        ]
        
        for cmd, desc in commands:
            self.write_to_output(f"  {cmd.ljust(30)} - {desc}\n")
        
        self.write_to_output("\n")

    def execute_system_command(self, command):
        """Execute system commands or custom shell commands."""
        try:
          
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
            self.write_to_output(output)
        except subprocess.CalledProcessError as e:
            self.write_to_output(f"Command failed with error code {e.returncode}:\n{e.output}\n", "#e06c75")
        except Exception as e:
            self.write_to_output(f"Error executing command: {e}\n", "#e06c75")


if __name__ == "__main__":
    root = tk.Tk()
    shell_app = ShellGUI(root)
    root.mainloop()
