import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import sys
from IPython.display import Image


cloudlet = "joaquim-MS-7996"
cloud = "compute-europe-west"

quality = ['SD','HD','UHD']
base_name = 'csv/saturation_boxplot_'
end = "_{}.csv"

sources = {
"local_cloud_cloudlet_8": [[0,0,0],[0,0,0],[0,0,0]],
"cloud_cloudlet_8": [[0,0,0],[0,0,0],[0,0,0]],
"local_cloud_cloudlet_4": [[0,0,0],[0,0,0],[0,0,0]],
"cloud_cloudlet_4": [[0,0,0],[0,0,0],[0,0,0]],
"local_cloud_8": [[0,0,0],[0,0,0],[0,0,0]],
#"cloud_8": [[0,0,0],[0,0,0],[0,0,0]],
"local_cloud_4": [[0,0,0],[0,0,0],[0,0,0]],
#"cloud_4": [[0,0,0],[0,0,0],[0,0,0]],
"local_cloudlet_8": [[0,0,0],[0,0,0],[0,0,0]],
#"cloudlet_8": [[0,0,0],[0,0,0],[0,0,0]],
"local_cloudlet_4": [[0,0,0],[0,0,0],[0,0,0]],
#"cloudlet_4": [[0,0,0],[0,0,0],[0,0,0]],
#"local": [[0,0,0],[0,0,0],[0,0,0]]
}

translate = {
"local_cloud_cloudlet_8": "LD/EC/IC 8",
"cloud_cloudlet_8": "EC/IC 8",
"local_cloud_cloudlet_4": "LD/EC/IC 4",
"cloud_cloudlet_4": "EC/IC 4",
"local_cloud_8": "LD/IC 8",
"cloud_8": "IC 8",
"local_cloud_4": "LD/IC 4",
"cloud_4": "IC 4",
"local_cloudlet_8": "LD/EC 8",
"cloudlet_8": "EC 8",
"local_cloudlet_4": "LD/EC 4",
"cloudlet_4": "EC 4",
"local": "LD"
}


# sources = {
# "local_remote_cloud_cloudlet_1p_8d_8x12": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "local_remote_cloud_cloudlet_1p_4d_8x12": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "local_cloud_cloudlet": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "cloud_cloudlet": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "local_remote_cloud_1p_8d_8x12": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "local_remote_cloud_1p_4d_8x12": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "local_cloud": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "cloud": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "local_remote_cloudlet_1p_8d_8x12": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "local_remote_cloudlet_1p_4d_8x12": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "local_cloudlet": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "cloudlet": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "remote_1p_8d_8x12": [[0,0,0,0],[0,0,0,0],[0,0,0,0]],
# "remote_1p_4d_8x12": [[0,0,0,0],[0,0,0,0],[0,0,0,0]]
# }
#
# translate = {
# "local_remote_cloud_cloudlet_1p_8d_8x12": "ND/EC/IC 8",
# "local_remote_cloud_cloudlet_1p_4d_8x12": "ND/EC/IC 4",
# "local_cloud_cloudlet": "LD/EC/IC",
# "cloud_cloudlet": "EC/IC",
# "local_remote_cloud_1p_8d_8x12": "ND/IC 8",
# "local_remote_cloud_1p_4d_8x12": "ND/IC 4",
# "local_cloud": "LD/IC",
# "cloud": "IC",
# "local_remote_cloudlet_1p_8d_8x12": "ND/EC 8",
# "local_remote_cloudlet_1p_4d_8x12": "ND/EC 4",
# "local_cloudlet": "LD/EC",
# "cloudlet": "EC",
# "remote_1p_8d_8x12": "ND 8",
# "remote_1p_4d_8x12": "ND 4"
# }

fig = go.Figure()

for source_file in sources.keys():
  for asset_quality in quality:
    data = open(base_name+source_file+end.format(asset_quality)).read().strip().split("\n")[1:]
    for entry in data:
        splitted_entry = entry.split(",")
        if len(splitted_entry) > 2:
          if splitted_entry[0] == splitted_entry[1]:
            sources[source_file][quality.index(asset_quality)][0] = sources[source_file][quality.index(asset_quality)][0] + 1
          elif splitted_entry[1] == cloud:
            #sources[source_file][quality.index(asset_quality)][3] = sources[source_file][quality.index(asset_quality)][3] + 1
            sources[source_file][quality.index(asset_quality)][2] = sources[source_file][quality.index(asset_quality)][2] + 1
          elif splitted_entry[1] == cloudlet:
            #sources[source_file][quality.index(asset_quality)][2] = sources[source_file][quality.index(asset_quality)][2] + 1
            sources[source_file][quality.index(asset_quality)][1] = sources[source_file][quality.index(asset_quality)][1] + 1
          else:
            sources[source_file][quality.index(asset_quality)][1] = sources[source_file][quality.index(asset_quality)][1] + 1
    total = sum(sources[source_file][quality.index(asset_quality)])
    #for x in range(4):
    for x in range(3):
      sources[source_file][quality.index(asset_quality)][x] = float(sources[source_file][quality.index(asset_quality)][x])/total*100
    #while sum(sources[source_file][quality.index(asset_quality)]) > 100:
        #print(sources[source_file][quality.index(asset_quality)])
        #sources[source_file][quality.index(asset_quality)][[sources[source_file][quality.index(asset_quality)]].index(max(sources[source_file][quality.index(asset_quality)]))] -= 1
        #.index(max(sources[source_file][quality.index(asset_quality))] -= 1


