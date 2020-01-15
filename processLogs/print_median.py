import sys
import statistics

f = open(sys.argv[1], "r")
r = f.read()
data = []

for l in r.split("\n")[1:]:
    if len(l.split(",")) < 2:
        continue
    data.append(int(l.split(",")[2]))

print("{:.1f}".format(round(statistics.median(data))/1000.0))
