// G33ThreadingVisualDetailsView.qml — G33 Threading on the profile canvas,
// laid out as Parting's: the header's Speeds and Feeds (RPM only, Pitch and
// Starts for its feeds) with Pause to Inspect, and a stock as big as the
// thread's Major Ø drawn as Parting draws its: broken off past Z End, and
// further from Z0 than its diameter its middle left out too, so Z End sits
// a quarter diameter along the far piece. Z Start and Z End each a line across
// the centre line, Major Ø and Minor Ø dimensioned in front of the stock; the
// threading insert on Z Start, Clearance out from Major Ø. The values in cards
// down the right edge, in a list that scrolls, as Turning has them: OD / ID,
// Clearance, Z Start / Z End, Major Ø and Minor Ø, and the passes (DOC,
// Infeed Angle, Spring Passes).
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
    // "OD" | "ID": an ID thread is taught in on its Minor Ø, its Major Ø
    // calculated
    property string location: "OD"
    property real   pitch: 0.0
    property int    starts: 1
    property real   majorDiameter: 0.0
    property real   minorDiameter: 0.0
    property real   zStart: 0.0
    property real   zEnd: 0.0
    property real   retract: 0.0
    property real   initialDoc: 0.0
    property real   compoundAngle: 0.0
    property int    springPasses: 0

    // the boxes' and their marks' colours
    readonly property color zStartColor:  "#1565c0"
    readonly property color zEndColor:    profileCanvas.endPositionColor
    //: The way the thread is cut, from Z Start to Z End.
    readonly property color travelColor:  Theme.success
    readonly property color majorColor:   "#00838f"
    readonly property color minorColor:   profileCanvas.feedColor
    readonly property color docColor:     "#ad1457"

    // the thread's form - metric for now (ThreadForm, data_types.py) - and
    // the included angle of its flanks
    property string threadForm: "metric"
    readonly property real threadAngle: editor ? editor.threadAngle(threadForm) : 60

    // The diameter calculated from the one taught in and the pitch: Minor Ø
    // from Major Ø for an OD thread, Major Ø from Minor Ø for an ID one. Set,
    // not saved; nothing while the one taught in is not set yet.
    function _recalculateDiameter() {
        if (!root.editor || !(pitch > 0)) return
        var taught = location === "ID" ? minorDiameter : majorDiameter
        if (!(taught > 0)) return
        var r = root.editor.calculateThreadDiameter(location, pitch, majorDiameter, minorDiameter)
        if (!r || !r.valid) return
        if (location === "ID") majorDiameter = Number(r.calculatedDiameter)
        else minorDiameter = Number(r.calculatedDiameter)
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
    // lines of drawn {z, x}. One that runs past Z Start or Z End - its crest
    // or root on the other side is not on the thread: many starts make the
    // lead, and so the half turn's shift, long - is cut there, as the thread
    // ends; and every one clipped at Z0.
    readonly property var helixLines: {
        var out = { crests: [], roots: [] }
        if (!_threadDrawable) return out
        var p = _profile, length = Math.abs(zEnd - zStart), dir = zEnd < zStart ? -1 : 1
        var shift = _upperPhase
        var marks = [[p.crest / 2, majorDiameter], [p.crest + p.flank + p.root / 2, minorDiameter]]
        // from the first line whose far end reaches Z Start to the last whose
        // near end does not pass Z End
        var kFirst = Math.floor(Math.min(0, -shift) / pitch) - 1
        var kLast = Math.ceil(Math.max(length, length - shift) / pitch)
        for (var k = kFirst; k <= kLast; k++)
            for (var m = 0; m < marks.length; m++) {
                var s0 = k * pitch + marks[m][0], s1 = s0 + shift
                var x0 = marks[m][1], x1 = -marks[m][1]
                // cut to the thread: s from 0 (Z Start) to its length (Z End)
                if (s0 === s1) {
                    if (s0 < 0 || s0 > length) continue
                } else {
                    var ta = -s0 / (s1 - s0), tb = (length - s0) / (s1 - s0)
                    var t0 = Math.max(0, Math.min(ta, tb)), t1 = Math.min(1, Math.max(ta, tb))
                    if (t1 - t0 <= 1e-9) continue
                    var cut0 = { s: s0 + (s1 - s0) * t0, x: x0 + (x1 - x0) * t0 }
                    var cut1 = { s: s0 + (s1 - s0) * t1, x: x0 + (x1 - x0) * t1 }
                    s0 = cut0.s; x0 = cut0.x; s1 = cut1.s; x1 = cut1.x
                }
                var z0 = zStart + dir * s0, z1 = zStart + dir * s1
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
        op.location = location
        op.compound_angle = compoundAngle
        op.spring_passes = springPasses
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

        location      = opData.location === "ID" ? "ID" : "OD"
        pitch         = opData.pitch          !== undefined ? Number(opData.pitch) : 0
        starts        = opData.starts         !== undefined ? Math.max(1, Math.round(Number(opData.starts))) : 1
        majorDiameter = opData.major_diameter !== undefined ? Number(opData.major_diameter) : 0
        minorDiameter = opData.minor_diameter !== undefined ? Number(opData.minor_diameter) : 0
        zStart        = opData.z_start        !== undefined ? Number(opData.z_start) : 0
        zEnd          = opData.z_end          !== undefined ? Number(opData.z_end) : 0
        retract       = opData.retract        !== undefined ? Number(opData.retract) : 0
        initialDoc    = opData.initial_doc    !== undefined ? Number(opData.initial_doc) : 0
        compoundAngle = opData.compound_angle !== undefined ? Number(opData.compound_angle) : 0
        springPasses  = opData.spring_passes  !== undefined ? Math.round(Number(opData.spring_passes)) : 0

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
            // the calculated diameter follows the pitch
            onPitchEdited: function(value) {
                root.pitch = value
                root._recalculateDiameter()
                root.save()
            }
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
                // Z End
                { travel: true, x: -zLineDiameter, from: root.zStartDrawn, to: root.zEndDrawn,
                  z: (root.zStartDrawn + root.zEndDrawn) / 2, color: root.travelColor },
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
            // of its extension lines. Mirrored only
            dimensions: {
                if (!mirrorAcrossCenterline) return []
                var dims = []
                if (root.majorDiameter > 0)
                    dims.push({ axis: "x", from: -root.majorDiameter, to: root.majorDiameter,
                                z: Math.max(0, root.zStart), offset: 24, extensionsCentred: true,
                                color: root.majorColor })
                if (root.minorDiameter > 0)
                    dims.push({ axis: "x", from: -root.minorDiameter, to: root.minorDiameter,
                                z: Math.max(0, root.zStart), offset: 48, extensionsCentred: true,
                                color: root.minorColor })
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

            // The cards down the right edge, in a list that scrolls, as
            // Turning has them: a card cut at the list's top or bottom edge
            // fades there. The drawing is fitted into what the list leaves free.
            fitInsetRight: fieldsScroll.width + profileCanvas.tickBand

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
                readonly property var cards: [locationBox, clearanceBox, zRangeBox, diametersBox, passesBox]
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

                    ThreadLocationBox {
                        id: locationBox
                        Layout.alignment: Qt.AlignRight
                        location: root.location
                        onLocationEdited: function(value) { root.location = value; root.save() }
                    }

                    DimensionBox {
                        id: clearanceBox
                        Layout.alignment: Qt.AlignRight
                        label: "Clearance"
                        dimensionColor: profileCanvas.rapidColor
                        settingName: "threading.retract"
                        value: root.retract
                        onValueEdited: function(value) { root.retract = Math.abs(value); root.save() }
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                    }

                    ZRangeBox {
                        id: zRangeBox
                        Layout.alignment: Qt.AlignRight
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

                    // the one taught in first (Major Ø OD, Minor Ø ID), the
                    // other calculated from it and the pitch
                    ThreadDiametersBox {
                        id: diametersBox
                        Layout.alignment: Qt.AlignRight
                        accent: root.location === "ID" ? root.minorColor : root.majorColor
                        majorColor: root.majorColor
                        minorColor: root.minorColor
                        location: root.location
                        majorDiameter: root.majorDiameter
                        minorDiameter: root.minorDiameter
                        onMajorEdited: function(value) { root.majorDiameter = value; root.save() }
                        onMinorEdited: function(value) { root.minorDiameter = value; root.save() }
                        onCalculateRequested: { root._recalculateDiameter(); root.save() }
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                    }

                    ThreadPassesBox {
                        id: passesBox
                        Layout.alignment: Qt.AlignRight
                        accent: root.docColor
                        docColor: root.docColor
                        initialDoc: root.initialDoc
                        infeedAngle: root.compoundAngle
                        springPasses: root.springPasses
                        finalRadialDepth: Math.abs(root.majorDiameter - root.minorDiameter) / 2
                        starts: root.starts
                        onInitialDocEdited: function(value) { root.initialDoc = value; root.save() }
                        onInfeedAngleEdited: function(value) { root.compoundAngle = value; root.save() }
                        onSpringPassesEdited: function(value) { root.springPasses = value; root.save() }
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
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

            // the tool it cuts with, at the top, in the middle; tapped, to
            // pick it - an OD or an ID threading tool, as the thread is
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
