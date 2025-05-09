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