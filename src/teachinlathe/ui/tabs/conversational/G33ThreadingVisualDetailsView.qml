// G33ThreadingVisualDetailsView.qml — G33 Threading on the profile canvas,
// laid out as Parting's: the header's Speeds and Feeds (RPM only, Pitch and
// Starts for its feeds) with Pause to Inspect, and the thread cut in a stock
// drawn as Parting draws its: broken off past the thread's far end, and
// further from Z0 than its diameter its middle left out too, so that end sits
// a quarter diameter along the far piece - for an OD thread a bar as big as
// Major Ø, for an ID one a tube, its bore Minor Ø. The thread itself is
// thread.js's. Z Start and Z End each a line across the centre line, Major Ø
// and Minor Ø dimensioned in front of the stock; the threading insert on Z
// Start, Clearance off the diameter it is taught in on. The values in cards
// down the right edge, in a list that scrolls, as Turning has them: OD / ID,
// Clearance, Z Start / Z End, Major Ø and Minor Ø, and the passes (DOC,
// Infeed Angle, Spring Passes). It keeps nothing of its own: all it shows is
// its editor's operation, and every change is the editor's edit, which the
// operation then shows.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import "profile_canvas/brokenstock.js" as Broken
import "profile_canvas/thread.js" as Thread
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place what the view shows comes from, and every edit goes to
    required property var editor
    readonly property var op: editor.operation

    // the program header's stock
    readonly property var workpiece: editor.workpiece || ({})
    // the tool it cuts with, as its Tool Library card shows it: editor.toolCard,
    // a ToolCard
    readonly property var toolCard: editor.toolCard

    // what the boxes on the canvas show
    // "OD" | "ID": an ID thread is taught in on its Minor Ø, its Major Ø
    // calculated
    readonly property string location: op.location === "ID" ? "ID" : "OD"
    readonly property real   pitch: Number(op.pitch || 0)
    readonly property int    starts: op.starts !== undefined ? Math.max(1, Math.round(Number(op.starts))) : 1
    readonly property real   majorDiameter: Number(op.major_diameter || 0)
    readonly property real   minorDiameter: Number(op.minor_diameter || 0)
    readonly property real   zStart: Number(op.z_start || 0)
    readonly property real   zEnd: Number(op.z_end || 0)
    readonly property real   retract: Number(op.retract || 0)
    readonly property real   initialDoc: Number(op.initial_doc || 0)
    readonly property real   compoundAngle: Number(op.compound_angle || 0)
    readonly property int    springPasses: Math.round(Number(op.spring_passes || 0))

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
    readonly property string threadForm: "metric"
    readonly property real threadAngle: editor.threadAngle(threadForm)

    // An ID thread is drawn in a tube: its bore Minor Ø - the hole before the
    // thread is cut - its wall this many times the thread's depth on each
    // side, as it is drawn: Major Ø + idWallFactor (Major Ø - Minor Ø)
    // across. A drawing's measure, not the stock's: to be adapted.
    readonly property real idWallFactor: 5
    readonly property bool internal: location === "ID"
    // the stock as drawn: as big as Major Ø - an ID thread's tube, its wall
    // round it - or the header's until that is set
    readonly property real stockDiameter: {
        if (internal && majorDiameter > 0 && minorDiameter > 0)
            return majorDiameter + idWallFactor * Math.abs(majorDiameter - minorDiameter)
        if (!internal && majorDiameter > 0) return majorDiameter
        return Number(workpiece && workpiece.external_diameter) || 0
    }
    // The thread's ends along the stock, whichever way it is cut: ``zFar``
    // the one toward the chuck - Z End cutting toward it (right-hand), Z
    // Start cutting away from it (left-hand) - and ``zNear`` the one toward
    // the face.
    readonly property real zFar: Math.min(zStart, zEnd)
    readonly property real zNear: Math.max(zStart, zEnd)
    // Further from Z0 than its diameter, the stock's middle is left out, as
    // Parting leaves it out, the thread's far end a quarter diameter along
    // the far piece, broken off a quarter diameter past it; null when not
    readonly property var middleBreak: Broken.middleBreak(stockDiameter, zFar)
    function drawnZ(z) { return Broken.drawnZ(middleBreak, z) }
    readonly property real zEndDrawn: drawnZ(zEnd)
    readonly property real zStartDrawn: drawnZ(zStart)
    readonly property real zFarDrawn: drawnZ(zFar)

    // The thread seen from the side (thread.js): {lower, upper, crests,
    // roots, face}, lines of drawn {z, x}
    readonly property var thread: Thread.drawing({
        zStart: zStart, zEnd: zEnd, pitch: pitch, starts: starts,
        major: majorDiameter, minor: minorDiameter, angle: threadAngle, brk: middleBreak })

    // where the insert starts each pass, as the G-code has it: Clearance out
    // from Major Ø, for an ID thread in from Minor Ø
    readonly property real startX: internal ? minorDiameter - retract : majorDiameter + retract
    signal openNumPadRequested(var field)

    // another operation: the drawing fitted to it
    onEditorChanged: profileCanvas.resetView()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // RPM only; its feeds are the pitch and the starts
        OperationHeader {
            id: header
            editor: root.editor
            rpmOnly: true
            feedKind: SpeedsAndFeeds.FeedKind.Threading
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
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
            // the header's stock, as big as Major Ø, broken off past the
            // thread's far end - and its middle left out when that is far down
            // it; the header's bore kept
            workpiece: {
                var w = JSON.parse(JSON.stringify(root.workpiece || {}))
                if (root.stockDiameter > 0) w.external_diameter = root.stockDiameter
                // an ID thread's tube: its bore Minor Ø
                if (root.internal && root.minorDiameter > 0) w.internal_diameter = root.minorDiameter
                w.stock_length = Math.max(Number(w.stock_length) || 0, Math.abs(root.zFar) + root.stockDiameter)
                w.break_far_end = false
                w.break_after_z = root.zFarDrawn
                w.break_middle = root.middleBreak
                if (root.middleBreak) w.break_after_setback = 0.25 * root.stockDiameter
                // the thread cut into it: its profile the stock's outline there
                w.thread = { lower: root.thread.lower, upper: root.thread.upper, internal: root.internal,
                             from: root.drawnZ(Math.min(root.zNear, 0)), to: root.zFarDrawn }
                return w
            }
            axisBreak: root.middleBreak

            // the Z lines across the centre line, past the stock
            readonly property real zLineDiameter: Math.max(root.stockDiameter, root.majorDiameter, 10) * 1.2
            markers: [
                { line: true, x: zLineDiameter, z: root.zStartDrawn, color: root.zStartColor },
                { line: true, x: zLineDiameter, z: root.zEndDrawn, color: root.zEndColor },
                // the way the thread is cut, across the lines' top ends, to
                // Z End
                { travel: true, x: -zLineDiameter, from: root.zStartDrawn, to: root.zEndDrawn,
                  z: (root.zStartDrawn + root.zEndDrawn) / 2, color: root.travelColor },
                // the thread: its profile under the centre line, the far
                // half's over it, and the helix joining them
                { polyline: root.thread.lower, color: "#455a64" },
                { polyline: root.thread.upper, color: "#455a64", visible: mirrorAcrossCenterline },
                { polyline: root.thread.crests, color: "#455a64", lineWidth: 1, visible: mirrorAcrossCenterline },
                { polyline: root.thread.roots, color: "#ef6c00", lineWidth: 1, visible: mirrorAcrossCenterline },
                // the face, where the thread is clipped at Z0
                { polyline: root.thread.face, color: "#455a64", visible: mirrorAcrossCenterline }
            ]
            // Major Ø then Minor Ø in front of the stock, each at the middle
            // of its extension lines. Mirrored only
            dimensions: {
                if (!mirrorAcrossCenterline) return []
                var dims = []
                if (root.majorDiameter > 0)
                    dims.push({ axis: "x", from: -root.majorDiameter, to: root.majorDiameter,
                                z: Math.max(0, root.zNear), offset: 24, extensionsCentred: true,
                                color: root.majorColor })
                if (root.minorDiameter > 0)
                    dims.push({ axis: "x", from: -root.minorDiameter, to: root.minorDiameter,
                                z: Math.max(0, root.zNear), offset: 48, extensionsCentred: true,
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
                        onLocationEdited: function(value) { root.editor.edit({ location: value }) }
                    }

                    DimensionBox {
                        id: clearanceBox
                        Layout.alignment: Qt.AlignRight
                        label: "Clearance"
                        dimensionColor: profileCanvas.rapidColor
                        settingName: "threading.retract"
                        value: root.retract
                        onValueEdited: function(value) { root.editor.edit({ retract: Math.abs(value) }) }
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
                        onZStartEdited: function(value) { root.editor.edit({ z_start: value }) }
                        onZEndEdited: function(value) { root.editor.edit({ z_end: value }) }
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
                        onMajorEdited: function(value) { root.editor.edit({ major_diameter: value }) }
                        onMinorEdited: function(value) { root.editor.edit({ minor_diameter: value }) }
                        onCalculateRequested: root.editor.calculateDiameter()
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
                        onInitialDocEdited: function(value) { root.editor.edit({ initial_doc: value }) }
                        onInfeedAngleEdited: function(value) { root.editor.edit({ compound_angle: value }) }
                        onSpringPassesEdited: function(value) { root.editor.edit({ spring_passes: value }) }
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
