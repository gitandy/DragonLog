DragonLog
=========

[![PyPI Package](https://img.shields.io/pypi/v/dragonlog?color=%2334D058&label=PyPI%20Package)](https://pypi.org/project/dragonlog)
[![Python versions](https://img.shields.io/pypi/pyversions/dragonlog.svg?color=%2334D058&label=Python)](https://pypi.org/project/dragonlog)

Author: Andreas Schawo, DF1ASC 
([HamQTH](http://www.hamqth.com/DF1ASC), [eQSL](http://www.eqsl.cc/Member.cfm?DF1ASC))

DragonLog is a logging program to log hamradio QSOs.
Beside logging for ham radio you can also log CB radio QSOs.

![Screenshot in german translation](https://github.com/gitandy/DragonLog/blob/master/dragonlog/icons/Screenshot.png?raw=true)

*Screenshot in german translation*

Features
--------
* predefined fields for logging
* log multiple QSOs
* edit logs
* input validation for callsign, RST, locator
* show worked before if a callsign is already logged
* distance calculation
* automatic time
* callbook search and log upload (HamQTH.com)
* eQSL upload, check and download
* LoTW signing, upload and check status
* CAT (band, frequency, mode/submode, power via hamlib integration)
* watch log files for automatic log import of WSJT-X, JS8Call, fldigi and others
* ADIF adi/adx export/import
* Excel/CSV export/import
* log 11m band QSOs
* filter recent QSOs (last week, month, half year, year)
* UTF-8 (i.e. use german umlauts)
* convert non ASCII characters for ADIF export (for supported languages)

Installation
------------
The installation requires a python installation (>= 3.10). 
On Linux you may have to install libxcb-cursor0.
    
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

The form requires a callsign from your QSO partner and a start date to save/upload the data.
It gives a colourful feedback for the quality of your supplied data.
The colour feedback highlights required and recommended data only.

| Colour                                               | Meaning         |
|------------------------------------------------------|-----------------|
| <span style="background-color:#ff0000">red</span>    | required        |
| <span style="background-color:#ff7f00">orange</span> | wrong format    |
| <span style="background-color:#ffff00">yellow</span> | empty           |
| <span style="background-color:#00ff00">green</span>  | ok              |
| <span style="background-color:#0000ff">blue</span>   | worked before   |

If automatic time is selected, the end time gets updated at saving the QSO.

QSOs can be edited by double-clicking on an entry in the database view.

DragonLog can retrieve additional OM data from HamQTH.com callbook and upload the QSO.

In log and change mode there is a second view for QSL and different upload status.
Here you can check the status of your eQSL inbox or LoTW QSLs.

While eQSL upload is handled per QSO only (currently) LoTW is handled for the whole database.

Make sure that you properly set the credentials for each online service in the settings.
The password is stored in the systems key vault (i.e. Credential Manager on Windows or KWallet on KDE/Linux).

### LoTW sign and upload
Only QSOs with a matching locator in TQSL application can be signed and uploaded.
DragonLog provides a selection from the configured stations in TQSL. 
Then it searches for all QSOs with the matching locator which were not already sent to LoTW.

If you secured your TQSL set DragonLog correspondingly. DragonLog will then request your password on 
each upload action.

### Automatic log import
If you want to automatically log QSOs from other programs i.e. WSJT-X or JS8Call 
DragonLog can watch an ADIF file for changes and import new logs as they are created.

Starting file watching opens a file dialog where you have to point to the log in question.
Check the manual of the other program to find the correct path.

If you want to use the worked before feature of the other program consider to export your 
QSOs beforehand.
Dragonlog will only import QSOs which are not already included in the current database.

[Keyboard shortcuts](https://github.com/gitandy/DragonLog/blob/master/SHORTCUTS.md)
----------------------------------

Export
------
Following formats are supported for export
* [ADIF 3](https://adif.org/) format (ADI/ADX)
* Excel file
* CSV format (UTF-8 encoding)

ADIF ADX is the best choice for creating a backup.

### ADIF format export
ADX should be preferred over ADI as UTF-8 is supported. 
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
UTF-8 content (*_INTL fields) are preferred over ASCII counterparts when importing ADX files.

For ADI files DragonLog fixes different problems 
depending on the source of the file (see [ADIF Compatibility](https://github.com/gitandy/DragonLog/blob/master/ADIF_COMPATIBILITY.md))

Hamlib integration
------------------
You can use hamlib to interact with your radio. 

The QSO logging form automatically updates radio information:
* frequency (and band)
* mode (and submode)
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
