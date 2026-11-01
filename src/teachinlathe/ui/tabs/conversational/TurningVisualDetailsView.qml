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
    property real xStart: 0
    property real zStart: 0
    property real xEnd: 0
    property real zEnd: 0
    property real ap: 0.5
    property string passType: "axial"
    property real clearance: 1
    property real stockRadial: 0
    property real stockAxial: 0
    property var startBlend: ({ type: "none", chamfer_width: 0, fillet_radius: 0 })
    property var shoulderBlend: ({ type: "none", chamfer_width: 0, fillet_radius: 0 })

    readonly property var turningPreview: (opIndex >= 0 && editor) ? editor.preview(_draftOp()) : null
    signal openNumPadRequested(var field)

    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.geometry_parameters = {
            x_start: xStart, z_start: zStart, x_end: xEnd, z_end: zEnd,
            start_blend: startBlend, shoulder_blend: shoulderBlend
        }
        op.cutting_parameters = { ap: ap, tool_clearance: clearance }
        op.profile_roughing_strategy = { profiling_type: "od", pass_type: passType }
        op.stock_to_leave = { radial: stockRadial, axial: stockAxial }
        return op
    }
    function save(op) {
        if (!editor || opIndex < 0 || !opData) return
        opData = op || _draftOp()
        editor.save(opData)
    }
    function setBlend(target, type, chamfer, fillet) {
        var blend = { type: type, chamfer_width: chamfer, fillet_radius: fillet }
        if (target === "start") startBlend = blend
        else shoulderBlend = blend
        save()
    }
    function applyData(index, data) {
        opIndex = index
        opData = data || {}
        workpiece = editor ? (editor.workpiece || {}) : {}
        toolCard = editor ? editor.toolCard : null
        var gp = opData.geometry_parameters || {}
        var cp = opData.cutting_parameters || {}
        xStart = Number(gp.x_start || 0); zStart = Number(gp.z_start || 0)
        xEnd = Number(gp.x_end || 0); zEnd = Number(gp.z_end || 0)
        ap = Number(cp.ap === undefined ? 0.5 : cp.ap)
        var strategy = opData.profile_roughing_strategy || {}
        passType = strategy.pass_type ? String(strategy.pass_type) : "axial"
        clearance = Number(cp.tool_clearance === undefined ? 1 : cp.tool_clearance)
        var st = opData.stock_to_leave || {}
        stockRadial = Number(st.radial || 0)
        stockAxial = Number(st.axial || 0)
        startBlend = gp.start_blend || ({ type: "none", chamfer_width: 0, fillet_radius: 0 })
        shoulderBlend = gp.shoulder_blend || ({ type: "none", chamfer_width: 0, fillet_radius: 0 })
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
            onSpeedsAndFeedsEdited: function(speeds) {
                var op = root._draftOp(); op.speeds_and_feeds = speeds; root.save(op)
            }
            onM1Edited: function(m1) {
                var op = root._draftOp(); op.m1_parameters = m1; root.save(op)
            }
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
                selectable: false
                mirrorAcrossCenterline: true
                primitives: []
                workpiece: {
                    var w = JSON.parse(JSON.stringify(root.workpiece || {}))
                    var hasHeaderStock = Number(w.external_diameter) > 0 && Number(w.stock_length) > 0
                    if (!hasHeaderStock && root.xStart > 0 && root.zStart > root.zEnd) {
                        w.external_diameter = root.xStart
                        w.stock_length = Math.max(10, Math.max(0, -root.zEnd) + 10)
                    }
                    if (root.xStart > 0 && root.zStart > root.zEnd) {
                        w.face_z = Math.max(0, Number(w.face_z) || 0, root.zStart)
                        w.break_after_z = root.zEnd
                        w.break_after_setback = 10
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
                            onPassTypeEdited: function(value) { root.passType = value; root.save() }
                        }

                        DimensionBox {
                            id: clearanceBox
                            Layout.alignment: Qt.AlignRight
                            label: "Tool Clearance"
                            dimensionColor: profileCanvas.rapidColor
                            settingName: "turning.tool_clearance"
                            value: root.clearance
                            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                            onValueEdited: function(value) { root.clearance = value; root.save() }
                        }
                        TurningPointBox {
                            id: p1Box
                            Layout.alignment: Qt.AlignRight
                            point: 1
                            xValue: root.xStart; zValue: root.zStart
                            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                            onFieldEdited: function(axis, value) {
                                if (axis === "x") root.xStart = value; else root.zStart = value
                                root.save()
                            }
                        }
                        TurningPointBox {
                            id: p2Box
                            Layout.alignment: Qt.AlignRight
                            point: 2
                            xValue: root.xEnd; zValue: root.zEnd
                            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                            onFieldEdited: function(axis, value) {
                                if (axis === "x") root.xEnd = value; else root.zEnd = value
                                root.save()
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
                            onValueEdited: function(value) { root.ap = value; root.save() }
                        }
                        CanvasBox {
                            id: startBlendBox
                            Layout.alignment: Qt.AlignRight
                            RowLayout {
                                Label { text: "Start Blend"; color: parent.parent.accent; font.pixelSize: Theme.fontBody }
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
                                Label { text: "Shoulder Blend"; color: parent.parent.accent; font.pixelSize: Theme.fontBody }
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
                            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                            onRadialEdited: function(value) { root.stockRadial = value; root.save() }
                            onAxialEdited: function(value) { root.stockAxial = value; root.save() }
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
