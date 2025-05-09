import win32file
import win32api
from .file_manager import FileManager

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
        current_output_dir = FileManager().create_directory_or_file(output_dir, f"Drive_{drive}_copy")
        print(f"Current output directory for files from disk {drive}: {current_output_dir}\n")
        return current_output_dir
