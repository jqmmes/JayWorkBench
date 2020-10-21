from sys import argv
from re import findall, match

f = open(argv[1], "r")
contents = f.read()
lines = contents.split("\n")

tasks = {}

class task_data:
    init_time = 0
    end_time = 0
    expected_time = {}
    selected_worker = None
    deadline_met = "false"

    def __init__(self):
        self.expected_time = {}
        self.deadline_met = "false"

    expected_power = 0




for line in lines:
    if match("([A-Za-z0-9\.\-]+),([0-9a-z\-]+),ANDROID,(\d+),Info,services\.broker\.BrokerService_scheduleTask\$Jay_Base_(\d+),INIT,([0-9a-z\-]+),", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(\d+),Info,services\.broker\.BrokerService_scheduleTask\$Jay_Base_(?:\d+),INIT,([0-9a-z\-]+),", line)
        if findings[0][1] not in tasks:
            tasks[findings[0][1]] = task_data()
        tasks[findings[0][1]].init_time = int(findings[0][0])
    elif match("([A-Za-z0-9\.\-]+),([0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.SchedulerService_canMeetDeadline\$Jay_Base_(\d+),CHECK_WORKER_MEETS_DEADLINE,([0-9a-z\-]+),\"WORKER=([0-9a-z\-]+);MAX_DEADLINE=(\d+);EXPECTED_DEADLINE=(\d+);", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(?:\d+),Info,services\.scheduler\.SchedulerService_canMeetDeadline\$Jay_Base_(?:\d+),CHECK_WORKER_MEETS_DEADLINE,([0-9a-z\-]+),\"WORKER=([0-9a-z\-]+);MAX_DEADLINE=(\d+);EXPECTED_DEADLINE=(\d+);", line)
        tasks[findings[0][0]].expected_time[findings[0][1]] = int(findings[0][3])
    elif match("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.SchedulerService_schedule\$Jay_Base_(?:\d+),SELECTED_WORKER,([0-9a-z\-]+),\"WORKER=([0-9a-z\-]+)\"", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(?:\d+),Info,services\.scheduler\.SchedulerService_schedule\$Jay_Base_(?:\d+),SELECTED_WORKER,([0-9a-z\-]+),\"WORKER=([0-9a-z\-]+)\"", line)
        tasks[findings[0][0]].selected_worker = findings[0][1]
    elif match("([A-Za-z0-9\.\-]+),([0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.schedulers\.(?:[A-Za-z]+)\$init\$\d+_invoke_(\d+),TASK_WITH_DEADLINE_COMPLETED,([0-9a-z\-]+),\"DEADLINE_MET=(?:true|false)\"", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.schedulers\.(?:[A-Za-z]+)\$init\$(?:\d+)_invoke_(?:\d+),TASK_WITH_DEADLINE_COMPLETED,([0-9a-z\-]+),\"DEADLINE_MET=(true|false)\"", line)
        tasks[findings[0][1]].end_time = int(findings[0][0])
        tasks[findings[0][1]].deadline_met = findings[0][2]


avg_err = 0
avg_cnt = 0.0
for task in tasks.keys():
    real = tasks[task].end_time-tasks[task].init_time
    expected = tasks[task].expected_time[tasks[task].selected_worker]-tasks[task].init_time
    diff = real - expected
    print("{}: {}, {}, {}, {}".format(task, real, expected, diff, tasks[task].deadline_met))
    avg_err += abs(diff)
    avg_cnt += 1
print(avg_err / avg_cnt)
