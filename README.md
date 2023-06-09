# venus.dbus-tasmota-inverter
Service to integrate a tasmota wallplug sensor data as pvinverter

The Python script subscribes to a MQTT Broker and parses the typical Tasmota Sensor telegrams. You can configure 3 topics, one for each phase. These will send the values to dbus.

### Configuration

See config.ini and amend for your own needs. The Inverter_Position parameter defines the phsical contact for this inverter. 0 means AC-In

In [Topics] section you can specify a unlimited number of topics per phase. If multiple topics are assigned to one phase the current and power values will be added to a total for this phase

Example:

    `L1 = topic1[,topic2,topic3]`
    
    `L3 = topic4`

### Installation

1. Copy the files to the /data folder on your venus:

   - /data/dbus-tasmota-inverter/dbus-tasmota-inverter.py
   - /data/dbus-tasmota-inverter/kill_me.sh
   - /data/dbus-tasmota-inverter/service/run

2. Set permissions for files:

   `chmod 755 /data/dbus-tasmota-inverter/service/run`

   `chmod 755 /data/dbus-tasmota-inverter/kill_me.sh`

   `chmod 755 /data/dbus-tasmota-inverter/rc.local`

3. Get two files from the [velib_python](https://github.com/victronenergy/velib_python) and install them on your venus:

   - /data/dbus-tasmota-inverter/vedbus.py
   - /data/dbus-tasmota-inverter/ve_utils.py

4. Add a symlink to the file /data/rc.local:

   `ln -s /data/dbus-tasmota-inverter/service /service/dbus-tasmota-inverter`

   Or if that file does not exist yet, store the file rc.local from this service on your Raspberry Pi as /data/rc.local .
   You can then create the symlink by just running rc.local:

   make it executable with

   `chmod 755 /data/rc.local`
  
   `/data/rc.local`

   The daemon-tools should automatically start this service within seconds.

### Debugging

The log you find in /var/log/dbus-tasmota-inverter

`tail -f -n 200 /data/log/dbus-tasmota-inverter/current.log`

You can check the status of the service with svstat:

`svstat /service/dbus-tasmota-inverter`

It will show something like this:

`/service/dbus-tasmota-inverter: up (pid 10078) 325 seconds`

If the number of seconds is always 0 or 1 or any other small number, it means that the service crashes and gets restarted all the time.

When you think that the script crashes, start it directly from the command line:

`python /data/dbus-tasmota-inverter/dbus-tasmota-inverter.py`

and see if it throws any error messages.

If the script stops with the message

`dbus.exceptions.NameExistsException: Bus name already exists: com.victronenergy.grid"`

it means that the service is still running or another service is using that bus name.

#### Restart the script

If you want to restart the script, for example after changing it, just run the following command:

`/data/dbus-tasmota-inverter/kill_me.sh`

The daemon-tools will restart the script within a few seconds.

### Hardware

Any Tasmota device, which has a Power Sensor.

