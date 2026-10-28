// G33ThreadingVisualDetailsView.qml — G33 Threading on the profile canvas,
// laid out as Parting's: the header's Speeds and Feeds (RPM only, Pitch and
// Starts for its feeds) with Pause to Inspect, and a stock as big as the
// thread's Major Ø drawn as Parting draws its: broken off past Z End, and
// further from Z0 than its diameter its middle left out too, so Z End sits
// a quarter diameter along the far piece. Z Start and Z End each a line across
// the centre line, Major Ø and Minor Ø dimensioned in front of the stock -
// each with an arrow to its box down the right edge - and Clearance (the
// retract) and DOC in boxes of their own; the threading insert on Z Start,
// Clearance out from Major Ø. Edits the same data as ThreadingDetailsView and
// saves every change through the same updateG33Threading slot.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import "profile_canvas/brokenstock.js" as Broken
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null

    // the program header's stock
    property var    workpiece: ({})
    // the tool it cuts with, as its Tool Library card
    // shows it: editor.toolCard, a ToolCard; null with none
    property var    toolCard: null

    // the values the boxes on the canvas show and edit
    property real   pitch: 0.0
    property int    starts: 1
    property real   majorDiameter: 0.0
    property real   minorDiameter: 0.0
    property real   zStart: 0.0
    property real   zEnd: 0.0
    property real   retract: 0.0
    property real   initialDoc: 0.0

    // the boxes' and their marks' colours
    readonly property color zStartColor:  "#1565c0"
    readonly property color zEndColor:    profileCanvas.endPositionColor
    //: The way the thread is cut, from Z Start to Z End.
    readonly property color travelColor:  Theme.success
    readonly property color majorColor:   "#00838f"
    readonly property color minorColor:   profileCanvas.feedColor
    readonly property color retractColor: "#6d4c41"
    readonly property color docColor:     "#ad1457"

    // the thread's form - metric for now (ThreadForm, data_types.py) - and
    // the included angle of its flanks
    property string threadForm: "metric"
    readonly property real threadAngle: editor ? editor.threadAngle(threadForm) : 60

    // Minor Ø from Major Ø and the pitch (external)
    function calculateMinor() {
        if (!root.editor) return
        var r = root.editor.calculateThreadDiameter("OD", pitch, majorDiameter, minorDiameter)
        if (!r || !r.valid) return
        minorDiameter = Number(r.calculatedDiameter)
        save()
    }

    // the stock as drawn: as big as Major Ø, or the header's until that is set
    readonly property real stockDiameter: majorDiameter > 0 ? majorDiameter
                                          : (Number(workpiece && workpiece.external_diameter) || 0)
    // Further from Z0 than its diameter, the stock's middle is left out, as
    // Parting leaves it out: the piece at the face 0.3 Ø, a gap, Z End a
    // quarter diameter along the far piece, broken off a quarter diameter
    // past it. ``zShift`` is how far right a real Z on the far piece is drawn.
    readonly property bool breakMiddle: stockDiameter > 0 && Math.abs(zEnd) > stockDiameter
    readonly property real breakGap: (Broken.reach(1.0) + 0.06) * stockDiameter
    readonly property real breakNear: -0.3 * stockDiameter
    readonly property real breakFar: breakNear - breakGap
    readonly property real zShift: breakMiddle ? (breakFar - 0.25 * stockDiameter) - zEnd : 0
    // a real Z where it is drawn: on the far piece moved by the shift, in
    // the stretch left out at the gap's middle
    function drawnZ(z) {
        if (!breakMiddle || z >= breakNear) return z
        if (z + zShift <= breakFar) return z + zShift
        return (breakNear + breakFar) / 2
    }
    readonly property real zEndDrawn: drawnZ(zEnd)
    readonly property real zStartDrawn: drawnZ(zStart)

    // The thread seen from the side. Its lead - how far it advances in a
    // turn - is the pitch times the starts, and its helix angle at Major Ø
    // atan(lead / (pi Major Ø)). Under the centre line is the near half's
    // profile, over it the far half's, half a turn round: shifted along Z
    // by pi Major Ø tan(helix angle) / 2 - half the lead - inwards (to Z-)
    // for a right-hand thread, outwards for a left-hand one. Each crest
    // below joined to the crest above it reaches, each root to the root -
    // the helix as it shows on the side facing us.
    //
    // A profile: crests on Major Ø, roots on Minor Ø, a pitch from crest to
    // crest, the flanks at the form's angle - each flank runs the thread's
    // depth times tan(angle / 2) along Z - what is left of the pitch flat,
    // a third at the crest and two at the root, as ISO truncates them.
    readonly property real lead: pitch * Math.max(1, starts)
    readonly property real helixAngle: majorDiameter > 0 && lead > 0
                                       ? Math.atan(lead / (Math.PI * majorDiameter)) * 180 / Math.PI : 0
    // cut towards the chuck - Z End past Z Start - is right-hand, as the
    // other threading screen has it
    readonly property bool rightHand: zEnd < zStart
    readonly property real halfTurnShift: Math.PI * majorDiameter * Math.tan(helixAngle * Math.PI / 180) / 2

    // the profile's measures: [crest flat, flank, root flat] along Z, mm
    readonly property var _profile: {
        if (!(pitch > 0)) return null
        var depth = Math.abs(majorDiameter - minorDiameter) / 2
        var flank = Math.min(pitch / 2, depth * Math.tan(threadAngle / 2 * Math.PI / 180))
        var flats = pitch - 2 * flank
        return { crest: flats / 3, flank: flank, root: flats - flats / 3 }
    }
    readonly property bool _threadDrawable: !!_profile && majorDiameter > 0 && minorDiameter > 0
                                           && zStart !== zEnd && Math.abs(zEnd - zStart) / pitch <= 1000

    // The profile's diameter at ``s`` mm along the thread from Z Start, its
    // pattern moved ``phase`` mm on.
    function _diameterAt(s, phase) {
        var p = _profile
        var u = ((s - phase) % pitch + pitch) % pitch
        if (u < p.crest) return majorDiameter
        u -= p.crest
        if (u < p.flank) return majorDiameter + (minorDiameter - majorDiameter) * u / p.flank
        u -= p.flank
        if (u < p.root) return minorDiameter
        u -= p.root
        return minorDiameter + (majorDiameter - minorDiameter) * u / p.flank
    }

    // Its corners from Z Start to Z End, as [s along it], phase as above.
    function _profileStations(phase) {
        var p = _profile, length = Math.abs(zEnd - zStart)
        var marks = [0, p.crest, p.crest + p.flank, p.crest + p.flank + p.root]
        var out = [0, length]
        for (var k = Math.floor(-phase / pitch) - 1; k * pitch + phase <= length; k++)
            for (var m = 0; m < marks.length; m++) {
                var s = k * pitch + phase + marks[m]
                if (s > 0 && s < length) out.push(s)
            }
        out.sort(function(a, b) { return a - b })
        return out
    }

    // a real Z's region of the drawing: past Z0, out of the stock and not
    // drawn; the piece at the face, the far piece, or the stretch left out
    // between them
    function _regionOf(z) {
        if (z > 0) return "out"
        if (!breakMiddle || z >= breakNear) return "face"
        if (z + zShift <= breakFar) return "far"
        return "gap"
    }

    // where two neighbouring regions meet, real Z
    function _boundary(a, b) {
        if (a === "out" || b === "out") return 0
        return a === "far" || b === "far" ? breakFar - zShift : breakNear
    }

    // The profile as lines of drawn {z, x}, x negative over the centre
    // line (``sign`` -1), clipped at Z0 and split where the stock's middle
    // is left out - each line run exactly to the edge of its piece.
    function _profileLines(phase, sign) {
        var lines = []
        if (!_threadDrawable) return lines
        var dir = zEnd < zStart ? -1 : 1
        var stations = _profileStations(phase)
        var current = [], region = null, last = null
        function drawn(r) { return r === "face" || r === "far" }
        for (var i = 0; i < stations.length; i++) {
            var z = zStart + dir * stations[i], x = sign * _diameterAt(stations[i], phase)
            var r = _regionOf(z)
            if (r !== region) {
                if (last && drawn(region)) {
                    var e = _boundary(region, r)
                    current.push({ z: drawnZ(e), x: last.x + (x - last.x) * (e - last.z) / (z - last.z) })
                }
                if (current.length > 1) lines.push(current)
                current = []
                if (last && drawn(r)) {
                    var e2 = _boundary(region, r)
                    current.push({ z: drawnZ(e2), x: last.x + (x - last.x) * (e2 - last.z) / (z - last.z) })
                }
                region = r
            }
            if (drawn(r)) current.push({ z: drawnZ(z), x: x })
            last = { z: z, x: x }
        }
        if (current.length > 1) lines.push(current)
        return lines
    }

    // the far half's pattern, half a turn round
    readonly property real _upperPhase: rightHand ? halfTurnShift : -halfTurnShift
    readonly property var threadLower: _profileLines(0, 1)
    readonly property var threadUpper: _profileLines(_upperPhase, -1)

    // the helix on the near side: each crest's middle below joined to the
    // crest's above, each root's to the root's - {crests, roots}, each
    // lines of drawn {z, x}, clipped at Z0
    readonly property var helixLines: {
        var out = { crests: [], roots: [] }
        if (!_threadDrawable) return out
        var p = _profile, length = Math.abs(zEnd - zStart), dir = zEnd < zStart ? -1 : 1
        var marks = [[p.crest / 2, majorDiameter], [p.crest + p.flank + p.root / 2, minorDiameter]]
        for (var k = -1; k * pitch <= length; k++)
            for (var m = 0; m < marks.length; m++) {
                var s0 = k * pitch + marks[m][0], s1 = s0 + _upperPhase
                if (s0 < 0 || s0 > length || s1 < 0 || s1 > length) continue
                var z0 = zStart + dir * s0, z1 = zStart + dir * s1
                var x0 = marks[m][1], x1 = -marks[m][1]
                if (z0 > 0 && z1 > 0) continue
                if (z0 > 0) { x0 = x0 + (x1 - x0) * z0 / (z0 - z1); z0 = 0 }
                else if (z1 > 0) { x1 = x1 + (x0 - x1) * z1 / (z1 - z0); z1 = 0 }
                var r0 = _regionOf(z0), r1 = _regionOf(z1)
                if (r0 === "gap" || r0 !== r1) continue
                out[m === 0 ? "crests" : "roots"].push([{ z: drawnZ(z0), x: x0 }, { z: drawnZ(z1), x: x1 }])
            }
        return out
    }

    // the face at Z0 across the thread's ends, when it starts past it
    readonly property var threadFace: zStart > 0 && threadLower.length > 0 && threadUpper.length > 0
                                      ? [[threadUpper[0][0], threadLower[0][0]]] : []

    // where the insert starts each pass: Clearance out from Major Ø, as
    // the G-code has it
    readonly property real startX: majorDiameter + retract
    signal openNumPadRequested(var field)

    // opData with the values edited in the boxes
    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.pitch = pitch
        op.starts = starts
        op.major_diameter = majorDiameter
        op.minor_diameter = minorDiameter
        op.z_start = zStart
        op.z_end = zEnd
        op.retract = retract
        op.initial_doc = initialDoc
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
        workpiece = editor ? (editor.workpiece || {}) : {}
        toolCard  = editor ? editor.toolCard : null

        pitch         = opData.pitch          !== undefined ? Number(opData.pitch) : 0
        starts        = opData.starts         !== undefined ? Math.max(1, Math.round(Number(opData.starts))) : 1
        majorDiameter = opData.major_diameter !== undefined ? Number(opData.major_diameter) : 0
        minorDiameter = opData.minor_diameter !== undefined ? Number(opData.minor_diameter) : 0
        zStart        = opData.z_start        !== undefined ? Number(opData.z_start) : 0
        zEnd          = opData.z_end          !== undefined ? Number(opData.z_end) : 0
        retract       = opData.retract        !== undefined ? Number(opData.retract) : 0
        initialDoc    = opData.initial_doc    !== undefined ? Number(opData.initial_doc) : 0

        header.pitch = pitch
        header.starts = starts
        header.applyData(opData)
        profileCanvas.resetView()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // RPM only; its feeds are the pitch and the starts
        OperationHeader {
            id: header
            rpmOnly: true
            feedKind: SpeedsAndFeeds.FeedKind.Threading
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpeedsAndFeedsEdited: function(speeds) {
                var op = root._draftOp()
                op.speeds_and_feeds = speeds
                root.save(op)
            }
            onPitchEdited: function(value) { root.pitch = value; root.save() }
            onStartsEdited: function(value) { root.starts = value; root.save() }
            onM1Edited: function(m1) {
                var op = root._draftOp()
                op.m1_parameters = m1
                root.save(op)
            }
        }

        ProfileCanvas {
            id: profileCanvas
            showTransitions: false
            // no axes: the origin alone marks Z0
            showAxes: false
            Layout.fillWidth: true
            Layout.fillHeight: true
            // pinch and the buttons zoom, a drag pans, a double tap fits
            selectable: false
            // the backplot's step (glnav's zoomin / zoomout)
            zoomStep: 1.1
            mirrorAcrossCenterline: true
            // a dot at both ends of each arrow to a box
            arrowStartDots: true
            primitives: []
            // the header's stock, as big as Major Ø, broken off past Z End -
            // and its middle left out when that is far down it; the header's
            // bore kept
            workpiece: {
                var w = JSON.parse(JSON.stringify(root.workpiece || {}))
                if (root.stockDiameter > 0) w.external_diameter = root.stockDiameter
                w.stock_length = Math.max(Number(w.stock_length) || 0, Math.abs(root.zEnd) + root.stockDiameter)
                w.break_far_end = false
                w.break_after_z = root.zEndDrawn
                w.break_middle = root.breakMiddle ? { near: root.breakNear, far: root.breakFar } : null
                if (root.breakMiddle) w.break_after_setback = 0.25 * root.stockDiameter
                // the thread cut into it: its profile the stock's outline there
                w.thread = { lower: root.threadLower, upper: root.threadUpper,
                             from: root.drawnZ(Math.min(root.zStart, 0)), to: root.zEndDrawn }
                return w
            }
            axisBreak: root.breakMiddle ? { near: root.breakNear, far: root.breakFar, shift: root.zShift } : null

            // the Z lines across the centre line, past the stock
            readonly property real zLineDiameter: Math.max(root.majorDiameter, 10) * 1.2
            markers: [
                { line: true, x: zLineDiameter, z: root.zStartDrawn, color: root.zStartColor },
                { line: true, x: zLineDiameter, z: root.zEndDrawn, color: root.zEndColor },
                // the way the thread is cut, across the lines' top ends, to
                // Z End; from its middle the leader to the Z Start / End box
                { travel: true, x: -zLineDiameter, from: root.zStartDrawn, to: root.zEndDrawn,
                  z: (root.zStartDrawn + root.zEndDrawn) / 2, color: root.travelColor,
                  leaderColor: root.zStartColor, arrowToRect: zRangeBox.rect },
                // the thread: its profile under the centre line, the far
                // half's over it, and the helix joining them
                { polyline: root.threadLower, color: "#455a64" },
                { polyline: root.threadUpper, color: "#455a64", visible: mirrorAcrossCenterline },
                { polyline: root.helixLines.crests, color: "#455a64", lineWidth: 1, visible: mirrorAcrossCenterline },
                { polyline: root.helixLines.roots, color: "#ef6c00", lineWidth: 1, visible: mirrorAcrossCenterline },
                // the face, where the thread is clipped at Z0
                { polyline: root.threadFace, color: "#455a64", visible: mirrorAcrossCenterline }
            ]
            // Major Ø then Minor Ø in front of the stock, each at the middle
            // of its extension lines; their leaders from a dot above the
            // centre line. Mirrored only
            dimensions: {
                if (!mirrorAcrossCenterline) return []
                var dims = []
                if (root.majorDiameter > 0)
                    dims.push({ axis: "x", from: -root.majorDiameter, to: root.majorDiameter,
                                z: Math.max(0, root.zStart), offset: 24, extensionsCentred: true,
                                color: root.majorColor, arrowToRect: majorBox.rect, leaderAt: 0.25 })
                if (root.minorDiameter > 0)
                    dims.push({ axis: "x", from: -root.minorDiameter, to: root.minorDiameter,
                                z: Math.max(0, root.zStart), offset: 48, extensionsCentred: true,
                                color: root.minorColor, arrowToRect: minorBox.rect, leaderAt: 0.25 })
                return dims
            }

            // the insert where it starts: its tip on Z Start, Clearance
            // out from Major Ø; in the fit too
            fitExtraPositions: {
                if (!canvasTool.drawn) return []
                var pts = canvasTool.outlineFromTip, out = []
                for (var i = 0; i < pts.length; i++)
                    out.push({ x: root.startX + 2 * pts[i].y, z: root.zStartDrawn + pts[i].x })
                return out
            }
            onFitExtraPositionsChanged: if (!_manualView) _scheduleFit()
            CanvasTool {
                id: canvasTool
                inset: profileCanvas.tickBand
                card: root.toolCard && root.toolCard.card ? root.toolCard.card : ""
                view: root.toolCard && root.toolCard.view ? root.toolCard.view : null
                pxPerMm: profileCanvas._scale
                tipX: profileCanvas._cx(root.zStartDrawn)
                tipY: profileCanvas._cy(root.startX)
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(zRangeBox.implicitWidth,
                                                      majorBox.implicitWidth, minorBox.implicitWidth,
                                                      retractBox.implicitWidth, docBox.implicitWidth)
            readonly property real boxGap: Theme.spacingLarge
            fitInsetRight: boxWidth + boxGap

            // top to bottom: Z Start and Z End in one box, Major Ø, Minor Ø
            // together, a gap apart; Retract and DOC at the bottom. The
            // position boxes as wide as each other, their labels lined up
            readonly property real positionBoxWidth: Math.max(zRangeBox.implicitWidth,
                                                              majorBox.implicitWidth, minorBox.implicitWidth)
            readonly property real positionLabelWidth: Math.max(zRangeBox.labelImplicitWidth,
                                                                majorBox.labelImplicitWidth,
                                                                minorBox.labelImplicitWidth)

            ZRangeBox {
                id: zRangeBox
                width: profileCanvas.positionBoxWidth
                labelWidth: profileCanvas.positionLabelWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.boxGap
                accent: root.zStartColor
                startColor: root.zStartColor
                endColor: root.zEndColor
                startSettingName: "threading.z_start"
                endSettingName: "threading.z_end"
                zStart: root.zStart
                zEnd: root.zEnd
                onZStartEdited: function(value) { root.zStart = value; root.save() }
                onZEndEdited: function(value) { root.zEnd = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            ZPositionBox {
                id: majorBox
                width: profileCanvas.positionBoxWidth
                labelWidth: profileCanvas.positionLabelWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: zRangeBox.y + zRangeBox.height + profileCanvas.boxGap
                axis: "x"
                accent: root.majorColor
                label: "Major Ø"
                settingName: "threading.teach_diam"
                value: root.majorDiameter
                onValueEdited: function(value) { root.majorDiameter = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            ZPositionBox {
                id: minorBox
                width: profileCanvas.positionBoxWidth
                labelWidth: profileCanvas.positionLabelWidth
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: majorBox.y + majorBox.height + profileCanvas.boxGap
                axis: "x"
                accent: root.minorColor
                label: "Minor Ø"
                settingName: "threading.calc_diam"
                // worked out from Major Ø and the pitch, not taught in
                actionText: "Calculate"
                onActionRequested: root.calculateMinor()
                value: root.minorDiameter
                onValueEdited: function(value) { root.minorDiameter = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            DimensionBox {
                id: retractBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: docBox.y - height - profileCanvas.boxGap
                label: "Clearance"
                dimensionColor: root.retractColor
                settingName: "threading.retract"
                value: root.retract
                onValueEdited: function(value) { root.retract = Math.abs(value); root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            DimensionBox {
                id: docBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.height - height - profileCanvas.boxGap
                label: "DOC"
                dimensionColor: root.docColor
                settingName: "threading.initial_doc"
                value: root.initialDoc
                onValueEdited: function(value) { root.initialDoc = Math.abs(value); root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // the tool it cuts with, at the top, in the middle; tapped, to
            // pick it - only an external (OD) threading tool for now
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
            }
        }
    }
}
