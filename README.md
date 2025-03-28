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
* edit log entries
* input validation for callsign, RST, locator
* show worked before if a callsign is already logged
* distance calculation
* automatic time
* callbook search (HamQTH.com and QRZCQ.com)
* Single and multiple QSO log upload 
  * HamQTH.com
  * eQSL upload, check and download
  * LoTW signing, upload and check status
* log Contests and xOTA QSOs data (supported Contests see `Help - Available Contests`)
  * follow Contest statistics
  * export Contest log as Cabrillo, EDI or special file formats
* CAT (band, frequency, mode/submode, power via hamlib integration)
* watch log files for automatic log import of WSJT-X, JS8Call, fldigi and others
* QSO log import/export
  * ADIF adi/adx/adi(zipped)
  * Excel/CSV
* log 11m band QSOs
* filter preset for recent QSOs (last week, month, half year, year)
* UTF-8 support (e.g. use german umlauts)
* convert non ASCII characters for ADIF export (for supported languages)
* integrates [CassiopeiaConsole](https://github.com/gitandy/HamCC#hamcc---cassiopeiaconsole)
* display DX spots from DX cluster via telnet
* selectable font and font size
  * default proportional font with slashed zero (modified Inter font)
  * 3 independant font sizes for application, QSO form and CassiopeiaConsole 


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


Starting and first start
------------------------
At first start DragonLog opens the settings dialog for you. You should configure
at least your callsign, name and locator for a sufficient experience.

To select a default QTH/locator go to the `QTH & Rig` tab and 
add your first QTH and locator e.g. `Koblenz (JO30si)`.  

Before you can start to log QSOs a database has to be selected.
It can be placed on a path where you wish to.
The database will be created and initialised.

At the next start of the program the last database gets opened automatically.

You can switch between different databases as you like.

### Commandline Arguments
If you want to manage different QSO databases you can select them via commandline argument e.g.

    # DragonLog QSOs-2024.qlog

If you also want to provide a separate configuration you can use e.g.

    # DragonLog -ini DF1ASC.ini

The arguments must follow the format in this order

    DragonLog [-ini INI_FILE] [QSODB_FILE]


QSOs
----
You can log single QSOs by using the shortcut Ctrl+L.

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

DragonLog can retrieve additional OM data from HamQTH.com or QRZCQ.com callbook and upload the QSO to different services.

In log and change mode there is a second view for QSL and different upload status.
Here you can check the status of your paper QSL, eQSL inbox or LoTW QSLs.

Make sure that you properly set the credentials for each online service in the settings.
The password is stored in the systems key vault (e.g. Credential Manager on Windows or KWallet on KDE/Linux).

### LoTW sign and upload
Only QSOs with a matching locator in the TQSL application (installation required) can be signed and uploaded.
DragonLog provides a selection for the stations configured in TQSL. 
Then it searches for all QSOs with the matching locator which were not already sent to LoTW.

If you secured your TQSL (which is not recommended) set DragonLog correspondingly. 
DragonLog will then request your password on each upload action.

### Automatic log import
If you want to automatically log QSOs from other programs e.g. WSJT-X or JS8Call 
DragonLog can watch their ADIF file for changes and import new logs as they are created.

Starting file watching opens a file dialog where you have to point to the log in question.
Some programms are preconfigured. Check the user manual of other programs to find the correct path.

If you want to use the worked before feature of the other program consider to export your QSOs beforehand.
DragonLog will only import QSOs which are not already included in the current database.

Contests
--------
Only a few little contest are currently supported. 
The number will increase as I make progress in contests or someone using this Logger places a feature request.

If you want to log a contest, bring up the Contest Statistics with `Ctrl + T` and select the contest and date.
This will also set the QSO filter of your Logbook to display only this type of contest in the given range of date.
CassiopeiaConsole also will be set to contest mode.

Then you should start to log QSOs with either CassipeiaConsole (heavily suggested) or via QSO form.

For contests you do not have to track your sent exchange. DragonLog will care about at export.
So just let the running number increase and care about the received exchange from your QSO partner.

After the contest, use File - Export Contest... to generate a contest file in the special format (e.g. Cabrillo).
The contest name and dates should be preset in the dialog from the Contest Statistics. These informations maybe important, 
as DragonLog may build your sent exchange out of them.

**Please check the exported file properly before sending it in!!!**

Especially an EDI file will need some care, due to not all the data is handled via the dialog.

Export
------
Following formats are supported for export
* [ADIF 3](https://adif.org/) format (ADI/ADX/ADI zipped)
* Excel file
* CSV format (UTF-8 encoding)

If you backup your log regularly at HamQTH use zipped ADI format for your whole logbook.

ADIF ADX is the best choice for creating a backup for your own storage. The data can completly be restored from this format.
Also 

### ADIF format export
ADX should be preferred over ADI as UTF-8 is supported. Unfortunatly most services do not support ADX.
For ADX fields where UTF-8 is supported (*_INTL fields) additionally the ASCII counterpart is exported.

For ADX ASCII only fields (all ADI fields) all german umlauts and ligatures are converted 
automatically to suiting ASCII counterparts.

Import 
------
Following formats are supported for import
* [ADIF 3](https://adif.org/) format (ADI/ADX/ADI zipped)
* Excel file
* CSV format (UTF-8 encoding)

### Excel/CSV import
The import file is expected to have the same structure and column order as exported by DragonLog.
So best practice is to export an example QSOs with the current program version and 
adjust the import file accordingly.

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

Country Data
------------
Each release of DragonLog provides a very recent country data file. 
If you want to update it manually visit https://www.country-files.com/category/big-cty/ by Jim, AD1C 
and download a Big CTY Zip file. 
Unpack the Zip and goto Settings - Dx Spots to select the file.
You can check if the file is correctly loaded via Help - About. 
Check if the Version date and Version entity corresponds to the website.

The flag display is based on the mapping from [Flagpedia.net](https://flagpedia.net) 
and matched against the Big CTY data. This is sometimes weak and thus error prone and needed manual fixes. 
There are still 25% unmapped (mostly islands).

If a flag is mapped wrong please stay calm and drop me a mail. 
The mapping does not reflect my view on country borders.

Copyright
---------
DragonLog &copy; 2023-2024 by Andreas Schawo is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/) 
