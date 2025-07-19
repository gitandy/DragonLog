Installation on Windows
=======================

The installation will cover following steps

1. Install Python
2. Create a dedicated virtual environment for DragonLog
3. Install DragonLog package
4. Run DragonLog
5. Update DragonLog


Install Python
--------------

The installation requires a python installation (>= 3.10). 
I will recommend downloading the current python 3.13 release from [python.org](https://www.python.org/downloads/). 


Create vitual environment
-------------------------

Create a folder where your DragonLog should go to (e.g. folder under your user home: `C:\Users\username\DragonLog`).
Open up a terminal window and change to your user home folder

    C:\Users\username> py -m venv DragonLog

You should end up with a `DragonLog` folder inside your user home folder

It is possible to install DragonLog without a virtual environment.
But virtual environments will prevent collisons between other installations you may have.


Install DragonLog
-----------------

If your virtual envirnoment is initialised run     

    C:\Users\username> DragonLog\Scripts\pip.exe install DragonLog[xlformat,qslqrcode]

This will install DragonLog and all of its dependencies including the extras.


Run DragonLog
-------------

Now you can either run DragonLog via terminal

    C:\Users\username> DragonLog\Scripts\DragonLog.exe

or you just doubleclick the executable. In this case you may not want a terminal window and 
use `C:\Users\username\DragonLog\Scripts\DragonLogW.exe` instead.


Updateting DragonLog
--------------------

To update DragonLog open a terminal and change to your folder

    C:\Users\username> DragonLog\Scripts\pip.exe install DragonLog -U
