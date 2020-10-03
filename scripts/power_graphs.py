from sys import argv, maxsize
import os
from re import findall, match
import shelve

import plotly.graph_objects as go
from plotly.subplots import make_subplots

use_cloudlet = True
process_files = True
with_Cloudlet = ""
file_cloudlet = ""
shelve_file = "power_processed.shelve"

if use_cloudlet:
    with_Cloudlet = "W\ Cloudlet "
    file_cloudlet = "CLOUDLET_"
    shelve_file = "power_cloudlet_processed.shelve"

storage = shelve.open(shelve_file)

device_names = {
"HT4BTJT00030": "Nexus 9 ",
"unknown_device_192.168.3.34": "Xiaomi Mi 9T",
"7a3e71d8": "Xiaomi Mi 9T",
"unknown_device_192.168.3.10": "Galaxy S7e",
"ce0616067b654c2805": "Galaxy S7e",
"R52N50ZGEYE": "Tab S5e  ",
"unknown_device_192.168.3.35": "Tab S5e  ",
"cloudlet_192.168.3.15": "Cloudlet",
"unknown_device_192.168.3.48": "Pixel 4 ",
"9B021FFAZ00510": "Pixel 4 ",
"HT4BVJT00012": "Nexus 9 ",
"HT4BVJT00003": "Nexus 9 "
}

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
total_duration = {}
files_tasks_generated = {}
files_tasks_executed = {}

def getDeviceType(line):
    finds = findall(",(CLOUD|ANDROID),", line)
    if len(finds) > 0:
        return finds[0]

def getTimeStamp(line):
    finds = findall("(?:CLOUD|ANDROID),(\d+),", line)
    if len(finds) > 0:
        return int(finds[0])
    return None

def checkOffload(line):
    selected_worker = findall("SCHEDULED,(?:[a-f0-9\-]+),\"WORKER_ID=([a-f0-9\-]+)", line)
    device_id = findall("([a-f0-9\-]+),(?:CLOUD|ANDROID)", line)
    if len(selected_worker) > 0 and len(device_id) > 0:
        if (selected_worker[0] != device_id[0]):
            return 1
    return 0

def getDataFromLines(data):
    #getPowerMap
    power_map = []
    #getTasksInfo
    generated = 0
    executed = 0
    offloaded = 0
    #getDeadlines
    success = 0
    fail = 0
    #getTasksCompletionDuration
    device_type = getDeviceType(data[1])
    completion_durations = []
    #getTasksComputeDuration(data):
    #device_type = getDeviceType(data[1])
    compute_durations = []
    job_id = None
    timestamp = None
    #getBatteryLevel
    levels = []
    #getBatteryCapacity
    charges = []

    executed_tasks = []
    generated_tasks = []

    for line in data:
        power_finds = findall("POWER=-(\d+\.\d+)", line)
        if len(power_finds) > 0:
            power_map.append((getTimeStamp(line), float(power_finds[0])))
            continue

        if len(findall("TASK_SUBMITTED", line)) > 0:
             generated += 1
             continue
        elif len(findall("COMPUTATION_TIME", line)) > 0:
             executed += 1
             continue
        elif len(findall("SCHEDULED", line)) > 0:
            offloaded += checkOffload(line)
            continue

        deadline_finds = findall("DEADLINE_MET=(true|false)", line)
        if len(deadline_finds) > 0:
            if deadline_finds[0] == "true":
                success += 1
            else:
                fail += 1
            continue

        if not device_type == "CLOUD":
            task_generated_id = findall("services.broker.BrokerService_scheduleTask\$Jay_Base_157,INIT,([a-f0-9\-]+)", line)
            if len(task_generated_id) > 0:
                generated_tasks.append(task_generated_id[0])
                continue

            task_duration = findall("EXECUTION_COMPLETE,(?:[a-f0-9\-]+),\"DATA_SIZE=(?:\d+)\;DURATION_MILLIS=(\d+)", line)
            if len(task_duration) > 0:
                completion_durations.append(int(task_duration[0]))
                continue

        if job_id is None:
            if device_type == "CLOUD":
                id = findall("ThreadPoolExecutor_runWorker_1128,INIT,([a-f0-9\-]+)", line)
            else:
                id = findall("RunnableTaskObjects_run_21(?:6|7),INIT,([a-f0-9\-]+)", line)
            if len(id) > 0:
                job_id = id[0]
                timestamp = getTimeStamp(line)
                executed_tasks.append(id[0])
                continue
        else:
            if device_type == "CLOUD":
                new_id = findall("ThreadPoolExecutor_runWorker_1128,COMPLETE,([a-f0-9\-]+)", line)
            else:
                new_id = findall("WorkerGRPCClient\$execute\$1_run_42,COMPLETE,([a-f0-9\-]+)", line)
            if len(new_id) > 0:
                if new_id[0] == job_id:
                    compute_durations.append((timestamp, getTimeStamp(line)))
                    job_id = None
                    timestamp = None
                    continue

        battery_finds = findall("NEW_BATTERY_LEVEL=(\d+)", line)
        if len(battery_finds) > 0:
            levels.append((getTimeStamp(line), int(battery_finds[0])))
            continue

        capacity_finds = findall(";CHARGE=(\d+)", line)
        if len(capacity_finds) > 0:
            charges.append((getTimeStamp(line), int(capacity_finds[0])))
            continue
        else:
            capacity_finds = findall("NEW_BATTERY_CAPACITY=(\d+)", line)
            if len(capacity_finds) > 0:
                charges.append((getTimeStamp(line), int(capacity_finds[0])))
                continue

    if executed > 0:
        executed -= 1

    return power_map, (generated, executed, offloaded), (success, fail), completion_durations, compute_durations, levels, charges, generated_tasks, executed_tasks

