# File Copy Assistant

**File Copy Assistant** is a Python utility designed to automate the process of copying files from removable drives (USB drives, external hard disks) to a specified directory on your machine. The program allows you to prioritize specific file extensions, skip unnecessary file types, and provides notifications for completed tasks.

## Features

- **Prioritized File Copying**: You can set which file extensions should be prioritized for copying (e.g., `.jpg`, `.mp4`).
- **Exclusion of Certain File Types**: Easily exclude unwanted file types such as `.dat` or `.sav` from being copied.
- **Customizable Notifications**: Get notifications when the copying process is complete or after each priority level is processed.
- **Skip Already Copied Files**: The program maintains a `state.json` file that tracks copied files using checksums, preventing duplicate transfers.
- **Configurable Output Directory**: Choose where the files should be copied to, or use the default system downloads folder.
- **Interactive Setup**: The program includes prompts that allow you to adjust settings on-the-fly for each session.
- **Non-Priority File Handling**: In addition to copying prioritized files, the program can also handle all non-priority files.
- **Checksum-Based File Verification**: Files are verified with xxhash-based checksums to ensure the same files are not copied multiple times, even if they repeat across directories or drives.

## Installation

### Prerequisites

- Python 3.x
- `pip` for installing dependencies

### Required Libraries

The required libraries include standard Python libraries and the following non-standard libraries:

    platformdirs
    xxhash
    win32file
    win32api
    winotify

Install the required Python packages using the following command:

`pip install platformdirs xxhash pypiwin32 winotify`

## Setup
1. Clone this repository:

```
    git clone https://github.com/current-meantime/file-copy-assistant.git
    cd file-copy-assistant
```

2. Set up the required libraries by running the pip install command.

3. Adjust the settings in the settings.json file after the first run, or use the program’s interactive prompt to configure it. 

## Usage

To run the program, simply execute:
```
python file_copy_assistant.py
```

## Program Flow

1. Interactive Prompts (optional):
    * Change the default output directory.
    * Clear or create a new state file.
    * Enable or disable priority-based copying for the session.
2. Detecting Drives: The program waits for a removable drive to be connected.
3. File Copying:
    * Files are copied according to their priority, with the option to skip unwanted extensions.
    * Non-priority files can be copied at the end.
4. Notifications: Notifications are sent when copying is complete or after each priority level, depending on user settings.

## Settings

The settings.json file is automatically created on first run and stores user preferences:

```json

{
    "Prioritized file extensions": [".jpg", ".mp4"],
    "Disabled file extensions": [".dat", ".sav"],
    "Enable notifications": {
        "after all transfers are finished": true,
        "after every priority": true,
        "after first priority": false,
        "after last priority": false
    },
    "Default output directory": "path/to/output/dir",
    "Copy only priority files": false,
    "Skip prompts": false,
    "Enable priority": true
}
```
Bear in mind that the first extension in the "Prioritized file extensions" list will be treated as the main priority.

You can add as many prioritized and disabled extensions as you wish.

## Example

1. Upon starting, the program will ask whether you want to change the default output directory for this session and provide other configuration prompts.
2. The program will detect connected removable drives and start copying files based on the priority rules in settings.json.


### TODO:
* Fix Issue: fix counting file size of copied files