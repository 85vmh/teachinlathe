import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import theme
import "define_radial_profile" as Radial
import common

Item {
    id: root
    anchors.fill: parent
    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place what the view shows comes from, and every edit goes to
    required property var editor
    readonly property var op: editor.operation
    readonly property var _undercut: op.undercut_parameters || ({})

    readonly property var workpiece: editor.workpiece || ({})
    readonly property var toolCard: editor.toolCard
    readonly property real p1X: Number(op.p1_x || 0)
    readonly property real p1Z: Number(op.p1_z || 0)
    readonly property string direction: op.finishing_direction || "towards_z_minus"
    readonly property bool addUndercut: !!op.add_undercut
    readonly property real undercutRadius: Number(_undercut.radius === undefined ? 0.4 : _undercut.radius)
    readonly property real undercutDepth: Number(_undercut.depth === undefined ? 0.4 : _undercut.depth)
    readonly property real undercutLength: Number(_undercut.length === undefined ? 2.5 : _undercut.length)

    // the profile of the turning it finishes, with the undercut when it has one
    readonly property var _parentProfile: editor.parentProfile || ({})
    readonly property string profileType: _parentProfile.profile_type || "od"
    readonly property var primitives: {
        var next = JSON.parse(JSON.stringify(_parentProfile.profile_primitives || []))
        if (addUndercut && next.length > 1) {
            next[1].blend = {
                type: "undercut_din509", chamfer_width: 0, fillet_radius: 0,
                undercut_radius: undercutRadius, undercut_depth: undercutDepth,
                undercut_length: undercutLength
            }
        }
        return next
    }

    readonly property var previewData: editor.preview
    signal openNumPadRequested(var field)

    // a change to the undercut: the whole undercut_parameters, as the
    // operation takes them
    function editUndercut(field, value) {
        var u = { radius: undercutRadius, depth: undercutDepth, length: undercutLength }
        u[field] = value
        editor.edit({ undercut_parameters: u })
    }

    // another operation: the drawing fitted to it
    onEditorChanged: profileCanvas.resetView()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        OperationHeader {
            id: header
            editor: root.editor
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
        }

        ProfileCanvas {
            id: profileCanvas
            Layout.fillWidth: true
            Layout.fillHeight: true
            showAxes: false
            showZeroLine: true
            selectable: false
            mirrorAcrossCenterline: true
            profileLineColor: "#6b7280"
            profileLineWidth: 1.5
            workpiece: root.workpiece
            primitives: root.primitives
            profileType: root.profileType
            roughingPreview: root.previewData ? {
                profile: root.previewData.profile,
                offset: [],
                feeds: root.previewData.feeds,
                rapids: root.previewData.rapids
            } : null
            fitInsetRight: fieldsScroll.width + tickBand
            fitPadding: 72
            markers: [{ x: root.p1X, z: root.p1Z, color: "#1565c0" }]

            OperationToolBox {
                editor: root.editor
                pickerWidth: root.width
                x: (profileCanvas.width - width) / 2
                y: 8
            }
            CanvasTool {
                id: canvasTool
                inset: profileCanvas.tickBand
                card: root.toolCard && root.toolCard.card ? root.toolCard.card : ""
                view: root.toolCard && root.toolCard.view ? root.toolCard.view : null
                pxPerMm: profileCanvas._scale
                tipX: profileCanvas._cx(root.p1Z)
                tipY: profileCanvas._cy(root.p1X)
            }
            fitExtraPositions: {
                if (!canvasTool.drawn) return []
                var points = canvasTool.outlineFromTip, result = []
                for (var i = 0; i < points.length; i++)
                    result.push({ x: root.p1X + 2 * points[i].y, z: root.p1Z + points[i].x })
                return result
            }
            onFitExtraPositionsChanged: if (!_manualView) _scheduleFit()
            Radial.GroovePointTag {
                point: 1
                axes: "XZ"
                x: profileCanvas._cx(root.p1Z) + 12
                y: profileCanvas._cy(root.p1X) - height - 12
            }

            Flickable {
                id: fieldsScroll
                width: fields.implicitWidth
                readonly property real edgePadding: profileCanvas.tickBand
                readonly property real fadeExtent: Theme.scrollFadeHeight * 2
                height: profileCanvas.height - 2 * edgePadding
                x: profileCanvas.width - width - edgePadding
                y: edgePadding
                contentWidth: width
                contentHeight: fields.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                readonly property var cards: [directionBox, p1Box, undercutCheck, undercutBox]
                function cardAtContentY(position) {
                    for (var i = 0; i < cards.length; i++) {
                        var card = cards[i]
                        if (card.visible && card.y < position && card.y + card.height > position)
                            return card
                    }
                    return null
                }
                readonly property var topCutCard: contentY > 0 ? cardAtContentY(contentY) : null
                readonly property var bottomCutCard: contentY + height < contentHeight
                    ? cardAtContentY(contentY + height) : null

                ColumnLayout {
                    id: fields
                    width: fieldsScroll.width
                    spacing: Theme.spacingSmall
                    TurningFinishDirectionBox {
                        id: directionBox
                        Layout.alignment: Qt.AlignRight
                        direction: root.direction
                        onDirectionEdited: function(value) { root.editor.edit({ finishing_direction: value }) }
                    }
                    TurningPointBox {
                        id: p1Box
                        Layout.alignment: Qt.AlignRight
                        point: 1
                        xValue: root.p1X; zValue: root.p1Z
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                        onFieldEdited: function(axis, value) {
                            root.editor.edit(axis === "x" ? { p1_x: value } : { p1_z: value })
                        }
                    }
                    ModelCheckBox {
                        id: undercutCheck
                        visible: root.editor.undercutAvailable
                        Layout.alignment: Qt.AlignRight
                        text: "Add DIN509 Undercut"
                        checked: root.addUndercut
                        font.pixelSize: Theme.fontBody
                        onToggledTo: function(on) { root.editor.edit({ add_undercut: on }) }
                    }
                    TurningUndercutBox {
                        id: undercutBox
                        visible: undercutCheck.visible && root.addUndercut
                        Layout.alignment: Qt.AlignRight
                        radius: root.undercutRadius; depth: root.undercutDepth; length: root.undercutLength
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                        onFieldEdited: function(field, value) { root.editUndercut(field, value) }
                    }
                }
            }

            Rectangle {
                visible: !!fieldsScroll.topCutCard
                x: fieldsScroll.x + (fieldsScroll.topCutCard ? fieldsScroll.topCutCard.x : 0)
                y: fieldsScroll.y
                width: fieldsScroll.topCutCard ? fieldsScroll.topCutCard.width : 0
                height: fieldsScroll.topCutCard
                    ? Math.min(fieldsScroll.fadeExtent,
                               fieldsScroll.topCutCard.y + fieldsScroll.topCutCard.height - fieldsScroll.contentY)
                    : 0
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0; color: Theme.surface }
                    GradientStop { position: 1; color: "transparent" }
                }
            }
            Rectangle {
                visible: !!fieldsScroll.bottomCutCard
                x: fieldsScroll.x + (fieldsScroll.bottomCutCard ? fieldsScroll.bottomCutCard.x : 0)
                width: fieldsScroll.bottomCutCard ? fieldsScroll.bottomCutCard.width : 0
                height: fieldsScroll.bottomCutCard
                    ? Math.min(fieldsScroll.fadeExtent,
                               fieldsScroll.contentY + fieldsScroll.height - fieldsScroll.bottomCutCard.y)
                    : 0
                y: fieldsScroll.y + fieldsScroll.height - height
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0; color: "transparent" }
                    GradientStop { position: 1; color: Theme.surface }
                }
            }
            CanvasViewButtons { canvas: profileCanvas; showMirror: false }
        }
    }
}
