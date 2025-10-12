Installationsanleitung
======================

Das Ziel ist hier, die Installation mittels Python PyPI zu unterstützen und insbesondere für zusätzlich benötigte Komponenten eine Hilfestellung zu leisten.

Die Installation mittels Installer oder Zip-Paket wird hier nicht geschildert, da dies selbsterklärend sein sollte.

Zuerst zeige ich die Installation unter Windows und anschließend für Linux. Die Installation in macOS sollte ähnlich zu Linux sein.


Installation unter Windows
--------------------------

Die Anleitung deckt folgende Schritte ab

1. Installation von Python
2. Erstellen einer virituellen Umgebung für DragonLog
3. Installation des DragonLog-Pakets
4. DragonLog starten
5. DragonLog aktualisieren


### Installation von Python

Für DragonLog wird Python >= 3.10 benötigt. 
Ich empfehle Python 3.12 und die Verwendung des Python Ínstallmanagers (pymanager) [python.org](https://www.python.org/downloads/). 


### Erstellen einer virituellen Umgebung

Du solltest in den Ordner auswählen in dem Du DragonLog installieren möchtest. Ich nutze den persönlichen Ordner.

Öffne ein Terminal und wechsle in diesen Ordner. Dann erstellst Du die virituelle Umgebung

    C:\Users\username> py -m venv DragonLog

Danach sollte ein Ordner `DragonLog` vorhanden sein.

Man kann DragonLog auch ohne virtuelle Umgebung installieren, wenn man evtl. Paketkollisionen mit anderen Projekten in kauf nimmt.


### DragonLog installieren

Wenn die virtuelle Umgebung initialisiert ist nutze

    C:\Users\username> DragonLog\Scripts\pip.exe install DragonLog[xlformat,qslqrcode]

Dies installiert DragonLog and alle Abhängigkeiten inklusive der Extras.


### DragonLog starten

Jetzt kannst Du DragonLog starten

    C:\Users\username> DragonLog\Scripts\DragonLog.exe

Oder Du kannst die ausfürbare Datei einfach Doppelklicken. In dem Fall stört wahrscheinlich das Terminalfenster und Du nutzt bessere `C:\Users\username\DragonLog\Scripts\DragonLogW.exe`.


### DragonLog aktualisieren

DragonLog kann nun ganz einfach aktualisiert werden

    C:\Users\username> DragonLog\Scripts\pip.exe install DragonLog -U



Installation unter Linux
------------------------

Die Anleitung deckt folgende Schritte ab

1. Installation von Python-Venv und benötigte Bibliotheken
2. Erstellen einer virituellen Umgebung für DragonLog
3. Installation des DragonLog-Pakets
4. DragonLog starten
5. DragonLog aktualisieren


### Installation von venv und Bibliotheken

Um DragonLog zu nutzen benötigst Du noch einige System-Pakete. `libzbar0` wird nur benötigt, wenn Du DragonLog mit der Erweiterung `qslqrcode` installaierst.

    # sudo apt install python3.12-venv libxcb-cursor0 libzbar0


### Erstellen einer virituellen Umgebung

Du solltest in den Ordner auswählen in dem Du DragonLog installieren möchtest. Ich nutze den persönlichen Ordner.

Öffne ein Terminal und wechsle in diesen Ordner. Dann erstellst Du die virituelle Umgebung

    # python3 -m venv dragonlog

Danach sollte ein Ordner `dragonlog` vorhanden sein.

Man kann DragonLog auch ohne virtuelle Umgebung installieren, wenn man evtl. Paketkollisionen mit anderen Projekten in kauf nimmt.


### DragonLog installieren

Wenn die virtuelle Umgebung initialisiert ist nutze

    # dragonlog/bin/pip install DragonLog[xlformat,qslqrcode]

Dies installiert DragonLog and alle Abhängigkeiten inklusive der Extras.


### DragonLog starten

Jetzt kannst Du DragonLog starten

    # dragonlog/bin/DragonLog


### DragonLog aktualisieren

DragonLog kann nun ganz einfach aktualisiert werden

    # dragonlog/bin/pip install DragonLog -U

