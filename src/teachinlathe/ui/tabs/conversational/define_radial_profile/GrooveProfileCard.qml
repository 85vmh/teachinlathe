// GrooveProfileCard.qml — a groove in the list, as its four points' boxes
// (GroovePointBox): its bottom's two corners on top - P3 bottom left, P2
// bottom right - and its flanks' starts under them - P4 the left flank's,
// P1 the right flank's. Between each pair, two buttons that copy one side
// onto the other, mirrored: the flanks' angle and blend, the bottom's
// diameter and blend.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common
import tabs.programs as Programs

Rectangle {
    id: root

    property var primData: ({})
    property int primIdx: 0
    property bool isSelected: false

    signal primUpdated(int idx, var data)
    signal openNumPadRequested(var field)
    signal tapped()

    // selected: its border alone
    color: Theme.surfaceAlt
    radius: Theme.radiusLarge
    border.color: isSelected ? Theme.accent : Theme.outline
    border.width: isSelected ? 2 : 1
    implicitWidth: content.implicitWidth + 24
    height: content.implicitHeight + 24

    TapHandler { onTapped: root.tapped() }

    // the box of point ``point`` (1..4) flashed, its tag on the canvas tapped
    function flashPoint(point) {
        var box = [p1Box, p2Box, p3Box, p4Box][point - 1]
        if (box)
            box.flash()
    }

    function _clone() {
        var d = JSON.parse(JSON.stringify(primData || {}))
        d.type = "groove"
        if (!d.right_flank) d.right_flank = {}
        if (!d.bottom) d.bottom = {}
        if (!d.left_flank) d.left_flank = {}
        if (!d.right_flank.start_blend) d.right_flank.start_blend = _emptyBlend()
        if (!d.bottom.blend_right) d.bottom.blend_right = _emptyBlend()
        if (!d.bottom.blend_left) d.bottom.blend_left = _emptyBlend()
        if (!d.left_flank.start_blend) d.left_flank.start_blend = _emptyBlend()
        return d
    }

    function _emptyBlend() {
        return { type: "none", chamfer_width: 0, fillet_radius: 0 }
    }

    function _value(section, key, fallback) {
        return primData && primData[section] && primData[section][key] !== undefined
            ? Number(primData[section][key])
            : fallback
    }

    function _blend(section, key) {
        return primData && primData[section] && primData[section][key]
            ? primData[section][key]
            : _emptyBlend()
    }

    function _commit(section, key, value) {
        var d = _clone()
        d[section][key] = Number(value)
        root.primUpdated(primIdx, d)
    }

    function _commitBlend(section, key, blendType, chamferWidth, filletRadius) {
        var d = _clone()
        d[section][key] = { type: blendType, chamfer_width: chamferWidth, fillet_radius: filletRadius }
        root.primUpdated(primIdx, d)
    }

    // the flanks: the angle and the start blend of one copied onto the other
    function _mirrorFlanks(toRight) {
        var d = _clone()
        var from = toRight ? d.left_flank : d.right_flank
        var to = toRight ? d.right_flank : d.left_flank
        to.angle = from.angle !== undefined ? Number(from.angle) : 0
        to.start_blend = JSON.parse(JSON.stringify(from.start_blend))
        root.primUpdated(primIdx, d)
    }

    // the bottom: one corner's diameter and blend copied onto the other's
    function _mirrorBottom(toRight) {
        var b = _clone()
        var d = b.bottom
        if (toRight) {
            d.x_end_right = d.x_end_left !== undefined ? Number(d.x_end_left) : 0
            d.blend_right = JSON.parse(JSON.stringify(d.blend_left))
        } else {
            d.x_end_left = d.x_end_right !== undefined ? Number(d.x_end_right) : 0
            d.blend_left = JSON.parse(JSON.stringify(d.blend_right))
        }
        root.primUpdated(primIdx, b)
    }

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 10

        Label {
            text: (primIdx + 1) + ". Groove"
            font.pixelSize: Theme.fontBody
            font.bold: true
        }

        Rectangle {
            Layout.fillWidth: true
            height: Theme.hairline
            color: Theme.separator
        }

        // the boxes in two columns, the mirror buttons between them
        GridLayout {
            Layout.fillWidth: true
            columns: 3
            columnSpacing: Theme.spacing
            rowSpacing: Theme.spacingSmall

            SideLabel { text: "Bottom Left" }
            Item { Layout.preferredWidth: 1 }
            SideLabel { text: "Bottom Right" }

            GroovePointBox {
                id: p3Box
                Layout.fillWidth: true
                point: 3
                flankStart: false
                xValue: root._value("bottom", "x_end_left", 20)
                blend: root._blend("bottom", "blend_left")
                settingPrefix: "radial_profile.p3"
                onClicked: root.tapped()
                onFieldEdited: function(key, value) { root._commit("bottom", "x_end_left", value) }
                onBlendEdited: function(blendType, chamferWidth, filletRadius) {
                    root._commitBlend("bottom", "blend_left", blendType, chamferWidth, filletRadius)
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }
            MirrorButtons {
                onMirrorRequested: function(toRight) { root._mirrorBottom(toRight) }
            }
            GroovePointBox {
                id: p2Box
                Layout.fillWidth: true
                point: 2
                flankStart: false
                xValue: root._value("bottom", "x_end_right", 20)
                blend: root._blend("bottom", "blend_right")
                settingPrefix: "radial_profile.p2"
                onClicked: root.tapped()
                onFieldEdited: function(key, value) { root._commit("bottom", "x_end_right", value) }
                onBlendEdited: function(blendType, chamferWidth, filletRadius) {
                    root._commitBlend("bottom", "blend_right", blendType, chamferWidth, filletRadius)
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // the flanks a row apart from the bottom
            SideLabel { text: "Left Flank"; Layout.topMargin: Theme.spacingLarge }
            Item { Layout.preferredWidth: 1 }
            SideLabel { text: "Right Flank"; Layout.topMargin: Theme.spacingLarge }

            GroovePointBox {
                id: p4Box
                Layout.fillWidth: true
                point: 4
                flankStart: true
                xValue: root._value("left_flank", "x_start", 30)
                zValue: root._value("left_flank", "z_start", -5)
                angleValue: root._value("left_flank", "angle", 0)
                blend: root._blend("left_flank", "start_blend")
                settingPrefix: "radial_profile.p4"
                onClicked: root.tapped()
                onFieldEdited: function(key, value) {
                    root._commit("left_flank", key === "x" ? "x_start" : key === "z" ? "z_start" : "angle", value)
                }
                onBlendEdited: function(blendType, chamferWidth, filletRadius) {
                    root._commitBlend("left_flank", "start_blend", blendType, chamferWidth, filletRadius)
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }
            MirrorButtons {
                onMirrorRequested: function(toRight) { root._mirrorFlanks(toRight) }
            }
            GroovePointBox {
                id: p1Box
                Layout.fillWidth: true
                point: 1
                flankStart: true
                xValue: root._value("right_flank", "x_start", 30)
                zValue: root._value("right_flank", "z_start", 0)
                angleValue: root._value("right_flank", "angle", 0)
                blend: root._blend("right_flank", "start_blend")
                settingPrefix: "radial_profile.p1"
                onClicked: root.tapped()
                onFieldEdited: function(key, value) {
                    root._commit("right_flank", key === "x" ? "x_start" : key === "z" ? "z_start" : "angle", value)
                }
                onBlendEdited: function(blendType, chamferWidth, filletRadius) {
                    root._commitBlend("right_flank", "start_blend", blendType, chamferWidth, filletRadius)
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }
        }
    }

    // centred over its box
    component SideLabel: Label {
        Layout.alignment: Qt.AlignHCenter
        font.pixelSize: Theme.fontSmall
        font.bold: true
    }

    // Copy the left box onto the right one, mirrored, or the right onto the
    // left: the profile's mirror turned a quarter clockwise - its arrow over
    // it going left to right - and that flipped left to right. Pressed, not
    // switched on.
    component MirrorButtons: Column {
        id: mirrors
        signal mirrorRequested(bool toRight)

        Layout.alignment: Qt.AlignVCenter
        // as far apart as the fields in the boxes (GroovePointBox)
        spacing: 20

        Programs.BackplotIconButton {
            id: toRightButton
            iconSource: Images.url("mirror.svg")
            transform: Rotation {
                origin.x: toRightButton.width / 2
                origin.y: toRightButton.height / 2
                angle: 90
            }
            onClicked: mirrors.mirrorRequested(true)
        }
        Programs.BackplotIconButton {
            id: toLeftButton
            iconSource: Images.url("mirror.svg")
            transform: [
                Rotation {
                    origin.x: toLeftButton.width / 2
                    origin.y: toLeftButton.height / 2
                    angle: 90
                },
                Scale {
                    origin.x: toLeftButton.width / 2
                    origin.y: toLeftButton.height / 2
                    xScale: -1
                }
            ]
            onClicked: mirrors.mirrorRequested(false)
        }
    }
}
