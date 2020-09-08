from sys import argv
from re import findall

proc = open(argv[1], "r").read().split("\n")

sums = 0
i = 0

max_battery = 0
min_battery = 100

for l in proc:
  r = findall("CURRENT=(.*)\"", l)
  if r != []:
    index = r[0].find(";")
    if index != -1:
        b = findall("NEW_BATTERY_LEVEL=(\d+);", l)
        if int(b[0]) > max_battery:
            max_battery = int(b[0])
        if int(b[0]) < min_battery:
            min_battery = int(b[0])
        sums += int(r[0][:index])
    else:
        sums += int(r[0])
    i += 1

print("%d\t%d\t%d" % (sums/i, max_battery, min_battery))
