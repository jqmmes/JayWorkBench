import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import sys
# TODO: Separar ACTIVE de PASSIVE   [_ACTIVE_BW_ESTIMATE | _PASSIVE_BW_ESTIMATE]
schedulers = ["MultiDeviceScheduler [Random] [LOCAL, REMOTE]", "MultiDeviceScheduler [Random] [LOCAL, CLOUD, REMOTE]", "SingleDeviceScheduler [LOCAL]", "SingleDeviceScheduler [REMOTE]", "SingleDeviceScheduler [CLOUD]", "EstimatedTimeScheduler", "ComputationEstimateScheduler"]
schedulers_translate = {"MultiDeviceScheduler [Random] [LOCAL, REMOTE]": "MultiDevice_Local_Remote", "MultiDeviceScheduler [Random] [LOCAL, CLOUD, REMOTE]": "MultiDevice_Local_Remote", "SingleDeviceScheduler [LOCAL]": "SingleDevice_Local", "SingleDeviceScheduler [REMOTE]": "SingleDevice_Remote", "SingleDeviceScheduler [CLOUD]": "SingleDevice_Cloud", "EstimatedTimeScheduler" : "EstimatedTimeScheduler", "ComputationEstimateScheduler": "ComputationEstimateScheduler"}
asset_types = ["SD", "HD", "UHD"]
should_use_cloudlet = [False, True]
should_use_cloud = [False, True]
base_dir = sys.argv[1]
processed_experiments = []
scheduler_map = {}
should_use_5s = [False, True]
should_use_500ms = [False, True]
should_use_calibrated = [False, True]

for asset_type in asset_types:
    for scheduler in schedulers:
        for use_cloudlet in should_use_cloudlet:
            for use_cloud in should_use_cloud:
                for use_5s in should_use_5s:
                    for use_500ms in should_use_500ms:
                        for use_calibrated in should_use_calibrated:
                            first = True
                            for entry in os.listdir(base_dir):
                                if (entry in processed_experiments) or (not os.path.isdir("{}/{}".format(base_dir, entry))):
                                   continue
                                conf = ""
                                try:
                                    conf = open("{}/{}/conf.cfg".format(base_dir, entry), "r").read()
                                except:
                                    continue
                                cloudlet_pass = (entry.lower().find("_cloudlet") != -1 and use_cloudlet) or (entry.lower().find("_cloudlet") == -1 and not use_cloudlet)
                                cloud_pass = ((entry.lower().find("_cloud_") != -1 or entry.lower().endswith("_cloud")) and use_cloud) or ((entry.lower().find("_cloud_") == -1 or entry.lower().endswith("_cloud")) and not use_cloud)
                                use_5s_pass = (entry.lower().find("_5s") != -1 and use_5s) or (entry.lower().find("_5s") == -1 and not use_5s)
                                use_500ms_pass = (entry.lower().find("_500ms_workerupdate") != -1 and use_500ms) or (entry.lower().find("_500ms_workerupdate") == -1 and not use_500ms) or schedulers_translate[scheduler] not in ["EstimatedTimeScheduler", "ComputationEstimateScheduler"]
                                calibrated_pass = (entry.upper().find("_CALIBRATED") != -1 and use_calibrated) or (entry.upper().find("_CALIBRATED") == -1 and not use_calibrated) or schedulers_translate[scheduler] not in ["EstimatedTimeScheduler", "ComputationEstimateScheduler"]
                                if entry.find("_{}".format(asset_type)) != -1 and conf.find(scheduler) != -1 and cloudlet_pass and cloud_pass and use_5s_pass and use_500ms_pass and calibrated_pass:
                                    processed_experiments.append(entry)
                                    cloudlet = ""
                                    if use_cloudlet:
                                        cloudlet = "_cloudlet"
                                    cloud = ""
                                    if use_cloud:
                                        cloud = "_cloud"
                                    checking_5s = ""
                                    if use_5s:
                                        checking_5s = "_5s"
                                    checking_500ms = ""
                                    if use_500ms and (schedulers_translate[scheduler] == "EstimatedTimeScheduler" or  schedulers_translate[scheduler] == "ComputationEstimateScheduler"):
                                        checking_500ms = "_500ms_WorkerUpdate"
                                    calibrated = ""
                                    if use_calibrated:
                                        calibrated = "_CALIBRATED"
                                    print("PROCESSING\t{}\t{}\tINTO\t{}".format(scheduler, entry ,"csv/scheduler_boxplot_{}{}{}{}{}{}_{}.csv".format(schedulers_translate[scheduler], cloudlet, cloud, checking_5s, checking_500ms, calibrated, asset_type)), end="")
                                    if os.path.isfile("csv/scheduler_boxplot_{}{}{}{}{}{}_{}.csv".format(schedulers_translate[scheduler], cloudlet, cloud, checking_5s, checking_500ms, calibrated, asset_type)):
                                        print("\tALREADY_PROCESSED")
                                        continue
                                    print()
                                    if first:
                                        os.system("python3 printJobDetails.py {}/{}/0/* > csv/scheduler_boxplot_{}{}{}{}{}{}_{}.csv 2> /dev/null".format(base_dir, entry, schedulers_translate[scheduler], cloudlet, cloud, checking_5s, checking_500ms, calibrated, asset_type))
                                    else:
                                        os.system("python3 printJobDetails.py no-header {}/{}/0/* >> csv/scheduler_boxplot_{}{}{}{}{}{}_{}.csv 2> /dev/null".format(base_dir, entry, schedulers_translate[scheduler], cloudlet, cloud, checking_5s, checking_500ms, calibrated, asset_type))
                                    scheduler_map[scheduler] = entry
                                    first = False

