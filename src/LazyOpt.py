import queue; import sys; import platform; import os; from pathlib import Path; import datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess as s; s.run("", shell=True)

#LazyOpt, 2026 made by AlanCodes0 on Youtube, or Alanbutidk on Github!
#Uses the GPL3.0 license
#Modify it as much as you want!
#---------------------------------------------------------------------------------------------------------------------------------------------------------------

#::Random helper functions::
def CheckForLinuxExecutables(filename):
    if not os.path.isfile(filename):
        return False
    if not os.access(filename, os.X_OK):
        return False
    try:
        with open(filename, 'rb') as f:
            if f.read(4) == b'\x7fELF':
                return True
    except IOError:
        return False
    return False

def ShutDownDoIt(action, integer):
    if not isinstance(integer, int):
        print("\x1b[31mTime must be an integer\033[0m")
        return
    print(f"{'Shutting down' if action == 'shutdown' else 'Rebooting'} in {integer} seconds...")
    if platform.system() == "Windows":
        flag = "/s" if action == "shutdown" else "/r"
        s.run(["shutdown", flag, "/t", str(integer)])
    elif platform.system() in ("Linux", "Darwin"):
        cmd = "poweroff" if action == "shutdown" else "reboot"
        s.run(f"sleep {integer} && sudo systemctl {cmd}", shell=True)
    else:
        print("\x1b[31mCould not determine OS!\033[0m")

#print("LAZYOPT Logo + commands")
if len(sys.argv) < 2:
    print("\x1b[33m" + """\
██╗      █████╗ ███████╗██╗   ██╗ ██████╗ ██████╗ ████████╗
██║     ██╔══██╗╚══███╔╝╚██╗ ██╔╝██╔═══██╗██╔══██╗╚══██╔══╝
██║     ███████║  ███╔╝  ╚████╔╝ ██║   ██║██████╔╝   ██║   
██║     ██╔══██║ ███╔╝    ╚██╔╝  ██║   ██║██╔═══╝    ██║   
███████╗██║  ██║███████╗   ██║   ╚██████╔╝██║        ██║   
╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝        ╚═╝""" + "\033[0m")
    print("1: pathto <Filename> <InDrive (optional)>")
    print("2: run <whatever (full path or else taken from $PATH)>")
    print("3: shutd <Option(s): --time <whatever>>")
    print("4: reboot <Option(s): --time <whatever>>")
    print("5: log <Text> <Filename>")
    print("6: licversion <NameOfLic <Options: \"gpl3\", \"MIT\">> <Optional: Filename>:\n Gives the version info needed to put in a console program for the license given")
    print("7: lserver <Option(s)>: Launches server.exe with optional args.\n   lserver                    -> file browser on :8080\n   lserver 9000               -> file browser on :9000\n   lserver <file.html>        -> serve single file on :8080\n   lserver <file.html> 9000   -> serve single file on :9000\n   lserver file_sharing 9000  -> file browser on :9000\n   lserver tunnel 5555        -> encrypted AES tunnel")
    print("8: kprocess <PID/ProcessName>: kills the process with the PID/ProcessName given.")
    print("9: getccinfo <CCName (case-sensetive)>: gives the compiler info.")
    print("10: listpath: Lists everything in PATH")

args = sys.argv[1:]

#pathto start (QUEUE-BASED)
if "pathto" in args:
    wherepathto = args.index("pathto")
    filename = args[wherepathto + 1]
    drive = args[wherepathto + 2] if wherepathto + 2 < len(args) else None
    if drive is None:
        if platform.system() == "Windows": dirQueue = "C:/"
        elif platform.system() == "Linux": dirQueue = "/"
    elif not drive is None: dirQueue = drive
    else: raise NotADirectoryError("Drive was not found or some else error")
    found = []
    q = queue.Queue()
    q.put(dirQueue)
    def scan(current):
        results = []
        try:
            for entry in os.scandir(current):
                try:
                    if entry.is_file(follow_symlinks=False):
                        if entry.name == filename:
                            results.append(entry.path)
                    elif entry.is_dir(follow_symlinks=False):
                        q.put(entry.path)
                except (PermissionError, KeyboardInterrupt, OSError):
                    pass
        except (PermissionError, KeyboardInterrupt, OSError):
            pass
        return results
    with ThreadPoolExecutor() as executor:
        while not q.empty():
            futures = [executor.submit(scan, q.get()) for _ in range(min(q.qsize() or 1, 32))]
            for f in futures:
                found.extend(f.result())
            print(f"\r\033[33mscanning... {len(found)} found, {q.qsize()} dirs queued\033[0m", end="")
    print()
    if found:
        for p in found: print(p)
    else:
        print(f"'{filename}' not found in {dirQueue}")