def getDeltaE(experiment_key, device, data_lines):
    # Time in hours
    last_power_read = None
    init_time = (getTimeStamp(data_lines[2]) / 1000.0) / 3600.0
    end_time = (getTimeStamp(data_lines[-2]) / 1000.0) / 3600.0
    deltaE = 0
    for entry in files_powermap[experiment_key][device]:
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
        deltaE += files_powermap[experiment_key][device][-1][1] * (end_time - ((files_powermap[experiment_key][device][-1][0] / 1000.0) / 3600.0))
    except:
        print("POSITIVE_CHARGES_NEEDS_REPEAT ON FILE %s" % device)
    return deltaE * 1000.0


y_labels = ["d={}".format(chr(0x00D8)), "d=12", "d=9", "d=6", "d=3"]

base_name = "SAC21_"
groups = ["GREEN_DYN", "GREEN_FIXED", "PERFORMANCE", "LOCAL_FIXED"]
if use_cloudlet:
    groups = ["GREEN_DYN", "GREEN_FIXED", "PERFORMANCE"]

generation_deadlines = ["{}12_NO_DEADLINE".format(file_cloudlet),"{}12_12".format(file_cloudlet),
                        "{}12_9".format(file_cloudlet), "{}12_6".format(file_cloudlet),
                        "{}12_3".format(file_cloudlet), "{}9_NO_DEADLINE".format(file_cloudlet),
                        "{}9_9".format(file_cloudlet), "{}9_6".format(file_cloudlet),
                        "{}9_3".format(file_cloudlet), "{}6_NO_DEADLINE".format(file_cloudlet),
                        "{}6_6".format(file_cloudlet), "{}6_3".format(file_cloudlet)]

fix_12 = []
fix_9 = []
fix_6 = []
dyn_12 = []
dyn_9 = []
dyn_6 = []
perf_12 = []
perf_9 = []
perf_6 = []
local_12 = []
local_9 = []
local_6 = []

deadline_fix_12 = []
deadline_fix_9 = []
deadline_fix_6 = []
deadline_dyn_12 = []
deadline_dyn_9 = []
deadline_dyn_6 = []
deadline_perf_12 = []
deadline_perf_9 = []
deadline_perf_6 = []
deadline_local_12 = []
deadline_local_9 = []
deadline_local_6 = []

avg_task_execution_fix_12 = []
avg_task_execution_fix_9 = []
avg_task_execution_fix_6 = []
avg_task_execution_dyn_12 = []
avg_task_execution_dyn_9 = []
avg_task_execution_dyn_6 = []
avg_task_execution_perf_12 = []
avg_task_execution_perf_9 = []
avg_task_execution_perf_6 = []
avg_task_execution_local_12 = []
avg_task_execution_local_9 = []
avg_task_execution_local_6 = []

avg_task_energy_fix_12 = []
avg_task_energy_fix_9 = []
avg_task_energy_fix_6 = []
avg_task_energy_dyn_12 = []
avg_task_energy_dyn_9 = []
avg_task_energy_dyn_6 = []
avg_task_energy_perf_12 = []
avg_task_energy_perf_9 = []
avg_task_energy_perf_6 = []
avg_task_energy_local_12 = []
avg_task_energy_local_9 = []
avg_task_energy_local_6 = []


distribution_local_12 = []
distribution_remote_12 = []
distribution_cloudlet_12 = []

distribution_local_9 = []
distribution_remote_9 = []
distribution_cloudlet_9 = []

distribution_local_6 = []
distribution_remote_6 = []
distribution_cloudlet_6 = []

