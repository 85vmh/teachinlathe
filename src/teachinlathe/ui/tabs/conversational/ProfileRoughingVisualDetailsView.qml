// ProfileRoughingVisualDetailsView.qml — Profile Roughing with a profile viewer.
// Saves every change through updateProfileRoughing.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import theme
import "define_radial_profile" as Radial

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null

    // the last profile defined above this operation
    property var    primitives:  []
    property string profileType: "od"
    property var    workpiece:   ({})
    // the tool it cuts with, as its Tool Library card
    // shows it: editor.toolCard, a ToolCard; null with none
    property var    toolCard:    null

    // the values the boxes on the canvas show and edit
    property real   xStart: 0.0
    property real   zStart: 0.0
    property real   stockRadial: 0.0
    property real   stockAxial: 0.0
    property real   doc: 0.0
    property real   retract: 0.0
    property string passType: "axial"
    readonly property bool isIdProfile: String(profileType).toLowerCase() === "id"

    // what roughing will cut with the values above
    // Rest material: it cuts what the roughings above it leave, keeping to
    // their stock to leave and start position - neither is set here.
    readonly property bool restMaterial: !!(opData && opData.rest_material)

    // Asked for a moment after the values settle, not on each one: opening
    // the operation sets them one after another.
    property var roughingPreview: null
    readonly property string _previewKey: (opIndex >= 0 && primitives.length > 0 && editor)
                                          ? JSON.stringify(_draftOp()) : ""
    on_PreviewKeyChanged: previewTimer.restart()
    Timer {
        id: previewTimer
        interval: 150
        onTriggered: {
            if (root._previewKey === "")
                root.roughingPreview = null
            else
                root.editor.requestPreview(JSON.parse(root._previewKey))
        }
    }
    // worked out in the planning worker, off the GUI thread: the screen goes
    // on - an opening program's slide too - and the drawing follows
    Connections {
        target: root.editor
        function onPreviewReady(preview) { root.roughingPreview = preview }
    }
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    Geometry { id: geom }

    function _maxProfileDiameter() {
        var b = geom.computeBounds(geom.resolvePrimitives(primitives))
        return b ? b.fXMax : 0
    }

    // Where the profile ends: its last primitive's X
    function _lastProfileDiameter() {
        var resolved = geom.resolvePrimitives(primitives)
        if (resolved.length === 0) return 0
        var last = resolved[resolved.length - 1]
        return Number(last.type === "startPoint" ? last.x_start : last.x_end) || 0
    }

    // opData with the values edited in the boxes
    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.profiling_parameters = op.profiling_parameters || {}
        op.profiling_parameters.x_start = xStart
        op.profiling_parameters.z_start = zStart
        op.stock_to_leave = { radial: stockRadial, axial: stockAxial }
        op.cutting_parameters = op.cutting_parameters || {}
        op.cutting_parameters.doc = doc
        op.cutting_parameters.retract = retract
        op.profile_roughing_strategy = { profiling_type: profileType, pass_type: passType }
        return op
    }

    // the whole op with every edited value, sent as one save; opData keeps it,
    // so the next edit builds on this one
    function save(op) {
        if (opIndex < 0 || !opData) return
        opData = op || _draftOp()
        root.editor.save(opData)
    }

    function applyData(index, data) {
        opIndex = index
        opData  = data || {}

        var profileOp = editor ? (editor.lastProfile || {}) : {}
        primitives  = JSON.parse(JSON.stringify(profileOp.profile_primitives || []))
        profileType = profileOp.profile_type !== undefined ? String(profileOp.profile_type) : "od"
        // the stock broken off right after the profile, as the Program
        // Header draws its stock - set before it is handed on
        var stock = JSON.parse(JSON.stringify(profileOp.workpiece || {}))
        stock.break_after_profile = true
        workpiece   = stock
        toolCard    = editor ? editor.toolCard : null

        // X Start defaults, OD, to the profile's largest diameter plus the
        // retract; ID, to the diameter it ends on
        var pp = opData.profiling_parameters || {}
        var cp = opData.cutting_parameters || {}
        var st = opData.stock_to_leave || {}
        var savedX = pp.x_start !== undefined ? Number(pp.x_start) : 0
        retract = cp.retract !== undefined ? Number(cp.retract) : 0
        doc     = cp.doc !== undefined ? Number(cp.doc) : 0
        xStart  = savedX !== 0 ? savedX
                : (String(profileType).toLowerCase() === "id" ? _lastProfileDiameter() : _maxProfileDiameter() + retract)
        zStart  = pp.z_start !== undefined ? Number(pp.z_start) : 0
        stockRadial = st.radial !== undefined ? Number(st.radial) : 0
        stockAxial  = st.axial !== undefined ? Number(st.axial) : 0
        var strategy = opData.profile_roughing_strategy || {}
        passType = strategy.pass_type ? String(strategy.pass_type) : "axial"

        header.applyData(opData)
        profileCanvas.resetView()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // each edit goes into the whole op with the canvas boxes' values
        OperationHeader {
            id: header
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpeedsAndFeedsEdited: function(speeds) {
                var op = root._draftOp()
                op.speeds_and_feeds = speeds
                root.save(op)
            }
            onM1Edited: function(m1) {
                var op = root._draftOp()
                op.m1_parameters = m1
                root.save(op)
            }
        }

        ProfileCanvas {
            id: profileCanvas
            // drawn simpler at every step of a zoom or pan (see ProfileCanvas)
            simplifyWhileMoving: true
            showTransitions: false
            // no axes: the origin marks Z0, and the dashed X axis through it
            showAxes: false
            showZeroLine: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            // pinch and the buttons zoom, a drag pans, a double tap fits
            selectable: false
            // the backplot's step (glnav's zoomin / zoomout)
            zoomStep: 1.1
            // the profile in the stock's outline colour and weight
            profileLineColor: "#6b7280"
            profileLineWidth: 1.5
            fitDiameterMargin: 10
            primitives:  root.primitives
            profileType: root.profileType
            workpiece:   root.workpiece
            startPosition: root.primitives.length > 0 && !root.restMaterial ? { x: root.xStart, z: root.zStart } : null
            roughingPreview: root.roughingPreview
            startPositionArrowRect: null
            stockToLeaveArrowRect: null
            readonly property real p1TagOffset: 56
            readonly property real p1TagX: root.isIdProfile
                ? _cx(root.zStart) + p1TagOffset
                : _cx(root.zStart) - p1TagOffset - p1Tag.width
            readonly property real p1TagY: _cy(root.xStart) + p1TagOffset
            markers: root.primitives.length > 0 && !root.restMaterial ? [
                { leader: true, x: root.xStart, z: root.zStart, color: "#1565c0",
                  toZ: root.zStart, dx: root.isIdProfile ? p1TagOffset : -p1TagOffset, slope: 1 }
            ] : []
            Radial.GroovePointTag {
                id: p1Tag
                visible: root.primitives.length > 0 && !root.restMaterial
                point: 1
                axes: "XZ"
                x: profileCanvas.p1TagX
                y: profileCanvas.p1TagY - height / 2
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // the tool - a turning tool's insert or a blade - its control
            // point on the start position, turned as its orientation has it,
            // inside the ticks; in the fit too. Declared before the boxes,
            // the note and the buttons: they stay over it
            fitExtraPositions: {
                if (!canvasTool.drawn) return []
                var pts = canvasTool.outlineFromTip, out = []
                for (var i = 0; i < pts.length; i++)
                    out.push({ x: root.xStart + 2 * pts[i].y, z: root.zStart + pts[i].x })
                return out
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

            // What the plan could not do - a tool that cannot reach a pocket,
            // or no plan at all - in the bottom left corner, clear of the zoom
            // buttons. With material left for another tool, tapping it adds a
            // rest roughing for that, its tool still to be chosen.
            Rectangle {
                id: note
                readonly property var preview: root.roughingPreview
                readonly property bool offersRest: !!preview && !preview.error && !!preview.restOffered
                    && !!root.editor
                readonly property string message: !preview ? ""
                    : preview.error ? preview.error
                    : (preview.warnings || []).join("\n")
                      + (offersRest ? "\nTap to rough it with another tool" : "")
                visible: message !== ""
                x: Theme.spacingLarge
                y: profileCanvas.height - height - Theme.spacingLarge
                width: Math.min(noteText.implicitWidth + 2 * Theme.spacing,
                                profileCanvas.width - profileCanvas.boxWidth - 3 * Theme.spacingLarge)
                height: noteText.implicitHeight + 2 * Theme.spacingSmall
                radius: Theme.radius
                color: preview && preview.error ? Theme.dangerSoft : "#fff3e0"
                border.color: preview && preview.error ? Theme.danger : "#ef6c00"
                border.width: Theme.hairline

                Text {
                    id: noteText
                    x: Theme.spacing
                    y: Theme.spacingSmall
                    width: parent.width - 2 * Theme.spacing
                    text: parent.message
                    color: Theme.foreground
                    font.pixelSize: Theme.fontSmall
                    wrapMode: Text.Wrap
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: note.offersRest
                    onClicked: root.editor.addRestRoughing()
                }
            }

            // over the note: what this operation cuts, when it is a rest roughing
            Rectangle {
                visible: root.restMaterial && root.primitives.length > 0
                x: Theme.spacingLarge
                y: (note.visible ? note.y : profileCanvas.height - Theme.spacingLarge) - height - Theme.spacingSmall
                width: restText.implicitWidth + 2 * Theme.spacing
                height: restText.implicitHeight + 2 * Theme.spacingSmall
                radius: Theme.radius
                color: Theme.selection
                border.color: Theme.accent
                border.width: Theme.hairline

                Text {
                    id: restText
                    anchors.centerIn: parent
                    text: "Rest material: what the roughing above leaves, to its stock to leave"
                    color: Theme.foreground
                    font.pixelSize: Theme.fontSmall
                }
            }

            // Right-aligned cards, sized to their own content; they scroll
            // inside the canvas when the viewport is shorter than the stack.
            readonly property real boxWidth: fieldsScroll.width
            fitInsetRight: root.primitives.length > 0 ? boxWidth + profileCanvas.tickBand : 0

            Flickable {
                id: fieldsScroll
                width: Math.max(1, fields.implicitWidth)
                height: profileCanvas.height - 2 * profileCanvas.tickBand
                x: profileCanvas.width - width - profileCanvas.tickBand
                y: profileCanvas.tickBand
                contentWidth: width
                contentHeight: fields.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                ColumnLayout {
                    id: fields
                    width: parent.width
                    spacing: Theme.spacingSmall

                    ProfilingTypeBox {
                        id: strategyBox
                        visible: root.primitives.length > 0
                        Layout.alignment: Qt.AlignRight
                        profilingType: root.profileType
                        passType: root.passType
                        onPassTypeEdited: function(value) { root.passType = value; root.save() }
                    }
                    DimensionBox {
                        id: clearanceBox
                        visible: root.primitives.length > 0
                        Layout.alignment: Qt.AlignRight
                        label: "Tool Clearance"
                        dimensionColor: profileCanvas.rapidColor
                        settingName: "profile_roughing.tool_clearance"
                        value: root.retract
                        onValueEdited: function(value) { root.retract = value; root.save() }
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                    }
                    TurningPointBox {
                        id: startBox
                        visible: profileCanvas.startPosition !== null
                        Layout.alignment: Qt.AlignRight
                        point: 1
                        settingPrefix: "profile_roughing"
                        xValue: root.xStart
                        zValue: root.zStart
                        onFieldEdited: function(axis, value) {
                            if (axis === "x") root.xStart = value; else root.zStart = value
                            root.save()
                        }
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                    }
                    DimensionBox {
                        id: apBox
                        visible: root.primitives.length > 0
                        Layout.alignment: Qt.AlignRight
                        label: "Ap"
                        dimensionColor: profileCanvas.feedColor
                        settingName: "profile_roughing.ap"
                        value: root.doc
                        onValueEdited: function(value) { root.doc = value; root.save() }
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                    }
                    StockToLeaveBox {
                        id: stockBox
                        visible: root.primitives.length > 0 && !root.restMaterial
                        Layout.alignment: Qt.AlignRight
                        labelColor: profileCanvas.stockToLeaveColor
                        radial: root.stockRadial
                        axial: root.stockAxial
                        onRadialEdited: function(value) { root.stockRadial = value; root.save() }
                        onAxialEdited: function(value) { root.stockAxial = value; root.save() }
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                    }
                }
            }

            // the tool it cuts with, at the top, in the middle; tapped, to
            // pick it - a turning tool for an OD profile, a boring bar for
            // an ID one
            OperationToolBox {
                editor: root.editor
                pickerWidth: root.width
                x: (profileCanvas.width - width) / 2
                // lined up with the view buttons, as tall as they are
                y: viewButtons.y
                rowHeight: viewButtons.height
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                id: viewButtons
                canvas: profileCanvas
                visible: root.primitives.length > 0
            }

            Label {
                anchors.centerIn: parent
                visible: root.primitives.length === 0
                text: "No profile defined above this operation"
                color: Theme.foregroundMuted
                font.pixelSize: Theme.fontBody
            }
        }
    }
}
