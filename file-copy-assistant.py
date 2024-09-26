from os import system, walk, SEEK_END
from platformdirs import user_downloads_dir
from pathlib import Path
from shutil import copy2
from datetime import datetime
from winotify import Notification, audio
import win32file
import win32api
import xxhash
import json

# SettingsManager is responsible for managing the application settings stored in a 'settings.json' file.
class SettingsManager:
    def __init__(self):
        """
        Initializes the SettingsManager instance. Loads or creates settings.json and sets defaults for the application.
        """
        self.current_file_path = Path(__file__)
        self.current_directory = self.current_file_path.parent
        self.settings_path = self.current_directory / "settings.json"
        self.state_file = self.current_directory / "state.json"
        self.downloads_path = Path(user_downloads_dir())

        # Template for the settings.json file
        self.settings_template = {
            "Prioritized file extensions": [".jpg", ".txt"],    # extensions should start with a "."
            "Disabled file extensions": [".mov",".mp4"],        # if the same extension is also in prioritiezed file extensions, it won't be disabled
            "Enable notifications": {                           # if you don't want any system notifications, set everything to false 
                "after all transfers are finished": True,       
                "after every priority": True,                   
                "after first priority": False,                  # will not influence the behavior of the program if "after every priority" is set to True
                "after last priority": False                    # will not influence the behavior of the program if "after every priority" is set to True
            },
            "Default output directory": "path/to/output/dir",
            "Copy only priority files": False,
            "Skip prompts": False,                              # if True, the user will not be prompted after the program is run and it will relay on settings alone
            "Enable priority": True                             # if False, all files except for those with disabled file extensions are copied
        }

        # Update default output directory in settings template
        self.settings_template["Default output directory"] = str(self.downloads_path)

        # Load user-defined settings from settings.json
        self.settings = self.get_json_data()

        # Assign settings to internal attributes
        self.default_output_dir = self.settings.get("Default output directory")
        self.priority_list = self.get_priority_list()
        self.enable_priority = self.settings.get("Enable priority")
        self.copy_only_priority = self.settings.get("Copy only priority files")
        self.notification_after_last_priority = self.settings.get("Enable notifications")["after last priority"]
        self.first_priority_notification = self.settings.get("Enable notifications")["after first priority"]
        self.notify_after_all_transfers = self.settings.get("Enable notifications")["after all transfers are finished"]
        self.notification_after_every_priority = self.settings.get("Enable notifications")["after every priority"]
        self.disabled_extensions = set([ext.lower() for ext in self.settings.get("Disabled file extensions")])
        self.skip_prompts = self.settings.get("Skip prompts", False)

    def is_extension_valid(self, extension):
        """
        Checks if a file extension is valid (starts with a dot and has more than one character).
        """
        return len(extension) > 1 and extension[0] == "."

    def get_priority_list(self):
        """
        Returns a list of unique, valid, prioritized file extensions.
        """
        seen = set()
        priority_list = []
        for extension in self.settings.get("Prioritized file extensions"):
            extension = extension.lower()
            if self.is_extension_valid(extension) and extension not in seen:
                priority_list.append(extension)
                seen.add(extension)
        return priority_list

    def set_settings(self):
        """
        Prompts the user to change the settings if needed.
        """
        print("\nCurrent settings:")
        self.print_settings()
        wants_change = input("\nChange settings? (y/n) ").lower()
        if wants_change == "y":
            self.open_settings()
        input("\nIf you're happy with the settings, press Enter to start.")

    def create_settings(self):
        """
        Creates a 'settings.json' file using the default template.
        """
        print("Creating 'settings.json'.")
        with open(self.settings_path, 'w') as json_file:
            json.dump(self.settings_template, json_file, indent=4)
        print(f"'settings.json' has been saved at: {self.settings_path}\n")

    def get_json_data(self):
        """
        Reads settings from 'settings.json'. If not found or invalid, it creates a new one.
        """
        try:
            with self.settings_path.open('r') as file:
                contents = file.read()
            return json.loads(contents)
        except FileNotFoundError:
            print("File 'settings.json' has not been found.")
            self.create_settings()
            return self.get_json_data()
        except ValueError as ve:
            print(f"Error: {ve}")
            self.create_settings()
            return self.get_json_data()

    def open_settings(self):
        """
        Opens the 'settings.json' file in the default editor.
        """
        system(f'start "" "{self.settings_path}"')

    def print_settings(self):
        """
        Prints the content of the 'settings.json' file.
        """
        try:
            with open(self.settings_path, 'r') as file:
                print(file.read())
        except FileNotFoundError:
            self.create_settings()
            self.open_settings()

    def get_copied(self):
        """
        Returns the set of file checksums from 'state.json' or creates an empty 'state.json' if it doesn't exist.
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                return set(data)
            except json.JSONDecodeError:
                print(f"The state file contains invalid JSON.")
                return self.create_state_file()
        else:
            print(f"\nThe state file does not exist.")
            return self.create_state_file()

    def create_state_file(self):
        """
        Creates a new empty 'state.json' file and returns an empty set.
        """
        with open(self.state_file, "w") as f:
            json.dump([], f)
        print(f"Creating a new state file at '{self.state_file}'.")
        return set()

    def save_state(self, state, state_file):
        """
        Updates the 'state.json' file with the current list of copied file checksums.
        """
        with open(state_file, "w") as f:
            json.dump(list(state), f)
        print("Saved the current state of copied to 'state.json'.\n")


# FileManager handles operations related to file copying, size retrieval, and checksum generation.
class FileManager:
    @staticmethod
    def copy_file(old_file_path, new_file_path):
        """
        Copies a file from 'old_file_path' to 'new_file_path'. Adds '_copy' suffix if destination already exists.
        """
        if new_file_path.exists():
            new_file_path = new_file_path.with_name(f"{new_file_path.stem}_copy{new_file_path.suffix}")
        try:
            copy2(old_file_path, new_file_path)
            print(f"Copying {old_file_path} to {new_file_path}")  # Comment this line if output is not desired.
        except Exception as ex:
            print("Exception: " + str(ex))

    @staticmethod
    def get_file_size(file_path):
        """
        Returns the size of the file at 'file_path' in bytes.
        """
        return Path(file_path).stat().st_size

    @staticmethod
    def get_creation_time(file_path):
        """
        Returns the creation time of the file as a datetime object.
        """
        creation_time = datetime.fromtimestamp(file_path.stat().st_ctime)
        return creation_time

    @staticmethod
    def get_checksum(filename, file_size):
        """
        Returns a checksum of the file using xxhash. If file is larger than 100MB, only parts of the file are used.
        """
        if file_size < 100 * 1024 * 1024:
            h = xxhash.xxh64()
            with open(filename, "rb") as f:
                h.update(f.read())
            return h.hexdigest() + "_xxh64"
        else:
            h = xxhash.xxh64()
            with open(filename, "rb") as f:
                h.update(f.read(5 * 1024 * 1024))  # Read the first 5MB
                f.seek(-5 * 1024 * 1024, SEEK_END)  # Seek to the last 5MB
                h.update(f.read())
            return h.hexdigest() + "_partial_xxh64"

    @staticmethod
    def create_directory(output_dir, path_name1, path_name2=None):
        """
        Creates a directory at 'output_dir/path_name1/path_name2' (if path_name2 is provided). Returns the directory path.
        """
        if path_name2 is None:
            directory = Path(output_dir) / path_name1
        else:
            directory = Path(output_dir) / path_name1 / path_name2
        if not directory.exists():
            directory.mkdir(parents=True)
            print(f"Directory '{directory}' has been created.")
        return directory


# DriveManager handles operations related to removable drives, such as detecting drives and calculating disk space.
class DriveManager:
    @staticmethod
    def get_removable_drives():
        """
        Returns a list of removable drives on the system.
        """
        drives = win32api.GetLogicalDriveStrings()
        drives = drives.split('\000')[:-1]
        return [drive[:-1] for drive in drives if win32file.GetDriveType(drive) == win32file.DRIVE_REMOVABLE]

    @staticmethod
    def get_disk_space(drive_letter):
        """
        Prints and returns the size of used space on the given removable drive.
        """
        drive_info = win32file.GetDiskFreeSpaceEx(drive_letter)
        total_bytes = drive_info[1]
        free_bytes = drive_info[0]
        used_bytes = total_bytes - free_bytes
        total_weight_gb = used_bytes / (1024 ** 3)
        disk_weight = round(total_weight_gb)
        print(f"Total size of files on disk {drive_letter[:-1]}: {total_weight_gb:.2f} GB")
        return disk_weight

    @staticmethod
    def create_drive_dir(output_dir, drive):
        """
        Creates a directory for copying files from a removable drive.
        """
        DriveManager.get_disk_space(drive)
        drive = drive[:-1]
        current_output_dir = FileManager.create_directory(output_dir, f"Drive_{drive}_copy")
        print(f"Current output directory for files from disk {drive}: {current_output_dir}\n")
        return current_output_dir


# NotificationManager handles sending system notifications.
class NotificationManager:
    @staticmethod
    def send_notification(title, message):
        """
        Sends a system notification with the given title and message.
        """
        notification = Notification(
            app_id="File Copy Assistant",
            title=title,
            msg=message,
            duration="short"
        )
        notification.set_audio(audio.Default, loop=False)
        notification.show()


# CopyManager manages the logic for copying files based on priority and other user-defined settings.
class CopyManager:
    def __init__(self, settings_manager, file_manager, drive_manager, notification_manager):
        """
        Initializes the CopyManager with the necessary managers for settings, file operations, drives, and notifications.

        Args:
            settings_manager (SettingsManager): Instance to manage user settings.
            file_manager (FileManager): Instance to manage file operations such as copying.
            drive_manager (DriveManager): Instance to manage removable drive detection and disk space.
            notification_manager (NotificationManager): Instance to send system notifications.
        """
        self.settings_manager = settings_manager
        self.file_manager = file_manager
        self.drive_manager = drive_manager
        self.notification_manager = notification_manager
        self.first_priority_notification = self.settings_manager.first_priority_notification
        self.notification_after_every_priority = self.settings_manager.notification_after_every_priority
        self.notify_after_all_transfers_finished = self.settings_manager.notify_after_all_transfers
        self.disabled_extensions = self.settings_manager.disabled_extensions
        self.state_file = self.settings_manager.state_file

    def walk_through_files(self, drive, output_dir, priority_list, copied, temp_state, wants_priority):
        """
        Walks through all files on the specified drive, checking their extensions and copying them based on priority settings.

        Args:
            drive (str): The removable drive to search for files.
            output_dir (str): The directory to copy files into.
            priority_list (list): List of prioritized file extensions to copy first.
            copied (set): Set of checksums representing files that have already been copied.
            temp_state (bool): Flag indicating whether to use a temporary state for this session.
            wants_priority (bool): Flag indicating whether the user wants to prioritize file types.

        Returns:
            tuple: lower_priority_files (dict) - Dictionary of lower-priority files by extension.
                   non_priority_files (set) - Set of non-priority files.
                   copied (set) - Updated set of copied file checksums.
        """
        # Initialize state and prepare containers for lower priority and non-priority files.
        lower_priority_files = {priority: set() for priority in priority_list[1:]}
        non_priority_files = set()
        self.temp_state = temp_state
        first_run = True
        size_of_copied = 0
        number_of_copied = 0
        if priority_list and wants_priority:
            self.enable_priority = True
        priority1_name = priority_list[0][1:].upper()
        priority1_message = "Priority 1 ({}).".format(priority1_name)
        for dirpath, subdirs, filenames in walk(drive):
            for filename in filenames:
                    old_file_path = Path(dirpath) / filename
                    file_size = self.file_manager.get_file_size(old_file_path)
                    checksum = self.file_manager.get_checksum(old_file_path, file_size)

                    # Skip already copied files.
                    if checksum in copied:
                        continue

                    extension = old_file_path.suffix.lower()

                    # Check priority settings and handle file copying accordingly.
                    if self.enable_priority:                       
                        if extension in priority_list:
                            if extension == priority_list[0].lower():
                                if first_run:
                                    print(f"Started {priority1_message}")
                                    new_file_path = self.file_manager.create_directory(output_dir, f"Priority_{priority_list[0][1:]}") / filename
                                    print(f"Started copying Priority 1 ({extension[1:].upper()}) files to {new_file_path}.\n")
                                    first_run = False
                                self.file_manager.copy_file(old_file_path, new_file_path)
                                copied.add(checksum)
                                size_of_copied += file_size
                                number_of_copied +=1
                            else:
                                lower_priority_files[extension].add((checksum, old_file_path, file_size))
                        else:
                            if extension not in self.disabled_extensions:
                                non_priority_files.add((checksum, old_file_path, file_size))
                    else:
                        # Copy all files if priority is disabled.
                        if extension not in self.disabled_extensions:
                            if first_run:
                                print(f"Started copying all files to {output_dir}")
                                first_run = False
                            new_file_path = self.file_manager.create_directory(output_dir, "All_files_copied")
                            self.file_manager.copy_file(old_file_path, new_file_path)
                            copied.add(checksum)
                            size_of_copied += file_size
                            number_of_copied +=1   
        print()

        if self.enable_priority:
            # Handle terminal output and notifications after finishing copying Priority 1 files.
            title = f"Finished {priority1_message}"
            print(title) 
            if number_of_copied > 0 and not self.temp_state:
                message = f"Copied {number_of_copied} files of total size of {size_of_copied / 1e9:.2f} GB."
                print(message)
                if not temp_state:
                    self.settings_manager.save_state(copied, self.state_file)
            else:
                message = f"No Priority 1 files ({priority1_name}) have been found. No files were copied in this priority."
                print(message)
                
            if self.first_priority_notification or self.notification_after_every_priority:                   
                self.notification_manager.send_notification(title, message)
        else:
            # Handle terminal outputs and notifications after finishing copying all files if priorities were disabled.
            title = f"Finished copying all files from disk {drive[":-1"]}"
            print(title)
            if number_of_copied > 0:
                message = f"Copied {number_of_copied} files of total size of {size_of_copied / 1e9:.2f} GB." 
                print(message) 
                # Save the current state of copied if the temporary state is not enabled
                if not temp_state:
                    self.settings_manager.save_state(copied, self.state_file)
            else:
                message = "No files were copied."
                print(message)
            if self.notify_after_all_transfers_finished:
                self.notification_manager.send_notification(title, message)
  
        return lower_priority_files, non_priority_files, copied

    def copy_other_priorities(self, lower_priority_files, output_dir, copied):
        """
        Copies files from the lower priority file set.

        Args:
            lower_priority_files (dict): A dictionary containing files of lower priority grouped by extension.
            output_dir (str): The directory to copy files into.
            copied (set): Set of checksums representing files that have already been copied.

        Returns:
            set: Updated set of copied file checksums.
        """
        if self.enable_priority:
            size_of_copied = 0
            number_of_copied = 0
            priority_count = 1
            notify_after_last = False
            for priority, files in lower_priority_files.items():
                priority_count += 1
                priority = priority[1:]
                if files:                 
                    print(f"Started Priority {priority_count} ({priority.upper()}).")
                    priority_dir = self.file_manager.create_directory(output_dir, f"Priority_{priority}")
                    print(f"Started copying Priority {priority.upper()} files to {output_dir}.\n")
                    for checksum, old_file_path, file_size in files:
                        new_file_path = priority_dir / old_file_path.name
                        self.file_manager.copy_file(old_file_path, new_file_path)
                        copied.add(checksum)
                        number_of_copied +=1
                        size_of_copied += file_size
                print()
                title = f"Finished Priority {priority_count} ({priority.upper()})."
                print(title)

                if number_of_copied > 0:
                    message = f"Copied {number_of_copied} files of total size of {size_of_copied / 1e9:.2f} GB."
                    print(message)
                    if not self.temp_state:
                        self.settings_manager.save_state(copied, self.state_file)
                else:
                    message = f"No {priority.upper()} files have been found. No files were copied in this priority."
                    print(message)         

                if self.notification_after_every_priority:
                    self.notification_manager.send_notification(title, message)
                else:
                    if self.settings_manager.notification_after_last_priority:
                        notify_after_last = True    
            if notify_after_last:
                self.notification_manager.send_notification(title, message)

        return copied

    def copy_non_priority(self, non_priority_files, output_dir, copied):
        """
        Copies all non-priority files.

        Args:
            non_priority_files (set): A set containing non-priority files.
            output_dir (str): The directory to copy files into.
            copied (set): Set of checksums representing files that have already been copied.

        Returns:
            set: Updated set of copied file checksums.
        """
        size_of_copied = 0
        number_of_copied = 0  
        if non_priority_files:
            print(f"Started Non-Priority.")
            non_priority_dir = self.file_manager.create_directory(output_dir, "Non-priority")
            print(f"Started copying Non-Priority files to {output_dir}.\n")
            for checksum, old_file_path, file_size in non_priority_files:
                new_file_path = non_priority_dir / old_file_path.name
                self.file_manager.copy_file(old_file_path, new_file_path)
                copied.add(checksum)
                number_of_copied +=1
                size_of_copied += file_size
        print()
        title = "Finished copying Non-Priority files"
        print(title + ".")
        if number_of_copied > 0:
            message = f"Copied {number_of_copied} files of total size of {size_of_copied / 1e9:.2f} GB."
            print(message)
            if not self.temp_state:
                self.settings_manager.save_state(copied, self.state_file)          
        else:
            message = f"No non-priority files have been found. No non-priority files were copied."
            print(message)
        
        if self.notify_after_all_transfers_finished:
                self.notification_manager.send_notification(title, message)
        print()
        return copied

def prompts(settings_manager):
    """
    Prompts the user for settings, such as output directory and priority options, before starting the file copy process.
    """
    output_dir = settings_manager.default_output_dir
    enable_priority = settings_manager.enable_priority
    print("This script copies files from removable drives to a specified directory.")
    print(f"Default output directory: {output_dir}")
    wants_another_dir = input("Do you want to change the output directory for this session? (y/n) ").lower()
    if wants_another_dir == "y":
        output_dir = input("Enter the new output directory path: ")
    wants_cleared_state_file = input("Do you want to clear the 'state.json' file before this session? (y/n) ")
    if wants_cleared_state_file == "y":
        settings_manager.create_state_file()
    wants_temp_state = input("Do you want to use an empty state of copied files for this session? (y/n) ")
    wants_temp_state = wants_temp_state.lower() == "y"
    if wants_temp_state:
        settings_manager.create_state_file(wants_temp_state)
    wants_priority = False
    if enable_priority:
        wants_priority = input("Do you want to disable the priority feature for this session? (y/n) ").lower() != "y"
    settings_manager.set_settings()
    return output_dir, wants_priority, wants_temp_state


def main():
    """
    Main function that initializes managers and starts the file copy process based on user input and settings.
    """
    settings_manager = SettingsManager()
    file_manager = FileManager()
    drive_manager = DriveManager()
    notification_manager = NotificationManager()
    copy_manager = CopyManager(settings_manager, file_manager, drive_manager, notification_manager)
    output_dir = settings_manager.default_output_dir

    if not settings_manager.skip_prompts:
        output_dir, wants_priority, temp_state = prompts(settings_manager)

    priority_list = settings_manager.priority_list if wants_priority else []

    if not temp_state:
        copied = settings_manager.get_copied()
    else:
        copied = set()

    while True:
        removable_drives = drive_manager.get_removable_drives()
        first_loop = True

        if removable_drives:
            print(f"\nDetected drives: {removable_drives}.\n")
            for drive in removable_drives:
                current_output_dir = drive_manager.create_drive_dir(output_dir, drive)
                lower_priority_files, non_priority_files, copied = copy_manager.walk_through_files(drive, current_output_dir, priority_list, copied, temp_state, wants_priority)

                if wants_priority:
                    copied = copy_manager.copy_other_priorities(lower_priority_files, current_output_dir, copied)
                if not settings_manager.copy_only_priority:
                    copy_manager.copy_non_priority(non_priority_files, current_output_dir, copied)
                    
            print("All transfers are finished. Exiting.\n") # you can comment this line if you run the program as a background service
            break # you can comment this line if you run the program as a background service

        elif first_loop:
            print("The program is ready and waiting for you to connect a removable drive.")
            first_loop = False

if __name__ == "__main__":
    main()
