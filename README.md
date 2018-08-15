# ldrop
Data recording sensor api and gui.

### What is ldrop?
ldrop is a more open version of drop that does not require any predefined
structure for the experiment. ldrop is aiming to be a library which provides 
user a sensor-API to be easily used with their own scripts.

### System requirements
ldrop is not platform dependend by nature. However we use Linux because python
is easiest to use on Linux.

### How to use ldrop?
[API design not final]
```
import Drop
exp = MyExperiment()
ldrop = Drop.DropController()
ldrop.set_callbacks("myexp", exp.on_play, exp.on_stop, exp.on_continue, exp.on_data)
exp.tag_callback = drop.on_tag
ldrop.start_gui()
```
