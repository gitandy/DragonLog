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

This README will provide only brief instructions. 

For detailed instructions see
- [Manual](doc/EN_00_MANUAL.md)  
- [Handbuch](doc/DE_00_HANDBUCH.md)  


Features
--------
* Runs on Windows, Linux and macOS
* predefined fields for logging
* input validation for callsign, RST, locator
* show worked before if a callsign is already logged
* distance calculation
* automatic time
* local callbook with immediate lookup
  * OM data build of your contacts (per callsign)
  * contest call history with received exchanges (per contest and callsign)
  * incorporating prefixes/suffixes
* user triggered callbook search (HamQTH.com, QRZ.com and QRZCQ.com)
* single and multiple QSO log upload 
  * HamQTH.com
  * eQSL upload, check and download
  * LoTW signing, upload and check status
* QSO and QSL statistics
* log Contest and xOTA QSOs data (supported Contests see `Help - Available Contests`)
  * follow Contest statistics
  * export Contest log as Cabrillo, EDI or special file formats
* CAT (band, frequency, mode/submode, power via hamlib integration)
* watch log files for automatic log import of WSJT-X, JS8Call, fldigi and others
* QSO log import/export
  * ADIF adi/adx/adi zipped
  * Excel/CSV
* log 11m band QSOs
* filter preset for recent QSOs (last week, month, half year, year)
* UTF-8 support (e.g. use german umlauts)
* convert non ASCII characters for ADIF export (for supported languages)
* integrates [CassiopeiaConsole](https://github.com/gitandy/HamCC#hamcc---cassiopeiaconsole)
* display DX spots from DX cluster via telnet
* selectable font and font size
  * default proportional font with slashed zero (modified Inter font)
  * 3 independent font sizes for application, QSO form and CassiopeiaConsole 
* Read QSL-QR-Codes to QSL or import QSOs (based on work of [TobbY, DG1ATN](https://www.dg1atn.de/darc-qsl-qr-code-reader/))


Security Notes
--------------

The passwords for callbook lookup, QSO upload and DX spots are securely stored 
in your systems key vault (e.g. Credential Manager on Windows, KWallet on KDE/Linux, Keychain on macOS).

At startup, DragonLog will inform about which service is actually in use.

DragonLog relies on the [keyring](https://github.com/jaraco/keyring) module.


Note about the Windows Installer
--------------------------------

For Windows there is also an installable MSI and ZIP package available for convenience.
Unfortunately the QSL-QR-Code reader is not available with these Windows prebuild versions.
Anyway the Python version is currently stuck at 3.12 as the MSI packaging will not be ported to higher versions.


LoTW sign and upload
--------------------

Only QSOs with a matching locator in the TQSL application (installation required) can be signed and uploaded.
DragonLog provides a selection for the stations configured in TQSL. 
Then it searches for all QSOs with the matching locator which were not already sent to LoTW.

If you secured your TQSL (which is not recommended) set DragonLog correspondingly. 
DragonLog will then request your password on each upload action.


Contests
--------
Only a few little contest are currently supported. 
The number will increase as I make progress in contests or someone using this Logger places a feature request.

If you want to log a contest, bring up the Contest Statistics with `Ctrl + T` and select the contest and date.
This will also set the QSO filter of your Logbook to display only this type of contest in the given range of date.
CassiopeiaConsole also will be set to contest mode.

Then you should start to log QSOs with either CassiopeiaConsole (heavily suggested) or via QSO form.

For contests, you do not have to track your sent exchange. DragonLog will care about at export.
So just let the running number increase and care about the received exchange from your QSO partner.

After the contest, use Contest - Export Contest... to generate a contest file in the special format (e.g. Cabrillo).
The contest name and dates should be preset in the dialog from the Contest Statistics. These information maybe important, 
as DragonLog may build your sent exchange out of them.

**Please check the exported file properly before sending it in!!!**

During a contest the call lookup is performed against the call history instead of the internal callbook.
After typing a callsign the received exchange will be filled with data from the lookup.

After saving a QSO in a running contest, the received exchange data is added to or updated in the call history.
The callbook will also be updated.


Hamlib integration
------------------
You can use hamlib to interact with your radio. 

The QSO logging form automatically updates radio information:
* frequency (and band)
* mode (and submode)
* power

Hamlib can be downloaded at https://github.com/Hamlib/Hamlib/releases.
DragonLog is tested against version 4.5.5 and 4.6.2.

After selecting your radio and interface settings you can press the start button to start the communication.

Currently, DragonLog can only configure radios with serial interface (including USB serial).

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
Check if the version date and version entity corresponds to the website.

The flag display is based on the mapping from [Flagpedia.net](https://flagpedia.net) 
and matched against the Big CTY data. This is sometimes weak and thus error-prone and needed manual fixes. 
There are still 15% unmapped (mostly islands).

If a flag is mapped wrong, please stay calm and drop me a mail. 
The mapping does not reflect my view on country borders.

Copyright
---------
DragonLog &copy; 2023 by Andreas Schawo is licensed under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/) 
