import QtQuick 2.15
import "../app_shell_qml" as Shell
import theme 1.0

// One chuck / fixture. Selecting it makes it the active fixture, which is what
// sets the chuck Z-minus limit the machine is held to.
Rectangle {
    id: root

    property var fixture: null
    property bool active: fixture ? fixture.active : false
    signal selected(int index)
    signal teachRequested()

    width: 200
    height: 240
    radius: Theme.radiusLarge
    color: active ? Theme.accentSoft : "white"
    border.width: active ? 2 : 1
    border.color: active ? Theme.primary : Theme.separator

    MouseArea {
        anchors.fill: parent
        onClicked: if (root.fixture) root.selected(root.fixture.index)
    }

    Column {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        Image {
            width: parent.width
            height: 90
            fillMode: Image.PreserveAspectFit
            source: root.fixture && root.fixture.imageUrl
                    ? "file://" + root.fixture.imageUrl : ""
            visible: source != ""
        }

        Text {
            width: parent.width
            text: root.fixture ? root.fixture.description : ""
            font.pixelSize: Theme.fontSmall
            font.bold: true
            color: Theme.foreground
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }

        Text {
            text: {
                if (!root.fixture || root.fixture.diameter === "") return ""
                return "Ø " + root.fixture.diameter + " " + root.fixture.units
            }
            font.pixelSize: Theme.fontSmall
            color: Theme.keySurface
            visible: text !== ""
        }

        Text {
            text: root.fixture ? "Max " + root.fixture.maxRpm + " rpm" : ""
            font.pixelSize: Theme.fontSmall
            color: Theme.keySurface
        }

        Text {
            text: root.fixture
                  ? "Z− limit " + root.fixture.zMinusLimit.toFixed(3)
                  : ""
            font.pixelSize: Theme.fontSmall
            color: Theme.keySurface
        }

        Shell.ShellActionButton {
            text: "Teach Z−"
            secondary: true
            width: parent.width
            // Only the active fixture's limit can be taught: teaching sets it
            // from where the machine is standing now.
            enabled: root.active
            onClicked: root.teachRequested()
        }
    }
}
