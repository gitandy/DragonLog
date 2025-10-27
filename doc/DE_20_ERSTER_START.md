Erster Start und Programmstart
==============================

Beim ersten Start öffnet DragonLog den Einstellungsdialog. Du solltest zumindest 
Dein Rufzeichen, Namen und Locator für ein erfolgreiches Arbeiten einstellen.

Um den Standard-QTH/Locator zu setzen, gehe zuerst in den Einstellungen zum Reiter `QTH & Rig` und füge 
Deinen ersten QTH und Locator hinzu z.B. `Koblenz (JO30si)`.
Hierzu drückst Du das `+` unter der Liste worauf ein neuer Eintrag erscheint. 
Diesen kannst Du dann durch Doppelklick ändern.
Jetzt kannst Du Deinen Standard QTH auf dem Reiter `Station` auswählen.

Das gleich gilt für Radio und Antenne. Auch diese müssen zuerst im Reiter `QTH & Rig` hinzugefügt werden.

Hast Du die Einstellungen abgeschlossen kannst Du mit `Strg+L` Dein erstes QSO loggen.

Bevor Du QSOs loggen kannst, muss natürlich noch eine Datenbank ausgewählt bzw. angelegt werden.
Diese kannst Du speichern, wo Du möchtest. Sie wird dann erstellt und initialisiert.

Beim nächsten Start wird die zuletzt verwendete Datenbank automatisch geöffnet.

Du kannst zwischen verschiedenen Datenbanken wechseln wie Du möchtest.


Kommandozeilen Argumente
------------------------

Wenn Du verschieden QSO-Datenbanken verwendest, kannst Du diese mit folgendem Aufruf öffnen

    DragonLog QSOs-2024.qlog

Wenn Du unterschiedliche Konfigurationen z.B. pro Rufzeichen nutzen willst kannst Du diese so aufrufen

    DragonLog -ini DF1ASC.ini

Die Argumente müssen in folgendem Format verwendet werden

    DragonLog [-ini INI_FILE] [QSODB_FILE]

Hiermit hast Du die Möglichkeit verschiedene Arbeitsbereiche mit unterschiedlichem QTH, Rig, etc. zu nutzen

- Feststation `DragonLog -ini DF1ASC.ini Logbook_DF1ASC.qlog`
- Portabel-Station `DragonLog -ini DF1ASC_portable.ini Logbook_DF1ASC_portable.qlog`
- CB-Station `DragonLog -ini CB.ini Logbook_CB.qlog`
