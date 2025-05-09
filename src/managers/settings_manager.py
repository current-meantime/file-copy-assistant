from os import system
from platformdirs import user_downloads_dir
from pathlib import Path
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
            "Skip prompts": False,                              # if True, the user will not be prompted after the program is run and it will rely on settings alone
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
        self.last_priority_notification = self.settings.get("Enable notifications")["after last priority"]
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

