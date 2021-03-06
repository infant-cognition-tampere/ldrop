"""LDrop Controller-class."""

import sys
import os
import time
import glib
import utils
from pyee import EventEmitter
from LdropPygtkView import LDPV
from yapsy.PluginManager import PluginManager
from plugins import LdropPluginLocator


class Controller(EventEmitter):
    """Main controller of the class. Views+ui separated to different files."""

    def __init__(self):
        """Constructor."""
        # run the superclass constructor
        EventEmitter.__init__(self)

        # Model initialization code
        self.sensors = []
        self.tags = []

        # define important directories for external (not program code) files
        homedir = os.environ["HOME"]
        ldrop_home = os.path.join(homedir, "Documents", "ldrop_data")
        self.rootdir = ldrop_home
        self.plugindir = os.path.join(ldrop_home, "plugins")
        self.savedir = os.path.join(ldrop_home, "recordings")

        # check that saving, experiment etc directories are present
        utils.dircheck(self.savedir)
        utils.dircheck(self.plugindir)

        # put the plugins-directory
        sys.path.append(self.plugindir)

        # temporary? keyboard-contigency list
        self.keyboard_contigency = []

        # initialize plugin manager
        self.pluginmanager = PluginManager(plugin_locator=LdropPluginLocator())
        self.pluginmanager.setPluginPlaces([self.plugindir])
        self.pluginmanager.collectPlugins()
        self.gui = []

        self.play_callback = None
        self.stop_callback = None
        self.continue_callback = None
        self.data_callback = None

        self.participant_id = ""

    def add_model(self, model):
        """Add a model to listen for."""
        #TODO: currently same add_model for different kinds of emitters
        # (sensors and experiments), just counting they send different signals
        model.on("tag", self.on_tag)
        model.on("data", self.on_data)
        model.on("close_controller", self.on_close_controller)
        model.on("start_collecting_data", self.on_start_collecting_data)
        model.on("stop_collecting_data", self.on_stop_collecting_data)
        model.on("log_message", self.on_log_message)
        model.on("query", self.on_query)

    def add_sensor(self, sensor_name):
        """Callback for Add sensor -button."""
        # TODO: Improve APIs for plugins
        plugin_info = self.pluginmanager.getPluginByName(sensor_name)

        if plugin_info is None:
            print("Plugin " + sensor_name + " not found")
        else:
            plugin_info.plugin_object.get_sensor(self.rootdir,
                                                 self.on_sensor_created,
                                                 self.on_sensor_error)

    def close(self):
        """Method that closes the drop controller."""
        # disconnect all the sensors from the host
        for sensor in self.sensors:
            # TODO: this is done on stop_collecting data - unify
            sensor.stop_recording()
            sensor.disconnect()

        self.remove_all_listeners()

        self.ml.quit()
        print("ldrop mainloop stopped.")

    def close_gui(self):
        """Clear gui reference."""
        self.gui = []

        # run in what condition
        self.close()

    def continue_experiment(self):
        """Callback for continuebutton click."""
        if self.continue_callback is not None:
            self.continue_callback()

    def enable_gui(self):
        """Initialize pygtk-view to be run when mainloop starts."""
        self.gui.append(LDPV(self, self.savedir))

    def get_participant_id(self):
        """Return participant_id."""
        return self.participant_id

    def get_sensors(self):
        """Return list of connected sensors."""
        return self.sensors

    def get_sensor_plugins(self):
        """Return list of available sensors."""
        plugins = self.pluginmanager.getAllPlugins()
        sensornames = []
        for p in plugins:
            sensornames.append(p.name)

        return sensornames

    def message_to_sensor(self, sensortype, msg):
        """
        Callback for a message to sensor.

        Sensor needs to support the msg.
        """
        # find the right sensor(s) to forward the message to
        for sensor in self.sensors:
            if sensor.get_type == sensortype:
                sensor.on_message(msg)

    def on_close_controller(self):
        """Callback for signal close_controller."""
        glib.idle_add(self.close)

    def on_data(self, dp):
        """Callback for data-signal."""
        if self.data_callback is not None:
            glib.idle_add(self.data_callback, dp)

    def on_experiment_completed(self):
        """Callback for experiment finished."""
        # clear view references
        for r in self.sensors:
            self.exp_view.remove_model(r)
        # self.exp_view = None

    def on_keypress(self, keyname):
        """Callback for keypress."""
        if keyname in self.keyboard_contigency:
            self.keyboard_contigency = []
            self.emit("continue")
            tag = {"id": keyname, "secondary_id": "keypress",
                   "timestamp": self.timestamp()}
            self.on_tag("tag", tag)

    def on_query(self, msg, title, buttons, callbacks, callback_args):
        if len(self.gui) > 0:
            for g in self.gui:
                g.show_message_box(msg, title, buttons, callbacks,
                                   callback_args)

    def on_sensor_error(self, msg):
        """Sensor error-handler."""
        self.emit("error", msg)

    def on_sensor_created(self, shandle):
        """Callback for sensor initialization."""
        self.sensors.append(shandle)
        self.emit("sensorcount_changed")

        # add model to hear calls from sensors, such as data_condition met
        self.add_model(shandle)

    def on_start_collecting_data(self, savesubdir, savefilestring):
        """A callback for start_collecting_data signal."""
        self.start_collecting_data(savesubdir, savefilestring)

    def on_stop_collecting_data(self):
        """A callback for stop_collecting_data signal."""
        self.stop_collecting_data(None)

    def on_tag(self, tag):
        """
        Send a tag to all sensors.

        Tag might not come instantly here so the
        timestamp is taken in advance. The sensor must sync itself with the
        computer. Tag consists of:
        id = string, identifier of the tag
        timestamp = timestamp in ms of the localtime clock
        secondary_id = string, defines "start", "end", or "impulse", as a start
        of perioid, end of it or single impulse
        misc = other possible information (depends on the sensor how to use)
        """
        for sensor in self.sensors:
            # send a copy of the dict to each sensor
            sensor.tag(tag.copy())

    def on_log_message(self, logmsg):
        """Callback for log_append signal."""
        self.emit("log_update", logmsg)

    def play(self):
        """Start the experiment."""
        # TODO: possibly change the "pipeline" of the drop-involvement in exp
        if self.play_callback is not None:
            glib.idle_add(self.play_callback)

    def run(self):
        """Initialize controller start mainloop."""
        # if no gui to control experiment is present, just start running the
        # experiment
        if len(self.gui) == 0 and self.play_callback is not None:
            self.play()

        self.ml = glib.MainLoop()
        self.ml.run()

    def remove_model(self, model):
        """Remove model listeners."""
        model.remove_listener("tag", self.on_tag)
        model.remove_listener("data", self.on_data)
        model.remove_listener("close_controller", self.on_close_controller)
        model.remove_listener("start_collecting_data", self.on_start_collecting_data)
        model.remove_listener("stop_collecting_data", self.on_stop_collecting_data)
        model.remove_listener("log_message", self.on_log_message)
        model.remove_listener("query", self.on_query)

    def remove_sensor(self, sensor_id):
        """Disconnect the sensor with the provided sensor_id."""
        for sensor in self.sensors:
            if sensor.get_sensor_id() == sensor_id:
                sensor.disconnect()
                self.sensors.remove(sensor)
        self.emit("sensorcount_changed")

    def set_callbacks(self, play_callback, stop_callback,
                      continue_callback, data_callback):
        """Experiment side callback-setter."""
        self.play_callback = play_callback
        self.stop_callback = stop_callback
        self.continue_callback = continue_callback
        self.data_callback = data_callback

    def set_participant_id(self, pid):
        """Method for setting participant_id."""
        self.participant_id = pid
        self.emit("participant_id_updated")

    def sensor_action(self, sensor_id, action_id):
        """Perform action that is listed on sensors control elements."""
        for sensor in self.sensors:
            if sensor.get_sensor_id() == sensor_id:
                sensor.action(action_id)

    def start_collecting_data(self, savesubdir, savefilestring):
        """Function starts data collection on all sensors."""
        savepath = os.path.join(self.savedir, savesubdir)
        for sensor in self.sensors:
            sensor.start_recording(savepath, savefilestring)
#            sensor.start_recording(savepath, self.participant_id,
#                                   self.experiment_id)

    def stop(self):
        """Callback for stopbutton click."""
        if self.stop_callback is not None:
            self.stop_callback()

    def stop_collecting_data(self, callback):
        """Stop data collection on all sensors and run callback."""
        for sensor in self.sensors:
            sensor.stop_recording()
        if callback is not None:
            glib.idle_add(callback)

    def timestamp(self):
        """Return a local timestamp in microsecond accuracy."""
        return time.time()

    def __del__(self):
        """Destructor."""
        print("ldrop instance deleted.")
