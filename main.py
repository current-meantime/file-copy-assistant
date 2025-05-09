from src.managers.settings_manager import SettingsManager
from src.managers.file_manager import FileManager
from src.managers.drive_manager import DriveManager
from src.managers.notification_manager import NotificationManager
from src.managers.copy_manager import CopyManager
from src.utils.prompts import prompts


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
    wants_priority = settings_manager.enable_priority
    temp_state = False

    if not settings_manager.skip_prompts:
        output_dir, wants_priority, temp_state = prompts(settings_manager)

    priority_list = settings_manager.priority_list if wants_priority else []

    if not temp_state:
        copied = settings_manager.get_copied()
    else:
        copied = set()

    first_loop = True

    while True:
        removable_drives = drive_manager.get_removable_drives()

        if removable_drives:
            print(f"\nDetected drives: {removable_drives}.\n")
            for drive in removable_drives:
                current_output_dir = drive_manager.create_drive_dir(output_dir, drive)
                lower_priority_files, non_priority_files, copied = copy_manager.walk_through_files(
                    drive, current_output_dir, priority_list, copied, temp_state, wants_priority
                )

                if wants_priority:
                    copied = copy_manager.copy_other_priorities(lower_priority_files, current_output_dir, copied, temp_state)
                    if not settings_manager.copy_only_priority:
                        copy_manager.copy_non_priority(non_priority_files, current_output_dir, copied, temp_state)

            print("All transfers are finished. Exiting.\n")
            break

        elif first_loop:
            print("The program is ready and waiting for you to connect a removable drive.")
            first_loop = False


if __name__ == "__main__":
    main()