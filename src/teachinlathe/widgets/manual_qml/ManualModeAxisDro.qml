import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

RowLayout {
    id: root

    property string axisLabel: "X"
    property string primaryValue: "+0000.000"
    property string secondaryValue: "+0000.000"
    property bool secondaryVisible: false
    property string unit: "mm"

    signal primaryClicked()
    signal zeroClicked()
    signal absRelClicked()

    width: 1090
    height: 82
    spacing: 10

    Text {
        Layout.preferredWidth: 60
        Layout.preferredHeight: 82
        text: root.axisLabel
        font.family: "Liberation Sans Narrow"
        font.pixelSize: 80
        color: "#101010"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    Rectangle {
        Layout.preferredWidth: 132
        Layout.preferredHeight: 34
        visible: root.secondaryVisible
        radius: 6
        border.color: "#ccc"
        border.width: 1
        color: "#56babb"

        Text {
            anchors.fill: parent
            anchors.rightMargin: 7
            text: root.secondaryValue
            color: "#ffffff"
            font.family: "Noto Sans Mono"
            font.pixelSize: 21
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
        }
    }

    Item {
        Layout.preferredWidth: 132
        Layout.preferredHeight: 34
        visible: !root.secondaryVisible
    }

    Rectangle {
        Layout.preferredWidth: 316
        Layout.preferredHeight: 71
        radius: 6
        border.color: "#ccc"
        border.width: 1
        color: "#d9d9d9"

        Text {
            anchors.fill: parent
            anchors.rightMargin: 10
            text: root.primaryValue
            color: "#0a0a0a"
            font.family: "Noto Sans Mono"
            font.pixelSize: 52
            horizontalAlignment: Text.AlignRight
            verticalAlignment: Text.AlignVCenter
        }

        MouseArea {
            anchors.fill: parent
            onClicked: root.primaryClicked()
        }
    }

    Text {
        Layout.preferredWidth: 42
        Layout.preferredHeight: 71
        text: root.unit
        font.family: "Liberation Mono"
        font.pixelSize: 24
        color: "#101010"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    Button {
        Layout.preferredWidth: 72
        Layout.preferredHeight: 72
        text: "0"
        font.pixelSize: 18
        onClicked: root.zeroClicked()
    }

    Button {
        Layout.preferredWidth: 72
        Layout.preferredHeight: 72
        text: "A/R"
        font.pixelSize: 18
        onClicked: root.absRelClicked()
    }
}
