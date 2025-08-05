Building DragonLog
==================

First of all, clone the source from the github repository

    # git clone https://github.com/gitandy/DragonLog.git


On Linux
--------

Create a virtual environment and install the dependencies.

    # cd DragonLog
    # python3 -m venv venv
    # venv/bin/python -m pip install -r requirements.txt


Now you are ready to build and run (assuming `bash` shell)

    # source venv/bin/activate
    # make
    # python -m dragonlog


On Windows
----------

To build everything you need to have cygwin and some packages installed:
- make
- git
- qt5-linguist-tools

Create a virtual environment and install the dependencies.

If you want to be able to build the MSI-Package use Python <= 3.12.x.

    # cd DragonLog
    # py -3.12 -m venv venv
    # venv/Scripts/python -m pip install -r requirements

Then you can build and run

    # make.bat
    # venv/bin/python -m dragonlog


Building packages
-----------------

To build the wheel use the `dist` target

    # source venv/bin/activate
    # make dist

or on Windows

    # make.bat dist

On Windows you may want to build an MSI and ZIP package with the `bdist_msi` target

    # make.bat bdist_msi
