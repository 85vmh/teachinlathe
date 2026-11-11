import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import theme
import "define_radial_profile" as Radial

Item {
    id: root
    anchors.fill: parent
    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place what the view shows comes from, and every edit goes to
    required property var editor
    readonly property var op: editor.operation
    readonly property var _gp: op.geometry_parameters || ({})
    readonly property var _cp: op.cutting_parameters || ({})
    readonly property var _st: op.stock_to_leave || ({})
    readonly property var _noBlend: ({ type: "none", chamfer_width: 0, fillet_radius: 0 })

    readonly property var workpiece: editor.workpiece || ({})
    readonly property var toolCard: editor.toolCard
    readonly property real xStart: Number(_gp.x_start || 0)
    readonly property real zStart: Number(_gp.z_start || 0)
    readonly property real xEnd: Number(_gp.x_end || 0)
    readonly property real zEnd: Number(_gp.z_end || 0)
    readonly property real ap: Number(_cp.ap === undefined ? 0.5 : _cp.ap)
    readonly property string passType: op.profile_roughing_strategy && op.profile_roughing_strategy.pass_type
                                       ? String(op.profile_roughing_strategy.pass_type) : "axial"
    readonly property real clearance: Number(_cp.tool_clearance === undefined ? 1 : _cp.tool_clearance)
    readonly property real stockRadial: Number(_st.radial || 0)
    readonly property real stockAxial: Number(_st.axial || 0)
    readonly property var startBlend: _gp.start_blend || _noBlend
    readonly property var shoulderBlend: _gp.shoulder_blend || _noBlend

    // what turning cuts, as the planning worker works it out
    readonly property var turningPreview: editor.plannedPreview
    readonly property var turningProfile: editor.inlineProfile
    signal openNumPadRequested(var field)

    function editGeometry(changes) { editor.edit({ geometry_parameters: changes }) }
    function editCutting(changes) { editor.edit({ cutting_parameters: changes }) }
    function editStock(changes) { editor.edit({ stock_to_leave: changes }) }
    function setBlend(target, type, chamfer, fillet) {
        var blend = { type: type, chamfer_width: chamfer, fillet_radius: fillet }
        editGeometry(target === "start" ? { start_blend: blend } : { shoulder_blend: blend })
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

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spacingSmall

            ProfileCanvas {
                id: profileCanvas
                Layout.fillWidth: true
                Layout.fillHeight: true
                showAxes: false
                showZeroLine: true
                selectable: false
                mirrorAcrossCenterline: true
                primitives: root.turningProfile.profile_primitives || []
                profileType: root.turningProfile.profile_type || "od"
                workpiece: {
                    var w = JSON.parse(JSON.stringify(root.workpiece || {}))
                    var hasHeaderStock = Number(w.external_diameter) > 0 && Number(w.stock_length) > 0
                    if (!hasHeaderStock && root.xStart > 0 && root.zStart > root.zEnd) {
                        w.external_diameter = root.xStart
                        w.stock_length = Math.max(10, Math.max(0, -root.zEnd) + 10)
                    }
                    if (root.xStart > 0 && root.zStart > root.zEnd) {
                        w.face_z = Math.max(0, Number(w.face_z) || 0, root.zStart)
                        w.break_after_profile = true
                        delete w.break_after_z
                        delete w.break_after_setback
                    }
                    return w
                }
                startPosition: ({ x: root.xStart, z: root.zStart })
                endPosition: ({ x: root.xEnd, z: root.zEnd })
                roughingPreview: root.turningPreview
                stockToLeaveArrowRect: null
                fitInsetRight: fieldsScroll.width + profileCanvas.tickBand
                fitPadding: 72
                readonly property real p1TagOffset: 56
                readonly property real p1TagX: _cx(root.zStart) - p1TagOffset - p1Tag.width
                readonly property real p1TagY: _cy(root.xStart) + p1TagOffset
                readonly property real p2TagX: _cx(root.zEnd) + 56
                readonly property real p2TagY: _cy(root.xEnd) - 56
                markers: [
                    { leader: true, x: root.xStart, z: root.zStart, color: "#1565c0",
                      toZ: root.zStart, dx: -profileCanvas.p1TagOffset, slope: 1 },
                    { leader: true, x: root.xEnd, z: root.zEnd, color: "#00838f",
                      toZ: root.zEnd, dx: 56, slope: -1 }
                ]
                Radial.GroovePointTag {
                    id: p1Tag
                    point: 1
                    axes: "XZ"
                    x: profileCanvas.p1TagX
                    y: profileCanvas.p1TagY - height / 2
                }
                Radial.GroovePointTag {
                    id: p2Tag
                    point: 2
                    axes: "XZ"
                    x: profileCanvas.p2TagX
                    y: profileCanvas.p2TagY - height / 2
                }
                OperationToolBox {
                    editor: root.editor
                    pickerWidth: root.width
                    x: (profileCanvas.width - width) / 2
                    y: 8
                }

                fitExtraPositions: {
                    if (!canvasTool.drawn) return []
                    var points = canvasTool.outlineFromTip, result = []
                    for (var i = 0; i < points.length; i++)
                        result.push({ x: root.xStart + 2 * points[i].y,
                                      z: root.zStart + points[i].x })
                    return result
                }
                onFitExtraPositionsChanged: if (!_manualView) _scheduleFit()
                CanvasTool {
                    id: canvasTool
                    inset: profileCanvas.tickBand
                    card: root.toolCard && root.toolCard.card ? root.toolCard.card : ""
                    view: root.toolCard && root.toolCard.view ? root.toolCard.view : null
                    pxPerMm: profileCanvas._scale
                    tipX: profileCanvas._cx(root.zStart)
                    tipY: profileCanvas._cy(root.xStart)
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
                    readonly property var cards: [passesBox, clearanceBox, p1Box, p2Box, apBox,
                                                 startBlendBox, shoulderBlendBox, stockBox]
                    function cardAtContentY(position) {
                        for (var i = 0; i < cards.length; i++) {
                            var card = cards[i]
                            if (card.y < position && card.y + card.height > position)
                                return card
                        }
                        return null
                    }
                    readonly property var topCutCard: contentY > 0 ? cardAtContentY(contentY) : null
                    readonly property var bottomCutCard: contentY + height < contentHeight
                        ? cardAtContentY(contentY + height) : null
                    ColumnLayout {
                        id: fields
                        width: parent.width
                        spacing: Theme.spacingSmall

                        ProfilingTypeBox {
                            id: passesBox
                            Layout.alignment: Qt.AlignRight
                            profilingType: "od"
                            passType: root.passType
                            onPassTypeEdited: function(value) { root.editor.edit({ profile_roughing_strategy: { profiling_type: "od", pass_type: value } }) }
                        }

                        DimensionBox {
                            id: clearanceBox
                            Layout.alignment: Qt.AlignRight
                            label: "Tool Clearance"
                            dimensionColor: profileCanvas.rapidColor
                            settingName: "turning.tool_clearance"
                            value: root.clearance
                            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                            onValueEdited: function(value) { root.editCutting({ tool_clearance: value }) }
                        }
                        TurningPointBox {
                            id: p1Box
                            Layout.alignment: Qt.AlignRight
                            point: 1
                            xValue: root.xStart; zValue: root.zStart
                            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                            onFieldEdited: function(axis, value) {
                                root.editGeometry(axis === "x" ? { x_start: value } : { z_start: value })
                            }
                        }
                        TurningPointBox {
                            id: p2Box
                            Layout.alignment: Qt.AlignRight
                            point: 2
                            xValue: root.xEnd; zValue: root.zEnd
                            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                            onFieldEdited: function(axis, value) {
                                root.editGeometry(axis === "x" ? { x_end: value } : { z_end: value })
                            }
                        }
                        DimensionBox {
                            id: apBox
                            Layout.alignment: Qt.AlignRight
                            label: "Ap"
                            dimensionColor: profileCanvas.feedColor
                            settingName: "turning.ap"
                            value: root.ap
                            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                            onValueEdited: function(value) { root.editCutting({ ap: value }) }
                        }
                        CanvasBox {
                            id: startBlendBox
                            Layout.alignment: Qt.AlignRight
                            RowLayout {
                                Label { text: "Start Blend"; color: startBlendBox.accent; font.pixelSize: Theme.fontBody }
                                BlendPicker {
                                    Layout.fillWidth: true
                                    blendType: root.startBlend.type || "none"
                                    chamferWidth: Number(root.startBlend.chamfer_width || 0)
                                    filletRadius: Number(root.startBlend.fillet_radius || 0)
                                    onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                                    onEdited: function(type, chamfer, fillet) { root.setBlend("start", type, chamfer, fillet) }
                                }
                            }
                        }
                        CanvasBox {
                            id: shoulderBlendBox
                            Layout.alignment: Qt.AlignRight
                            RowLayout {
                                Label { text: "Shoulder Blend"; color: shoulderBlendBox.accent; font.pixelSize: Theme.fontBody }
                                BlendPicker {
                                    Layout.fillWidth: true
                                    blendType: root.shoulderBlend.type || "none"
                                    chamferWidth: Number(root.shoulderBlend.chamfer_width || 0)
                                    filletRadius: Number(root.shoulderBlend.fillet_radius || 0)
                                    onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                                    onEdited: function(type, chamfer, fillet) { root.setBlend("shoulder", type, chamfer, fillet) }
                                }
                            }
                        }
                        StockToLeaveBox {
                            id: stockBox
                            Layout.alignment: Qt.AlignRight
                            labelColor: profileCanvas.stockToLeaveColor
                            radial: root.stockRadial
                            axial: root.stockAxial
                            addFinishingPass: true
                            finishingOperationExists: root.editor.hasFinishingOperation
                            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                            onRadialEdited: function(value) { root.editStock({ radial: value }) }
                            onAxialEdited: function(value) { root.editStock({ axial: value }) }
                            onAddFinishingOperationRequested: root.editor.addTurningFinish()
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
                CanvasViewButtons {
                    canvas: profileCanvas
                    showMirror: false
                }
            }
        }
    }
}
