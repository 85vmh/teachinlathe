import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Qt5Compat.GraphicalEffects
import "."
import theme 1.0

Rectangle {
    id: root

    property url iconSource: ""
    property color tint: Theme.foregroundMuted
    property string text: ""
    property bool compact: false
    property bool iconOnRight: false
    property int buttonHeight: Theme.buttonHeightSmall
    property int iconSize: 20
    property int fontPixelSize: Theme.fontBody

    signal clicked()

    readonly property int hp: 8
    readonly property int vp: 6

    implicitHeight: buttonHeight
    implicitWidth: Math.max(90, Math.ceil(contentRow.implicitWidth) + hp * 2)
    Layout.preferredWidth: implicitWidth
    Layout.preferredHeight: implicitHeight

    radius: Theme.radius
    color: (enabled && area.pressed) ? Theme.accentSoft : "transparent"
    border.width: Theme.hairline
    border.color: enabled ? (area.pressed ? Theme.accentBorder : Theme.outlineStrong) : Theme.outlineDisabled
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
