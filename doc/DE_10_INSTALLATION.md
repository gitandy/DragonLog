Installationsanleitung
======================

Das Ziel ist hier, die Installation mittels Python PyPI zu unterstützen und insbesondere für zusätzlich benötigte Komponenten eine Hilfestellung zu leisten.

Die Installation mittels Installer oder Zip-Paket wird hier nicht geschildert, da dies selbsterklärend sein sollte.

Zuerst zeige ich die Installation unter Windows und anschließend für Linux. Die Installation in macOS sollte ähnlich zu Linux sein.


Installation unter Windows
--------------------------

Die Anleitung deckt folgende Schritte ab

1. Installation von Python
2. Erstellen einer virtuellen Umgebung für DragonLog
3. Installation des DragonLog-Pakets
4. DragonLog starten
5. DragonLog aktualisieren


### Installation von Python

Für DragonLog wird Python >= 3.10 benötigt. 
Ich empfehle Python 3.12 und die Verwendung des Python-Install-Managers (pymanager) [python.org](https://www.python.org/downloads/). 


### Erstellen einer virtuellen Umgebung

Du solltest den Ordner auswählen, in dem Du DragonLog installieren möchtest. Ich nutze den persönlichen Ordner.

Öffne ein Terminal und wechsle in diesen Ordner. Dann erstellst Du die virtuelle Umgebung

    py -m venv DragonLog

Danach sollte ein Ordner `DragonLog` vorhanden sein.

Man kann DragonLog auch ohne virtuelle Umgebung installieren, wenn man evtl. Paketkollisionen mit anderen Projekten in kauf nimmt.


### DragonLog installieren

Wenn die virtuelle Umgebung initialisiert ist, nutze

    DragonLog\Scripts\pip.exe install DragonLog[xlformat,qslqrcode]

Dies installiert DragonLog und alle Abhängigkeiten inklusive der Extras.


### DragonLog starten

Jetzt kannst Du DragonLog starten

    DragonLog\Scripts\DragonLog.exe

Oder Du kannst die ausführbare Datei einfach Doppelklicken. In dem Fall stört wahrscheinlich das Terminal-Fenster und Du nutzt bessere `C:\Users\username\DragonLog\Scripts\DragonLogW.exe`.


### DragonLog aktualisieren

DragonLog kann nun ganz einfach aktualisiert werden

    DragonLog\Scripts\pip.exe install DragonLog -U



Installation unter Linux
------------------------

Die Anleitung deckt folgende Schritte ab

1. Installation von Python-Venv und benötigte Bibliotheken
2. Erstellen einer virtuellen Umgebung für DragonLog
3. Installation des DragonLog-Pakets
4. DragonLog starten
5. DragonLog aktualisieren


### Installation von venv und Bibliotheken

Um DragonLog zu nutzen, benötigst Du noch einige System-Pakete. `libzbar0` wird nur benötigt, wenn Du DragonLog mit der Erweiterung `qslqrcode` installierst.

Hier für Debian/Ubuntu/Linux Mint/...

    sudo apt install python3.12-venv libxcb-cursor0 libzbar0


### Erstellen einer virtuellen Umgebung

Du solltest den Ordner auswählen, in dem Du DragonLog installieren möchtest. Ich nutze den persönlichen Ordner.

Öffne ein Terminal und wechsle in diesen Ordner. Dann erstellst Du die virtuelle Umgebung

    python3 -m venv dragonlog

Danach sollte ein Ordner `dragonlog` vorhanden sein.

Man kann DragonLog auch ohne virtuelle Umgebung installieren, wenn man evtl. Paketkollisionen mit anderen Projekten in kauf nimmt.


### DragonLog installieren

Wenn die virtuelle Umgebung initialisiert ist, nutze

    dragonlog/bin/pip install DragonLog[xlformat,qslqrcode]

Dies installiert DragonLog und alle Abhängigkeiten inklusive der Extras.

Unter macOS zsh muss der Teil `"DragonLog[...]"` in Anführungszeichen gesetzt werden, 
so dass die eckigen Klammern nicht interpretiert werden.


### DragonLog starten

Jetzt kannst Du DragonLog starten

    dragonlog/bin/DragonLog


### DragonLog aktualisieren

DragonLog kann nun ganz einfach aktualisiert werden

    dragonlog/bin/pip install DragonLog -U

