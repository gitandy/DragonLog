DragonLog
=========
DragonLog is a logging program to log hamradio QSOs.
Beside logging for ham radio you can also log CB radio QSOs.

![Screenshot in german translation](https://github.com/gitandy/DragonLog/blob/master/dragonlog/icons/Screenshot.png?raw=true)

*Screenshot in german translation*

Installation
------------
The installation requires a python installation (>= 3.9).
    
    # python3 -m pip install DragonLog

If you want to be able to export/import to/from Excel files install the extra packages

    # python3 -m pip install DragonLog[extra]

Run as

    # python3 -m dragonlog

Or if your python scripts folder is on PATH you can start DragonLog with 

    # DragonLog


For windows there is also an installable MSI and ZIP package available for convenience.

First start
-----------
Before you can start to log QSOs a database has to be selected.
It can be placed on a path where you wish to.
The database is created and initialised.

At the next start of the program the last database gets opened automatically.

You can switch between different databases as you like.

QSOs
----
You can log single QSOs by using the shortcut Ctrl+L or 
use a log loop to enter multiple QSOs via Ctrl+Shift+L.

The displayed form can be handled the easiest if you use TAB key to jump from field to field.

If automatic time is selected, the time gets updated at saving the QSO.

QSOs can be edited by double-clicking on an entry in the database view.

### Automatic log import
If you want to automatically log QSOs from other programms i.e. WSJT-X or JS8Call 
DragonLog can watch an ADIF file for changes and import new logs as they are created.

Starting file watching opens a file dialog where you have to point to the log in question.
Check the manual of the other program to find the correct path.

If you want to use the worked before feature of the other program consider to export your 
QSOs beforehand.
Dragonlog will only import QSOs which are not already included in the current database.

Export
------
Following formats are supported for export
* [ADIF 3](https://adif.org/) format (ADI/ADX)
* Excel file
* CSV format (UTF-8 encoding)

ADIF ADX is the best choice for creating a backup.

### ADIF format export
ADX should be prefered over ADI as UTF-8 is supported. 
For ADX where UTF-8 (*_INTL fields) is supported additionally the ASCII counterpart is exported.

For ADX ASCII only fields (all ADI fields) all german umlauts and ligatures are converted 
automatically to suiting counterparts. 

.adif is an alternative for .adi (as specified).

Import 
------
Following formats are supported for export
* [ADIF 3](https://adif.org/) format (ADI/ADX)
* Excel file
* CSV format (UTF-8 encoding)

### Excel/CSV import
The import file is expected to have the same structure and column order as exported by DragonLog.
So best practice is to export QSOs with the current program version and adjust the import file.

Empty rows are skipped. A row is considered empty if the date/time is missing.

### ADIF format import
UTF-8 content (*_INTL fields) are prefered over ASCII counterparts when importing ADX files.

Hamlib integration
------------------
You can use hamlib to interact with your radio. 

The QSO logging form automatically updates radio information:
* frequency (and band)
* mode
* power

Hamlib can be downloaded at https://github.com/Hamlib/Hamlib/releases.
DragonLog is tested against version 4.5.5.

After selecting your radio and interface settings you can press the start button to start the communication.

Currently, DragonLog can only configure radios with serial interface.

### On Windows
Unpack or install your hamlib release.
On the CAT settings tab you have to select your hamlib unpack/installation directory.

### On Linux
If no package is available for your distribution you have to compile the hamlib release first. 
Download the release .tar.gz (not source), unpack, ./configure, make, make install.
The rigctld is assumed to be in /usr/local/bin and thus on your path.

Copyright
---------
DragonLog &copy; 2023-2024 by Andreas Schawo is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/) 
