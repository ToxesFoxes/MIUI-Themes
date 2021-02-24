import os
import os.path
import sys
import time

from utils import *
from desc_builder import *
from progress_bar import print_progress_bar


theme_config = None
registered_tasks = {}
locked_tasks = {}
devnull = open(os.devnull, "w")


def get_themes_config():
    global theme_config
    if theme_config is None:
        from theme_config import themes_config as config

        theme_config = config
    return theme_config


CONFIG = get_themes_config()


def lock_task(name, silent=True):
    path = CONFIG.get_path(f"theme_builder/build/lock/{name}.lock")
    ensure_file_dir(path)
    await_message = False

    if os.path.exists(path):
        while True:
            try:
                if os.path.exists(path):
                    os.remove(path)
                break
            except IOError as _:
                if not await_message:
                    await_message = True
                    if not silent:
                        sys.stdout.write(
                            f"task {name} is locked by another process, waiting for it to unlock."
                        )
                    if name in locked_tasks:
                        error("ERROR: dead lock detected", code=-2)
                if not silent:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                time.sleep(0.5)
    if await_message:
        if not silent:
            print("")
    open(path, "tw").close()
    locked_tasks[name] = open(path, "a")


def unlock_task(name):
    if name in locked_tasks:
        locked_tasks[name].close()
        del locked_tasks[name]
    path = CONFIG.get_path(f"theme_builder/build/lock/{name}.lock")
    if os.path.isfile(path):
        os.remove(path)


def unlock_all_tasks():
    for name in list(locked_tasks.keys()):
        unlock_task(name)


def task(name, lock=None):
    if lock is None:
        lock = []

    def decorator(func):
        def caller(*args, **kwargs):
            lock_task(name, silent=False)
            for lock_name in lock:
                lock_task(lock_name, silent=False)
            os.system("color")
            print(f"\033[92m> executing task: {name}\033[0m")
            task_result = func(*args, **kwargs)
            unlock_task(name)
            for lock_name in lock:
                unlock_task(lock_name)
            return task_result

        registered_tasks[name] = caller
        return caller

    return decorator


THEME_DEST_LOC = CONFIG.get("push_directory")
# print(THEME_DEST_LOC)
THEME_LIST = CONFIG.get("project_list")
THEMES_ROOT = CONFIG.get("root_directory")
THEME_NAME = CONFIG.get("project_folder")
THEME_CFG = CONFIG.getCurrentThemeJSON(THEMES_ROOT, THEME_NAME)
# print(THEME_CFG)
THEME_OUT_NAME = THEME_NAME + ".mtz"
THEME_VERSION = "20.11.3_1604391099"
# print(THEMES_ROOT)
THEME_MODULES = THEME_CFG.get("modules")
THEME_ADDITIONAL = THEME_CFG.get("additional")
THEME_DESCRIPTION = THEME_CFG.get("description")


def task_assemble_zip(input_name, output_name, extension):
    import shutil

    input_dir = CONFIG.get_path(input_name)
    output_dir = CONFIG.get_path("output/" + THEME_NAME + "/" + output_name)
    shutil.make_archive(output_dir, "zip", input_dir)
    os.rename(output_dir + ".zip", output_dir + extension)
    return 0


@task("test")
def test():
    print(THEME_OUT_NAME)
    return 0


@task("build_modules")
def task_build_modules():
    for input_name in THEME_MODULES:
        output_name = THEME_MODULES[input_name]
        print("Building: " + input_name)
        task_assemble_zip(
            THEMES_ROOT + "/" + THEME_NAME + "/" + input_name, output_name, ""
        )
    return 0


@task("build_additional")
def task_build_additional():
    for input_name in THEME_ADDITIONAL:
        output_name = THEME_ADDITIONAL[input_name]
        input_dir = CONFIG.get_path(THEMES_ROOT + "/" + THEME_NAME + "/" + input_name)
        output_dir = CONFIG.get_path("output/" + THEME_NAME + "/" + output_name)
        print("Building additional: " + input_name)
        copy_directory(input_dir, output_dir)
    return 0


