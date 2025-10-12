Installation instructions
=========================

The target is to support you installing DragonLog via Python PyPI package and the additional components.

An installation via MSI or Zip package should be self explaining.

First I show the steps on Windows and finally on Linux. The installation on macOS should not be that diffrent from Linux.


Installation on Windows
-----------------------

The installation will cover following steps

1. Install Python
2. Create a dedicated virtual environment for DragonLog
3. Install DragonLog package
4. Run DragonLog
5. Update DragonLog


### Install Python

The installation requires a python installation >= 3.10. 
I recommend Python 3.12 and usage of the python install managere (pymanager) from [python.org](https://www.python.org/downloads/). 


### Create vitual environment

Choose a folder where your DragonLog should go to (e.g. your user home folder).
Open up a terminal window and change to your user home folder

    C:\Users\username> py -m venv DragonLog

You should end up with a `DragonLog` folder inside your user home folder

It is possible to install DragonLog without a virtual environment.
But virtual environments will prevent collisions between other installations you may have.


### Install DragonLog

If your virtual envirnoment is initialised run

    C:\Users\username> DragonLog\Scripts\pip.exe install DragonLog[xlformat,qslqrcode]

This will install DragonLog and all of its dependencies including the extras.


### Run DragonLog

Now you can either run DragonLog via terminal

    C:\Users\username> DragonLog\Scripts\DragonLog.exe

or you just doubleclick the executable. In this case you may not want a terminal window and 
use `C:\Users\username\DragonLog\Scripts\DragonLogW.exe` instead.


### Updating DragonLog

To update DragonLog open a terminal and change to your folder

    C:\Users\username> DragonLog\Scripts\pip.exe install DragonLog -U


Installation on Linux
---------------------

The installation will cover following steps

1. Installation of Python-Venv and required libraries
2. Create a dedicated virtual environment for DragonLog
3. Install DragonLog package
4. Run DragonLog
5. Update DragonLogDie Anleitung deckt folgende Schritte ab


### Installation of venv and libraries

To use DragonLog some system packages are required. `libzbar0` is only required, if you use DragonLog with `qslqrcode` extension.

    # sudo apt install python3.12-venv libxcb-cursor0 libzbar0


### Create vitual environment

Choose a folder where your DragonLog should go to (e.g. your user home folder).
Open up a terminal window and change to your user home folder

    # python3 -m venv dragonlog

You should end up with a `dragonlog` folder inside your user home folder

It is possible to install DragonLog without a virtual environment.
But virtual environments will prevent collisions between other installations you may have.


### Install DragonLog

If your virtual envirnoment is initialised run

    # dragonlog/bin/pip install DragonLog[xlformat,qslqrcode]

This will install DragonLog and all of its dependencies including the extras.


### Run DragonLog

Now you can run DragonLog

    # dragonlog/bin/DragonLog


### Updating DragonLog

To update DragonLog open a terminal and change to your folder

    # dragonlog/bin/pip install DragonLog -U