if process_files:
    for group in groups:
        for gen in generation_deadlines:
            for rep in range(3):
                if group == "LOCAL_FIXED" and gen not in ["12_12", "9_9", "6_6"]:
                    continue
                working_dir = "{}/{}{}_{}/0/{}/".format(argv[1], base_name, group, gen, rep)
                print("Processing {}".format(working_dir))

                files_powermap["{}_{}_{}".format(group, gen, rep)] = {}
                files_taskmap["{}_{}_{}".format(group, gen, rep)] = {}
                files_deadline_met["{}_{}_{}".format(group, gen, rep)] = {}
                files_task_completion_duration["{}_{}_{}".format(group, gen, rep)] = {}
                files_task_duration["{}_{}_{}".format(group, gen, rep)] = {}
                files_battery_level["{}_{}_{}".format(group, gen, rep)] = {}
                files_battery_charge["{}_{}_{}".format(group, gen, rep)] = {}
                files_tasks_generated["{}_{}_{}".format(group, gen, rep)] = {}
                files_tasks_executed["{}_{}_{}".format(group, gen, rep)] = {}
                files_duration["{}_{}_{}".format(group, gen, rep)] = {}
                files_delta_e["{}_{}_{}".format(group, gen, rep)] = {}
                total_duration["{}_{}_{}".format(group,gen,rep)] = 0
                for file in os.listdir(working_dir):
                    name = file.rstrip(".csv")
                    data_lines = open(working_dir + "/" + file, "r").read().split("\n")
                    files_powermap["{}_{}_{}".format(group, gen, rep)][name], files_taskmap["{}_{}_{}".format(group, gen, rep)][name], files_deadline_met["{}_{}_{}".format(group, gen, rep)][name], files_task_completion_duration["{}_{}_{}".format(group, gen, rep)][name], files_task_duration["{}_{}_{}".format(group, gen, rep)][name], files_battery_level["{}_{}_{}".format(group, gen, rep)][name], files_battery_charge["{}_{}_{}".format(group, gen, rep)][name], files_tasks_generated["{}_{}_{}".format(group, gen, rep)][name], files_tasks_executed["{}_{}_{}".format(group, gen, rep)][name] = getDataFromLines(data_lines)
                    files_duration["{}_{}_{}".format(group, gen, rep)][name] = getTimeStamp(data_lines[-2]) - getTimeStamp(data_lines[1])
                    files_delta_e["{}_{}_{}".format(group, gen, rep)][name] = getDeltaE("{}_{}_{}".format(group, gen, rep), name, data_lines)
                    total_duration["{}_{}_{}".format(group,gen,rep)] = max(total_duration["{}_{}_{}".format(group,gen,rep)], ((getTimeStamp(data_lines[-2])-getTimeStamp(data_lines[1])) / 1000.0))
    storage["files_powermap"] = files_powermap
    storage["files_taskmap"] = files_taskmap
    storage["files_deadline_met"] = files_deadline_met
    storage["files_task_completion_duration"] = files_task_completion_duration
    storage["files_task_duration"] = files_task_duration
    storage["files_battery_level"] = files_battery_level
    storage["files_battery_charge"] = files_battery_charge
    storage["files_tasks_generated"] = files_tasks_generated
    storage["files_tasks_executed"] = files_tasks_executed
    storage["files_duration"] = files_duration
    storage["files_delta_e"] = files_delta_e
    storage["total_duration"] = total_duration
else:
    files_powermap = storage["files_powermap"]
    files_taskmap = storage["files_taskmap"]
    files_deadline_met = storage["files_deadline_met"]
    files_task_completion_duration = storage["files_task_completion_duration"]
    files_task_duration = storage["files_task_duration"]
    files_battery_level = storage["files_battery_level"]
    files_battery_charge = storage["files_battery_charge"]
    files_tasks_generated = storage["files_tasks_generated"]
    files_tasks_executed = storage["files_tasks_executed"]
    files_duration = storage["files_duration"]
    files_delta_e = storage["files_delta_e"]
    total_duration = storage["total_duration"]

storage.close()


