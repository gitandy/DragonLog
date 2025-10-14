Exporting and Importing QSOs
============================

Export
------

Following formats are supported for export
* [ADIF 3](https://adif.org/) format (ADI/ADX/ADI zipped)
* Excel file (if you selected `xlformat` at installation)
* CSV format (UTF-8 encoding)

If you back up your log regularly at HamQTH use zipped ADI format for your whole logbook.

ADIF ADX is the best choice for creating a backup for your own storage. 
The data can completely be restored from this format.

### ADIF format export

ADX should be preferred over ADI as UTF-8 is supported. Unfortunately most services do not support ADX.
For ADX fields, where UTF-8 is supported (*_INTL fields) additionally the ASCII counterpart is exported.

For ADX ASCII only fields, thus all ADI fields, all german umlauts and ligatures are converted 
automatically to suiting ASCII counterparts.
This depends on your language and if a substitution is available.


Import 
------

Following formats are supported for import
* [ADIF 3](https://adif.org/) format (ADI/ADX/ADI zipped)
* Excel file (if you selected `xlformat` at installation)
* CSV format (UTF-8 encoding)


### Excel/CSV import

The import file is expected to have the same structure and column order as exported by DragonLog.
So best practice is to export an example QSOs with the current program version and 
adjust the import file accordingly.

Empty rows are skipped. A row is considered empty if the date/time is missing.


### ADIF format import

UTF-8 content (*_INTL fields) are preferred over ASCII counterparts when importing ADX files.

For ADI files DragonLog fixes different problems 
depending on the source of the file (see [ADIF Compatibility](../ADIF_COMPATIBILITY.md))


Automated Import
----------------

If you want to automatically log QSOs from other programs e.g. WSJT-X or JS8Call, 
DragonLog can watch their ADIF file for changes and import new logs as they are created.

Starting file watching opens a file dialog where you have to point to the log in question.
Some programs are preconfigured. Check the user manual of other programs to find the correct path.

If you want to use the worked before feature of the other program consider to export your QSOs beforehand.
DragonLog will only import QSOs which are not already included in its current database.
