import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property string axisLabel: "X"
    property string primaryValue: "+0000.000"
    property string secondaryValue: "+0000.000"
    property bool secondaryVisible: false
    property bool setDatumVisible: false
    property string unit: "mm"

    signal primaryClicked()
    signal zeroClicked()
    signal absRelClicked()
    signal setDatumClicked()

    width: 1090
    height: 82

    readonly property int gap: 10
    readonly property int axisWidth: 60
    readonly property int valueLeft: axisWidth + gap
    readonly property int primaryLeft: valueLeft + secondaryWidth + gap
    readonly property int buttonSize: 72
    readonly property int datumButtonWidth: 108
    readonly property int primaryWidth: 316
    readonly property int primaryHeight: 71
    readonly property int secondaryWidth: 132
    readonly property int secondaryHeight: 34
    readonly property int unitWidth: 42
    readonly property int rightButtonSpacing: 18
    readonly property int setDatumButtonSpacing: 26

    Text {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: root.axisWidth
        height: parent.height
        text: root.axisLabel
        font.family: "Liberation Sans Narrow"
        font.pixelSize: 80
        color: "#101010"
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
    }

    Rectangle {
        id: secondaryBox
        anchors.left: parent.left
        anchors.leftMargin: root.valueLeft
        anchors.top: parent.top
        anchors.topMargin: 10
        width: root.secondaryWidth
        height: root.secondaryHeight
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
        anchors.left: parent.left
        anchors.leftMargin: root.valueLeft
        anchors.top: parent.top
        anchors.topMargin: 4
        width: root.secondaryWidth
        height: root.secondaryHeight
        visible: !root.secondaryVisible
    }

    Rectangle {
        id: primaryBox
        anchors.left: parent.left
        anchors.leftMargin: root.primaryLeft
        anchors.verticalCenter: parent.verticalCenter
        width: root.primaryWidth
        height: root.primaryHeight
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
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
        }

        MouseArea {
            anchors.fill: parent
            onClicked: root.primaryClicked()
        }
    }

    Text {
        anchors.left: primaryBox.right
        anchors.leftMargin: root.gap
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        width: root.unitWidth
        height: 30
        text: root.unit
        font.family: "Liberation Mono"
        font.pixelSize: 24
        color: "#101010"
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignBottom
    }

    Button {
        id: zeroButton
        anchors.right: absRelButton.left
        anchors.rightMargin: root.rightButtonSpacing
        anchors.verticalCenter: parent.verticalCenter
        width: root.buttonSize
        height: root.buttonSize
        text: "0"
        font.pixelSize: 18
        onClicked: root.zeroClicked()
    }

    Button {
        id: absRelButton
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: root.buttonSize
        height: root.buttonSize
        text: "A/R"
        font.pixelSize: 18
        onClicked: root.absRelClicked()
    }

    Button {
        id: datumButton
        visible: root.setDatumVisible
        anchors.right: zeroButton.left
        anchors.rightMargin: root.setDatumButtonSpacing
        anchors.verticalCenter: parent.verticalCenter
        width: root.datumButtonWidth
        height: root.buttonSize
        text: "Set\nDatum"
        font.pixelSize: 16
        onClicked: root.setDatumClicked()
    }
}