for group in groups:
    for gen in generation_deadlines:
        absolute_total_delta_energy = 0
        absolute_total_deadline_met_pcnt = 0
        absolute_total_local_executions_pcnt = 0
        absolute_total_cloudlet_offloads_pcnt = 0
        absolute_total_remote_executions_pcnt = 0
        absolute_total_avg_task_time = 0
        absolute_avg_total_task_energy = 0
        i = 0
        for rep in range(3):
            if group == "LOCAL_FIXED" and gen not in ["12_12", "9_9", "6_6"]:
                continue
            working_dir = "{}/{}{}_{}/0/{}/".format(argv[1], base_name, group, gen, rep)
            print(working_dir)
            # for file in os.listdir(working_dir):
            #     name = file.rstrip(".csv")
            #     data_lines = open(working_dir + "/" + file, "r").read().split("\n")
            #     files_powermap[name], files_taskmap[name], files_deadline_met[name], files_task_completion_duration[name], files_task_duration[name], files_battery_level[name], files_battery_charge[name], files_tasks_generated[name], files_tasks_executed[name] = getDataFromLines(data_lines)
            #     files_duration[name] = getTimeStamp(data_lines[-2]) - getTimeStamp(data_lines[1])
            #     files_delta_e[name] = getDeltaE(name, data_lines)
            #     total_duration = max(total_duration, ((getTimeStamp(data_lines[-2])-getTimeStamp(data_lines[1])) / 1000.0))

            total_task_energy = 0
            total_task_count = 0
            files_avg_task_powers["{}_{}_{}".format(group, gen, rep)] = {}
            for file in sorted(files_powermap["{}_{}_{}".format(group, gen, rep)].keys()):
                entries = 0
                avg_p_file = 0
                for task in files_task_duration["{}_{}_{}".format(group, gen, rep)][file]:
                    avg_task_power = 0
                    avg_task_power_cnt = 0
                    for power in files_powermap["{}_{}_{}".format(group, gen, rep)][file]:
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
                    files_avg_task_powers["{}_{}_{}".format(group, gen, rep)][file] = avg_p_file / entries
                else:
                    files_avg_task_powers["{}_{}_{}".format(group, gen, rep)][file] = 0.0

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


            for file in sorted(files_taskmap["{}_{}_{}".format(group, gen, rep)].keys()):
                avg_compute_time = 0
                avg_task_time = 0
                for task in files_task_duration["{}_{}_{}".format(group, gen, rep)][file]:
                    avg_compute_time += task[1] - task[0]
                try:
                    avg_compute_time = (avg_compute_time / len(files_task_duration["{}_{}_{}".format(group, gen, rep)][file])) / 1000.0
                    total_avg_compute_time_cnt += files_taskmap["{}_{}_{}".format(group, gen, rep)][file][0]
                except:
                    None
                total_avg_compute_time += avg_compute_time*files_taskmap["{}_{}_{}".format(group, gen, rep)][file][0]
                for task in files_task_completion_duration["{}_{}_{}".format(group, gen, rep)][file]:
                    avg_task_time += task
                try:
                    avg_task_time = (avg_task_time / len(files_task_completion_duration["{}_{}_{}".format(group, gen, rep)][file])) / 1000.0
                    total_avg_task_time_cnt += files_taskmap["{}_{}_{}".format(group, gen, rep)][file][0]
                except:
                    None
                total_avg_task_time += avg_task_time*files_taskmap["{}_{}_{}".format(group, gen, rep)][file][0]
                max_bat = 0
                min_bat = 100
                for bat in files_battery_level["{}_{}_{}".format(group, gen, rep)][file]:
                    if bat[1] > max_bat:
                        max_bat = bat[1]
                    if bat[1] < min_bat:
                        min_bat = bat[1]
                if min_bat == 100 and max_bat == 0:
                    min_bat = 0
                max_cap = -maxsize - 1
                min_cap = maxsize
                for cap in files_battery_charge["{}_{}_{}".format(group, gen, rep)][file]:
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
                    deadline_success_pcnt = ((files_deadline_met["{}_{}_{}".format(group, gen, rep)][file][0]*100.0)/files_taskmap["{}_{}_{}".format(group, gen, rep)][file][0])
                    deadline_broken_pcnt = ((files_deadline_met["{}_{}_{}".format(group, gen, rep)][file][1]*100.0)/files_taskmap["{}_{}_{}".format(group, gen, rep)][file][0])
                except:
                    None
                total_tasks_generated += files_taskmap["{}_{}_{}".format(group, gen, rep)][file][0]
                total_tasks_executed += files_taskmap["{}_{}_{}".format(group, gen, rep)][file][1]
                total_tasks_offloaded += files_taskmap["{}_{}_{}".format(group, gen, rep)][file][2]
                total_deadline_met += files_deadline_met["{}_{}_{}".format(group, gen, rep)][file][0]
                total_deadline_broken += files_deadline_met["{}_{}_{}".format(group, gen, rep)][file][1]
                total_delta_energy += files_delta_e["{}_{}_{}".format(group, gen, rep)][file]

            total_global_local_executions = 0
            total_global_cloudlet_offloads = 0
            total_global_generated_tasks = 0

            for file in sorted(files_tasks_generated["{}_{}_{}".format(group, gen, rep)].keys()):
                for task_id in files_tasks_generated["{}_{}_{}".format(group, gen, rep)][file]:
                    total_global_generated_tasks += 1
                    if task_id in files_tasks_executed["{}_{}_{}".format(group, gen, rep)][file]:
                        total_global_local_executions += 1
                    elif "cloudlet_192.168.3.15" in files_tasks_executed["{}_{}_{}".format(group, gen, rep)].keys():
                        if task_id in files_tasks_executed["{}_{}_{}".format(group, gen, rep)]["cloudlet_192.168.3.15"]:
                            total_global_cloudlet_offloads += 1
            try:
                total_local_executions_pcnt = ((total_global_local_executions*100.0)/total_global_generated_tasks)
            except:
                total_local_executions_pcnt = 0
            try:
                total_cloudlet_executions_pcnt = ((total_global_cloudlet_offloads*100.0)/total_global_generated_tasks)
            except:
                total_cloudlet_executions_pcnt = 0
            total_remote_executions_pcnt = 100.0 - total_local_executions_pcnt - total_cloudlet_executions_pcnt

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

            i += 1
            #graph 1
            absolute_total_delta_energy += total_delta_energy
            absolute_total_deadline_met_pcnt = total_deadline_met_pcnt

            #graph 2
            absolute_total_local_executions_pcnt += total_local_executions_pcnt
            absolute_total_cloudlet_offloads_pcnt += total_cloudlet_executions_pcnt
            absolute_total_remote_executions_pcnt += total_remote_executions_pcnt

            #graph 3
            print(total_avg_task_time_pcnt)
            absolute_total_avg_task_time += total_avg_task_time_pcnt

            #graph 4
            absolute_avg_total_task_energy += total_task_energy_pcnt

        if group == "GREEN_DYN":
            if gen.strip("CLOUDLET_")[:2] == "12":
                dyn_12.append(absolute_total_delta_energy/i)
                avg_task_execution_dyn_12.append(absolute_total_avg_task_time/i)
                avg_task_energy_dyn_12.append(absolute_avg_total_task_energy/i)
                deadline_dyn_12.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                distribution_local_12.append(absolute_total_local_executions_pcnt/i)
                distribution_remote_12.append(absolute_total_remote_executions_pcnt/i)
                distribution_cloudlet_12.append(absolute_total_cloudlet_offloads_pcnt/i)
            if gen.strip("CLOUDLET_")[:1] == "9":
                dyn_9.append(absolute_total_delta_energy/i)
                avg_task_execution_dyn_9.append(absolute_total_avg_task_time/i)
                avg_task_energy_dyn_9.append(absolute_avg_total_task_energy/i)
                deadline_dyn_9.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                distribution_local_9.append(absolute_total_local_executions_pcnt/i)
                distribution_remote_9.append(absolute_total_remote_executions_pcnt/i)
                distribution_cloudlet_9.append(absolute_total_cloudlet_offloads_pcnt/i)
            if gen.strip("CLOUDLET_")[:1] == "6":
                dyn_6.append(absolute_total_delta_energy/i)
                avg_task_execution_dyn_6.append(absolute_total_avg_task_time/i)
                avg_task_energy_dyn_6.append(absolute_avg_total_task_energy/i)
                deadline_dyn_6.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                distribution_local_6.append(absolute_total_local_executions_pcnt/i)
                distribution_remote_6.append(absolute_total_remote_executions_pcnt/i)
                distribution_cloudlet_6.append(absolute_total_cloudlet_offloads_pcnt/i)
        if group == "GREEN_FIXED":
            if gen.strip("CLOUDLET_")[:2] == "12":
                fix_12.append(absolute_total_delta_energy/i)
                avg_task_execution_fix_12.append(absolute_total_avg_task_time/i)
                avg_task_energy_fix_12.append(absolute_avg_total_task_energy/i)
                deadline_fix_12.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                distribution_local_12.append(absolute_total_local_executions_pcnt/i)
                distribution_remote_12.append(absolute_total_remote_executions_pcnt/i)
                distribution_cloudlet_12.append(absolute_total_cloudlet_offloads_pcnt/i)
            if gen.strip("CLOUDLET_")[:1] == "9":
                fix_9.append(absolute_total_delta_energy/i)
                avg_task_execution_fix_9.append(absolute_total_avg_task_time/i)
                avg_task_energy_fix_9.append(absolute_avg_total_task_energy/i)
                deadline_fix_9.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                distribution_local_9.append(absolute_total_local_executions_pcnt/i)
                distribution_remote_9.append(absolute_total_remote_executions_pcnt/i)
                distribution_cloudlet_9.append(absolute_total_cloudlet_offloads_pcnt/i)
            if gen.strip("CLOUDLET_")[:1] == "6":
                fix_6.append(absolute_total_delta_energy/i)
                avg_task_execution_fix_6.append(absolute_total_avg_task_time/i)
                avg_task_energy_fix_6.append(absolute_avg_total_task_energy/i)
                deadline_fix_6.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                distribution_local_6.append(absolute_total_local_executions_pcnt/i)
                distribution_remote_6.append(absolute_total_remote_executions_pcnt/i)
                distribution_cloudlet_6.append(absolute_total_cloudlet_offloads_pcnt/i)
        if group == "PERFORMANCE":
            if gen.strip("CLOUDLET_")[:2] == "12":
                perf_12.append(absolute_total_delta_energy/i)
                avg_task_execution_perf_12.append(absolute_total_avg_task_time/i)
                avg_task_energy_perf_12.append(absolute_avg_total_task_energy/i)
                deadline_perf_12.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                distribution_local_12.append(absolute_total_local_executions_pcnt/i)
                distribution_remote_12.append(absolute_total_remote_executions_pcnt/i)
                distribution_cloudlet_12.append(absolute_total_cloudlet_offloads_pcnt/i)
            if gen.strip("CLOUDLET_")[:1] == "9":
                perf_9.append(absolute_total_delta_energy/i)
                avg_task_execution_perf_9.append(absolute_total_avg_task_time/i)
                avg_task_energy_perf_9.append(absolute_avg_total_task_energy/i)
                deadline_perf_9.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                distribution_local_9.append(absolute_total_local_executions_pcnt/i)
                distribution_remote_9.append(absolute_total_remote_executions_pcnt/i)
                distribution_cloudlet_9.append(absolute_total_cloudlet_offloads_pcnt/i)
            if gen.strip("CLOUDLET_")[:1] == "6":
                print(i)
                print(absolute_total_delta_energy)
                print(absolute_total_avg_task_time)
                print(absolute_avg_total_task_energy)
                print(absolute_total_deadline_met_pcnt)
                perf_6.append(absolute_total_delta_energy/i)
                avg_task_execution_perf_6.append(absolute_total_avg_task_time/i)
                avg_task_energy_perf_6.append(absolute_avg_total_task_energy/i)
                deadline_perf_6.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                distribution_local_6.append(absolute_total_local_executions_pcnt/i)
                distribution_remote_6.append(absolute_total_remote_executions_pcnt/i)
                distribution_cloudlet_6.append(absolute_total_cloudlet_offloads_pcnt/i)
        if group == "LOCAL_FIXED":
            try:
                if gen.strip("CLOUDLET_")[:2] == "12":
                    local_12.append(absolute_total_delta_energy/i)
                    avg_task_execution_local_12.append(absolute_total_avg_task_time/i)
                    avg_task_energy_local_12.append(absolute_avg_total_task_energy/i)
                    deadline_local_12.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                if gen.strip("CLOUDLET_")[:1] == "9":
                    local_9.append(absolute_total_delta_energy/i)
                    avg_task_execution_local_9.append(absolute_total_avg_task_time/i)
                    avg_task_energy_local_9.append(absolute_avg_total_task_energy/i)
                    deadline_local_9.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
                if gen.strip("CLOUDLET_")[:1] == "6":
                    local_6.append(absolute_total_delta_energy/i)
                    avg_task_execution_local_6.append(absolute_total_avg_task_time/i)
                    avg_task_energy_local_6.append(absolute_avg_total_task_energy/i)
                    deadline_local_6.append("({:.1f}%)".format(absolute_total_deadline_met_pcnt/i))
            except:
                None

