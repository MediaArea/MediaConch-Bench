#!/usr/bin/env python

import getopt
import os
import glob
import sys
import subprocess
import signal
import shutil
import urllib2
import json
import time

config_file = "./config.json"
config = {}

try:
    opts, args = getopt.getopt(sys.argv[1:], "hc:", ["config="])
except getopt.GetoptError:
    print './bench.py -c <config_file>'
    sys.exit(1)
for opt, arg in opts:
    if opt == '-h':
        print './bench.py -c <config_file>'
        sys.exit(0)
    elif opt in ("-c", "--config"):
        config_file = arg

if os.path.exists(config_file):
    with open(config_file) as f:
        data = f.read()
        data_json = json.loads(data)
        if "config" in data_json:
            config = data_json["config"]

home_dir = ""
daemon_bin = ""
ffmpeg_bin = "ffmpeg"
ffprobe_bin = "ffprobe"
script_bin = ""
database = ""
conf_file = ""
log_file = ""
orig_files_ext = ""
orig_files_dir = ""
created_dir = ""
reports_dir = ""
max_core = 32
has_vframes=False
vframes = "100"
api_version = "1.13"
plugins = []
if "plugins" in config and len(config["plugins"]) > 0:
    plugins = config["plugins"]

if "daemon_path" in config and len(config["daemon_path"]) > 0:
    daemon_bin = config["daemon_path"]
elif os.path.exists("/usr/bin/mediaconchd"):
    daemon_bin = "/usr/bin/mediaconchd"
else:
    print 'Please, provide the daemon path'
    sys.exit(1)

if "ffmpeg_path" in config and len(config["ffmpeg_path"]) > 0:
    ffmpeg_bin = config["ffmpeg_path"]

if "ffprobe_path" in config and len(config["ffprobe_path"]) > 0:
    ffprobe_bin = config["ffprobe_path"]

if "script_path" in config and len(config["script_path"]) > 0:
    script_bin = config["script_path"]
else:
    script_bin = ffmpeg_bin

if "database_dir" in config and len(config["database_dir"]) > 0:
    database = os.path.join(config["database_dir"], "MediaConch.db")
else:
    if len(home_dir) <= 0:
        home_dir = os.path.expanduser("~")
    if sys.platform == "win32":
        database = os.path.join(home_dir, os.getenv('APPDATA'), "MediaConch", "MediaConch.db")
    elif sys.platform == "darwin":
        database = os.path.join(home_dir, "Library/Application Support/MediaConch", "MediaConch.db")
    else:
        database = os.path.join(home_dir, ".local/share/MediaConch", "MediaConch.db")


if "config_dir" in config and len(config["config_dir"]) > 0:
    conf_file = os.path.join(config["config_dir"], "MediaConch.rc")
else:
    if len(home_dir) <= 0:
        home_dir = os.path.expanduser("~")
    if sys.platform == "win32":
        conf_file = os.path.join(home_dir, os.getenv('APPDATA'), "MediaConch", "MediaConch.rc")
    elif sys.platform == "darwin":
        conf_file = os.path.join(home_dir, "Library/Preferences", "MediaConch.rc")
    else:
        conf_file = os.path.join(home_dir, ".config", "MediaConch.rc")

if "log_dir" in config and len(config["log_dir"]) > 0:
    log_file = os.path.join(config["log_dir"], "MediaConch.log")
else:
    log_file = os.path.join(os.getcwd(), "mediaconch.log")

if "files_ext" in config and len(config["files_ext"]) > 0:
    orig_files_ext = config["files_ext"]
else:
    orig_files_ext = "mxf"

if "files_dir" in config and len(config["files_dir"]) > 0:
    orig_files_dir = config["files_dir"]
else:
    orig_files_dir = os.path.join(os.getcwd(), orig_files_ext)

orig_files = glob.glob(os.path.join(orig_files_dir, '*.mxf'))

if "created_files_dir" in config and len(config["created_files_dir"]) > 0:
    created_dir = config["created_files_dir"]
else:
    created_dir = os.getcwd()

if "reports_dir" in config and len(config["reports_dir"]) > 0:
    reports_dir = config["reports_dir"]
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)

if "nb_core_max" in config and config["nb_core_max"] >=1:
    max_core = config["nb_core_max"]

if "has_vframes" in config and config["has_vframes"] >=1:
    has_vframes = config["has_vframes"]

