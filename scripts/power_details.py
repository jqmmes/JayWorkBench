# # Tasks per device
# Delta Battery (%) or capacity when available OK [2]
# Global % deadline broken and suceded [3]
# Per device:
#   -> % deadline status [3]
#   -> Tasks generated [1] / tasks offloaded [5] / tasks executed [4]
#   -> Avg time per task executed here [4]
#   -> Avg power per task executed here [6]
# Global Avg time per task [4]
# Global Avg power per task [6]

#[1]
# TASK_SUBMITTED

#[2]
# Capacity: ;CHARGE=(\d+) So para Pixel e N9
#   NEW_BATTERY_CAPACITY=(\d+) mAh remaining. Não dá no S7e
#   NEW_BATTERY_LEVEL=(\d+) % de bateria max e min


#[3]
# DEADLINE_MET=(true|false)

#[4]
# COMPUTATION_TIME=(\d+);

# [5]
# SCHEDULED,([a-f0-9\-]),"WORKER_ID=([a-f0-9\-])"
# local if match[2] == local_id


# [6] Map with all power readings and timestamps
# Computation duration:
# init ->  RunnableTaskObjects_run_197,INIT,b2c76807-ee16-47ae-b7b2-b0b41070c4fb
# end ->  WorkerGRPCClient$execute$1_run_42,COMPLETE,b2c76807-ee16-47ae-b7b2-b0b41070c4fb
#
# init_cloudlet ->  ThreadPoolExecutor_runWorker_1128,INIT
# end_cloudlet -> ThreadPoolExecutor_runWorker_1128,COMPLETE
#
# duration: end.timestamp - init.timestamp
# power = avg sum powers from power_map[init.timestamp - 1] to power_map[end.timestamp]
#


# read power:
# POWER=-(\d+\.\d+)"
#
# timestamp:
# [CLOUD|ANDROID],(\d+),

from sys import argv, maxsize
import os
from re import findall, match

device_names = {
"HT4BTJT00030": "Nexus 9 ",
"unknown_device_192.168.3.34": "Xiaomi Mi 9T",
"unknown_device_192.168.1.92": "Xiaomi Mi 9T",
"7a3e71d8": "Xiaomi Mi 9T",
"unknown_device_192.168.3.10": "Galaxy S7e",
"unknown_device_192.168.1.91": "Galaxy S7e",
"ce0616067b654c2805": "Galaxy S7e",
"R52N50ZGEYE": "Tab S5e  ",
"unknown_device_192.168.3.35": "Tab S5e  ",
"unknown_device_192.168.1.93": "Tab S5e  ",
"cloudlet_192.168.3.15": "Cloudlet",
"cloudlet_192.168.1.94": "Cloudlet",
"unknown_device_192.168.3.48": "Pixel 4 ",
"unknown_device_192.168.1.90": "Pixel 4 ",
"9B021FFAZ00510": "Pixel 4 ",
"HT4BVJT00012": "Nexus 9 ",
"HT4BVJT00003": "Nexus 9 "
}

files = os.listdir(argv[1])

files_powermap = {}
files_taskmap = {}
files_duration = {}
files_deadline_met = {}
files_task_duration = {}
files_task_completion_duration = {}
files_battery_level = {}
files_battery_charge = {}
files_avg_task_powers = {}
files_delta_e = {}
total_duration = 0.0

def getDeviceType(line):
    finds = findall(",(CLOUD|ANDROID),", line)
    if len(finds) > 0:
        return finds[0]

def getTimeStamp(line):
    finds = findall("(?:CLOUD|ANDROID),(\d+),", line)
    if len(finds) > 0:
        return int(finds[0])
    return None

def getPowerMap(data):
    power_map = []
    for line in data:
        finds = findall("POWER=-(\d+\.\d+)", line)
        if len(finds) > 0:
            power_map.append((getTimeStamp(line), float(finds[0])))
    return power_map

def checkOffload(line):
    selected_worker = findall("SCHEDULED,(?:[a-f0-9\-]+),\"WORKER_ID=([a-f0-9\-]+)", line)
    device_id = findall("([a-f0-9\-]+),(?:CLOUD|ANDROID)", line)
    if len(selected_worker) > 0 and len(device_id) > 0:
        if (selected_worker[0] != device_id[0]):
            return 1
    return 0

