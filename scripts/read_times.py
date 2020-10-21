from sys import argv
from re import findall, match

f = open(argv[1], "r")
contents = f.read()
lines = contents.split("\n")

tasks = {}

class task_data:
    init_time = 0
    end_time = 0
    expected_time = 0
    deadline_met = "false"

    expected_power = 0




for line in lines:
    if match("([A-Za-z0-9\.\-]+),([0-9a-z\-]+),ANDROID,(\d+),Info,services\.broker\.BrokerService_scheduleTask\$Jay_Base_(\d+),INIT,([0-9a-z\-]+),", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(\d+),Info,services\.broker\.BrokerService_scheduleTask\$Jay_Base_(?:\d+),INIT,([0-9a-z\-]+),", line)
        if findings[0][1] not in tasks:
            tasks[findings[0][1]] = task_data()
        tasks[findings[0][1]].init_time = int(findings[0][0])
    elif match("([A-Za-z0-9\.\-]+),([0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.SchedulerService_canMeetDeadline\$Jay_Base_(\d+),CHECK_WORKER_MEETS_DEADLINE,([0-9a-z\-]+),\"WORKER=([0-9a-z\-]+);MAX_DEADLINE=(\d+);EXPECTED_DEADLINE=(\d+);", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(?:\d+),Info,services\.scheduler\.SchedulerService_canMeetDeadline\$Jay_Base_(?:\d+),CHECK_WORKER_MEETS_DEADLINE,([0-9a-z\-]+),\"WORKER=(?:[0-9a-z\-]+);MAX_DEADLINE=(\d+);EXPECTED_DEADLINE=(\d+);", line)
        tasks[findings[0][0]].expected_time = int(findings[0][2])
    elif match("([A-Za-z0-9\.\-]+),([0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.schedulers\.GreenTaskScheduler\$init\$\d+_invoke_(\d+),TASK_WITH_DEADLINE_COMPLETED,([0-9a-z\-]+),\"DEADLINE_MET=(?:true|false)\"", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.schedulers\.GreenTaskScheduler\$init\$(?:\d+)_invoke_(?:\d+),TASK_WITH_DEADLINE_COMPLETED,([0-9a-z\-]+),\"DEADLINE_MET=(true|false)\"", line)
        tasks[findings[0][1]].end_time = int(findings[0][0])
        tasks[findings[0][1]].deadline_met = findings[0][2]


for task in tasks.keys():
    real = tasks[task].end_time-tasks[task].init_time
    expected = tasks[task].expected_time-tasks[task].init_time
    diff = real - expected
    print("{}: {}, {}, {}, {}".format(task, real, expected, diff, tasks[task].deadline_met))
