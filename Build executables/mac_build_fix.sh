#!/bin/bash

APP_NAME="imzML_Writer"

cd dist/$APP_NAME.app/Contents/MacOS
mv $APP_NAME ${APP_NAME}_cli

cat << EOF > $APP_NAME
#!/bin/bash
# This is the launcher for OSX, this way the app will be opened
# when you double click it from the apps folder
open -n /Applications/${APP_NAME}.app/Contents/MacOS/${APP_NAME}_cli
EOF

chmod +x $APP_NAME
