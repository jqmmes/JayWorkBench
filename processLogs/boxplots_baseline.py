import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import sys
from IPython.display import Image


basename = "New_BaseLine"
asset_types = ["SD", "HD", "UHD"]
device_types = ["Cloudlet", "Local", "Cloud"]
base_dir = sys.argv[1]
processed_experiments = []

if True:
    for asset_type in asset_types:
        for device_type in device_types:
            print("PROCESSING\t{}\t{}\tINTO\tcsv/baseline_boxplot_{}_{}.csv".format(device_type, asset_type, device_type, asset_type), end="\n")
            print("python3 printJobDetails.py {}/{}_{}_{}/0/* > csv/baseline_boxplot_{}_{}.csv 2> /dev/null".format(base_dir.replace(" ", "\ "), basename, device_type, asset_type, device_type, asset_type))
            os.system("python3 printJobDetails.py {}/{}_{}_{}/0/* > csv/baseline_boxplot_{}_{}.csv 2> /dev/null".format(base_dir.replace(" ", "\ "), basename, device_type, asset_type, device_type, asset_type))


fig_0 = go.Figure()
fig_1 = go.Figure()
fig_2 = go.Figure()
fig_3 = go.Figure()
for asset_type in asset_types:
    new_data = False
    data_transfer = []
    detection = []
    total = []
    data_transfer_group_labels = []
    detection_group_labels = []
    single_graph = []
    single_graph_group_labels = []
    single_graph_data_transfer = []
    single_graph_data_transfer_group_labels = []
    total_group_labels = []
    for device_type in ["Cloud", "Cloudlet", "Local"]:
        if os.path.isfile("csv/baseline_boxplot_{}_{}.csv".format(device_type, asset_type)):
            print("reading csv/baseline_boxplot_{}_{}.csv".format(device_type, asset_type))
            new_data = True
            data = pd.read_csv("csv/baseline_boxplot_{}_{}.csv".format(device_type, asset_type))
            if device_type != "Local":
                data_transfer += data["DATA_TRANSFER"].values.tolist()
                data_transfer_group_labels += ["{}".format(device_type)]*len(data["DATA_TRANSFER"].values.tolist())
                single_graph_data_transfer += data["DATA_TRANSFER"].values.tolist()
                single_graph_data_transfer_group_labels += ["{} data transfer".format(device_type)]*len(data["DATA_TRANSFER"].values.tolist())
            detection += data["DETECTION"].values.tolist()
            detection_group_labels += ["{}".format(device_type)]*len(data["DETECTION"].values.tolist())
            total += data["TOTAL_DURATION"].values.tolist()
            total_group_labels += ["{}".format(device_type)]*len(data["TOTAL_DURATION"].values.tolist())
            single_graph += data["TOTAL_DURATION"].values.tolist()
            single_graph_group_labels += ["{}".format(device_type)]*len(data["TOTAL_DURATION"].values.tolist())
    if new_data:
        fig_0.add_trace(go.Box(x=[x / 1000.0 for x in data_transfer], y=data_transfer_group_labels, name=asset_type, marker_size=2, line_width=1))
        fig_1.add_trace(go.Box(x=[x / 1000.0 for x in detection], y=detection_group_labels, name=asset_type, marker_size=2, line_width=1))
        fig_2.add_trace(go.Box(x=[x / 1000.0 for x in total], y=total_group_labels, name=asset_type, marker_size=2, line_width=1))#, fillcolor="green", marker_color='rgb(8,81,156)', line_color='rgb(8,81,156)'))
        fig_3.add_trace(go.Box(x=[x / 1000.0 for x in single_graph_data_transfer+single_graph], y=single_graph_data_transfer_group_labels+single_graph_group_labels, name=asset_type, marker_size=2, line_width=1))
fig_0.update_layout(
    xaxis_title='Baseline Data Transfer',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log"
)

fig_0.update_traces(orientation="h")

pio.write_image(fig_0, "baseline_data_transfer_logscale.pdf")

fig_1.update_layout(
    xaxis_title='Baseline Computation',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log"
)

fig_1.update_traces(orientation="h")

pio.write_image(fig_1, "baseline_computation_logscale.pdf")

fig_2.update_layout(
    xaxis_title='Baseline Total',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log"
)

fig_2.update_traces(orientation="h")
pio.write_image(fig_2, "baseline_total_logscale.pdf")

fig_0.update_layout(
    xaxis_title='Baseline Data Transfer',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear"
)

fig_0.update_traces(orientation="h")

pio.write_image(fig_0, "baseline_data_transfer_linear.pdf")

fig_1.update_layout(
    xaxis_title='Baseline Computation',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear"
)

fig_1.update_traces(orientation="h")

pio.write_image(fig_1, "baseline_computation_linear.pdf")

fig_2.update_layout(
    xaxis_title='Baseline Total',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear",
    showlegend=True
)

fig_2.update_traces(orientation="h")
pio.write_image(fig_2, "baseline_total_linear.pdf")

fig_3.update_layout(
    xaxis_title='Baseline Total and Transfer Time',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="log"
)

fig_3.update_traces(orientation="h")
pio.write_image(fig_3, "baseline_single_logscale.pdf")

fig_3.update_layout(
    xaxis_title='Baseline Total and Transfer Time',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    boxmode='group',
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis_type="linear",
    showlegend=True
)

fig_3.update_traces(orientation="h")
pio.write_image(fig_3, "baseline_single_linear.pdf")
