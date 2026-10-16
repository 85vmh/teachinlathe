// FacingVisualDetailsView.qml — Facing on the profile canvas, laid out as
// Profile Roughing's: no profile, so the passes are drawn over the header's
// stock, from the start position to the end position. Edits the same data
// as FacingDetailsView and saves every change through the same updateFacing
// slot.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "profile_canvas"
import theme 1.0

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData: null

    // the program header's stock
    property var    workpiece: ({})

    // the values the boxes on the canvas show and edit
    property real   xStart: 0.0
    property real   zStart: 0.0
    property real   xEnd: 0.0
    property real   zEnd: 0.0
    property real   doc: 0.0
    property real   retract: 0.0
    property bool   zEndBecomesNewZ0: false
    // the canvas mirrored or not: off unless the editor says otherwise; the
    // mirror button changes it, and the editor keeps it for the next Facing
    property bool   canvasMirror: false
    onCanvasMirrorChanged: profileCanvas.mirrorAcrossCenterline = canvasMirror

    // what facing will cut with the values above
    readonly property var facingPreview: (opIndex >= 0 && typeof conversationalQml !== "undefined" && conversationalQml)
                                         ? conversationalQml.facingPreview(_draftOp())
                                         : null

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    // opData with the values edited in the boxes
    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.geometry_parameters = { x_start: xStart, z_start: zStart, x_end: xEnd, z_end: zEnd }
        op.cutting_parameters = op.cutting_parameters || {}
        op.cutting_parameters.doc = doc
        op.cutting_parameters.retract = retract
        op.z_end_becomes_new_z0 = zEndBecomesNewZ0
        return op
    }

    // the whole op with every edited value, sent as one save; opData keeps it,
    // so the next edit builds on this one
    function save(op) {
        if (opIndex < 0 || !opData) return
        opData = op || _draftOp()
        root.saveRequested({index: opIndex, payload: opData})
    }

    function applyData(index, data) {
        opIndex = index
        opData  = data || {}

        workpiece = (typeof conversationalQml !== "undefined" && conversationalQml)
                    ? (conversationalQml.currentWorkpiece() || {}) : {}

        var gp = opData.geometry_parameters || {}
        var cp = opData.cutting_parameters || {}
        xStart  = gp.x_start !== undefined ? Number(gp.x_start) : 0
        zStart  = gp.z_start !== undefined ? Number(gp.z_start) : 0
        xEnd    = gp.x_end   !== undefined ? Number(gp.x_end)   : 0
        zEnd    = gp.z_end   !== undefined ? Number(gp.z_end)   : 0
        doc     = cp.doc     !== undefined ? Number(cp.doc)     : 0
        retract = cp.retract !== undefined ? Number(cp.retract) : 0
        zEndBecomesNewZ0 = !!opData.z_end_becomes_new_z0

        header.applyData(opData, cp.feed_rate)
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
            onSpindleEdited: function(spindle) {
                var op = root._draftOp()
                op.spindle_parameters = spindle
                root.save(op)
            }
            onFeedRateEdited: function(value) {
                var op = root._draftOp()
                op.cutting_parameters.feed_rate = value
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
            Layout.fillWidth: true
            Layout.fillHeight: true
            // pinch and the buttons zoom, a drag pans, a double tap fits
            selectable: false
            // the backplot's step (glnav's zoomin / zoomout)
            zoomStep: 1.1
            mirrorAcrossCenterline: false
            primitives: []
            // the header's stock, and in front of Z0 up to Z Start, the
            // material being faced off
            workpiece: {
                var w = JSON.parse(JSON.stringify(root.workpiece || {}))
                w.face_z = Math.max(0, root.zStart)
                return w
            }
            startPosition: ({ x: root.xStart, z: root.zStart })
            endPosition:   ({ x: root.xEnd,   z: root.zEnd })
            roughingPreview: root.facingPreview
            startPositionArrowRect: startBox.rect
            endPositionArrowRect:   endBox.rect

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // the mirror button changes it here; the view passes it on
            Connections {
                target: profileCanvas
                function onMirrorAcrossCenterlineChanged() { root.canvasMirror = profileCanvas.mirrorAcrossCenterline }
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(docBox.implicitWidth, z0Check.implicitWidth,
                                                      endBox.implicitWidth, startBox.implicitWidth)
            readonly property real boxGap: Theme.spacingLarge
            fitInsetRight: boxWidth + boxGap

            DepthOfCutBox {
                id: docBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.boxGap
                docColor: profileCanvas.feedColor
                retractColor: profileCanvas.rapidColor
                doc: root.doc
                retract: root.retract
                onDocEdited: function(value) { root.doc = value; root.save() }
                onRetractEdited: function(value) { root.retract = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // the end position, and above it whether Z End becomes the new
            // Z0, in its colour - halfway between Ap / Retract and the start
            readonly property real endGroupHeight: z0Check.height + Theme.spacingSmall + endBox.height
            readonly property real endGroupY: (docBox.y + docBox.height + startBox.y - endGroupHeight) / 2

            CheckBox {
                id: z0Check
                x: endBox.x
                y: profileCanvas.endGroupY
                text: "Set Z End as the new Z0"
                font.pixelSize: Theme.fontBody
                font.bold: true
                checked: root.zEndBecomesNewZ0
                onToggled: { root.zEndBecomesNewZ0 = checked; root.save() }
                contentItem: Text {
                    text: z0Check.text
                    font: z0Check.font
                    color: profileCanvas.endPositionColor
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: z0Check.indicator.width + z0Check.spacing
                }
            }

            StartPositionBox {
                id: endBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: z0Check.y + z0Check.height + Theme.spacingSmall
                accent: profileCanvas.endPositionColor
                xLabel: "X End Position"
                zLabel: "Z End Position"
                xStart: root.xEnd
                zStart: root.zEnd
                onXStartEdited: function(value) { root.xEnd = value; root.save() }
                onZStartEdited: function(value) { root.zEnd = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            StartPositionBox {
                id: startBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.height - height - profileCanvas.boxGap
                xStart: root.xStart
                zStart: root.zStart
                onXStartEdited: function(value) { root.xStart = value; root.save() }
                onZStartEdited: function(value) { root.zStart = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                canvas: profileCanvas
            }
        }
    }
}