fig = go.Figure(data=[])

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing = 0.05, subplot_titles=("{}=12".format(chr(0x03BB)),"{}=9".format(chr(0x03BB)), "{}=6".format(chr(0x03BB))))

fig.add_trace(go.Bar(name='Green w\ Fix Estimations', y=y_labels, x=fix_12, orientation='h',textposition = 'outside', text=deadline_fix_12, marker_color="#009E73",showlegend=True), row=1, col=1)
fig.add_trace(go.Bar(name="Green w\ Dynamic Estimations", y=y_labels, x=dyn_12, orientation='h',textposition = 'outside', text=deadline_dyn_12, marker_color="#D55E00",showlegend=True), row=1, col=1)
fig.add_trace(go.Bar(name="Performance", y=y_labels, x=perf_12, orientation='h',textposition = 'outside', text=deadline_perf_12, marker_color="#E69F00",showlegend=True), row=1, col=1)
fig.add_trace(go.Bar(name="Local only", y=y_labels, x=local_12, orientation='h',textposition = 'outside', text=deadline_local_12, marker_color="#0072B2",showlegend=True), row=1, col=1)


fig.add_trace(go.Bar(name='Green w\ Fix Estimations', y=y_labels[:1]+y_labels[2:], x=fix_9, orientation='h',textposition = 'outside', text=deadline_fix_9, marker_color="#009E73", showlegend=False), row=2, col=1)
fig.add_trace(go.Bar(name="Green w\ Dynamic Estimations", y=y_labels[:1]+y_labels[2:], x=dyn_9, orientation='h',textposition = 'outside', text=deadline_dyn_9, marker_color="#D55E00", showlegend=False), row=2, col=1)
fig.add_trace(go.Bar(name="Performance", y=y_labels[:1]+y_labels[2:], x=perf_9, orientation='h',textposition = 'outside', text=deadline_perf_9, marker_color="#E69F00", showlegend=False), row=2, col=1)
fig.add_trace(go.Bar(name="Local only", y=y_labels[:1]+y_labels[2:], x=local_9, orientation='h',textposition = 'outside', text=deadline_local_9, marker_color="#0072B2", showlegend=False), row=2, col=1)