#run start
if "run" in args:
    whererun = args.index("run")
    if whererun + 1 >= len(args):
        print("Argument was not given with [run]!")
    else:
        filename = args[whererun + 1]
        extens = Path(filename).suffix.lower()
        if extens == ".exe":
            if platform.system() == "Windows": s.run([filename])
            else: print("\x1b[31mThis system is not Windows! Maybe try running Wine (if you have it?)\033[0m")
        elif extens == ".py":
            s.run([sys.executable, filename], text=True)
        elif extens == ".html":
            if platform.system() == "Windows": s.run(["start", filename], shell=True)
            elif platform.system() == "Linux": s.run(["xdg-open", filename])
            elif platform.system() == "Darwin": s.run(["open", filename])
            else: print("Couldn't determine OS")
        elif extens == ".js":
            s.run(["node", filename], text=True)
        elif extens == ".c":
            print(f"\x1b[31m{filename} is not an executable, rather a \".c\" file...\033[0m")
        elif extens == ".bat":
            if platform.system() == "Windows": s.run([filename], shell=True)
            else: print("\x1b[31mThis system can't run Windows-Native Files\033[0m")
        elif extens == ".sh":
            if platform.system() != "Windows": s.run(["sh", filename], text=True)
            else: print("\x1b[31mThis system can't run Linux/macOS/Unix-Native Files\033[0m")
        elif CheckForLinuxExecutables(filename):
            s.run([filename])
        else:
            print(f"\x1b[31mUnknown or unsupported file type: '{extens}'\033[0m")

#shutdown/reboot start
if "shutd" in args:
    if "--time" in args:
        timeidx = args.index("--time")
        if timeidx + 1 < len(args):
            ShutDownDoIt("shutdown", int(args[timeidx + 1]))
        else:
            print("\x1b[31m--time requires a value\033[0m")
    else:
        ShutDownDoIt("shutdown", 5)

if "reboot" in args:
    if "--time" in args:
        timeidx = args.index("--time")
        if timeidx + 1 < len(args):
            ShutDownDoIt("reboot", int(args[timeidx + 1]))
        else:
            print("\x1b[31m--time requires a value\033[0m")
    else:
        ShutDownDoIt("reboot", 5)

#log start
if "log" in args:
    wherelog = args.index("log")
    try:
        textis = args[wherelog + 1]
        filenameis = args[wherelog + 2]
        ts = datetime.datetime.now()
        entry = f"[{ts}] {textis}\n"
        with open(filenameis, 'a', encoding='utf-8') as f:
            f.write(entry)
        print(f"Logged to {filenameis}")
    except IndexError:
        print("\x1b[31mArgument was not given! Usage: log <Text> <Filename>\033[0m")
    except OSError:
        print("\x1b[31mOSError was recorded, exiting!\033[0m")

#licversion start
if "licversion" in args:
    wherelicv = args.index("licversion")
    try:
        lic = args[wherelicv + 1]
    except IndexError:
        print("\x1b[31mNo license name given! Options: gpl3, MIT\033[0m")
        lic = None
    if lic is not None:
        filename = args[wherelicv + 2] if wherelicv + 2 < len(args) else None
        if lic == "gpl3":
            text = "This program is free software: you can redistribute it and/or modify\nit under the terms of the GNU General Public License as published by\nthe Free Software Foundation, either version 3 of the License, or\n(at your option) any later version."
        elif lic == "MIT":
            text = "Permission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files, to deal in the Software\nwithout restriction, including without limitation the rights to use, copy,\nmodify, merge, publish, distribute, sublicense, and/or sell copies of the Software."
        else:
            print(f"\x1b[31mUnknown license '{lic}'. Options: gpl3, MIT\033[0m")
            text = None
        if text is not None:
            if filename is None:
                print(text)
            else:
                try:
                    with open(filename, 'a', encoding='utf-8') as f:
                        f.write(text + "\n")
                    print(f"Written to {filename}")
                except OSError:
                    print("\x1b[31mOSError writing to file!\033[0m")

