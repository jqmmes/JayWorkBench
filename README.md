# JayWorkBench

JayWorkBench is a tool for automating computation offloading experiments using [Jay](https://github.com/jqmmes/Jay). Written in Python, uses gRPC to control a hybrid cloud of Jay instances, the Android Debug Bridge (ADB) to setup the necessary Android devices, and ssh/shell to setup Linux/x86 cloudlet and cloud server instances.

> Copyright (c) 2021 University of Porto/Faculty of Sciences (UP/FCUP).
>
> Author: Joaquim Silva
>
> This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
> This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
> You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

## Usage

The tool is described in detail in Appendix B
of [my PhD Thesis](https://hdl.handle.net/10216/139189). A basic summary of usage options is provided below.

### Invocation

The workbench is executed using 

```
python workbench.py [options]
```

### General options

Option|Description
------|-----------
`-show-help`| Show a help message and quit.
`--configs dirs`| Specify the directories where configuration files may be found.
`--debug-adb`| Print every ADB call and its output.
`--adb-log-level L`|Complements the previous setting by defining the log level to use.
`--debug-grpc`| Print every gRPC call and its output.
`--wifi`| Tells the workbench to consider Android devices available via WiFi, in addition to devices connected through USB or Ethernet.
`--ip-mask M` | If using Wi-Fi, this sets the IP address mask for WiFi addresses.

### Android device lifecycle

A set of options may be used for common lifecycle tasks necessary to setup Android devices. Note that each option affects every Android device detected by the workbench (i.e., all of them). Moreover, if one of the options is specified in conjunction with a configuration, then the associated commands run first.

Option|Description
------|-----------
`--clean-data`| Completely remove Jay and every data stored by it.
`--install` | Install the Jay app.
`--reboot-devices`| Reboot devices.
`--shutdown`| Shutdown devices.
`--screen-on`| Turns on device display.
`--screen-off`| Turns off device display.
`--brightness I`| Sets the screen brightness to the specified intensity.

### Smart power plug control

It is also possible to control a Meross smart power plug using complementary options.

Option|Description
------|-----------
`--smart-plug P` | Informs the workbench of the plug used. 
`--power-on`| Power on the plug.
`--power-off`| Power off the plug