if "vframes" in config and len(config["vframes"]):
    vframes = config["vframes"]

if "api_version" in config and len(config["api_version"]):
    api_version = config["api_version"]

plugins_step1 = []
plugins_step1.append("ffmpeg1")
plugins_step1.append("logger")

plugins_step1_1 = []
plugins_step1_1.append("ffmpeg1-1")
plugins_step1_1.append("logger")

plugins_step2 = []
plugins_step2.append("ffmpeg2")
plugins_step2.append("logger")

plugins_step2_1 = []
plugins_step2_1.append("ffmpeg2-1")
plugins_step2_1.append("logger")

plugins_step4 = []
plugins_step4.append("ffmpeg4")
plugins_step4.append("logger")

plugins_step4_1 = []
plugins_step4_1.append("ffmpeg4-1")
plugins_step4_1.append("logger")

plugins_analyze = []
plugins_analyze.append("logger")

def remove_database():
    try:
        os.remove(database)
    except OSError:
        pass

def remove_conf_file():
    try:
        os.remove(conf_file)
    except OSError:
        pass

def remove_log_file():
    try:
        os.remove(log_file)
    except OSError:
        pass

def remove_dst_dir(dst_dir):
    if os.path.exists(dst_dir):
        torm = glob.glob(os.path.join(dst_dir, "*"))
        for fil in torm:
            if os.path.isfile(fil):
                os.remove(fil)

def read_log_file():
    with open(log_file) as fd:
        buff = fd.read()
        fd.close()
        return buff.splitlines()
    sys.exit(1)

def get_first_timestamp(lines, filename=None):
    search = ":start analyze:"
    if filename:
        search += filename
    for line in lines:
        pos = line.find(search)
        if pos != -1:
            return line[:pos]
    sys.exit(1)

def get_last_timestamp(lines, filename=None):
    search = ":end analyze:"
    if filename:
        search += filename
    for line in reversed(lines):
        pos = line.find(search)
        if pos != -1:
            return line[:pos]
    sys.exit(1)

def create_url(command):
    return "http://localhost:4242/" + api_version + "/" + command

