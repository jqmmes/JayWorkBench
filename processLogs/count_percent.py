import sys

f = open(sys.argv[1], "r")
r = f.read()
cloudlet = "joaquim-MS-7996"
cloud = "compute-europe-west"

c_cloudlet = 0
c_cloud = 0
c_local = 0
c_remote = 0
total = 0.0

for l in r.split("\n")[1:]:
    if len(l.split(",")) < 2:
        continue
    if l.split(",")[1] == cloudlet:
        c_cloudlet += 1
    elif l.split(",")[1] == cloud:
        c_cloud += 1
    elif l.split(",")[1] == l.split(",")[0]:
        c_local += 1
    else:
        c_remote += 1
    total += 1.0
if c_cloudlet > 0:
    print("cloudlet: {}".format(c_cloudlet/total*100))
if c_cloud > 0:
    print("cloud: {}".format(c_cloud/total*100))
if c_local > 0:
    print("local: {}".format((c_local)/total*100))
if c_remote > 0:
    print("remote: {}".format((c_remote)/total*100))
if c_local+c_remote > 0:
    print("local+remote: {}".format((c_local+c_remote)/total*100))