#try:
fig_0 = go.Figure()
fig_1 = go.Figure()
fig_2 = go.Figure()
fig_3 = go.Figure()
fig_4 = go.Figure()
fig_5 = go.Figure()
for scheduler in schedulers:
    for use_cloudlet in should_use_cloudlet:
        for use_cloud in should_use_cloud:
            for use_5s in should_use_5s:
                for use_500ms in should_use_500ms:
                    for use_calibrated in should_use_calibrated:
                        data_transfer = []
                        image_load = []
                        detection = []
                        total = []
                        scheduler_decision = []
                        queue = []
                        group_labels = []
                        new_data = False
                        cloudlet = ""
                        if use_cloudlet:
                            cloudlet = "_cloudlet"
                        cloud = ""
                        if use_cloud:
                            cloud = "_cloud"
                        checking_5s = ""
                        if use_5s:
                            checking_5s = "_5s"
                        checking_500ms = ""
                        if use_500ms:# and schedulers_translate[scheduler] == "EstimatedTimeScheduler":
                            checking_500ms = "_500ms_WorkerUpdate"
                        calibrated = ""
                        if use_calibrated:
                            calibrated = "_CALIBRATED"
                        for asset_type in asset_types:
                            if os.path.isfile("csv/scheduler_boxplot_{}{}{}{}{}{}_{}.csv".format(schedulers_translate[scheduler], cloudlet, cloud, checking_5s, checking_500ms, calibrated, asset_type)):
                                print("reading csv/scheduler_boxplot_{}{}{}{}{}{}_{}.csv".format(schedulers_translate[scheduler], cloudlet, cloud, checking_5s, checking_500ms, calibrated, asset_type))
                                new_data = True
                                data = pd.read_csv("csv/scheduler_boxplot_{}{}{}{}{}{}_{}.csv".format(schedulers_translate[scheduler], cloudlet, cloud, checking_5s, checking_500ms, calibrated, asset_type))
                                data_transfer += data["DATA_TRANSFER"].values.tolist()
                                image_load += data["IMAGE_LOAD"].values.tolist()
                                detection += data["DETECTION"].values.tolist()
                                total += data["TOTAL_DURATION"].values.tolist()
                                scheduler_decision += data["SCHEDULER_DECISION"].values.tolist()
                                queue += data["QUEUE"].values.tolist()
                                #labels = [asset_type]*len(data["DATA_TRANSFER"].values.tolist())
                                group_labels += [asset_type]*len(data["DATA_TRANSFER"].values.tolist())
                        if new_data:
                            if use_cloudlet:
                                cloudlet = " cloudlet"
                            if use_cloud:
                                cloudlet = " cloud"
                            if use_5s:
                                checking_5s = " 5s"
                            if use_calibrated:
                                calibrated = " CALIBRATED"
                            fig_0.add_trace(go.Box(y=data_transfer, x=group_labels, name=scheduler+cloudlet+cloud+checking_5s+checking_500ms+calibrated))
                            fig_1.add_trace(go.Box(y=image_load, x=group_labels, name=scheduler+cloudlet+cloud+checking_5s+checking_500ms+calibrated))
                            fig_2.add_trace(go.Box(y=detection, x=group_labels, name=scheduler+cloudlet+cloud+checking_5s+checking_500ms+calibrated))
                            fig_3.add_trace(go.Box(y=total, x=group_labels, name=scheduler+cloudlet+cloud+checking_5s+checking_500ms+calibrated))
                            fig_4.add_trace(go.Box(y=scheduler_decision, x=group_labels, name=scheduler+cloudlet+cloud+checking_5s+checking_500ms+calibrated))
                            fig_5.add_trace(go.Box(y=queue, x=group_labels, name=scheduler+cloudlet+cloud+checking_5s+checking_500ms+calibrated))

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

fig_3.update_layout(
    yaxis_title='Total Time',
    boxmode='group' # group together boxes of the different traces for each value of x
)

fig_4.update_layout(
    yaxis_title='Scheduler Decision',
    boxmode='group' # group together boxes of the different traces for each value of x
)

fig_5.update_layout(
    yaxis_title='Queue Time',
    boxmode='group' # group together boxes of the different traces for each value of x
)

pio.write_html(fig_0, "html/scheduler/data_transfer_all_grouped_boxplot.html")
pio.write_html(fig_1, "html/scheduler/image_load_all_grouped_boxplot.html")
pio.write_html(fig_2, "html/scheduler/detection_all_grouped_boxplot.html")
pio.write_html(fig_3, "html/scheduler/total_time_all_grouped_boxplot.html")
pio.write_html(fig_4, "html/scheduler/scheduler_decision_all_grouped_boxplot.html")
pio.write_html(fig_5, "html/scheduler/queue_time_all_grouped_boxplot.html")
