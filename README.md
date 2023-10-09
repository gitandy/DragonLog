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
* ADIF 3.x format (CB QSOs are skipped automatically)

Import 
------
### CSV format import
The import file is expected to have the same format and column order as the exported CSV file (Excel style but UTF-8).
So best practice is to export a QSO with the current program version and adjust the import file.

Empty rows are skipped. A row is considered empty if the date/time is missing.