fig.add_trace(go.Bar(name='Green w\ Fix Estimations', y=y_labels[:1]+y_labels[3:], x=fix_6, orientation='h', textposition = 'outside', text=deadline_fix_6, marker_color="#009E73", showlegend=False), row=3, col=1)
fig.add_trace(go.Bar(name="Green w\ Dynamic Estimations", y=y_labels[:1]+y_labels[3:], x=dyn_9, orientation='h',textposition = 'outside', text=deadline_dyn_6, marker_color="#D55E00", showlegend=False), row=3, col=1)
fig.add_trace(go.Bar(name="Performance", y=y_labels[:1]+y_labels[3:], x=perf_6, orientation='h',textposition = 'outside', text=deadline_perf_6, marker_color="#E69F00", showlegend=False), row=3, col=1)
fig.add_trace(go.Bar(name="Local only", y=y_labels[:1]+y_labels[3:], x=local_6, orientation='h',textposition = 'outside', text=deadline_local_6, marker_color="#0072B2", showlegend=False), row=3, col=1)

fig.update_layout(barmode='group', title="Power Consumption {}(Wh) (Deadline met %)".format(with_Cloudlet))

fig.show()

fig_1 = go.Figure(data=[])

fig_1 = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing = 0.05, subplot_titles=("{}=12".format(chr(0x03BB)),"{}=9".format(chr(0x03BB)), "{}=6".format(chr(0x03BB))))

