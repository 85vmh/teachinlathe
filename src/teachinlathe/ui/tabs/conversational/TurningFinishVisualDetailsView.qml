import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import theme
import "define_radial_profile" as Radial

Item {
    id: root
    anchors.fill: parent
    property var editor: null
    property int opIndex: -1
    property var opData: null
    property var workpiece: ({})
    property var toolCard: null
    property var primitives: []
    property string profileType: "od"
    property real p1X: 0
    property real p1Z: 0
    property string direction: "towards_z_minus"
    property bool addUndercut: false
    property real undercutRadius: 0.4
    property real undercutDepth: 0.4
    property real undercutLength: 2.5

    readonly property var previewData: (opIndex >= 0 && editor) ? editor.preview(_draftOp()) : null
    signal openNumPadRequested(var field)

    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.p1_x = p1X; op.p1_z = p1Z
        op.finishing_direction = direction
        op.add_undercut = addUndercut
        op.undercut_parameters = { radius: undercutRadius, depth: undercutDepth, length: undercutLength }
        return op
    }
    function _refreshProfile() {
        var profile = JSON.parse(JSON.stringify(editor ? (editor.parentProfile || {}) : ({})))
        var nextPrimitives = profile.profile_primitives || []
        profileType = profile.profile_type || "od"
        if (addUndercut && nextPrimitives.length > 1) {
            nextPrimitives[1].blend = {
                type: "undercut_din509", chamfer_width: 0, fillet_radius: 0,
                undercut_radius: undercutRadius, undercut_depth: undercutDepth,
                undercut_length: undercutLength
            }
        }
        // Assign after editing the primitive so ProfileCanvas sees the new
        // path and rebuilds the mirrored render segments, including DIN509.
        primitives = nextPrimitives
    }
    function save() { if (editor) editor.save(_draftOp()) }
    function applyData(index, data) {
        opIndex = index; opData = data || {}
        workpiece = editor ? (editor.workpiece || {}) : ({})
        toolCard = editor ? editor.toolCard : null
        p1X = Number(opData.p1_x || 0); p1Z = Number(opData.p1_z || 0)
        direction = opData.finishing_direction || "towards_z_minus"
        addUndercut = !!opData.add_undercut
        var undercut = opData.undercut_parameters || ({})
        undercutRadius = Number(undercut.radius === undefined ? 0.4 : undercut.radius)
        undercutDepth = Number(undercut.depth === undefined ? 0.4 : undercut.depth)
        undercutLength = Number(undercut.length === undefined ? 2.5 : undercut.length)
        _refreshProfile()
        header.applyData(opData)
        profileCanvas.resetView()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        OperationHeader {
            id: header
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpeedsAndFeedsEdited: function(speeds) { var op = root._draftOp(); op.speeds_and_feeds = speeds; root.editor.save(op) }
            onM1Edited: function(m1) { var op = root._draftOp(); op.m1_parameters = m1; root.editor.save(op) }
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
                        onDirectionEdited: function(value) { root.direction = value; root.save() }
                    }
                    TurningPointBox {
                        id: p1Box
                        Layout.alignment: Qt.AlignRight
                        point: 1
                        xValue: root.p1X; zValue: root.p1Z
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                        onFieldEdited: function(axis, value) {
                            if (axis === "x") root.p1X = value; else root.p1Z = value
                            root.save()
                        }
                    }
                    CheckBox {
                        id: undercutCheck
                        visible: !!root.editor && root.editor.undercutAvailable
                        Layout.alignment: Qt.AlignRight
                        text: "Add DIN509 Undercut"
                        checked: root.addUndercut
                        font.pixelSize: Theme.fontBody
                        onToggled: { root.addUndercut = checked; root._refreshProfile(); root.save() }
                    }
                    TurningUndercutBox {
                        id: undercutBox
                        visible: undercutCheck.visible && root.addUndercut
                        Layout.alignment: Qt.AlignRight
                        radius: root.undercutRadius; depth: root.undercutDepth; length: root.undercutLength
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                        onFieldEdited: function(field, value) {
                            if (field === "radius") root.undercutRadius = value
                            else if (field === "depth") root.undercutDepth = value
                            else root.undercutLength = value
                            root._refreshProfile()
                            root.save()
                        }
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