def get_file_duration(filename):
    p = subprocess.Popen([ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    time = p.stdout.read()
    time = time[:-1]
    if time[-1:] == '\r':
        time = time[:-1]
    return time

def create_out_param(files_dir, files, out):
    f_id = 0
    for filename in files:
        out_file = {}
        out_file["file"] = os.path.join(files_dir, filename)
        out_file["orig_size"] = os.path.getsize(out_file["file"])
        out_file["orig_duration"] = get_file_duration(out_file["file"])
        out_file["time"] = 0
        out_file["time_report"] = 0
        out_file["dst_size"] = 0
        out_file["out_id"] = -1
        out_file["generated_id"] = []
        out_file["generated_file"] = ""
        out_file["analyzed"] = False
        out_file["valid"] = False
        out[f_id] = out_file
        f_id += 1


def create_analyze_param(out, pl, ana):
    j = {}
    array = []
    for i,f in out.items():
        arg = {}
        arg["file"] = f["file"]
        arg["id"] = i
        arg["plugins"] = pl
        arg["mil_analyze"] = ana
        if ana:
            arg["options"] = []
            option = {}
            option["parsespeed"] = "1"
            arg["options"].append(option)
        array.append(arg)

    j["args"] = array
    params = {}
    params["CHECKER_ANALYZE"] = j
    return params

def parse_analyze(out, data):
    d = json.loads(data)
    for key, val in d.items():
        for res_k, res_v in val.items():
            if res_k == "ok":
                for k in res_v:
                    out[k["inId"]]["out_id"] = k["outId"]

def create_report_param(out):
    arg = {}

    ids = []
    ids.append(out["out_id"])
    arg["ids"] = ids

    reports = []
    reports.append("IMPLEMENTATION")
    arg["reports"] = reports

    params = {}
    params["CHECKER_REPORT"] = arg
    return params

def parse_report(out, data):
    d = json.loads(data)
    for key, val in d.items():
        for res_k, res_v in val.items():
            if res_k == "ok":
                for k, v in res_v.items():
                    if k == "valid":
                        out["valid"] = v

def create_file_from_id(tid):
    arg = {}

    arg["id"] = tid

    params = {}
    params["CHECKER_FILE_FROM_ID"] = arg
    return params

def parse_file_from_id(data):
    d = json.loads(data)
    for key, val in d.items():
        for res_k, res_v in val.items():
            if res_k == "file":
                return res_v

def create_status_param(fval):
    params = "?id=" + str(fval["out_id"])
    return params

def parse_status(out, data):
    d = json.loads(data)
    for key, val in d.items():
        for res_k, res_v in val.items():
            if res_k == "ok":
                for k in res_v:
                    out["analyzed"] = k["finished"]
                    out["generated_id"] = k.get("generated_id", [])

def test_status(fval):
    params = create_status_param(fval)
    url = create_url("checker_status")
    url += params
    res = urllib2.urlopen(url)
    data = res.read()
    parse_status(fval, data)

def wait_for_all_analyzed(out):
    for f,v in out.items():
        v["analyzed"] = False
        v["generated_id"] = []

    is_finish = False
    while not is_finish:
        is_finish = True
        for f,v in out.items():
            if not v["analyzed"]:
                test_status(v)
            if not v["analyzed"]:
                is_finish = False
        if not is_finish:
            time.sleep(1)

def get_reports(out):
    for f,v in out.items():
        t = time.time()
        params = create_report_param(v)
        url = create_url("checker_report")
        req = urllib2.Request(url)
        req.add_header('Content-Type', 'application/json')
        res = urllib2.urlopen(req, json.dumps(params))
        data = res.read()
        v["time_report"] = time.time() - t
        parse_report(v, data)

def get_generated_files(out):
    for f,v in out.items():
        if len(out[f].get("generated_id", [])) == 0:
            continue

        params = create_file_from_id(out[f]["generated_id"][0])
        url = create_url("checker_file_from_id")
        req = urllib2.Request(url)
        req.add_header('Content-Type', 'application/json')
        res = urllib2.urlopen(req, json.dumps(params))
        data = res.read()
        out[f]["generated_file"] = parse_file_from_id(data)
        out[f]["dst_size"] = os.path.getsize(out[f]["generated_file"])

def execute_command(out, pl, ana):
    params = create_analyze_param(out, pl, ana)
    url = create_url("checker_analyze")
    req = urllib2.Request(url)
    req.add_header('Content-Type', 'application/json')
    res = urllib2.urlopen(req, json.dumps(params))
    data = res.read()
    parse_analyze(out, data)
    wait_for_all_analyzed(out)
    if ana:
        #if analyze need to be done, get the reports
        get_reports(out)
    else:
        #else, a generated file is made, need the size
        get_generated_files(out)

def file_by_file(lines, out):
    for k,v in out.items():
        start_time_stamp = get_first_timestamp(lines, v["file"])
        stop_time_stamp = get_last_timestamp(lines, v["file"])
        diff_time_stamp = int(stop_time_stamp) - int(start_time_stamp)
        v["time"] = diff_time_stamp

def print_transcoding_seq(out, filename):
    filename_multi = filename + "-sequential.csv"
    with open(filename_multi, "w") as f:
        f.write("orig_file,orig_size,orig_duration,transcode_time,created_file_size\n")
        for k,v in out.items():
            f.write(str(v["file"]) + "," + str(v["orig_size"]) + "," + str(v["orig_duration"]) + "," + str(int(v["time"]) / float(1000)) + "," + str(v["dst_size"]))
            f.write("\n")
        f.write("\n")
        f.close()

def print_transcoding_mul(filename, total):
    filename_s = filename + "-multithreads.csv"
    with open(filename_s, "w") as f:
        f.write("orig_file,orig_size,orig_duration,transcode_time,created_file_size\n")
        f.write("all,,," + str(int(total) / float(1000)) + ",")
        f.write("\n")
        f.close()

def print_analyze_seq(out, filename):
    filename_multi = filename + "-sequential.csv"
    with open(filename_multi, "w") as f:
        f.write("orig_file,analyze_time,valid\n")
        for k,v in out.items():
            f.write(str(v["file"]) + "," + str((int(v["time"]) / float(1000)) + float(v["time_report"])) + "," + str(v["valid"]))
            f.write("\n")
        f.write("\n")
        f.close()

def print_analyze_mul(filename, total):
    filename_s = filename + "-multithreads.csv"
    with open(filename_s, "w") as f:
        f.write("orig_file,analyze_time,valid\n")
        f.write("all," + str(int(total) / float(1000)) + ",")
        f.write("\n")
        f.close()

def print_analyze_mul2(filename, total, out):
    r_total = 0
    for k,v in out.items():
        r_total += float(v["time_report"])

    filename_s = filename + "-multithreads.csv"
    with open(filename_s, "w") as f:
        f.write("orig_file,analyze_time,valid,report_time\n")
        f.write("all," + str(int(total) / float(1000)) + "," + str(r_total))
        f.write("\n")
        f.close()

def all_files_in_one(lines):
    start_time_stamp = get_first_timestamp(lines)
    stop_time_stamp = get_last_timestamp(lines)
    diff_time_stamp = int(stop_time_stamp) - int(start_time_stamp)
    return diff_time_stamp

def launch_daemon():
    return subprocess.Popen([daemon_bin, "-n"])#, stderr=subprocess.PIPE)

def change_ffmpeg_ffprobe_path(input_params):
    i = 0
    while i + 1 < len(input_params):
        if input_params[i] == "--ffmpegpath":
            i += 1
            input_params[i] = ffmpeg_bin
        if input_params[i] == "--ffprobepath":
            i += 1
            input_params[i] = ffprobe_bin
        i += 1

def change_plugin_output_dir(plugin, directory):
    if "outputs" in plugin:
        for out in plugin["outputs"]:
            out["outputDir"] = directory

def create_conf(nb):
    configs = []
    config = {}
    config["Use_Daemon"] = True
    configs.append(config)

    config = {}
    config["Daemon_Port"] = 4242
    configs.append(config)

    config = {}
    config["Daemon_Address"] = "0.0.0.0"
    configs.append(config)

    config = {}
    config["Scheduler_Max_Threads"] = nb
    configs.append(config)

    config = {}

    copy = []
    for plugin in plugins:
        if "id" in plugin and plugin["id"] == "ffmpeg1":
            plugin["bin"] = script_bin
            change_ffmpeg_ffprobe_path(plugin["inputParams"])
            change_plugin_output_dir(plugin, os.path.join(created_dir, "tmp1"))

        if "id" in plugin and plugin["id"] == "ffmpeg1-1":
            plugin["bin"] = script_bin
            change_ffmpeg_ffprobe_path(plugin["inputParams"])
            change_plugin_output_dir(plugin, os.path.join(created_dir, "tmp1-1"))

        if "id" in plugin and plugin["id"] == "ffmpeg2":
            plugin["bin"] = script_bin
            change_ffmpeg_ffprobe_path(plugin["inputParams"])
            change_plugin_output_dir(plugin, os.path.join(created_dir, "tmp2"))

        if "id" in plugin and plugin["id"] == "ffmpeg2-1":
            plugin["bin"] = script_bin
            change_ffmpeg_ffprobe_path(plugin["inputParams"])
            change_plugin_output_dir(plugin, os.path.join(created_dir, "tmp2-1"))

        if "id" in plugin and plugin["id"] == "ffmpeg4":
            plugin["bin"] = script_bin
            change_ffmpeg_ffprobe_path(plugin["inputParams"])
            change_plugin_output_dir(plugin, os.path.join(created_dir, "tmp4"))

        if "id" in plugin and plugin["id"] == "ffmpeg4-1":
            plugin["bin"] = script_bin
            change_ffmpeg_ffprobe_path(plugin["inputParams"])
            change_plugin_output_dir(plugin, os.path.join(created_dir, "tmp4-1"))

        if "id" in plugin and plugin["id"] == "logger":
            plugin["file"] = log_file

        copy.append(plugin)

    config["Plugins"] = copy
    configs.append(config)

    with open(conf_file, "w") as f:
        json.dump(configs, f, indent=4)
        f.close()

def clean(dst_dir):
    remove_dst_dir(dst_dir)
    remove_log_file()
    remove_database()
    remove_conf_file()

def start_daemon(dst_dir, nb):
    clean(dst_dir)
    create_conf(nb)
    return launch_daemon()

def stop_daemon(hdl):
    hdl.terminate()

def step1(out):
    create_out_param(orig_files_dir, orig_files, out)
    dst_dir = os.path.join(created_dir, "tmp1")
    daemon_proc = start_daemon(dst_dir, 1)
    time.sleep(2)
    execute_command(out, plugins_step1, False)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    file_by_file(lines, out)
    print_transcoding_seq(out, os.path.join(reports_dir, "report-1"))

    dst_dir = os.path.join(created_dir, "tmp1-1")
    daemon_proc = start_daemon(dst_dir, max_core)
    time.sleep(2)
    execute_command(out, plugins_step1_1, False)
    stop_daemon(daemon_proc)
    lines = read_log_file()
    total = all_files_in_one(lines)
    print_transcoding_mul(os.path.join(reports_dir, "report-1"), total)

def step2(out):
    create_out_param(orig_files_dir, orig_files, out)
    dst_dir = os.path.join(created_dir, "tmp2")

    daemon_proc = start_daemon(dst_dir, 1)
    time.sleep(2)
    execute_command(out, plugins_step2, False)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    file_by_file(lines, out)
    print_transcoding_seq(out, os.path.join(reports_dir, "report-2"))

    dst_dir = os.path.join(created_dir, "tmp2-1")
    daemon_proc = start_daemon(dst_dir, max_core)
    time.sleep(2)
    execute_command(out, plugins_step2_1, False)
    stop_daemon(daemon_proc)
    lines = read_log_file()
    total = all_files_in_one(lines)
    print_transcoding_mul(os.path.join(reports_dir, "report-2"), total)


def step3(out):
    files = glob.glob(os.path.join(created_dir, "tmp2-1", '*.mkv'))
    create_out_param(os.path.join(created_dir, "tmp2-1"), files, out)
    dst_dir = os.path.join(created_dir, "tmp3")

    daemon_proc = start_daemon(dst_dir, 1)
    time.sleep(2)
    execute_command(out, plugins_analyze, True)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    file_by_file(lines, out)
    print_analyze_seq(out, os.path.join(reports_dir, "report-3"))

    daemon_proc = start_daemon(dst_dir, max_core)
    time.sleep(2)
    execute_command(out, plugins_analyze, True)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    total = all_files_in_one(lines)
    for k,v in out.items():
        total += (float(v["time_report"]) * 1000)
    print_analyze_mul(os.path.join(reports_dir, "report-3"), total)


def step4(out):
    files = glob.glob(os.path.join(created_dir, "tmp2", '*.mkv'))
    create_out_param(os.path.join(created_dir, "tmp2"), files, out)
    dst_dir = os.path.join(created_dir, "tmp4")

    daemon_proc = start_daemon(dst_dir, 1)
    time.sleep(2)
    execute_command(out, plugins_step4, False)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    file_by_file(lines, out)
    print_transcoding_seq(out, os.path.join(reports_dir, "report-4"))

    dst_dir = os.path.join(created_dir, "tmp4-1")
    daemon_proc = start_daemon(dst_dir, max_core)
    time.sleep(2)
    execute_command(out, plugins_step4_1, False)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    total = all_files_in_one(lines)
    print_transcoding_mul(os.path.join(reports_dir, "report-4"), total)

def step3_multi(out):
    files = glob.glob(os.path.join(created_dir, "tmp2-1", '*.mkv'))
    create_out_param(os.path.join(created_dir, "tmp2-1"), files, out)
    dst_dir = os.path.join(created_dir, "tmp3")

    daemon_proc = start_daemon(dst_dir, 1)
    time.sleep(2)
    execute_command(out, plugins_analyze, True)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    total = all_files_in_one(lines)
    print_analyze_mul2(os.path.join(report_dir, "report-3-1"), total, out)

    daemon_proc = start_daemon(dst_dir, 16)
    time.sleep(2)
    execute_command(out, plugins_analyze, True)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    total = all_files_in_one(lines)
    print_analyze_mul2(os.path.join(reports_dir, "report-3-16"), total, out)

    daemon_proc = start_daemon(dst_dir, 24)
    time.sleep(2)
    execute_command(out, plugins_analyze, True)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    total = all_files_in_one(lines)
    print_analyze_mul2(os.path.join(reports_dir, "report-3-24"), total, out)

    daemon_proc = start_daemon(dst_dir, 32)
    time.sleep(2)
    execute_command(out, plugins_analyze, True)
    stop_daemon(daemon_proc)

    lines = read_log_file()
    total = all_files_in_one(lines)
    print_analyze_mul2(os.path.join(reports_dir, "report-3-32"), total, out)


out = {}
step1(out)
step2(out)
step3(out)
step4(out)
# step3_multi(out)