fig_1.add_trace(go.Bar(name='Green w\ Fix Estimations', y=y_labels, x=avg_task_execution_fix_12, orientation='h', marker_color="#009E73"), row=1, col=1)
fig_1.add_trace(go.Bar(name="Green w\ Dynamic Estimations", y=y_labels, x=avg_task_execution_dyn_12, orientation='h', marker_color="#D55E00"), row=1, col=1)
fig_1.add_trace(go.Bar(name="Performance", y=y_labels, x=avg_task_execution_perf_12, orientation='h', marker_color="#E69F00"), row=1, col=1)
fig_1.add_trace(go.Bar(name="Local only", y=y_labels, x=avg_task_execution_local_12, orientation='h', marker_color="#0072B2"), row=1, col=1)


fig_1.add_trace(go.Bar(name='Green w\ Fix Estimations', y=y_labels[:1]+y_labels[2:], x=avg_task_execution_fix_9, orientation='h', marker_color="#009E73", showlegend=False), row=2, col=1)
fig_1.add_trace(go.Bar(name="Green w\ Dynamic Estimations", y=y_labels[:1]+y_labels[2:], x=avg_task_execution_dyn_9, orientation='h', marker_color="#D55E00", showlegend=False), row=2, col=1)
fig_1.add_trace(go.Bar(name="Performance", y=y_labels[:1]+y_labels[2:], x=avg_task_execution_perf_9, orientation='h', marker_color="#E69F00", showlegend=False), row=2, col=1)
fig_1.add_trace(go.Bar(name="Local only", y=y_labels[:1]+y_labels[2:], x=avg_task_execution_local_9, orientation='h', marker_color="#0072B2", showlegend=False), row=2, col=1)

fig_1.add_trace(go.Bar(name='Green w\ Fix Estimations', y=y_labels[:1]+y_labels[3:], x=avg_task_execution_fix_6, orientation='h', marker_color="#009E73", showlegend=False), row=3, col=1)
fig_1.add_trace(go.Bar(name="Green w\ Dynamic Estimations", y=y_labels[:1]+y_labels[3:], x=avg_task_execution_dyn_9, orientation='h', marker_color="#D55E00", showlegend=False), row=3, col=1)
fig_1.add_trace(go.Bar(name="Performance", y=y_labels[:1]+y_labels[3:], x=avg_task_execution_perf_6, orientation='h', marker_color="#E69F00", showlegend=False), row=3, col=1)
fig_1.add_trace(go.Bar(name="Local only", y=y_labels[:1]+y_labels[3:], x=avg_task_execution_local_6, orientation='h', marker_color="#0072B2", showlegend=False), row=3, col=1)

fig_1.update_layout(barmode='group', title="Average Task Completion Time {}(s)".format(with_Cloudlet))
fig_1.update_xaxes(tick0=0)

fig_1.show()

fig_2 = go.Figure(data=[])

fig_2 = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing = 0.05, subplot_titles=("{}=12".format(chr(0x03BB)),"{}=9".format(chr(0x03BB)), "{}=6".format(chr(0x03BB))))

fig_2.add_trace(go.Bar(name='Green w\ Fix Estimations', y=y_labels, x=avg_task_energy_fix_12, orientation='h', marker_color="#009E73"), row=1, col=1)
fig_2.add_trace(go.Bar(name="Green w\ Dynamic Estimations", y=y_labels, x=avg_task_energy_dyn_12, orientation='h', marker_color="#D55E00"), row=1, col=1)
fig_2.add_trace(go.Bar(name="Performance", y=y_labels, x=avg_task_energy_perf_12, orientation='h', marker_color="#E69F00"), row=1, col=1)
fig_2.add_trace(go.Bar(name="Local only", y=y_labels, x=avg_task_energy_local_12, orientation='h', marker_color="#0072B2"), row=1, col=1)


fig_2.add_trace(go.Bar(name='Green w\ Fix Estimations', y=y_labels[:1]+y_labels[2:], x=avg_task_energy_fix_9, orientation='h', marker_color="#009E73", showlegend=False), row=2, col=1)
fig_2.add_trace(go.Bar(name="Green w\ Dynamic Estimations", y=y_labels[:1]+y_labels[2:], x=avg_task_energy_dyn_9, orientation='h', marker_color="#D55E00", showlegend=False), row=2, col=1)
fig_2.add_trace(go.Bar(name="Performance", y=y_labels[:1]+y_labels[2:], x=avg_task_energy_perf_9, orientation='h', marker_color="#E69F00", showlegend=False), row=2, col=1)
fig_2.add_trace(go.Bar(name="Local only", y=y_labels[:1]+y_labels[2:], x=avg_task_energy_local_9, orientation='h', marker_color="#0072B2", showlegend=False), row=2, col=1)

