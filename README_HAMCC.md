Working with CassiopeiaConsole
==============================

If you want to use CassiopeiaConsole to add QSOs more quickly, start typing in the input field right hand of `QSO>`.
The single words must conform to a special format (s. below) to be evaluated as valid QSO information.

You also can edit the fields directly.
This is not encouraged as it slows down massivly but may help to get the contest ID right.

Your own data (call, locator, name) should already be filled with your default settings.
If not, edit your station settings (recommended) or type it in manually (via QSO line or directly in to the fields).


Example session
---------------

Press `CTRL+K` to open CassiopeiaConsole. The cursor should jump to the `QSO>` line. Now:

1. Type in `8` or `80m` followed by SPACE and CassiopeiaConsole recons you are using the 80m band
2. Now type `s` or `ssb` and CassiopeiaConsole saves the mode SSB after you hit SPACE
3. We are ready for the first QSO? Ah, `DF1ASC` is calling so type it in and hit SPACE (I won't repeat it from now on)
4. He told you his name Andreas and we prefix it like `'Andreas`
5. You want to leave some comments? Type in `"#Ant Dipol, Rig FT-991A"`

After hitting ENTER the QSO will be added to the database. You can also use the button with the `+` sign.
Typing `~` or pushing the button with the `x` sign will clear all input (except that of type memory and auto).


Input format
------------

The table shows all available pre- and postfixes. The following will work for API and if run as program.

Placeholder x for characters and 9 for numbers.
Types marked with auto are prefilled but can be overwritten. Types marked with memory are retained for the session.

| Info          | Format                   | Type    | Comments                                                        |
|---------------|--------------------------|---------|-----------------------------------------------------------------|
| Callsign      | xx9xx                    |         | format checked                                                  |
| Locator/QTH   | @xx99xx or @QTH(Locator) |         | format checked (max. 8 digit locator)                           |
| Name          | 'xxxx                    |         |                                                                 |
| Comment       | #xxxx                    | memory  |                                                                 |
| Band          | valid ADIF band          | memory  |                                                                 |
| Mode          | valid ADIF mode          | memory  |                                                                 | 
| RST rcvd      | .599                     | auto    | default CW 599, phone 59                                        |
| RST sent      | ,599                     | auto    | default CW 599, phone 59                                        |
| QSL rcvd      | *                        |         | toggles the information                                         |
| Event ID      | $xxxxxx                  | memory  | Contest ID or one of POTA, SOTA                                 |
| Rcvd Exch     | %xxxxx                   |         | Contest exchange or xOTA reference                              |
| Time          | HHMMt                    | memory  | partly time will be filled (see comments below)                 |
| Date          | YYYYMMDDd                | memory  | partly date will be filled (see comments below)                 |
| Date/Time     | =                        | auto    | sync date/time to now                                           |
| Frequency     | 99999f                   | memory  | in kHz                                                          |
| TX Power      | 99p                      | memory  | in W                                                            | 
| Your Call     | -cxx9xx                  | memory  | Preset with your default from station settings                  | 
| Your Locator  | -lxx99xx                 | memory  | Preset with your default from station settings                  | 
| Your Name     | -nxxxx                   | memory  | Preset with your default from station settings                  |
| Finish QSO    | ENTER-Key                | command |                                                                 |
| Clear QSO     | ~                        | command | clears input not cached QSO                                     |
| Show QSO      | ?                        | command |                                                                 |
| Sent Exch     | -N9 or -Nxx              | auto    | set start value (if number) for contest QSO No. or own xOTA ref |
| Toggle online | -o                       | command | toggles online (automatic date/time at saving) and offline      |
| Show version  | -V                       | command |                                                                 |

For callsigns, mode, locators, RST and contest id lowercase will be converted to uppecase.

Some info allows to use `_` which will be converted to spaces.

    QSO> #Long_comment 'Long_name

It is also possible to enclose the sequence in quotes to type spaces instead.

    QSO> "#Long comment" "'Long name"

### RST

RST fields supports the whole range like `59` for phone, `599` for CW or `-06` for digimodes.
For CW the last digit can also be an `a` for aurora, `s` for scatter or alike
(see [R-S-T System](https://en.wikipedia.org/wiki/R-S-T_system) on Wikipedia).

### Date and Time

If you only give minutes to time e.g. `23t` the time will be filled with the last hour as if `1823t` was given
(assuming last time is something like 18:12 or so).
For partial dates it will be filled in the same manner for each 2 digits missing from left to right.
So the date `240327d`, `0327d` or `27d` will be filled as if `20240327d` was given.

hostilog shortcuts for bands and modes
--------------------------------------
HamCC also supports the [hostilog](https://df1lx.darc.de/hosti-logger/) shortcuts
for modes and bands (bands limited to hostilog shortwave mode).
Only the mode shortcut `d` will result in MFSK for ADIF compatibility.

### For Bands

Only the shortcuts from shortwave mode are supported

| Short | Meaning |
|-------|---------|
| 0     | 160m    |
| 1     | 10m     |
| 2     | 20m     |
| 3     | 30m     |
| 4     | 40m     |
| 5     | 15m     |
| 6     | 12m     |
| 7     | 17m     |
| 8     | 80m     |
| 9     | 60m     |
| -2    | 2m      |
| -4    | 4m      |
| -5    | 6m      |
| -6    | 60m     |
| -7    | 70cm    |

### For Modes

| Short | Meaning      | Comment                             |
|-------|--------------|-------------------------------------|
| S     | SSB          |                                     |
| C     | CW           |                                     |
| R     | RTTY         |                                     |
| A     | AMTOR        |                                     |
| D     | MFSK         | Maps to MFSK for ADIF compatibility |
| F     | FM           |                                     |
| H     | HELL         |                                     |
| J     | JT65         |                                     |
| P     | PSK          |                                     |
| T     | FT8          |                                     |
| M     | MFSK         | Extension                           |
| DV    | DIGITALVOICE | Extension                           |

Event mode for contests and xOTA
--------------------------------

If you typed in a contest id HamCC starts to increase a QSO contest exchange (see `-N`)
which you may want to communicate to your QSO partners. If the exchange is not a number it is simply carried as text.
The exchange is stored in STX and STX_STRING if it is a number. Else it is only stored in STX_STRING.

Changing the contest id resets the QSO counter.

The received contest data will simply be stored without further handling.
If it is a number it is stored as SRX and SRX_STRING. Else it is stored as SRX_STRING only.

To leave the event mode for the following QSOs type a single `$` followed by a SPACE.

### xOTA

For xOTA just enter one of SOTA, POTA e.g. `$pota` instead of the contest ID.
Then set your own xOTA reference with `-Nxx-999` and track the QSO partners reference with `%xx-999`.

Source Code of HamCC
--------------------
The source code is available at [GitHub](https://github.com/gitandy/HamCC)

Copyright
---------
HamCC - CassiopeiaConsole &copy; 2024 by Andreas Schawo is licensed
under [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/) 
