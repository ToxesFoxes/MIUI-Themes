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


def get_theme_config():
    global theme_config
    if theme_config is None:
        from theme_config import theme_config as config
        theme_config = config
    return theme_config


def lock_task(name, silent=True):
    path = get_theme_config().get_path(f"theme_builder/build/lock/{name}.lock")
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
                            f"task {name} is locked by another process, waiting for it to unlock.")
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
    path = get_theme_config().get_path(f"theme_builder/build/lock/{name}.lock")
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


THEME_LOC = get_theme_config().get_value("pushDir")
THEME_NAME = get_theme_config().get_value("projectDir")+".mtz"
THEME_VERSION = "20.11.3_1604391099"


def task_assemble_zip(input_name, output_name, extension):
    import shutil
    input_dir = get_theme_config().get_path(input_name)
    output_dir = get_theme_config().get_path(
        "output/"+theme_config.get_value("projectDir")+"/"+output_name)
    shutil.make_archive(output_dir, 'zip', input_dir)
    os.rename(output_dir+'.zip', output_dir+extension)
    return 0


@task("test")
def test():
    print(THEME_NAME)
    return 0


@task("build_modules")
def task_build_modules():
    for input_name in theme_config.get_value("modules"):
        output_name = theme_config.get_value("modules")[input_name]
        task_assemble_zip(theme_config.get_value(
            "projectDir") + "/"+input_name, output_name, '')
    return 0


@task("build_additional")
def task_build_additional():
    for input_name in theme_config.get_value("additional"):
        output_name = theme_config.get_value("additional")[input_name]
        input_dir = get_theme_config().get_path(
            theme_config.get_value("projectDir")+"/"+input_name)
        output_dir = get_theme_config().get_path(
            "output/"+theme_config.get_value("projectDir")+"/"+output_name)
        copy_directory(input_dir, output_dir)
    return 0


@task("build_info")
def task_build_info():
    filename = "description.xml"
    output_dir = get_theme_config().get_path(
        "output/"+theme_config.get_value("projectDir")+"/"+filename)
    file_data = open(output_dir, "w")
    data = theme_config.get_value("description")
    file_data.write(build_description(data))
    return 0


@task("build_release")
def task_build_release():
    task_build_theme()
    task_assemble_zip(
        "output/"+theme_config.get_value("projectDir")+"/", '', ".mtz")
    return 0


@task("build_all")
def task_build_theme():
    task_build_additional()
    task_build_modules()
    task_build_info()
    return 0


@task("cleanup")
def task_cleanup():
    output_dir = get_theme_config().get_path("output")
    clear_directory(output_dir)
    return 0


@task("push")
def task_push():
    from push import push
    src_file = get_theme_config().get_path("output")+"/" + THEME_NAME
    dst_path = THEME_LOC
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
    call([theme_config.get_adb(), "tcpip", port],
         stdout=devnull, stderr=devnull)
    result = call([theme_config.get_adb(), "connect", ip])
    return result


@task("launch_theme_app")
def task_launch_theme_app():
    from subprocess import call
    result = call([theme_config.get_adb(), "shell", "monkey", "-p", "com.android.thememanager",
                   "-c", "android.intent.category.LAUNCHER", "1"], stdout=devnull, stderr=devnull)
    if result != 0:
        print(
            "\033[91mno devices/emulators found, try to use task \"Connect to ADB\"\033[0m")
    return 0


@task("stop_theme_app")
def task_stop_theme_app():
    from subprocess import call
    result = call([theme_config.get_adb(), "shell", "am", "force-stop",
                   "com.android.thememanager"], stdout=devnull, stderr=devnull)
    if result != 0:
        print(
            "\033[91mno devices/emulators found, try to use task \"Connect to ADB\"\033[0m")
    return result


@task("apply_theme")
def task_apply_theme():
    from subprocess import call
    command = "am start -n com.android.thememanager/com.android.thememanager.ApplyThemeForScreenshot -e \"" + "theme_file_path" + \
        "\" \"" + THEME_LOC + THEME_NAME + "\" " + \
        " -e \"api_called_from\" \"ThemeEditor_" + THEME_VERSION + "\""

    progress = 0
    print_progress_bar(progress, 7, suffix='', length=50)

    result = call([theme_config.get_adb(), "shell", command],
                  stdout=devnull, stderr=devnull)
    if result != 0:
        print(
            "\033[91mno devices/emulators found, try to use task \"Connect to ADB\"\033[0m")
        print_progress_bar(
            progress, 7, suffix=f'Error!' + (" " * 20), length=50)

    if result == 0:
        while progress < 7:
            print_progress_bar(
                progress, 7, suffix=f'Applying!' + (" " * 20), length=50)
            time.sleep(1)
            progress += 1
        print_progress_bar(
            progress, 7, suffix=f'Complete!' + (" " * 20), length=50)
    return result


def error(message, code=-1):
    sys.stderr.write(message + "\n")
    unlock_all_tasks()
#    input("Press enter to continue...")
    exit(code)


if __name__ == '__main__':
    if len(sys.argv[1:]) > 0:
        for task_name in sys.argv[1:]:
            if task_name in registered_tasks:
                try:
                    result = registered_tasks[task_name]()
                    if result != 0:
                        error(
                            f"task {task_name} failed with result {result}", code=result)
                except BaseException as err:
                    if isinstance(err, SystemExit):
                        raise err

                    import traceback
                    traceback.print_exc()
                    error(f"task {task_name} failed with above error")
    else:
        error("no tasks to execute")
    unlock_all_tasks()
