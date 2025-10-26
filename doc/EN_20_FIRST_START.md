First start and Startup
=======================

At first start DragonLog opens the settings dialog for you. You should configure
at least your callsign, name and locator for a sufficient experience.

To select a default QTH/locator first go to the `Listings` tab and 
add your first QTH and locator e.g. `Koblenz (JO30si)`.  
With pressing the `+` under the list a new entry appears which you can edit after double-clicking. 
Now you can select your default QTH on the `Station` tab.

The same applies for radio and antenna. First add them on the `Listings` tab.

After closing the Settings you can log your first QSO with `Ctrl+L`.

Before you can start to log QSOs a database has to be selected.
It can be placed on a path where you wish to. The database will then be created and initialised.

At the next start the last database gets opened automatically.

You can switch between different databases as you like.


Commandline Arguments
---------------------

If you want to manage different QSO databases you can select them via commandline argument e.g.

    DragonLog QSOs-2024.qlog

If you also want to provide a separate configuration (maybe per callsign) you can use e.g.

    DragonLog -ini DF1ASC.ini

The arguments must follow the format in this order

    DragonLog [-ini INI_FILE] [QSODB_FILE]

With this, it is possible to maintain different workspaces with different QTH, Rig, etc. setups for e.g.

- home station `DragonLog -ini DF1ASC.ini Logbook_DF1ASC.qlog`
- portable station `DragonLog -ini DF1ASC_portable.ini Logbook_DF1ASC_portable.qlog`
- CB station `DragonLog -ini CB.ini Logbook_CB.qlog`
