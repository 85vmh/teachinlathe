import QtQuick 2.15
import "../app_shell_qml" as Shell

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
    radius: 8
    color: active ? "#e6edf7" : "white"
    border.width: active ? 2 : 1
    border.color: active ? "#2d7d46" : "#d5dbe4"

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
            font.pixelSize: 14
            font.bold: true
            color: "#1e2430"
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }

        Text {
            text: {
                if (!root.fixture || root.fixture.diameter === "") return ""
                return "Ø " + root.fixture.diameter + " " + root.fixture.units
            }
            font.pixelSize: 13
            color: "#55606f"
            visible: text !== ""
        }

        Text {
            text: root.fixture ? "Max " + root.fixture.maxRpm + " rpm" : ""
            font.pixelSize: 13
            color: "#55606f"
        }

        Text {
            text: root.fixture
                  ? "Z− limit " + root.fixture.zMinusLimit.toFixed(3)
                  : ""
            font.pixelSize: 13
            color: "#55606f"
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
