// ProfilingTypeBox.qml — how a profile is roughed (pass type), laid over the
// profile canvas. The angled passes are offered for ID profiles only, in a
// second column, and after them the button that opens their angle: the box
// grows down to show a slider for it, the canvas's passes following it.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

CanvasBox {
    id: root
    accent: Theme.foregroundStrong

    property string profilingType: "od"   // from the profile
    // "axial" | "radial" | "diagonal_interior" | "diagonal_exterior"
    property string passType: "axial"
    // the angled passes' angle, from the Z axis, in degrees, and the angles
    // it may be (editor.diagonalAngleRange)
    property real diagonalAngle: 45
    property var diagonalAngleRange: [30, 60]

    signal passTypeEdited(string value)
    signal diagonalAngleEdited(real value)

    // how long the angle's panel takes to open, and to close
    readonly property int anglePanelDuration: 250
    // the angled passes, and their angle, are an ID profile's only
    readonly property bool _isId: profilingType === "id"
    // view state: the angle's panel open, under the passes
    property bool _anglePanelOpen: false

    component PassButton: ModelRadioButton {
        property string value
        font.pixelSize: Theme.fontBody
        checked: root.passType === value
        onChosen: root.passTypeEdited(value)
    }

    // An angled pass's button: its angle in its text, as wide as the widest
    // angle in the range needs - the box keeps its width as the angle changes.
    component AngledPassButton: PassButton {
        // the way it cuts, after its angle
        property string arrow
        // the widest of its texts over the range: worked out again only
        // with the range
        readonly property real widestText: root._widestAngledText(arrow)
        text: root._angledText(root.diagonalAngle, arrow)
        Layout.minimumWidth: implicitWidth - passFont.advanceWidth(text) + widestText
    }

    FontMetrics { id: passFont; font.pixelSize: Theme.fontBody }

    function _angledText(angle, arrow) { return Math.round(angle) + "° Passes " + arrow }

    // the width of the widest of an angled pass's texts, over the range
    function _widestAngledText(arrow) {
        var widest = 0
        for (var a = Math.ceil(diagonalAngleRange[0]); a <= diagonalAngleRange[1]; a++)
            widest = Math.max(widest, passFont.advanceWidth(_angledText(a, arrow)))
        return widest
    }

    // the passes, and under them the angle's panel: opening, it grows the
    // box down from its bottom, pushing the boxes under it down
    ColumnLayout {
        spacing: 0

        // the straight passes; beside them, for an ID profile only, the
        // angled ones, their arrows pointing the way they go: up-left toward
        // the interior, down-right toward the exterior - then, past a line,
        // the button that opens their angle (a check while it is open)
        RowLayout {
            spacing: Theme.spacingLarge

            ColumnLayout {
                Layout.alignment: Qt.AlignTop
                spacing: Theme.spacingSmall
                PassButton { value: "axial";  text: "Axial Passes" }
                PassButton { value: "radial"; text: "Radial Passes" }
            }

            ColumnLayout {
                visible: root._isId
                Layout.alignment: Qt.AlignTop
                spacing: Theme.spacingSmall
                AngledPassButton { value: "diagonal_interior"; arrow: "\u2196" }
                AngledPassButton { value: "diagonal_exterior"; arrow: "\u2198" }
            }

            Divider {
                visible: root._isId
            }

            // an angle, alone, as Edit Profile's icon is drawn
            OperationIconTextButton {
                visible: root._isId
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: Theme.buttonHeight
                iconSource: Images.url(root._anglePanelOpen ? "check.svg" : "angle.svg")
                compact: true
                tint: Theme.success
                color: Theme.surface
                buttonHeight: Theme.buttonHeight
                iconSize: 28
                onClicked: root._anglePanelOpen = !root._anglePanelOpen
            }
        }

        // the angle's panel: a line across, then the slider; its height opens
        // from none, what is in it cut off at its bottom on the way
        Item {
            id: anglePanel
            visible: Layout.preferredHeight > 0
            Layout.fillWidth: true
            Layout.preferredHeight: root._isId && root._anglePanelOpen ? angleContent.implicitHeight : 0
            Behavior on Layout.preferredHeight {
                NumberAnimation { duration: root.anglePanelDuration; easing.type: Easing.InOutCubic }
            }
            clip: true

            ColumnLayout {
                id: angleContent
                width: parent.width
                spacing: 0

                Divider {
                    Layout.topMargin: Theme.spacingSmall
                    orientation: Qt.Horizontal
                }

                AngleSlider {
                    Layout.topMargin: Theme.spacing
                    Layout.fillWidth: true
                    from: root.diagonalAngleRange[0]
                    to: root.diagonalAngleRange[1]
                    value: root.diagonalAngle
                    onValueEdited: function(value) { root.diagonalAngleEdited(value) }
                }
            }
        }
    }
}
