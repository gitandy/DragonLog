DragonLog
=========
DragonLog is a logging program to log hamradio QSOs.
Beside logging for ham radio you can also log CB radio QSOs.

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

Export
------
Following formats are supported for export
* Excel format
* CSV format (Excel style with separator ; and local encoding)
* ADIF 3 format (ADI/ADX) (CB QSOs are skipped automatically)

Import 
------
### CSV format import
The import file is expected to have the same format and column order as the exported CSV file (Excel style but UTF-8).
So best practice is to export a QSO with the current program version and adjust the import file.

Empty rows are skipped. A row is considered empty if the date/time is missing.

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
You have to compile the hamlib release first. 
Download the release .tar.gz (not source), unpack, ./configure, make, make install.
The rigctld should be in /usr/local/bin and thus on your path.

Copyright
---------
DragonLog &copy; 2023 by Andreas Schawo is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/) 