def getTasksInfo(data):
    generated = 0
    executed = 0
    offloaded = 0
    for line in data:
        if len(findall("TASK_SUBMITTED", line)) > 0:
             generated += 1
        elif len(findall("COMPUTATION_TIME", line)) > 0:
             executed += 1
        elif len(findall("SCHEDULED", line)) > 0:
            offloaded += checkOffload(line)
    if executed > 0:
        executed -= 1
    return (generated, executed, offloaded)

def getDeadlines(data):
    success = 0
    fail = 0
    for line in data:
        find = findall("DEADLINE_MET=(true|false)", line)
        if len(find) > 0:
            if find[0] == "true":
                success += 1
            else:
                fail += 1
    return (success, fail)


def getTasksCompletionDuration(data):
    device_type = getDeviceType(data[1])
    if device_type == "CLOUD":
        return []
    durations = []
    for line in data:
        task_duration = findall("EXECUTION_COMPLETE,(?:[a-f0-9\-]+),\"DATA_SIZE=(?:\d+)\;DURATION_MILLIS=(\d+)", line)
        if len(task_duration) > 0:
            durations.append(int(task_duration[0]))
    return durations


def getTasksComputeDuration(data):
    device_type = getDeviceType(data[1])
    durations = []
    job_id = None
    timestamp = None
    for line in data:
        if job_id is None:
            if device_type == "CLOUD":
                id = findall("ThreadPoolExecutor_runWorker_1128,INIT,([a-f0-9\-]+)", line)
            else:
                id = findall("RunnableTaskObjects_run_216,INIT,([a-f0-9\-]+)", line)
            if len(id) > 0:
                job_id = id[0]
                timestamp = getTimeStamp(line)
        else:
            if device_type == "CLOUD":
                new_id = findall("ThreadPoolExecutor_runWorker_1128,COMPLETE,([a-f0-9\-]+)", line)
            else:
                new_id = findall("WorkerGRPCClient\$execute\$1_run_42,COMPLETE,([a-f0-9\-]+)", line)
            if len(new_id) > 0:
                if new_id[0] == job_id:
                    durations.append((timestamp, getTimeStamp(line)))
                    job_id = None
                    timestamp = None
    return durations

def getBatteryLevel(data):
    levels = []
    for line in data:
        finds = findall("NEW_BATTERY_LEVEL=(\d+)", line)
        if len(finds) > 0:
            levels.append((getTimeStamp(line), int(finds[0])))
    return levels

def getBatteryCapacity(data):
    charges = []
    for line in data:
        finds = findall(";CHARGE=(\d+)", line)
        if len(finds) > 0:
            charges.append((getTimeStamp(line), int(finds[0])))
        else:
            finds = findall("NEW_BATTERY_CAPACITY=(\d+)", line)
            if len(finds) > 0:
                charges.append((getTimeStamp(line), int(finds[0])))
    return charges

def getDeltaE(device, data_lines):
    # Time in hours
    last_power_read = None
    init_time = (getTimeStamp(data_lines[2]) / 1000.0) / 3600.0
    end_time = (getTimeStamp(data_lines[-2]) / 1000.0) / 3600.0
    deltaE = 0
    for entry in files_powermap[device]:
        if last_power_read is None:
            power = entry[1]
            last_time = init_time
        else:
            power = (last_power_read + entry[1]) / 2.0
        last_power_read = power
        this_time = ((entry[0] / 1000.0) / 3600.0)
        deltaE += (power * (this_time - last_time))
        last_time = this_time
    try:
        deltaE += files_powermap[device][-1][1] * (end_time - ((files_powermap[device][-1][0] / 1000.0) / 3600.0))
    except:
        print("POSITIVE_CHARGES_NEEDS_REPEAT ON FILE %s" % device)
    return deltaE * 1000.0

