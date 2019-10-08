import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import sys

#schedulers = ["MultiDeviceScheduler [Random] [LOCAL, REMOTE]", "SingleDeviceScheduler [LOCAL]", "SingleDeviceScheduler [REMOTE]", "EstimatedTimeScheduler"]
schedulers = ["SD", "HD", "UHD"]
base_dir = sys.argv[1]
processed_experiments = []
scheduler_map = {}


i = 0
fig_0 = go.Figure()
fig_1 = go.Figure()
fig_2 = go.Figure()
for scheduler in schedulers:
    first = True
    for entry in os.listdir(base_dir):
        if (entry in processed_experiments) or (not os.path.isdir("{}/{}".format(base_dir, entry))):
            continue
    #     conf = ""
    #     try:
    #         conf = open("{}/{}/conf.cfg".format(base_dir, entry), "r").read()
    #     except:
    #         continue
        if entry.find("_{}".format(scheduler)) != -1:
            processed_experiments.append(entry)
            if first:
                os.system("python3 printJobDetails.py {}/{}/0/* > data_transfer_boxplot_{}.csv".format(base_dir, entry, i))
            else:
                os.system("python3 printJobDetails.py no-header {}/{}/0/* >> data_transfer_boxplot_{}.csv".format(base_dir, entry, i))
            scheduler_map[scheduler] = entry
            first = False
    try:
        data = pd.read_csv("data_transfer_boxplot_{}.csv".format(i))
        fig_0.add_trace(go.Box(y=data["DATA_TRANSFER"].values, name=scheduler))
        fig_2.add_trace(go.Box(y=data["IMAGE_LOAD"].values, name=scheduler))
        fig_2.add_trace(go.Box(y=data["DETECTION"].values, name=scheduler))
    except:
        None
    i += 1

pio.write_html(fig_0, "data_transfer_global_boxplot.html")
pio.write_html(fig_1, "image_load_global_boxplot.html")
pio.write_html(fig_2, "detection_global_boxplot.html")
#fig.show()




#os.sys
#pd.read_csv("")
