import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import sys
from IPython.display import Image

#pdf_name = "all_comparison_6_remote"
#pdf_name = "comparison_nd_ic_ec_median"#_median"
pdf_name = "ld_ec_ic_4_8_combi_with_old"
asset_types = ["SD","HD","UHD"]
asset_colors = {'SD': '#424242', 'HD': '#BDBDBD', 'UHD': '#757575'}
schedulers_map = {
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.8_early': "local cloud 0.8 early",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.5_early': "local cloud 0.5 early",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.35_early': "local cloud 0.35 early",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.25_early': "local cloud 0.25 early",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.1_early': "local cloud 0.1 early",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_early': "local cloud early",
#
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.8': "local cloud 0.8 new",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.5': "local cloud 0.5 new",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.35': "local cloud 0.35 new",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.25': "local cloud 0.25 new",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s_0.1': "local cloud 0.1 new",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s': "local cloud new",



# comparison_nd_ic_ec
# 'Saturation_Random_Local_Remote_Cloud_Cloudlet_{}_8d_1p_8x12_5s_paper': "Random",
# 'Saturation_ComputationEstimate_Local_Remote_Cloud_Cloudlet_{}_8d_1p_8x12_5s_paper': "Computation Estimate",
# 'Saturation_EstimatedTime_Local_Remote_Cloud_Cloudlet_{}_8d_1p_8x12_5s': "Estimated Time",


# ld_ec_ic_4_8_1p_combi
# 'Saturation_EstimatedTime_Local_Remote_Cloud_Cloudlet_{}_8d_1p_8x12_5s': "local remote cloud cloudlet 1p 8d 8x12",
# 'Saturation_EstimatedTime_Local_Remote_Cloud_Cloudlet_{}_4d_1p_8x12_5s': "local remote cloud cloudlet 1p 4d 8x12",
# 'Saturation_EstimatedTime_Local_Cloud_Cloudlet_{}_8d_1p_8x12_5s': "local cloud cloudlet",
# #'Saturation_EstimatedTime_Cloud_Cloudlet_{}_8_5s': "cloud cloudlet",
# #'Saturation_EstimatedTime_Cloud_Cloudlet_{}_8d_1p_8x12_5s_paper': "cloud cloudlet",
# 'Saturation_EstimatedTime_Cloud_Cloudlet_{}_8d_1p_8x12_5s_paper_retry_1': "cloud cloudlet",
#
# 'Saturation_EstimatedTime_Local_Remote_Cloud_{}_8d_1p_8x12_5s': "local remote cloud 1p 8d 8x12",
# 'Saturation_EstimatedTime_Local_Remote_Cloud_{}_4d_1p_8x12_5s': "local remote cloud 1p 4d 8x12",
# 'Saturation_EstimatedTime_Local_Cloud_{}_8d_1p_8x12_5s': "local cloud",
# #'New_Saturation_Cloud_{}_8_5s': "cloud",
# 'SingleDevice_Cloud_{}_8d_1p_8x12_5s': "cloud",
#
#
# 'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_8d_1p_8x12_5s': "local remote cloudlet 1p 8d 8x12",
# 'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_4d_1p_8x12_5s': "local remote cloudlet 1p 4d 8x12",
# 'Saturation_EstimatedTime_Local_Cloudlet_{}_8d_1p_8x12_5s': "local cloudlet",
# #'New_Saturation_Cloudlet_{}_8_5s': "cloudlet",
# 'SingleDevice_Cloudlet_{}_8d_1p_8x12_5s': "cloudlet",
#
# 'Saturation_EstimatedTime_Local_Remote_{}_8d_1p_8x12_5s_paper': 'remote 1p 8d 8x12',
# 'Saturation_EstimatedTime_Local_Remote_{}_4d_1p_8x12_5s_paper_retry': 'remote 1p 4d 8x12',

#Extra results

#'Saturation_EstimatedTime_Local_Cloud_UHD_8d_1p_8x12_5s_0.35_new': "local cloud new",
#'SingleDevice_Cloud_{}_8d_1p_8x12_5s': "cloud new",
#'SingleDevice_Cloudlet_{}_8d_1p_8x12_5s': "cloudlet new",

# ld_ec_ic_4_8_combi
#'Saturation_EstimatedTime_Local_Cloud_Cloudlet_{}_8_5s': "local cloud cloudlet 8 old",
'Saturation_EstimatedTime_Local_Cloud_Cloudlet_{}_8_5s_paper': "local cloud cloudlet 8",
'Saturation_EstimatedTime_Cloud_Cloudlet_{}_8_5s': "cloud cloudlet 8",
#'Saturation_EstimatedTime_Local_Cloud_Cloudlet_{}_4_5s': "local cloud cloudlet 4 old",
'Saturation_EstimatedTime_Local_Cloud_Cloudlet_{}_4_5s_paper': "local cloud cloudlet 4",
'Saturation_EstimatedTime_Cloud_Cloudlet_{}_4_5s_paper': "cloud cloudlet 4",

'Saturation_EstimatedTime_Local_Cloud_{}_8_5s': "local cloud 8",
'New_Saturation_Cloud_{}_8_5s': "cloud 8",
'Saturation_EstimatedTime_Local_Cloud_{}_4_5s': "local cloud 4",
'New_Saturation_Cloud_{}_4_5s': "cloud 4",

'Saturation_EstimatedTime_Local_Cloudlet_{}_8_5s': "local cloudlet 8",
'New_Saturation_Cloudlet_{}_8_5s': "cloudlet 8",
'Saturation_EstimatedTime_Local_Cloudlet_{}_4_5s': "local cloudlet 4",
'New_Saturation_Cloudlet_{}_4_5s': "cloudlet 4",

'New_Saturation_Local_{}_8_5s': "local",





#'Saturation_EstimatedTime_Local_Cloud_{}_6_5s': "local cloud 6",
#'New_Saturation_Cloud_{}_6_5s': "cloud 6",
#'New_Saturation_Cloudlet_{}_6_5s': "cloudlet 6",




#'Saturation_EstimatedTime_Local_Remote_{}_4_5s': "local remote 4",
#'Saturation_EstimatedTime_Local_Remote_{}_6_5s': "local remote 6",
#'Saturation_EstimatedTime_Local_Remote_{}_8_5s': "local remote 8",
#'Saturation_EstimatedTime_Local_Remote_{}_4d_1p_4x12_5s': "local remote 1p 4d 4x12",
#'Saturation_EstimatedTime_Local_Remote_{}_8d_1p_4x12_5s': "local remote 1p 8d 4x12",
#'Saturation_EstimatedTime_Local_Remote_{}_6d_1p_6x12_5s': "local remote 1p 6d 6x12",
#'Saturation_EstimatedTime_Local_Remote_{}_8d_1p_6x12_5s': "local remote 1p 8d 6x12",

#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_4_5s': "local remote cloud 4",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_6_5s': "local remote cloud 6",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_8_5s': "local remote cloud 8",
#'Saturation_EstimatedTime_Local_Cloud_{}_4d_1p_4x12_5s': "local cloud 1p 4d 4x12",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_4d_1p_4x12_5s': "local remote cloud 1p 4d 4x12",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_8d_1p_4x12_5s': "local remote cloud 1p 8d 4x12",
#'Saturation_EstimatedTime_Local_Cloud_{}_6d_1p_6x12_5s': "local cloud 1p 6d 6x12",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_6d_1p_6x12_5s': "local remote cloud 1p 6d 6x12",
#'Saturation_EstimatedTime_Local_Remote_Cloud_{}_8d_1p_6x12_5s': "local remote cloud 1p 8d 6x12",
#'Saturation_EstimatedTime_Local_Remote_Cloud_0.8_{}_6d_1p_6x12_5s': "local remote cloud 1p 6d 6x12 0.8",
#'Saturation_EstimatedTime_Local_Remote_Cloud_0.8_{}_8d_1p_6x12_5s': "local remote cloud 1p 8d 6x12 0.8",
#'Saturation_EstimatedTime_Local_Remote_Cloud_0.5_{}_6d_1p_6x12_5s': "local remote cloud 1p 6d 6x12 0.5",
#'Saturation_EstimatedTime_Local_Remote_Cloud_0.5_{}_8d_1p_6x12_5s': "local remote cloud 1p 8d 6x12 0.5",

#'Saturation_EstimatedTime_Local_Cloudlet_{}_6_5s': "local cloudlet 6",

#'Saturation_EstimatedTime_Local_Cloudlet_{}_4d_1p_4x12_5s': "local cloudlet 1p 4d 4x12",
#'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_4d_1p_4x12_5s': "local remote cloudlet 1p 4d 4x12",
#'Saturation_EstimatedTime_Local_Remote_Cloudlet_{}_8d_1p_4x12_5s': "local remote cloudlet 1p 8d 4x12",
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
'local': 'LD',
'Estimated Time': 'C+N',
'Computation Estimate': 'C',
'Random': 'R'
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
        label = label.strip()
        label = label.replace("1p 4d 8x12", "4")
        label = label.replace("1p 8d 8x12", "8")
        label = label.replace(" ", "/")
        if label.rfind("/") != -1 and len(label.split("/")[-1]) == 1:
            label = label[:label.rfind("/")] + " " + label[label.rfind("/")+1:]
        label = label.replace("IC/EC", "EC/IC")
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
        fig_0.add_trace(go.Box(x=[x / 1000.0 for x in data_transfer], y=data_transfer_group_labels, name=asset_type, marker_size=2, line_width=1, marker_color=asset_colors[asset_type]))
        fig_1.add_trace(go.Box(x=[x / 1000.0 for x in detection], y=detection_group_labels, name=asset_type, marker_size=2, line_width=1, marker_color=asset_colors[asset_type]))
        fig_2.add_trace(go.Box(x=[x / 1000.0 for x in total], y=total_group_labels, name=asset_type, marker_size=2, line_width=0.7, marker_color=asset_colors[asset_type],fillcolor=asset_colors[asset_type], line_color='#000000'))#, fillcolor="green", marker_color='rgb(8,81,156)', line_color='rgb(8,81,156)'))


#exit()

fig_0.update_layout(
    xaxis_title='Communcation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear",
    legend_orientation="h",
    font=dict(size=10) #default 12
)

fig_0.update_traces(orientation="h")

pio.write_image(fig_0, "data_transfer_linear_" + pdf_name + ".pdf")

fig_1.update_layout(
    xaxis_title='Computation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear",
    legend_orientation="h",
    font=dict(size=10) #default 12
)

fig_1.update_traces(orientation="h")

pio.write_image(fig_1, "computation_linear_" + pdf_name + ".pdf")

fig_2.update_layout(
    #xaxis_title='Total Time (seconds)',
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear",
    showlegend=True,
    legend_orientation="h",
    font=dict(size=10) #default 12
)

fig_2.update_traces(orientation="h")
pio.write_image(fig_2, "total_linear_" + pdf_name + ".pdf")

fig_0.update_layout(
    xaxis_title='Communcation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log",
    legend_orientation="h",
    font=dict(size=10) #default 12
)

fig_0.update_traces(orientation="h")

pio.write_image(fig_0, "data_transfer_logscale_" + pdf_name + ".pdf")

fig_1.update_layout(
    xaxis_title='Computation Time (seconds)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log",
    legend_orientation="h",
    font=dict(size=10) #default 12
)

fig_1.update_traces(orientation="h")

pio.write_image(fig_1, "computation_logscale_" + pdf_name + ".pdf")

fig_2.update_layout(
    #xaxis_title='Total Time (seconds)',
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(zeroline=False, gridcolor='lightgray',tick0 = 0, dtick = 1,tickvals = [1, 2, 5, 10, 20, 50, 100, 200, 300], ticktext=['1', '2', '5', '10', '20', '50', '100', '200','300']),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log",
    legend_orientation="h",
    font=dict(size=10) #default 12
)

fig_2.update_traces(orientation="h")
pio.write_image(fig_2, "total_logscale_" + pdf_name + ".pdf")