#devices = ["LD", "ND", "EC", "IC"]
devices = ["LD", "EC", "IC"]
asset_colors = {'LD': '#424242', 'ND': '#DDDDDD', 'EC': '#757575', 'IC': '#BDBDBD'}
devices.reverse()
quality.reverse()

for dev in devices:
    x_data = []
    y_label = []
    for res in sources.keys():
        for qual in quality:
            x_data.append(sources[res][abs(quality.index(qual)-2)][abs(devices.index(dev)-2)]) #abs(devices.index(dev)-3)
            y_label.append(translate[res]+" "+qual)
    fig.add_trace(go.Bar(x=x_data, y=y_label, name=dev, orientation="h", marker_color=asset_colors[dev], width=[0.8]*len(x_data)))


fig.update_layout(
    #xaxis_title='% of tasks per device type',
    barmode='stack',
    legend_orientation="h",
    paper_bgcolor='rgb(255, 255, 255)',
    plot_bgcolor='rgb(255, 255, 255)',
    xaxis=dict(zeroline=False, gridcolor='lightgray'),
    font=dict(size=8),
    margin=dict(l=0, r=0, t=0, b=0),
    yaxis=dict(side='right')
    )

#pio.write_image(fig, "device_distribution_1p.pdf")#_no_ec_ic.pdf")
pio.write_image(fig, "device_distribution_p_eq_w_no_ld_ec_ic.pdf")#_no_ld_ec_ic.pdf")

exit()

sd_total = sd_ld+sd_nd+sd_ic+sd_ec
hd_total = hd_ld+hd_nd+hd_ic+hd_ec
uhd_total = uhd_ld+uhd_nd+uhd_ic+uhd_ec

p_sd_ld = round((float(sd_ld)/sd_total)*100)
p_sd_nd = round((float(sd_nd)/sd_total)*100)
p_sd_ic = round((float(sd_ic)/sd_total)*100)
p_sd_ec = round((float(sd_ec)/sd_total)*100)
p_hd_ld = round((float(hd_ld)/hd_total)*100)
p_hd_nd = round((float(hd_nd)/hd_total)*100)
p_hd_ic = round((float(hd_ic)/hd_total)*100)
p_hd_ec = round((float(hd_ec)/hd_total)*100)
p_uhd_ld = round((float(uhd_ld)/uhd_total)*100)
p_uhd_nd = round((float(uhd_nd)/uhd_total)*100)
p_uhd_ic = round((float(uhd_ic)/uhd_total)*100)
p_uhd_ec = round((float(uhd_ec)/uhd_total)*100)

print("{} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%)".format(sd_ld,p_sd_ld,sd_ic,p_sd_ic,sd_ec,p_sd_ec,hd_ld,p_hd_ld,hd_ic,p_hd_ic,hd_ec,p_hd_ec,uhd_ld,p_uhd_ld,uhd_ic,p_uhd_ic,uhd_ec,p_uhd_ec))


#hd_ld,p_hd_ld,uhd_ld,p_uhd_ld,sd_nd,p_sd_nd,hd_nd,p_hd_nd,uhd_nd,p_uhd_nd,sd_ic,p_sd_ic,hd_ic,p_hd_ic,uhd_ic,p_uhd_ic,sd_ec,p_sd_ec,hd_ec,p_hd_ec,uhd_ec,p_uhd_ec))

#print("{} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%) & {} ({}\%)".format(sd_ld,p_sd_ld, hd_ld,p_hd_ld,uhd_ld,p_uhd_ld,sd_nd,p_sd_nd,hd_nd,p_hd_nd,uhd_nd,p_uhd_nd,sd_ic,p_sd_ic,hd_ic,p_hd_ic,uhd_ic,p_uhd_ic,sd_ec,p_sd_ec,hd_ec,p_hd_ec,uhd_ec,p_uhd_ec))
