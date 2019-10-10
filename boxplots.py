import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import sys

#schedulers = ["MultiDeviceScheduler [Random] [LOCAL, REMOTE]", "SingleDeviceScheduler [LOCAL]", "SingleDeviceScheduler [REMOTE]", "EstimatedTimeScheduler"]
schedulers = ["SD", "HD", "UHD"]
devices = ["local", "remote", "cloud"]
base_dir = sys.argv[1]
processed_experiments = []
scheduler_map = {}



fig_0 = go.Figure()
fig_1 = go.Figure()
fig_2 = go.Figure()
i = 0
for scheduler in schedulers:
    for device in devices[1:]:
        first = True
        for entry in os.listdir(base_dir):
            #if (entry in processed_experiments) or (not os.path.isdir("{}/{}".format(base_dir, entry))):
            #    continue
        #     conf = ""
        #     try:
        #         conf = open("{}/{}/conf.cfg".format(base_dir, entry), "r").read()
        #     except:
        #         continue
            if entry.find("_{}".format(scheduler)) != -1:
                print("PROCESSING\t{}".format(device))
                processed_experiments.append(entry)
                if first:
                    os.system("python3 printJobDetails.py {}-only {}/{}/0/* > data_transfer_boxplot_{}_{}.csv".format(device, base_dir, entry, device, i))
                else:
                    os.system("python3 printJobDetails.py {}-only-no-header {}/{}/0/* >> data_transfer_boxplot_{}_{}.csv".format(device, base_dir, entry, device, i))
                #scheduler_map[scheduler] = entry
                first = False
    i += 1

#try:
for device in devices:
    data_transfer = []
    image_load = []
    detection = []
    group_labels = []
    new_data = False
    for i in range(len(schedulers)):
        if os.path.isfile("data_transfer_boxplot_{}_{}.csv".format(device, i)):
            new_data = True
            data = pd.read_csv("data_transfer_boxplot_{}_{}.csv".format(device, i))
            data_transfer += data["DATA_TRANSFER"].values.tolist()
            image_load += data["IMAGE_LOAD"].values.tolist()
            detection += data["DETECTION"].values.tolist()
            labels = [schedulers[i]]*len(data["DATA_TRANSFER"].values.tolist())
            group_labels += labels
    if new_data:
        fig_0.add_trace(go.Box(y=data_transfer, x=group_labels, name=device))
        fig_1.add_trace(go.Box(y=image_load, x=group_labels, name=device))
        fig_2.add_trace(go.Box(y=detection, x=group_labels, name=device))
    #fig_0.add_trace(go.Box(y=data["DATA_TRANSFER"].values, name=device))
    #fig_1.add_trace(go.Box(y=data["IMAGE_LOAD"].values, name=device))
    #fig_2.add_trace(go.Box(y=data["DETECTION"].values, name=device))
#except:
#    None
fig_0.update_layout(
    yaxis_title='Data Transfer',
    boxmode='group' # group together boxes of the different traces for each value of x
)

fig_1.update_layout(
    yaxis_title='Image Load',
    boxmode='group' # group together boxes of the different traces for each value of x
)

fig_2.update_layout(
    yaxis_title='Detection',
    boxmode='group' # group together boxes of the different traces for each value of x
)

pio.write_html(fig_0, "data_transfer_grouped_boxplot.html")
pio.write_html(fig_1, "image_load_grouped_boxplot.html")
pio.write_html(fig_2, "detection_grouped_boxplot.html")
#fig.show()




#os.sys
#pd.read_csv("")
