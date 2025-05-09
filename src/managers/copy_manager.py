from pathlib import Path
from os import walk

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
        self.last_priority_notification = self.settings_manager.last_priority_notification
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
        temp_state = temp_state
        first_run = True
        size_of_copied = 0
        number_of_copied = 0
        enable_priority = bool(priority_list and wants_priority)

        if enable_priority:
            priority1_name = priority_list[0][1:].upper()
            priority1_message = f"Priority 1 ({priority1_name})."
        else:
            priority1_name = priority1_message = None  # Or just skip entirely

        for dirpath, subdirs, filenames in walk(drive):
            for filename in filenames:
                old_file_path = Path(dirpath) / filename
                file_size = self.file_manager.get_file_size(old_file_path)
                checksum = self.file_manager.get_checksum(old_file_path, file_size)

                # Skip already copied files.
                if checksum in copied:
                    continue

                extension = old_file_path.suffix.lower()

                # Check if priority is enabled and handle file copying accordingly.
                if enable_priority:
                    if extension in priority_list:
                        if extension == priority_list[0].lower():
                            if first_run:
                                print(f"Started {priority1_message}")
                                new_dir_path = self.file_manager.create_directory_or_file(output_dir,
                                                                                           f"Priority_{priority_list[0][1:]}")
                                print(f"Started copying {priority1_message}) files to {new_dir_path}.\n")
                                first_run = False
                            new_file_path = self.file_manager.create_directory_or_file(output_dir,
                                                                                       f"Priority_{priority_list[0][1:]}") / filename
                            # Copy the current file immediately since its extension is the first priority
                            self.file_manager.copy_file(old_file_path, new_file_path)
                            copied.add(checksum)
                            size_of_copied += file_size
                            number_of_copied += 1
                        else:
                            # Add the current file to the priority queue since its extension is still in the priority list
                            lower_priority_files[extension].add((checksum, old_file_path, file_size))
                    else:
                        # Add the current file at the end of queue since its not a priority
                        if extension not in self.disabled_extensions:
                            non_priority_files.add((checksum, old_file_path, file_size))
                else:
                    # Copy all files if priority is disabled.
                    if extension not in self.disabled_extensions:
                        new_file_path = self.file_manager.create_directory_or_file(output_dir, "All_files_copied")
                        if first_run:
                            print(f"Started copying all files to {new_file_path}")
                            first_run = False
                        self.file_manager.copy_file(old_file_path, new_file_path)
                        copied.add(checksum)
                        size_of_copied += file_size
                        number_of_copied += 1

        print()
        message = f"Copied {number_of_copied} files of total size of {size_of_copied / 1e9:.2f} GB."
        if enable_priority:
            # Handle terminal output and notifications on finishing the copying of Priority 1
            title = f"Finished {priority1_message}"
            print(title)
            if number_of_copied > 0 and not temp_state:
                print(message)
                # Save the current state of copied if the temporary state is not enabled
                if not temp_state:
                    self.settings_manager.save_state(copied, self.state_file)
            else:
                message = f"No Priority 1 files ({priority1_name}) have been found. No files were copied in this priority."
                print(message)

            if self.first_priority_notification or self.notification_after_every_priority:
                self.notification_manager.send_notification(title, message)
        else:
            # Handle terminal outputs and notifications on copying all of the files
            title = f"Finished copying all files from disk {drive[:-1]}"
            print(title)
            if number_of_copied > 0:
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


    def copy_other_priorities(self, lower_priority_files, output_dir, copied, temp_state):
        """
        Copies files from the lower priority file set.

        Args:
            lower_priority_files (dict): A dictionary containing files of lower priority grouped by extension.
            output_dir (str): The directory to copy files into.
            copied (set): Set of checksums representing files that have already been copied.
            temp_state (bool): Flag indicating whether to use a temporary state for this session.

        Returns:
            set: Updated set of copied file checksums.
        """
        size_of_copied = 0
        number_of_copied = 0
        priority_count = 1          # starting with '1' since Priority 1 was handled in walk_through_files()
        notify_after_last = False   # in order not to send double messages if both "notify after every priority" and "notify after last" are enabled

        for priority, files in lower_priority_files.items():
            priority_count += 1
            priority = priority[1:].upper() # getting rid of '.' from the beginning of the extension
            if files:
                print(f"Started Priority {priority_count} ({priority}).")
                # Create a directory based on what the current priority is
                priority_dir = self.file_manager.create_directory_or_file(output_dir, f"Priority_{priority}")
                print(f"Started copying Priority {priority} files to {priority_dir}.\n")
                for checksum, old_file_path, file_size in files:
                    new_file_path = priority_dir / old_file_path.name
                    self.file_manager.copy_file(old_file_path, new_file_path)
                    copied.add(checksum)
                    number_of_copied +=1
                    size_of_copied += file_size
            print()

            # Handle terminal output messages
            title = f"Finished Priority {priority_count} ({priority})."
            print(title)
            if number_of_copied > 0:
                message = f"Copied {number_of_copied} files of total size of {size_of_copied / 1e9:.2f} GB."
                print(message)
                # Save the current state of copied if the temporary state is not enabled
                if not temp_state:
                    self.settings_manager.save_state(copied, self.state_file)
            else:
                message = f"No {priority} files have been found. No files were copied in this priority."
                print(message)

        # Handle notifications
            if self.notification_after_every_priority:
                self.notification_manager.send_notification(title, message)
            else:
                # Sets the flag 'notify_after_last' to True
                # only if 'notification after last priority' is enabled and 'notification after every priority' is not
                # to ensure the notification doesn't pop-up twice
                if self.last_priority_notification:
                    notify_after_last = True
        if notify_after_last:
            title = "Copied last priority files"
            message = f"Copied {number_of_copied} files of total size of {size_of_copied / 1e9:.2f} GB."
            self.notification_manager.send_notification(title, message)

        return copied

    def copy_non_priority(self, non_priority_files, output_dir, copied, temp_state):
        """
        Copies all non-priority files.

        Args:
            non_priority_files (set): A set containing non-priority files.
            output_dir (str): The directory to copy files into.
            copied (set): Set of checksums representing files that have already been copied.
            temp_state (bool): Whether or not to save the state of copied files into the state file.

        Returns:
            set: Updated set of copied file checksums.
        """
        size_of_copied = 0
        number_of_copied = 0

        if non_priority_files:
            print(f"Started Non-Priority.")
            # Create a directory for all non-priority files in the parent drive output directory
            non_priority_dir = self.file_manager.create_directory_or_file(output_dir, "Non-priority")
            print(f"Started copying Non-Priority files to {non_priority_dir}.\n")
            for checksum, old_file_path, file_size in non_priority_files:
                new_file_path = non_priority_dir / old_file_path.name
                self.file_manager.copy_file(old_file_path, new_file_path)
                copied.add(checksum)
                number_of_copied +=1
                size_of_copied += file_size
        print()
        # Handle terminal output messages
        title = "Finished copying Non-Priority files"
        print(title + ".")
        if number_of_copied > 0:
            message = f"Copied {number_of_copied} files of total size of {size_of_copied / 1e9:.2f} GB."
            print(message)
            # Save the current state of copied if the temporary state is not enabled
            if not temp_state:
                self.settings_manager.save_state(copied, self.state_file)
        else:
            message = f"No non-priority files have been found. No non-priority files were copied."
            print(message)
        # Notify that all transfers are finished if this feature is enabled
        if self.notify_after_all_transfers_finished:
                self.notification_manager.send_notification(title, message)
        print()

        return copied
