// dungeonOS login screen for SDDM: the desktop wallpaper, and panels framed like waybar
// and the Hyprland windows (bronze line, dark band, drop shadow). Preview it with
//   ~/Dotfiles/sddm/install.sh --preview
import QtQuick 2.15

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#1A1816"

    // dungeonOS palette
    readonly property color bg:       "#1A1816"
    readonly property color bgDark:   "#141210"
    readonly property color band:     "#463D34"
    readonly property color bronze:   "#7E705D"
    readonly property color fg:       "#C8B8A0"
    readonly property color fgMuted:  "#9D8E7C"
    readonly property color comment:  "#6F675E"
    readonly property color brass:    "#A88A5B"
    readonly property color rust:     "#7B4A3E"
    readonly property color moss:     "#6E7F5A"

    // the login screen runs as its own user, so the fonts travel with the theme
    FontLoader { id: cloister; source: "fonts/CloisterBlack.ttf" }
    readonly property string iconFont: "Symbols Nerd Font"

    // ------------------------------------------------------------- framed panel
    component Panel: Item {
        default property alias content: inner.data
        property int pad: 28
        implicitWidth: inner.childrenRect.width + 2 * (pad + 4)
        implicitHeight: inner.childrenRect.height + 2 * (pad + 4)

        // drop shadow like the windows': dark at the edge, gone by ~10px
        Rectangle { anchors.fill: parent; anchors.margins: -8; color: "#1a1a1a"; opacity: 0.12 }
        Rectangle { anchors.fill: parent; anchors.margins: -5; color: "#1a1a1a"; opacity: 0.22 }
        Rectangle { anchors.fill: parent; anchors.margins: -2; color: "#1a1a1a"; opacity: 0.45 }

        Rectangle {            // 1px bronze line
            anchors.fill: parent
            color: root.bg
            border.color: root.bronze
            border.width: 1
            Rectangle {        // 3px band
                anchors.fill: parent
                anchors.margins: 1
                color: "transparent"
                border.color: root.band
                border.width: 3
            }
        }
        Item {
            id: inner
            x: pad + 4
            y: pad + 4
            width: childrenRect.width
            height: childrenRect.height
        }
    }

    // ----------------------------------------------------------- text field
    component Field: Rectangle {
        property alias text: input.text
        property alias input: input
        property string placeholder: ""
        property bool secret: false
        width: 360
        height: 52
        color: root.bgDark
        border.width: 1
        border.color: input.activeFocus ? root.brass : root.band

        TextInput {
            id: input
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            verticalAlignment: TextInput.AlignVCenter
            color: root.fg
            selectionColor: root.band
            font.family: cloister.name
            font.pixelSize: 26
            echoMode: secret ? TextInput.Password : TextInput.Normal
            passwordCharacter: "•"
            clip: true
        }
        Text {
            anchors.fill: input
            verticalAlignment: Text.AlignVCenter
            visible: input.text.length === 0
            text: parent.placeholder
            color: root.comment
            font: input.font
        }
    }

    // ------------------------------------------------------------- background
    Image {
        anchors.fill: parent
        source: config.background
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
    }

    // sessions (Hyprland, ...) and users, read through Repeaters so we can get their names
    QtObject {
        id: sessions
        property int currentIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
        readonly property int count: sessionRepeater.count
        readonly property string currentName: {
            // mention count so this updates once the list has filled in
            var it = sessionRepeater.count > 0 ? sessionRepeater.itemAt(currentIndex) : null
            return it ? it.sessionName : ""
        }
    }
    Item {
        visible: false
        Repeater { id: sessionRepeater; model: sessionModel; Item { property string sessionName: model.name } }
        Repeater { id: userRepeater; model: userModel; Item { property string userName: model.name } }
    }
    // last user who logged in, or else the first user on the system
    readonly property string defaultUser: userModel.lastUser !== "" ? userModel.lastUser
        : (userRepeater.count > 0 && userRepeater.itemAt(0) ? userRepeater.itemAt(0).userName : "")

    function doLogin() {
        message.text = ""
        sddm.login(user.text, password.text, sessions.currentIndex)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            message.text = "Login failed"
            password.text = ""
            password.input.forceActiveFocus()
        }
    }

    // ---------------------------------------------------------- login panel
    Panel {
        id: loginPanel
        anchors.centerIn: parent

        Column {
            spacing: 14

            Text {
                id: clock
                anchors.horizontalCenter: parent.horizontalCenter
                color: root.brass
                font.family: cloister.name
                font.pixelSize: 96
                text: Qt.formatTime(new Date(), "HH:mm")
            }
            Text {
                id: date
                anchors.horizontalCenter: parent.horizontalCenter
                color: root.fgMuted
                font.family: cloister.name
                font.pixelSize: 28
                text: Qt.formatDate(new Date(), "dddd, d MMMM")
            }
            Timer {
                interval: 1000; running: true; repeat: true
                onTriggered: {
                    clock.text = Qt.formatTime(new Date(), "HH:mm")
                    date.text = Qt.formatDate(new Date(), "dddd, d MMMM")
                }
            }

            Item { width: 1; height: 10 }

            Field {
                id: user
                placeholder: "Username"
                text: root.defaultUser
                input.onAccepted: password.input.forceActiveFocus()
            }
            Field {
                id: password
                placeholder: "Password"
                secret: true
                input.onAccepted: root.doLogin()
                Component.onCompleted: input.forceActiveFocus()
            }

            // session picker:  ‹ Hyprland ›
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 18
                Text {
                    text: "‹"; color: prevArea.containsMouse ? root.brass : root.comment
                    font.family: cloister.name; font.pixelSize: 30
                    MouseArea { id: prevArea; anchors.fill: parent; hoverEnabled: true
                        onClicked: sessions.currentIndex = (sessions.currentIndex + sessions.count - 1) % sessions.count }
                }
                Text {
                    text: sessions.currentName
                    color: root.fg
                    font.family: cloister.name; font.pixelSize: 26
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: "›"; color: nextArea.containsMouse ? root.brass : root.comment
                    font.family: cloister.name; font.pixelSize: 30
                    MouseArea { id: nextArea; anchors.fill: parent; hoverEnabled: true
                        onClicked: sessions.currentIndex = (sessions.currentIndex + 1) % sessions.count }
                }
            }

            Text {
                id: message
                anchors.horizontalCenter: parent.horizontalCenter
                height: text.length > 0 || capsNote.visible ? implicitHeight : 0
                color: root.rust
                font.family: cloister.name
                font.pixelSize: 24
                text: ""
            }
            Text {
                id: capsNote
                anchors.horizontalCenter: parent.horizontalCenter
                visible: keyboard.capsLock
                color: root.brass
                font.family: cloister.name
                font.pixelSize: 22
                text: "Caps Lock is on"
            }
        }
    }

    // ---------------------------------------------------------- power panel
    Panel {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 10
        pad: 10

        Row {
            spacing: 6
            Repeater {
                // suspend, reboot (nerd-font icons), power off: the ♰ cross from the fish greeting
                model: ["\uDB81\uDCB2", "\uDB81\uDF09", "\u2670"]
                delegate: Rectangle {
                    width: 52; height: 46
                    color: area.containsMouse ? (index === 2 ? root.rust : root.band) : "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        color: area.containsMouse ? root.fg : (index === 2 ? root.rust : root.fgMuted)
                        // the cross is drawn in the same font kitty uses for it in the greeting
                        font.family: index === 2 ? "DejaVu Sans Mono" : root.iconFont
                        font.pixelSize: index === 2 ? 25 : 24   // cross matches the waybar power button (25px)
                    }
                    MouseArea {
                        id: area; anchors.fill: parent; hoverEnabled: true
                        onClicked: index === 0 ? sddm.suspend() : index === 1 ? sddm.reboot() : sddm.powerOff()
                    }
                }
            }
        }
    }
}