fig_2.add_trace(go.Bar(name='Green w\ Fix Estimations', y=y_labels[:1]+y_labels[3:], x=avg_task_energy_fix_6, orientation='h', marker_color="#009E73", showlegend=False), row=3, col=1)
fig_2.add_trace(go.Bar(name="Green w\ Dynamic Estimations", y=y_labels[:1]+y_labels[3:], x=avg_task_energy_dyn_9, orientation='h', marker_color="#D55E00", showlegend=False), row=3, col=1)
fig_2.add_trace(go.Bar(name="Performance", y=y_labels[:1]+y_labels[3:], x=avg_task_energy_perf_6, orientation='h', marker_color="#E69F00", showlegend=False), row=3, col=1)
fig_2.add_trace(go.Bar(name="Local only", y=y_labels[:1]+y_labels[3:], x=avg_task_energy_local_6, orientation='h', marker_color="#0072B2", showlegend=False), row=3, col=1)

fig_2.update_layout(barmode='group', title="Average Energy Consumption Per Task {}(mWh)".format(with_Cloudlet))
fig_2.update_xaxes(tick0=0)

fig_2.show()



fig_3 = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing = 0.05, subplot_titles=("{}=12".format(chr(0x03BB)),"{}=9".format(chr(0x03BB)), "{}=6".format(chr(0x03BB))))


y_labels_1 = [["d={}".format(chr(0x00D8)),"d={}".format(chr(0x00D8)),"d={}".format(chr(0x00D8)),
                "d=12","d=12","d=12","d=9","d=9","d=9", "d=6","d=6","d=6","d=3","d=3","d=3"],
            ['Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance",
            'Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance",
            'Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance",
            'Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance",
            'Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance"]]


y_labels_2 = [["d={}".format(chr(0x00D8)),"d={}".format(chr(0x00D8)),"d={}".format(chr(0x00D8)),
                "d=9","d=9","d=9", "d=6","d=6","d=6", "d=3","d=3","d=3"],
            ['Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance",
            'Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance",
            'Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance",
            'Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance"]]



y_labels_3 = [["d={}".format(chr(0x00D8)),"d={}".format(chr(0x00D8)),"d={}".format(chr(0x00D8)), "d=6","d=6","d=6", "d=3","d=3","d=3"],
            ['Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance",
            'Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance",
            'Green w\ Fix Estimations', "Green w\ Dynamic Estimations", "Performance"]]

# Green_Fix: [local_12_no_deadline, local_12_12, local_12_9, local_12_6, local_12_3]
# Green_Dyn: [remote_12_no_deadline, remote_12_12, remote_12_9, remote_12_6, remote_12_3]
# Performance: [cloudlet_12_no_deadline, cloudlet_12_12, cloudlet_12_9, cloudlet_12_6, cloudlet_12_3]

# Green_Fix: [local_9_no_deadline, local_9_9, local_9_6, local_9_3]
# Green_Dyn: [remote_9_no_deadline, remote_9_9, remote_9_6, remote_9_3]
# Performance: [cloudlet_9_no_deadline, cloudlet_9_9, cloudlet_9_6, cloudlet_9_3]

# Green_Fix: [local_6_no_deadline, local_6_6, local_6_3]
# Green_Dyn: [remote_6_no_deadline, remote_6_6, remote_6_3]
# Performance: [cloudlet_6_no_deadline, cloudlet_6_6, cloudletv_6_3]



fig_3.add_trace(go.Bar(name='Local', y=y_labels_1, x=distribution_local_12, orientation='h', marker_color="#004D40"), row=1, col=1)
fig_3.add_trace(go.Bar(name="Remote", y=y_labels_1, x=distribution_remote_12, orientation='h', marker_color="#FFC107"), row=1, col=1)
fig_3.add_trace(go.Bar(name="Cloudlet", y=y_labels_1, x=distribution_cloudlet_12, orientation='h', marker_color="#D81B60"), row=1, col=1)

fig_3.add_trace(go.Bar(name='Local', y=y_labels_2, x=distribution_local_9, orientation='h', marker_color="#004D40", showlegend=False), row=2, col=1)
fig_3.add_trace(go.Bar(name="Remote", y=y_labels_2, x=distribution_remote_9, orientation='h', marker_color="#FFC107", showlegend=False), row=2, col=1)
fig_3.add_trace(go.Bar(name="Cloudlet", y=y_labels_2, x=distribution_cloudlet_9, orientation='h', marker_color="#D81B60", showlegend=False), row=2, col=1)

print(distribution_local_6)
fig_3.add_trace(go.Bar(name='Local', y=y_labels_3, x=distribution_local_6, orientation='h', marker_color="#004D40", showlegend=False), row=3, col=1)
fig_3.add_trace(go.Bar(name="Remote", y=y_labels_3, x=distribution_remote_6, orientation='h', marker_color="#FFC107", showlegend=False), row=3, col=1)
fig_3.add_trace(go.Bar(name="Cloudlet", y=y_labels_3, x=distribution_cloudlet_6, orientation='h', marker_color="#D81B60", showlegend=False), row=3, col=1)

fig_3.update_layout(barmode='stack', title="Execution Distribution {}".format(with_Cloudlet))
fig_3.update_yaxes(type='multicategory', row=1, col=1)
fig_3.update_yaxes(type='multicategory', row=2, col=1)
fig_3.update_yaxes(type='multicategory', row=3, col=1)

fig_3.show()
