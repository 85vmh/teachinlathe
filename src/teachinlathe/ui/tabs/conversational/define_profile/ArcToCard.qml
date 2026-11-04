// ArcToCard.qml
import QtQuick
import QtQuick.Layouts
import theme
import common

PrimitiveCard {
    id: root

    iconName: "arc_to.svg"

    readonly property color clrDirBtnActiveBg: "#e3f2fd"
    readonly property int   szBtn:             50
    readonly property int   szBtnIcon:         36
    readonly property int   szBtnIconSrc:      112
    readonly property real  defaultRadius:     10

    ColumnLayout {
        spacing: CardMetrics.rowGap
        Layout.fillWidth: true

        RowLayout {
            spacing: 0
            Layout.fillWidth: true

            FieldCell {
                label: "Direction"
                // as wide as an input, one button at either end of it
                RowLayout {
                    spacing: CardMetrics.inputWidth - 2 * root.szBtn
                    Layout.preferredWidth: CardMetrics.inputWidth
                    DirectionButton { direction: "cw"; icon: "cw_arrrow.svg" }
                    DirectionButton { direction: "ccw"; icon: "ccw_arrow.svg" }
                }
            }
            ArcField { label: "Radius"; field: "arc_radius"; fallback: root.defaultRadius; description: "Arc radius" }
        }

        RowLayout {
            spacing: 0
            Layout.fillWidth: true

            ArcField { label: "X Center"; field: "x_center"; description: "Arc Center on X" }
            ArcField { label: "Z Center"; field: "z_center"; description: "Arc Center on Z" }
        }

        RowLayout {
            spacing: 0
            Layout.fillWidth: true

            ArcField { label: "X End"; field: "x_end"; description: "Arc End on X" }
            ArcField { label: "Z End"; field: "z_end"; description: "Arc End on Z" }
        }
    }

    component ArcField: ProfileField {
        id: cell

        property string field: ""
        property real fallback: 0

        settingName: "at." + root.primIdx + "." + field
        value: root.primData[field] !== undefined ? root.primData[field] : fallback
        onOpenRequested: function(numpadField) { root.openNumPadRequested(numpadField) }
        onCommitted: function(committedValue) {
            var d = JSON.parse(JSON.stringify(root.primData))
            d[cell.field] = committedValue
            root.primUpdated(root.primIdx, d)
        }
    }

    component DirectionButton: Rectangle {
        id: directionButton

        property string direction: ""
        property string icon: ""
        readonly property bool _active: root.primData.direction === direction

        implicitWidth: root.szBtn; implicitHeight: root.szBtn; radius: CardMetrics.radius
        color:   _active ? root.clrDirBtnActiveBg : (directionMouse.pressed ? Theme.accentSoft : "transparent")
        border.width: Theme.hairline
        border.color: _active ? Theme.accentStrong : (directionMouse.pressed ? Theme.accentBorder : Theme.outlineStrong)

        Image {
            anchors.centerIn: parent; width: root.szBtnIcon; height: root.szBtnIcon
            sourceSize.width: root.szBtnIconSrc; sourceSize.height: root.szBtnIconSrc
            source: Images.url(directionButton.icon)
            fillMode: Image.PreserveAspectFit; smooth: true
        }
        MouseArea {
            id: directionMouse; anchors.fill: parent
            onClicked: {
                var d = JSON.parse(JSON.stringify(root.primData))
                d.direction = directionButton.direction
                root.primUpdated(root.primIdx, d)
            }
        }
    }
}
