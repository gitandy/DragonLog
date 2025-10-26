Electronic QSLs
===============

eQSL.cc
-------

To upload QSOs to eQSL you can either select a bunch of QSOs and use `Upload & QSL - Upload to eQSL` or 
export your QSOs to ADIF format and upload them at eQSL webpage.

You can either check for eQSLs per QSO via `Upload & QSL - Check eQSL` or export a set of QSOs as ADIF from eQSL Inbox and import them regularly. 

For more than 20 QSOs you should consider to use the ADIF import/export way.

If DragonLog can not find an eQSL for a portable call it tries again and searches for an eQSL without `/P` suffix.


LoTW sign and upload
--------------------

For uploading and signing with LoTW you need to have TQSL installed and setup.

Only QSOs with a matching locator in the TQSL application can be signed and uploaded.
DragonLog provides a selection for the stations configured in TQSL. 
Then it searches for all QSOs with the matching locator which were not already sent to LoTW, exports them and 
initiates the signing and upload.

If you secured your TQSL (which is not recommended) set DragonLog correspondingly. 
Go to `Settings - Credentials - LoTW`.
DragonLog will then request your password on each upload action.

You can either check for QSLs per QSO or export a set of QSOs as ADIF at LoTW and import them regularly.
