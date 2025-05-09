from pathlib import Path
from shutil import copy2
from datetime import datetime
from os import SEEK_END
import xxhash

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
    def create_directory_or_file(output_dir, path_name1, path_name2=None):
        """
        Creates a directory or file path at 'output_dir/path_name1/path_name2' (if path_name2 is provided). Returns the directory/file path.
        """
        if path_name2 is None:
            directory = Path(output_dir) / path_name1
        else:
            directory = Path(output_dir) / path_name1 / path_name2
        if not directory.exists():
            directory.mkdir(parents=True)
            print(f"Directory '{directory}' has been created.")
        return directory