for file in files:
    name = file.rstrip(".csv")
    data_lines = open(argv[1] + "/" + file, "r").read().split("\n")
    files_powermap[name] = getPowerMap(data_lines)
    files_taskmap[name] = getTasksInfo(data_lines)
    files_duration[name] = getTimeStamp(data_lines[-2]) - getTimeStamp(data_lines[1])
    files_deadline_met[name] = getDeadlines(data_lines)
    files_task_duration[name] = getTasksComputeDuration(data_lines)
    files_task_completion_duration[name] = getTasksCompletionDuration(data_lines)
    files_battery_level[name] = getBatteryLevel(data_lines)
    files_battery_charge[name] = getBatteryCapacity(data_lines)
    files_delta_e[name] = getDeltaE(name, data_lines)
    total_duration = max(total_duration, ((getTimeStamp(data_lines[-2])-getTimeStamp(data_lines[1])) / 1000.0))



total_task_energy = 0
total_task_count = 0
for file in sorted(files_powermap.keys()):
    entries = 0
    avg_p_file = 0
    for task in files_task_duration[file]:
        avg_task_power = 0
        avg_task_power_cnt = 0
        for power in files_powermap[file]:
            if power[0] > task[0] and power[0] < task[1]:
                avg_task_power += power[1]
                avg_task_power_cnt += 1
        try:
            avg_task_power = avg_task_power / avg_task_power_cnt
            tot_task_power = (avg_task_power * ((task[1] - task[0]))) / 3600.0
            entries += 1
            avg_p_file += tot_task_power
            total_task_energy += tot_task_power
            total_task_count += 1
        except:
            None
    if entries > 0:
        files_avg_task_powers[file] = avg_p_file / entries
    else:
        files_avg_task_powers[file] = 0.0

total_tasks_generated = 0
total_tasks_executed = 0
total_tasks_offloaded = 0
total_deadline_met = 0
total_deadline_broken = 0
total_delta_energy = 0.0

total_avg_compute_time_cnt = 0
total_avg_task_time_cnt = 0
total_avg_compute_time = 0.0
total_avg_task_time = 0.0


print("\n\n\n\nNAME\t\tGENERATED\tEXECUTED\tLOCAL\t\tOFFLOADED\tDEADLINE_MET\tDEADLINE_BROKEN\tAVG_COMPUTE_TIME_TASK\tAVG_TIME_TASK\tAVG_ENERGY_TASK\tdeltaBAT\tdeltaCAP\tdeltaENERGY")
for file in sorted(files_taskmap.keys()):
    avg_compute_time = 0
    avg_task_time = 0
    for task in files_task_duration[file]:
        avg_compute_time += task[1] - task[0]
    try:
        avg_compute_time = (avg_compute_time / len(files_task_duration[file])) / 1000.0
        total_avg_compute_time_cnt += files_taskmap[file][0]
    except:
        None
    total_avg_compute_time += avg_compute_time*files_taskmap[file][0]
    for task in files_task_completion_duration[file]:
        avg_task_time += task
    try:
        avg_task_time = (avg_task_time / len(files_task_completion_duration[file])) / 1000.0
        total_avg_task_time_cnt += files_taskmap[file][0]
    except:
        None
    total_avg_task_time += avg_task_time*files_taskmap[file][0]
    max_bat = 0
    min_bat = 100
    for bat in files_battery_level[file]:
        if bat[1] > max_bat:
            max_bat = bat[1]
        if bat[1] < min_bat:
            min_bat = bat[1]
    if min_bat == 100 and max_bat == 0:
        min_bat = 0
    max_cap = -maxsize - 1
    min_cap = maxsize
    for cap in files_battery_charge[file]:
        if cap[1] > max_cap:
            max_cap = cap[1]
        if cap[1] < min_cap:
            min_cap = cap[1]
    if min_cap == maxsize and max_cap == -maxsize - 1:
        min_cap = 0
        max_cap = 0

    deadline_success_pcnt = None
    deadline_broken_pcnt = None

    try:
        deadline_success_pcnt = ((files_deadline_met[file][0]*100.0)/files_taskmap[file][0])
        deadline_broken_pcnt = ((files_deadline_met[file][1]*100.0)/files_taskmap[file][0])
    except:
        None
    if deadline_success_pcnt is not None and deadline_broken_pcnt is not None:
        print("{}\t{}\t\t{}\t\t{} ({:.1f}%)\t{} ({:.1f}%)\t{} ({:.1f}%)\t{} ({:.1f}%)\t{:.2f}s\t\t\t{:.2f}s\t\t{:.2f}mWh \t{}%\t\t{}mAh\t\t{:.2f}mWh".format(
            device_names[file], files_taskmap[file][0], files_taskmap[file][1],
            (files_taskmap[file][0]-files_taskmap[file][2]),
            (((files_taskmap[file][0]-files_taskmap[file][2])*100.0)/files_taskmap[file][0]),
            files_taskmap[file][2], ((files_taskmap[file][2]*100.0)/files_taskmap[file][0]),
            files_deadline_met[file][0], deadline_success_pcnt,
            files_deadline_met[file][1], deadline_broken_pcnt,
            avg_compute_time, avg_task_time, files_avg_task_powers[file], (max_bat - min_bat),
            (max_cap - min_cap), files_delta_e[file])
        )
    else:
        print("{}\t{}\t\t{}\t\t{}\t\t{}\t\t{}\t\t{}\t\t{:.2f}s\t\t\t{:.2f}s\t\t{:.2f}mWh \t{}%\t\t{}mAh\t\t{:.2f}mWh".format(
            device_names[file], files_taskmap[file][0], files_taskmap[file][1],
            (files_taskmap[file][0]-files_taskmap[file][2]), files_taskmap[file][2],
            files_deadline_met[file][0], files_deadline_met[file][1],
            avg_compute_time, avg_task_time, files_avg_task_powers[file], (max_bat - min_bat),
            (max_cap - min_cap), files_delta_e[file])
        )
    total_tasks_generated += files_taskmap[file][0]
    total_tasks_executed += files_taskmap[file][1]
    total_tasks_offloaded += files_taskmap[file][2]
    total_deadline_met += files_deadline_met[file][0]
    total_deadline_broken += files_deadline_met[file][1]
    total_delta_energy += files_delta_e[file]


