import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import sys
from IPython.display import Image

#pdf_name = "all_comparison_6_remote"
pdf_name = "1p_4d_5s"
asset_types = ["SD","HD","UHD"]
schedulers_map = {
#'New_Saturation_Local_{}_8_5s': "local",
#'Saturation_Cloud_{}_4_5s': "cloud 4",
#'New_Saturation_Cloudlet_{}_4_5s': "cloudlet 4",
#'New_Saturation_Cloud_{}_6_5s': "cloud 6",
#'New_Saturation_Cloudlet_{}_6_5s': "cloudlet 6",
#'New_Saturation_Cloud_{}_8_5s': "cloud 8",
#'New_Saturation_Cloudlet_{}_8_5s': "cloudlet 8",
#'Saturation_EstimatedTime_Local_Remote_{}_4_5s': "local remote 4",
#'Saturation_EstimatedTime_Local_Remote_{}_6_5s': "local remote 6",
#'Saturation_EstimatedTime_Local_Remote_{}_8_5s': "local remote 8",
'Saturation_EstimatedTime_Local_Remote_{}_4d_1p_4x12_5s': "local remote 1p 4d 4x12",
'Saturation_EstimatedTime_Local_Remote_{}_8d_1p_4x12_5s': "local remote 1p 8d 4x12",
#'Saturation_EstimatedTime_Local_Remote_{}_6d_1p_6x12_5s': "local remote 1p 6d 6x12",
#'Saturation_EstimatedTime_Local_Remote_{}_8d_1p_6x12_5s': "local remote 1p 8d 6x12",
#'Saturation_EstimatedTime_Local_Cloud_{}_4_5s': "local cloud 4",
#'Saturation_EstimatedTime_Local_Cloud_{}_6_5s': "local cloud 6",
#'Saturation_EstimatedTime_Local_Cloud_{}_8_5s': "local cloud 8",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_4_5s': "local remote cloud 4",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_6_5s': "local remote cloud 6",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_8_5s': "local remote cloud 8",
'Saturation_EstimatedTime_Local_Cloud_{}_4d_1p_4x12_5s': "local cloud 1p 4d 4x12",
'Saturation_EstimatedTime_Local_Remote_Cloud_{}_4d_1p_4x12_5s': "local remote cloud 1p 4d 4x12",
'Saturation_EstimatedTime_Local_Remote_Cloud_{}_8d_1p_4x12_5s': "local remote cloud 1p 8d 4x12",
#'Saturation_EstimatedTime_Local_Cloud_{}_6d_1p_6x12_5s': "local cloud 1p 6d 6x12",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_6d_1p_6x12_5s': "local remote cloud 1p 6d 6x12",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_8d_1p_6x12_5s': "local remote cloud 1p 8d 6x12",
#'Saturation_EstimatedTime_Local_Remote_Cloud_0.8_{}_6d_1p_6x12_5s': "local remote cloud 1p 6d 6x12 0.8",
#'Saturation_EstimatedTime_Local_Remote_Cloud_0.8_{}_8d_1p_6x12_5s': "local remote cloud 1p 8d 6x12 0.8",
#'Saturation_EstimatedTime_Local_Remote_Cloud_0.5_{}_6d_1p_6x12_5s': "local remote cloud 1p 6d 6x12 0.5",
#'Saturation_EstimatedTime_Local_Remote_Cloud_0.5_{}_8d_1p_6x12_5s': "local remote cloud 1p 8d 6x12 0.5",
#'Saturation_EstimatedTime_Local_Cloudlet_{}_4_5s': "local cloudlet 4",
#'Saturation_EstimatedTime_Local_Cloudlet_{}_6_5s': "local cloudlet 6",
#'Saturation_EstimatedTime_Local_Cloudlet_{}_8_5s': "local cloudlet 8",
'Saturation_EstimatedTime_Local_Cloudlet_{}_4d_1p_4x12_5s': "local cloudlet 1p 4d 4x12",
'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_4d_1p_4x12_5s': "local remote cloudlet 1p 4d 4x12",
'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_8d_1p_4x12_5s': "local remote cloudlet 1p 8d 4x12",
#'Saturation_EstimatedTime_Local_Cloudlet_{}_6d_1p_6x12_5s': "local cloudlet 1p 6d 6x12",
#'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_6d_1p_6x12_5s': "local remote cloudlet 1p 6d 6x12",
#'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_8d_1p_6x12_5s': "local remote cloudlet 1p 8d 6x12",

#'Saturation_EstimatedTime_Local_Cloud_{}_4d_1p_4x12_5s': "local cloud 1p 4d 4x12",
#'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_4_5s': "local remote cloudlet 4",
#'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_6_5s': "local remote cloudlet 6",
#'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_8_5s': "local remote cloudlet 8",
}

aliases = {
'cloudlet': 'EC',
'cloud': 'IC',
'remote': 'ND',
'local': 'LD'
}



base_dir = sys.argv[1]
processed_experiments = []

if True:
    for asset_type in asset_types:
        for key in list(schedulers_map.keys()):#[1:]:
            if not os.path.isfile("csv/saturation_boxplot_{}_{}.csv".format(schedulers_map[key].replace(" ", "_"), asset_type)):
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
        #print("csv/saturation_boxplot_{}_{}.csv".format(device_type.replace(" ", "_"), asset_type))
        label = device_type
        for alias_key in aliases:
            label = label.replace(alias_key, aliases[alias_key])
        if label.find("LD") != -1 and label.find("ND") != -1:
            label = label.replace("LD", "")
        #for to_remove in [" 4x12", " 6x12", " 6", " 4", " 8"]:
        #    label = label.replace(to_remove, "")
        if os.path.isfile("csv/saturation_boxplot_{}_{}.csv".format(device_type.replace(" ", "_"), asset_type)):
            print("reading csv/saturation_boxplot_{}_{}.csv".format(device_type.replace(" ", "_"), asset_type))
            new_data = True
            data = pd.read_csv("csv/saturation_boxplot_{}_{}.csv".format(device_type.replace(" ", "_"), asset_type))
            data_transfer += data["DATA_TRANSFER"].values.tolist()
            data_transfer_group_labels += ["{}".format(label)]*len(data["DATA_TRANSFER"].values.tolist())
            detection += data["DETECTION"].values.tolist()
            detection_group_labels += ["{}".format(label)]*len(data["DETECTION"].values.tolist())
            total += data["TOTAL_DURATION"].values.tolist()
            total_group_labels += ["{}".format(label)]*len(data["TOTAL_DURATION"].values.tolist())
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

pio.write_image(fig_0, "data_transfer_logscale_" + pdf_name + ".pdf")

fig_1.update_layout(
    xaxis_title='Computation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log"
)

fig_1.update_traces(orientation="h")

pio.write_image(fig_1, "computation_logscale_" + pdf_name + ".pdf")

fig_2.update_layout(
    xaxis_title='Total Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log"
)

fig_2.update_traces(orientation="h")
pio.write_image(fig_2, "total_logscale_" + pdf_name + ".pdf")

fig_0.update_layout(
    xaxis_title='Communcation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear"
)

fig_0.update_traces(orientation="h")

pio.write_image(fig_0, "data_transfer_linear_" + pdf_name + ".pdf")

fig_1.update_layout(
    xaxis_title='Computation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear"
)

fig_1.update_traces(orientation="h")

pio.write_image(fig_1, "computation_linear_" + pdf_name + ".pdf")

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
pio.write_image(fig_2, "total_linear_" + pdf_name + ".pdf")
