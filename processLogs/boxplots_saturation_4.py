import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import sys
from IPython.display import Image



#asset_types = ["SD", "HD", "UHD"]
asset_types = ["SD","HD","UHD"]
#schedulers_map = {'Speedup_Local_{}_1': "local", 'Saturation_Cloud_{}_8_5s': "cloud", 'Saturation_Cloudlet_{}_8_5s': "cloudlet", 'Saturation_EstimatedTime_Local_Cloud_{}_8_5s': "local cloud", 'Saturation_EstimatedTime_Local_Remote_Cloud_{}_8_5s': "local remote cloud", 'Saturation_EstimatedTime_Local_Remote_{}_8_5s': "local remote", 'Saturation_EstimatedTime_Local_Cloudlet_{}_8_5s': "local cloudlet", 'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_8_5s': "local remote cloudlet"}
schedulers_map = {'New_Saturation_Cloudlet_{}_1_5s': "cloudlet 1",'New_Saturation_Cloudlet_{}_2_5s': "cloudlet 2", 'New_Saturation_Cloudlet_{}_4_5s': "cloudlet 4", 'New_Saturation_Cloudlet_{}_6_5s': "cloudlet 6", 'New_Saturation_Cloudlet_{}_8_5s': "cloudlet 8", 'New_Saturation_Local_{}_8_5s': "local"}

base_dir = sys.argv[1]
processed_experiments = []

if True:
    for asset_type in asset_types:
        for key in list(schedulers_map.keys())[:-1]:
            print("python3 printJobDetails.py {}/{}/0/* > csv/saturation_boxplot_{}_{}.csv 2> /dev/null".format(base_dir.replace(" ", "\ "), key.format(asset_type), schedulers_map[key].replace(" ", "_"), asset_type))
            os.system("python3 printJobDetails.py {}/{}/0/* > csv/saturation_boxplot_{}_{}.csv 2> /dev/null".format(base_dir.replace(" ", "\ "), key.format(asset_type), schedulers_map[key].replace(" ", "_"), asset_type))

fig_0 = go.Figure()
fig_1 = go.Figure()
fig_2 = go.Figure()
for asset_type in asset_types:
    new_data = False
    data_transfer = []
    detection = []
    total = []
    data_transfer_group_labels = []
    detection_group_labels = []
    total_group_labels = []
    #for device_type in ["local remote cloud", "local remote cloudlet", "local cloud", "local cloudlet", "local remote", "cloud", "cloudlet", "local"]:
    for device_type in schedulers_map.values():
        if os.path.isfile("csv/saturation_boxplot_{}_{}.csv".format(device_type.replace(" ", "_"), asset_type)):
            print("reading csv/saturation_boxplot_{}_{}.csv".format(device_type.replace(" ", "_"), asset_type))
            new_data = True
            data = pd.read_csv("csv/saturation_boxplot_{}_{}.csv".format(device_type.replace(" ", "_"), asset_type))
            data_transfer += data["DATA_TRANSFER"].values.tolist()
            data_transfer_group_labels += ["{}".format(device_type)]*len(data["DATA_TRANSFER"].values.tolist())
            detection += data["DETECTION"].values.tolist()
            detection_group_labels += ["{}".format(device_type)]*len(data["DETECTION"].values.tolist())
            total += data["TOTAL_DURATION"].values.tolist()
            total_group_labels += ["{}".format(device_type)]*len(data["TOTAL_DURATION"].values.tolist())
    if new_data:
        fig_0.add_trace(go.Box(x=[x / 1000.0 for x in data_transfer], y=data_transfer_group_labels, name=asset_type, marker_size=2, line_width=1))
        fig_1.add_trace(go.Box(x=[x / 1000.0 for x in detection], y=detection_group_labels, name=asset_type, marker_size=2, line_width=1))
        fig_2.add_trace(go.Box(x=[x / 1000.0 for x in total], y=total_group_labels, name=asset_type, marker_size=2, line_width=1))#, fillcolor="green", marker_color='rgb(8,81,156)', line_color='rgb(8,81,156)'))

fig_0.update_layout(
    xaxis_title='Communcation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log"
)

fig_0.update_traces(orientation="h")

pio.write_image(fig_0, "saturation_data_transfer_logscale_cloudlet_comparison.pdf")

fig_1.update_layout(
    xaxis_title='Computation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log"
)

fig_1.update_traces(orientation="h")

pio.write_image(fig_1, "saturation_computation_logscale_cloudlet_comparison.pdf")

fig_2.update_layout(
    xaxis_title='Total Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log"
)

fig_2.update_traces(orientation="h")
pio.write_image(fig_2, "saturation_total_logscale_cloudlet_comparison.pdf")

fig_0.update_layout(
    xaxis_title='Communcation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear"
)

fig_0.update_traces(orientation="h")

pio.write_image(fig_0, "saturation_data_transfer_linear_cloudlet_comparison.pdf")

fig_1.update_layout(
    xaxis_title='Computation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear"
)

fig_1.update_traces(orientation="h")

pio.write_image(fig_1, "saturation_computation_linear_cloudlet_comparison.pdf")

fig_2.update_layout(
    xaxis_title='Total Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear",
    showlegend=True
)

fig_2.update_traces(orientation="h")
pio.write_image(fig_2, "saturation_total_linear_cloudlet_comparison.pdf")