#lserver start
if "lserver" in args:
    try:
        wherelserver = args.index("lserver")
        server_args = args[wherelserver + 1:]
        if platform.system() == "Windows":
            binary = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "server.exe")
        else:
            binary = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "server")
        if not os.path.isfile(binary):
            print(f"\x1b[31mserver binary not found at {binary}\033[0m")
        else:
            try:
                s.run([binary] + server_args, text=True)
            except OSError:
                print("\x1b[31mCouldn't launch server!\033[0m")
    except KeyboardInterrupt:
        print("\x1b[33mKilled Server!\033[0m")

#kprocess start
if "kprocess" in args:
    import psutil
    wherekprocess = args.index("kprocess")
    try:
        process_or_pid = args[wherekprocess + 1]
    except IndexError:
        print("\x1b[31mNo Argument given with [kprocess]!\033[0m")
        process_or_pid = None
    if process_or_pid is not None:
        killed = []
        # we try as PID first
        try:
            pid = int(process_or_pid)
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                killed.append(str(pid))
            except psutil.NoSuchProcess:
                print(f"\x1b[31mPID {pid} does not exist!\033[0m")
            except psutil.AccessDenied:
                print(f"\x1b[31mPID {pid} is a protected process, cannot terminate!\033[0m")
        except ValueError:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == process_or_pid:
                        proc.terminate()
                        killed.append(str(proc.info['pid']))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if not killed:
                print(f"\x1b[31mNo process named '{process_or_pid}' found!\033[0m")
        if killed:
            print(f"\033[32mKilled PID(s): {', '.join(killed)}\033[0m")

#getccinfo start
if "getccinfo" in args:
    whereccinfo = args.index("getccinfo")
    try:
        ccname = args[whereccinfo + 1]
    except IndexError:
        print("\x1b[31mNo Arguments given with [getccinfo]!\033[0m")
        ccname = None
    if ccname is not None:
        cc_version_flags = {
            "gcc":   ["gcc",   "--version"],
            "g++":   ["g++",   "--version"],
            "clang": ["clang", "--version"],
            "go":    ["go",    "version"],
            "rustc": ["rustc", "--version"],
            "cl":    ["cl"], #somehow cl prints version without a flag!
            "javac": ["javac", "-version"],
        }
        if ccname not in cc_version_flags:
            print(f"\x1b[31mUnknown compiler '{ccname}'. Options: {', '.join(cc_version_flags)}\033[0m")
        else:
            try:
                result = s.run(cc_version_flags[ccname], capture_output=True, text=True)
                #no need for cl, its weird
                output = (result.stdout or result.stderr or "").splitlines()
                version_line = output[0].strip() if output else "unknown"
                print(f"{ccname} {version_line}")
            except FileNotFoundError:
                print(f"\x1b[31m'{ccname}' is not installed or not in PATH\033[0m")
            except OSError:
                print(f"\x1b[31mCouldn't run '{ccname}'\033[0m")

#listpath start
if "listpath" in args:
    try:
        PATH_Data = os.getenv('PATH')
        print("\x1b[33mItems in PATH are:\033[0m")
        for p in PATH_Data.split(os.pathsep):
            print(p)
    except OSError:
        print("\x1b[31mOSError was recorded, could not list PATH!\033[0m")

#Code ends on <18/5/2026> at -> 1:53pm:))
#This was mind-breaking, took me 3 days!
#If you have bugs, please report them or ```crush them```
#------------------------------------------------------------------------------------------------------------------------------
