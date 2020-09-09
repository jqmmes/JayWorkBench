from re import findall
from sys import argv


def cal_average(num):
    if len(num) == 0:
        return 0
    sum_num = 0
    for t in num:
        sum_num = sum_num + float(t)

    avg = sum_num / len(num)
    return avg

f = open(argv[1], "r")
txt = f.read()

powers = findall("POWER=-(\d+\.\d+)", txt)
compute = findall("NEW_AVERAGE_COMPUTATION_TIME=(\d+)", txt)

print("%.2f Wh (%.2fs)" % (cal_average(powers), (cal_average(compute) / 1000.0)))
