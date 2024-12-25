ADIF-Compatibility
==================

Though ADIF is standardised very well not all applications or services use it in a proper way.

DragonLog reads standard conforming ADI files and is able to identify and fix 
some nonconforming ADI content on import (see table below).

Compatibility table
-------------------

| Application/Service   | DragonLog import        | Comment                                                                               |
|-----------------------|-------------------------|---------------------------------------------------------------------------------------|
| QRZ.com               | ok                      |                                                                                       |
| eQSL.cc Inbox/Archive | ok<br/>fixes wrong tags | only partial QSO data also import outbox before, <br/>manually fix non ASCII chars    |
| eQSL.cc Outbox        | ok<br/>fixes wrong tags | only partial QSO data also import inbox afterwards, <br/>manually fix non ASCII chars |
| WSJTX                 | ok                      |                                                                                       |
| fldigi                | ok<br/>fixes wrong data |                                                                                       |
| JS8Call               | ok                      |                                                                                       |
| LoTW                  | ok<br/>fixes wrong tag  |                                                                                       |
| UCXLog                | ok                      |                                                                                       |
| HAM Contest           | ok                      |                                                                                       |
| DARC DCL/DML          | ok<br/>drops QSL_RCVD   | DCL status will not be tracked in DragonLog                                           |
| HamQTH.com            | see note below          |                                                                                       |
| QRZCQ.com             | see note below          |                                                                                       |

If ok is shown in the table the corresponding programs ADI output was tested and works with DragonLog.  

HamQTH.com and QRZCQ.com are not listed here as the provided download seems to be the uploaded file.

Other applications or services ADI exports are currently untested. If you are experiencing issues 
please contact me, so I am able to implement a fix.
