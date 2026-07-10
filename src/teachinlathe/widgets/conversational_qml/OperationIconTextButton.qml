import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.0
import "."

Rectangle {
    id: root

    property url iconSource: ""
    property color tint: "#4F4F4F"
    property string text: ""
    property bool compact: false
    property bool iconOnRight: false
    property int buttonHeight: 36
    property int iconSize: 20
    property int fontPixelSize: Theme.fontSizeNormal

    signal clicked()

    readonly property int hp: 8
    readonly property int vp: 6

    implicitHeight: buttonHeight
    implicitWidth: Math.max(90, Math.ceil(contentRow.implicitWidth) + hp * 2)
    Layout.preferredWidth: implicitWidth
    Layout.preferredHeight: implicitHeight

    radius: 6
    color: (enabled && area.pressed) ? "#e1f0ff" : "transparent"
    border.width: 1
    border.color: enabled ? (area.pressed ? "#8ec5ff" : "#BDBDBD") : "#E0E0E0"
    opacity: enabled ? 1.0 : 0.35

    RowLayout {
        id: contentRow
        anchors.fill: parent
        anchors.leftMargin: root.hp
        anchors.rightMargin: root.hp
        anchors.topMargin: root.vp
        anchors.bottomMargin: root.vp
        spacing: 6
        layoutDirection: root.iconOnRight ? Qt.RightToLeft : Qt.LeftToRight

        Item {
            id: iconWrap
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: root.iconSize
            Layout.preferredHeight: root.iconSize
            visible: root.iconSource !== ""

            Image {
                id: baseImg
                anchors.fill: parent
                source: root.iconSource
                opacity: 0
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            ColorOverlay {
                anchors.fill: baseImg
                source: baseImg
                color: root.tint
            }
        }

        Label {
            visible: !root.compact
            text: root.text
            color: root.tint
            Layout.alignment: Qt.AlignVCenter
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: root.fontPixelSize
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        enabled: root.enabled
        onClicked: root.clicked()
    }
}