@task("build_info")
def task_build_info():
    filename = "description.xml"
    output_dir = CONFIG.get_path("output/" + THEME_NAME + "/" + filename)
    file_data = open(output_dir, "w")
    print(THEME_DESCRIPTION['description']+" by "+THEME_DESCRIPTION['author'])
    file_data.write(build_description(THEME_DESCRIPTION))
    return 0


@task("build_release")
def task_build_release():
    task_build_theme()
    task_assemble_zip("output/" + THEME_NAME + "/", "", ".mtz")
    return 0


@task("build_all")
def task_build_theme():
    task_build_additional()
    task_build_modules()
    task_build_info()
    return 0


@task("cleanup")
def task_cleanup():
    output_dir = CONFIG.get_path("output")
    clear_directory(output_dir)
    return 0


@task("push")
def task_push():
    from push import push

    src_file = CONFIG.get_path("output") + "/" + THEME_OUT_NAME
    dst_path = THEME_DEST_LOC
    return push(src_file, dst_path)


@task("connectToADB")
def task_connect_to_adb():
    import re

    ip = None
    port = None
    pattern = re.compile(r"(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}):(\d{4})")
    for arg in sys.argv:
        match = pattern.search(arg)
        if match:
            ip = match[0]
            port = match[1]

    if ip is None:
        print("incorrect IP-address")
        return 1

    print(f"connecting to {ip}")

    from subprocess import call

    call([theme_config.get_adb(), "disconnect"], stdout=devnull, stderr=devnull)
    call([theme_config.get_adb(), "tcpip", port], stdout=devnull, stderr=devnull)
    result = call([theme_config.get_adb(), "connect", ip])
    return result


@task("launch_theme_app")
def task_launch_theme_app():
    from subprocess import call

    result = call(
        [
            theme_config.get_adb(),
            "shell",
            "monkey",
            "-p",
            "com.android.thememanager",
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ],
        stdout=devnull,
        stderr=devnull,
    )
    if result != 0:
        print(
            '\033[91mno devices/emulators found, try to use task "Connect to ADB"\033[0m'
        )
    return 0


@task("stop_theme_app")
def task_stop_theme_app():
    from subprocess import call

    result = call(
        [
            theme_config.get_adb(),
            "shell",
            "am",
            "force-stop",
            "com.android.thememanager",
        ],
        stdout=devnull,
        stderr=devnull,
    )
    if result != 0:
        print(
            '\033[91mno devices/emulators found, try to use task "Connect to ADB"\033[0m'
        )
    return result


@task("apply_theme")
def task_apply_theme():
    from subprocess import call

    command = (
        'am start -n com.android.thememanager/com.android.thememanager.ApplyThemeForScreenshot -e "'
        + "theme_file_path"
        + '" "'
        + THEME_DEST_LOC
        + THEME_OUT_NAME
        + '" '
        + ' -e "api_called_from" "ThemeEditor_'
        + THEME_VERSION
        + '"'
    )

    progress = 0
    print_progress_bar(progress, 7, suffix="", length=50)

    result = call(
        [theme_config.get_adb(), "shell", command], stdout=devnull, stderr=devnull
    )
    if result != 0:
        print(
            '\033[91mno devices/emulators found, try to use task "Connect to ADB"\033[0m'
        )
        print_progress_bar(progress, 7, suffix=f"Error!" + (" " * 20), length=50)

    if result == 0:
        while progress < 7:
            print_progress_bar(progress, 7, suffix=f"Applying!" + (" " * 20), length=50)
            time.sleep(1)
            progress += 1
        print_progress_bar(progress, 7, suffix=f"Complete!" + (" " * 20), length=50)
    return result


def error(message, code=-1):
    sys.stderr.write(message + "\n")
    unlock_all_tasks()
    #    input("Press enter to continue...")
    exit(code)


if __name__ == "__main__":
    if len(sys.argv[1:]) > 0:
        for task_name in sys.argv[1:]:
            if task_name in registered_tasks:
                try:
                    result = registered_tasks[task_name]()
                    if result != 0:
                        error(
                            f"task {task_name} failed with result {result}", code=result
                        )
                except BaseException as err:
                    if isinstance(err, SystemExit):
                        raise err

                    import traceback

                    traceback.print_exc()
                    error(f"task {task_name} failed with above error")
    else:
        error("no tasks to execute")
    unlock_all_tasks()
