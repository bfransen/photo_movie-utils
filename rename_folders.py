import os
import re
import shutil
import argparse
from datetime import datetime

def convert_date_format(original_date):
    # Convert the string to a datetime object
    date_object = datetime.strptime(original_date, "%B %d, %Y")

    # Format the datetime object as YYYY-MM-DD
    formatted_date = date_object.strftime("%Y-%m-%d")

    return formatted_date

def rename_folders(input_path, output_file=None):
    renamed_folders = []

    for root, dirs, files in os.walk(input_path):
        for folder in dirs:
            folder_path = os.path.join(root, folder)

            # Extract date from the folder name using a regular expression
            match = re.search(r'(\b\w+ \d+, \d+\b)', folder)
            if match:
                original_date = match.group(0)
                new_date = convert_date_format(original_date)
                # Convert original date to YYYY-MM-DD format
                #new_date = re.sub(r'(\w+) (\d+), (\d+)', r'\3-\1-\2', original_date)
                #new_date = new_date.replace(" ", "_")

                # Create new folder name
                new_folder_name = f"{new_date}_{folder.replace(' ', '_')}"
                new_folder_name = new_folder_name.replace(',','')
                new_folder_name = new_folder_name.replace('_-_','_')

                # Rename the folder or add to the list for text output
                renamed_folders.append((folder_path, new_folder_name))
                new_folder_path = os.path.join(root, new_folder_name)
                shutil.move(folder_path, new_folder_path)
            else:
                output_file.append(f'No match - {folder_path}')

    if output_file:
        with open(output_file, 'w') as file:
            for original, renamed in renamed_folders:
                file.write(f"{original} -> {renamed}\n")
        print(f"Renamed folders information written to {output_file}")
    else:
        print("Folders renamed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename folders based on date in the format Month Day, Year.")
    parser.add_argument("input_path", help="Path to the root directory to start renaming from.")
    parser.add_argument("-o", "--output", help="Output file for renamed folders information.")

    args = parser.parse_args()
    rename_folders(args.input_path, args.output)
