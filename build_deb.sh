#!/bin/bash

VERSION=$1

echo Preparing build directory...
cd build
rm -r dragonlog_*_linux_amd64
rm dragonlog_*_linux_amd64.deb
rm ../dist/dragonlog_*_linux_amd64.deb

echo Preparing package directory...
mkdir -p dragonlog_${VERSION}_linux_amd64/DEBIAN
mkdir -p dragonlog_${VERSION}_linux_amd64/opt

cp -R exe.linux-x86_64-3.11 dragonlog_${VERSION}_linux_amd64/opt/DragonLog
chown root:root -R dragonlog_${VERSION}_linux_amd64
SIZE=$(du -s dragonlog_${VERSION}_linux_amd64/opt/DragonLog | awk '{print $1}')

cat << EOF > dragonlog_${VERSION}_linux_amd64/DEBIAN/control
Package: DragonLog
Version: 0.2
Architecture: amd64
Maintainer: Andreas Schawo <andreas@schawo.de>
Section: hamradio
Depends: 
Installed-Size: $SIZE
Package-Type: deb
Homepage: https://github.com/gitandy/DragonLog
Description: QSO logging for hamradio
 DragonLog is a logging program to log hamradio QSOs. 
 Beside logging for ham radio you can also log CB radio QSOs.
EOF

dpkg -b dragonlog_${VERSION}_linux_amd64

mv dragonlog_*_linux_amd64.deb ../dist
