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
    transfer_time = 0

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
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(?:\d+),Info,services\.scheduler\.SchedulerService_canMeetDeadline\$Jay_Base_(?:\d+),CHECK_WORKER_MEETS_DEADLINE,([0-9a-z\-]+),\"WORKER=([0-9a-z\-]+);MAX_DEADLINE=(\d+);EXPECTED_DEADLINE=(\d+);QUEUE_SIZE=(?:\d+);AVG_TIME_PER_TASK=(\d+)", line)
        tasks[findings[0][0]].expected_time[findings[0][1]] = (int(findings[0][3]), int(findings[0][4]))
    elif match("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.SchedulerService_schedule\$Jay_Base_(?:\d+),SELECTED_WORKER,([0-9a-z\-]+),\"WORKER=([0-9a-z\-]+)\"", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(?:\d+),Info,services\.scheduler\.SchedulerService_schedule\$Jay_Base_(?:\d+),SELECTED_WORKER,([0-9a-z\-]+),\"WORKER=([0-9a-z\-]+)\"", line)
        tasks[findings[0][0]].selected_worker = findings[0][1]
    elif match("([A-Za-z0-9\.\-]+),([0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.schedulers\.(?:[A-Za-z]+)\$init\$\d+_invoke_(\d+),TASK_WITH_DEADLINE_COMPLETED,([0-9a-z\-]+),\"DEADLINE_MET=(?:true|false)\"", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(\d+),Info,services\.scheduler\.schedulers\.(?:[A-Za-z]+)\$init\$(?:\d+)_invoke_(?:\d+),TASK_WITH_DEADLINE_COMPLETED,([0-9a-z\-]+),\"DEADLINE_MET=(true|false)\"", line)
        tasks[findings[0][1]].end_time = int(findings[0][0])
        tasks[findings[0][1]].deadline_met = findings[0][2]
    elif match("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(?:\d+),Info,services\.broker\.grpc\.BrokerGRPCClient\$ResponseStreamObserver_onNext_(?:\d+),DATA_REACHED_SERVER,([0-9a-z\-]+),\"DATA_SIZE=(?:\d+);DURATION_MILLIS=(\d+);", line):
        findings = findall("(?:[A-Za-z0-9\.\-]+),(?:[0-9a-z\-]+),ANDROID,(?:\d+),Info,services\.broker\.grpc\.BrokerGRPCClient\$ResponseStreamObserver_onNext_(?:\d+),DATA_REACHED_SERVER,([0-9a-z\-]+),\"DATA_SIZE=(?:\d+);DURATION_MILLIS=(\d+);", line)
        tasks[findings[0][0]].transfer_time = int(findings[0][1])



avg_err = 0
avg_cnt = 0.0
print(f'{"TASK":<36}\t{"REAL":<7}\t{"EXPECT":<7}\t{"DIFF":<7}\t{"TRANSFR":<7}\t{"COMPUTE":<7}\t{"DEADLINE":<7}')
print("------------------------------------------------------------------------------------------------")
for task in tasks.keys():
    real = tasks[task].end_time-tasks[task].init_time
    expected = tasks[task].expected_time[tasks[task].selected_worker][0]-tasks[task].init_time
    diff = real - expected
    if (diff < -100000):
        continue
    print(f"{task:<36}\t{real/1000:<7.2f}\t{expected/1000:<7.2f}\t{diff/1000:<7.2f}\t{tasks[task].transfer_time/1000:<7.2f}\t{tasks[task].expected_time[tasks[task].selected_worker][1]/1000:<7.2f}\t{tasks[task].deadline_met:<7}")
    avg_err += abs(diff)
    avg_cnt += 1
print(f'AVG_ERR\t{(avg_err / avg_cnt)/1000:.2f}')
