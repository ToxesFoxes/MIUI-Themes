import os
import os.path
import subprocess

from theme_config import themes_config
from progress_bar import print_progress_bar

# /dev/null
ignore = open(os.devnull, "w")
ADB = themes_config.get_adb()


def push(src_file, dst_path):
    result = subprocess.call([ADB, "devices"], stderr=ignore, stdout=ignore)
    if result != 0:
        print(
            '\033[91mno devices/emulators found, try to use task "Connect to ADB"\033[0m'
        )
        return result

    progress = 0
    print_progress_bar(progress, 1, suffix="", length=50)
    result = subprocess.call(
        [ADB, "push", src_file, dst_path], stderr=ignore, stdout=ignore
    )

    if result != 0:
        print_progress_bar(progress, 1, suffix=f"Error!" + (" " * 20), length=50)
        print(
            f"failed to push {src_file} to directory {dst_path} with result code {result}\n"
        )
        return result
    if result == 0:
        progress += 1
        print_progress_bar(progress, 1, suffix=f"Complete!" + (" " * 20), length=50)

    return result


def theme_locks(*locks):
    dst = "/sdcard/MIUI/theme/"
    if dst is None:
        return -1

    for lock in locks:
        lock = os.path.join(dst, lock).replace("\\", "/")
        result = subprocess.call([ADB, "shell", "touch", lock])
        if result != 0:
            return result
    return 0
