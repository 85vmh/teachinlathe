import QtQuick 2.15
import theme 1.0

// The spindle direction a cutting tool is used with: two square icon
// buttons, M3 then M4, as tall as an input field, the chosen one blue as
// the editors' other toggles have it.
// `clockwise` is M3.
Row {
    id: root

    property var clockwise: null        // true M3, false M4, null neither
    //: The only direction allowed - a drill's or a tap's twist decides it:
    //: true M3, false M4. null allows both. The other button is disabled.
    property var onlyClockwise: null

    signal picked(bool clockwise)

    // Far enough apart that a finger picks one, not both.
    spacing: Theme.margin

    Repeater {
        model: [{ icon: "icons/spindle_m3.svg", clockwise: true },
                { icon: "icons/spindle_m4.svg", clockwise: false }]
        delegate: Rectangle {
            readonly property bool chosen: root.clockwise === modelData.clockwise
            readonly property bool allowed: root.onlyClockwise === null
                                            || root.onlyClockwise === undefined
                                            || root.onlyClockwise === modelData.clockwise
            width: Theme.inputHeight
            height: Theme.inputHeight
            radius: Theme.radius
            color: chosen ? Theme.selection : Theme.surface
            border.color: chosen ? Theme.accent : Theme.outline
            border.width: chosen ? 2 : 1
            opacity: allowed ? 1.0 : 0.35

            Image {
                anchors.centerIn: parent
                // Inside the chosen one's 2 px border, no more; the SVG is
                // square, so its ratio is kept either way.
                width: parent.height - 4
                height: width
                source: Qt.resolvedUrl(modelData.icon)
                sourceSize.width: width
                sourceSize.height: height
                fillMode: Image.PreserveAspectFit
                smooth: true
            }
            MouseArea {
                anchors.fill: parent
                enabled: parent.allowed
                onClicked: root.picked(modelData.clockwise)
            }
        }
    }
}
