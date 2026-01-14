import os
import re
import shutil
import argparse
from datetime import datetime


def delete_by_filename(input_path, output_file=None):
    deleted_files = []
    delete_mode = True
    file_name_index = 1

    for root, dirs, files in os.walk(input_path):
        for dir1 in dirs:
            for subroot, subdirs, subfiles in os.walk(os.path.join(root, dir1)):
                for file in subfiles:
                    file_path = os.path.join(root, dir1, file)
                    file_path = remove_bad_characters_from_filename(dir1, file, file_name_index, file_path, root)
                    file_name_index = file_name_index + 1
                    if file.startswith("._") and os.path.getsize(file_path) < 4500:
                        deleted_files.append(file_path)
                        if delete_mode:
                            os.remove(file_path)
    if deleted_files:
        with open(output_file, 'w') as file:
            for name in deleted_files:
                print(name)
                file.write(f"{name.replace('\u2a31','').replace('\u02bb','')}\n")
        print(f"Deleted files information written to {output_file}")
    else:
        print("No files to delete.")


def remove_bad_characters_from_filename(dir1, file, file_name_index, file_path, root):
    if "chat-media-video" in file:
        sanitized_file_path = os.path.join(root, dir1, f"chat-media-video{file_name_index}")
        shutil.move(file_path, sanitized_file_path)
        file_path = sanitized_file_path
    return file_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete files that start with ._ and are 4k or under")
    parser.add_argument("input_path", help="Path to the root directory to start deleting from.")
    parser.add_argument("-o", "--output", help="Output file for deleted files information.")

    args = parser.parse_args()
    delete_by_filename(args.input_path, args.output)