try:
    total_local_pcnt = ((total_tasks_generated-total_tasks_offloaded)*100.0)/total_tasks_generated
except:
    total_local_pcnt = 0
try:
    total_tasks_offloaded_pcnt = (total_tasks_offloaded*100.0)/total_tasks_offloaded
except:
    total_tasks_offloaded_pcnt = 0
try:
    total_deadline_met_pcnt = (total_deadline_met*100.0)/total_tasks_generated
except:
    total_deadline_met_pcnt = 0
try:
    total_avg_compute_time_pcnt = total_avg_compute_time/total_avg_compute_time_cnt
except:
    total_avg_compute_time_pcnt = 0
try:
    total_avg_task_time_pcnt = total_avg_task_time/total_avg_task_time_cnt
except:
    total_avg_task_time_pcnt = 0
try:
    total_task_energy_pcnt = total_task_energy / total_task_count
except:
    total_task_energy_pcnt = 0
try:
    total_deadline_broken_pcnt = (total_deadline_broken*100.0)/total_tasks_generated
except:
    total_deadline_broken_pcnt = 0

print("--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
print("GLOBAL\t\t{}\t\t{}\t\t{} ({:.1f}%)\t{} ({:.1f}%)\t{} ({:.1f}%)\t{} ({:.1f}%)\t{:.2f}s\t\t\t{:.2f}s\t\t{:.2f}mWh\t\t\t\t\t\t{:.2f}mWh".format(
    total_tasks_generated,total_tasks_executed,
    (total_tasks_generated-total_tasks_offloaded), total_local_pcnt,
    total_tasks_offloaded, total_tasks_offloaded_pcnt,
    total_deadline_met,total_deadline_met_pcnt, total_deadline_broken,
    total_deadline_broken_pcnt, total_avg_compute_time_pcnt, total_avg_task_time_pcnt,
    total_task_energy_pcnt, total_delta_energy)
)
print("\nTOTAL_DURATION: {:.2f}s".format(total_duration))
print("\n\n\n\n")
