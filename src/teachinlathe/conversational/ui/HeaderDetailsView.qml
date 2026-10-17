// HeaderDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import touchable_input 1.0
import theme 1.0
import "profile_canvas/brokenstock.js" as Broken

Item {
    id: root
    anchors.fill: parent
    property int fieldFontSize: 16
    readonly property int labelWidth: 150
    readonly property int inputWidth: 90
    readonly property int programNameWidth: 360
    readonly property int inputHeight: 48
    readonly property int inputFontSize: 20
    readonly property int rowGap: 20
    readonly property int columnGap: 8

    // --- Input model ---
    // Expect either applyProgram(programDict) or applyData(_, programDict)
    property var programData: null          // { id, header: { name, last_edit, datum, units, workpiece{...} } }

    // --- Header fields (editable) ---
    property string programName:  (programData && programData.header && programData.header.name) ? programData.header.name : ""
    property int    datum:        (programData && programData.header && programData.header.datum !== undefined) ? programData.header.datum : 0
    // One of "do_nothing" | "g28" | "g30" — mirrors AfterLastOperation in data_types.py
    property string afterLastOperation: (programData && programData.header && programData.header.after_last_operation) ? programData.header.after_last_operation : "do_nothing"

    // Workpiece
    property string material:     (programData && programData.header && programData.header.workpiece && programData.header.workpiece.material) ? programData.header.workpiece.material : ""
    property real   extDia:       (programData && programData.header && programData.header.workpiece && programData.header.workpiece.external_diameter !== undefined) ? programData.header.workpiece.external_diameter : 0.0
    property real   intDia:       (programData && programData.header && programData.header.workpiece && programData.header.workpiece.internal_diameter !== undefined) ? programData.header.workpiece.internal_diameter : 0.0
    property real   stickout:     (programData && programData.header && programData.header.workpiece && programData.header.workpiece.stickout_length !== undefined) ? programData.header.workpiece.stickout_length : 0.0
    property real   stockLength:  (programData && programData.header && programData.header.workpiece && programData.header.workpiece.stock_length !== undefined) ? programData.header.workpiece.stock_length : 0.0

    // --- Bridge signals (same pattern as other detail views) ---
    signal saveRequested(var updated)
    signal openNumPadRequested(var field)
    signal openKeyboardRequested(var field)

    // Populate from Program object
    function applyProgram(program) {
        programData = program || {}
        programName = (programData.header && programData.header.name) ? programData.header.name : ""
        datum       = (programData.header && programData.header.datum !== undefined) ? programData.header.datum : 0
        afterLastOperation = (programData.header && programData.header.after_last_operation) ? programData.header.after_last_operation : "do_nothing"

        if (programData.header && programData.header.workpiece) {
            var wp = programData.header.workpiece
            material = (wp.material !== undefined) ? wp.material : ""
            extDia   = (wp.external_diameter !== undefined) ? wp.external_diameter : 0.0
            intDia   = (wp.internal_diameter !== undefined) ? wp.internal_diameter : 0.0
            stickout = (wp.stickout_length  !== undefined) ? wp.stickout_length  : 0.0
            stockLength = (wp.stock_length !== undefined) ? wp.stock_length : 0.0
        } else {
            material = ""
            extDia = intDia = stickout = 0.0
            stockLength = 0.0
        }
    }

    // Keep compatibility with ChildScreen.receiveDetailsData if you ever pass the full program
    function applyData(index, data) {
        applyProgram(data)
    }

    function emitSave() {
        var payload = {
            type: "header",
            header: {
                name: programName,
                // last_edit is set server-side; omit or leave as previous
                datum: datum,
                units: "mm",
                after_last_operation: afterLastOperation,
                workpiece: {
                    material: material,
                    external_diameter: extDia,
                    internal_diameter: intDia,
                    stickout_length:  stickout,
                    stock_length: stockLength
                }
            }
        }
        root.saveRequested({ index: -1, payload: payload })
    }

    // the insert type's dropdown, from the tool editors
    component Choice: ComboBox {
        // just wide enough for its text and the arrow: the padding on the
        // right already holds the arrow
        Layout.preferredWidth: leftPadding + contentItem.implicitWidth + rightPadding
        Layout.preferredHeight: Theme.inputHeight
        font.pixelSize: Theme.fontTitle
        contentItem: Text {
            leftPadding: 8
            rightPadding: 8
            text: parent.displayText
            font: parent.font
            color: Theme.foregroundStrong
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        delegate: Component {
            ItemDelegate {
                width: parent ? parent.width : 0
                height: Theme.inputHeight
                text: modelData
                font.pixelSize: Theme.fontTitle
            }
        }
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // Program Details, then On Program Finished as tall
        RowLayout {
            id: topRow
            Layout.fillWidth: true
            spacing: Theme.innerSpacings

            GroupBox {
                id: programDetails
                title: "Program Details"
                Layout.alignment: Qt.AlignTop
                font.pixelSize: root.fieldFontSize

                RowLayout {
                    anchors.fill: parent
                    spacing: Theme.spacing

                    Label {
                        text: "Program name"
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: root.fieldFontSize
                    }
                    KeyboardField {
                        Layout.preferredWidth: root.programNameWidth
                        Layout.preferredHeight: root.inputHeight
                        font.pixelSize: root.inputFontSize
                        titleText: "Program name"
                        text: root.programName
                        commitUpdatesText: false
                        onOpenRequested: root.openKeyboardRequested(field)
                        onValueCommitted: {
                            root.programName = value
                            root.emitSave()
                        }
                    }

                    Rectangle {
                        implicitWidth: Theme.hairline
                        Layout.fillHeight: true
                        color: Theme.outline
                    }

                    Label {
                        text: "Datum"
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: root.fieldFontSize
                    }
                    // G54..G59, saved as the work offset's P number, 1..6
                    Choice {
                        model: ["G54", "G55", "G56", "G57", "G58", "G59"]
                        currentIndex: (root.datum >= 1 && root.datum <= 6) ? root.datum - 1 : 0
                        onActivated: function(index) { root.datum = index + 1; root.emitSave() }
                    }
                }
            }

            GroupBox {
                title: "On Program Finished"
                Layout.alignment: Qt.AlignTop
                // whatever width Program Details leaves, and as tall
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 0
                Layout.preferredHeight: programDetails.implicitHeight
                font.pixelSize: root.fieldFontSize

                ButtonGroup { id: afterLastGroup }

                // the buttons as wide as their texts, the space left shared
                // out equally between them: first at the left, last at the right
                RowLayout {
                    anchors.fill: parent
                    spacing: 0

                    Repeater {
                        model: [
                            { value: "do_nothing", label: "Do nothing" },
                            { value: "g28",        label: "Retract at <b>G28</b>" },
                            { value: "g30",        label: "Retract at <b>G30</b>" }
                        ]
                        // a stretch, then the button; the first without it
                        RowLayout {
                            spacing: 0
                            Layout.fillWidth: index > 0
                            Item { visible: index > 0; Layout.fillWidth: true }
                            RadioButton {
                                text: modelData.label
                                font.pixelSize: Theme.fontBody
                                ButtonGroup.group: afterLastGroup
                                checked: root.afterLastOperation === modelData.value
                                onToggled: if (checked && root.afterLastOperation !== modelData.value) {
                                    root.afterLastOperation = modelData.value
                                    root.emitSave()
                                }
                            }
                        }
                    }
                }
            }
        }

        // The workpiece, hatched, with its dimensions: the diameters right of
        // the face, the lengths below it, each pointing to the box with its
        // value down the right edge.
        ProfileCanvas {
            id: workpieceCanvas
            showTransitions: false
            // a dot at both ends of each arrow to a box
            arrowStartDots: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            // pinch and the buttons zoom, a drag pans, a double tap fits
            selectable: false
            // the backplot's step (glnav's zoomin / zoomout)
            zoomStep: 1.1
            primitives: []
            // The stock drawn from its face, its far end always broken off
            // (brokenstock.js). Up to twice its diameter it is drawn whole;
            // longer, its middle is left out too, so it is drawn twice its
            // diameter long: the piece at the face and the far piece, a gap
            // between. stock_length here is how much is drawn; the boxes keep
            // the true values.
            readonly property bool breakMiddle: root.extDia > 0 && root.stockLength > 2 * root.extDia
            // the gap: as far as the two breaks reach into it, and a clearance
            readonly property real gap: (Broken.reach(1.0) + 0.06) * root.extDia
            // each piece's length, and where the drawing ends
            readonly property real pieceLength: (2 * root.extDia - gap) / 2
            readonly property real drawnLength: breakMiddle ? 2 * root.extDia : root.stockLength
            // in drawn Z: where the piece at the face is broken off, where the
            // far piece starts; a real Z on the far piece is drawn at real + shift
            readonly property var middle: breakMiddle
                ? { near: -pieceLength, far: -(pieceLength + gap), shift: root.stockLength - 2 * root.extDia }
                : null
            // a real Z, where it is drawn: on the far piece moved by the shift,
            // in the stretch left out at the gap's middle
            function drawnZ(z) {
                if (!middle || z >= middle.near) return z
                if (z <= -root.stockLength + pieceLength) return z + middle.shift
                return (middle.near + middle.far) / 2
            }
            workpiece: ({ external_diameter: root.extDia, internal_diameter: root.intDia,
                          stickout_length: root.stickout, stock_length: drawnLength,
                          break_far_end: true,
                          break_middle: middle ? { near: middle.near, far: middle.far } : null })
            axisBreak: middle

            readonly property color externalColor: "#1565c0"
            readonly property color internalColor: "#6a1b9a"
            readonly property color stickoutColor: "#00838f"
            readonly property color stockLengthColor: "#ad1457"

            // px from the part: the inner dimension first, the outer beyond it
            readonly property real nearOffset: 24
            readonly property real farOffset: 48
            fitPadding: farOffset + 16
            // Internal Ø inside the stock, across the bore 3/4 of the way from
            // its Z- end, its leader from the lower half; the stock length
            // above the part, the stickout below it
            dimensions: {
                var dims = [
                    // to the drawn ends: the stock to the break, the stickout to
                    // where it ends - at the break if it reaches past it
                    { axis: "z", from: 0, to: -drawnLength, x: -root.extDia, offset: -nearOffset,
                      color: stockLengthColor, arrowToRect: stockLengthBox.rect },
                    { axis: "x", from: -root.extDia, to: root.extDia, z: 0, offset: nearOffset,
                      color: externalColor, arrowToRect: externalBox.rect },
                    { axis: "z", from: 0, to: drawnZ(-root.stickout), x: root.extDia, offset: nearOffset,
                      color: stickoutColor, arrowToRect: stickoutBox.rect }
                ]
                if (root.intDia > 0)
                    dims.push({ axis: "x", from: root.intDia, to: -root.intDia, z: -(breakMiddle ? pieceLength : drawnLength) / 4, offset: 0,
                                color: internalColor, arrowToRect: internalBox.rect })
                return dims
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline; border.width: Theme.hairline
            }

            // The boxes stack down the right edge, each as wide as it needs;
            // the drawing is fitted into what the widest leaves free.
            readonly property real boxWidth: Math.max(externalBox.implicitWidth, internalBox.implicitWidth,
                                                      stickoutBox.implicitWidth, stockLengthBox.implicitWidth)
            readonly property real boxGap: Theme.spacingLarge
            fitInsetRight: boxWidth + boxGap

            // top to bottom: stock length, the two diameters, stickout - each
            // near its dimension - the first at the top, the last at the
            // bottom, the space between them shared out equally
            readonly property real boxSpacing: (height - 2 * boxGap - stockLengthBox.height - externalBox.height
                                                - internalBox.height - stickoutBox.height) / 3
            DimensionBox {
                id: stockLengthBox
                x: workpieceCanvas.width - width - workpieceCanvas.boxGap
                y: workpieceCanvas.boxGap
                label: "Stock length"
                dimensionColor: workpieceCanvas.stockLengthColor
                settingName: "smart_numpad.workpiece-stock-length"
                value: root.stockLength
                // the stickout cannot be longer: it comes down with it
                onValueEdited: function(value) {
                    root.stockLength = value
                    root.stickout = Math.min(root.stickout, value)
                    root.emitSave()
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            DimensionBox {
                id: externalBox
                x: workpieceCanvas.width - width - workpieceCanvas.boxGap
                y: stockLengthBox.y + stockLengthBox.height + workpieceCanvas.boxSpacing
                label: "External Ø"
                dimensionColor: workpieceCanvas.externalColor
                settingName: "smart_numpad.workpiece-external-dia"
                value: root.extDia
                onValueEdited: function(value) { root.extDia = value; root.emitSave() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            DimensionBox {
                id: internalBox
                x: workpieceCanvas.width - width - workpieceCanvas.boxGap
                y: externalBox.y + externalBox.height + workpieceCanvas.boxSpacing
                label: "Internal Ø"
                dimensionColor: workpieceCanvas.internalColor
                settingName: "smart_numpad.workpiece-internal-dia"
                value: root.intDia
                onValueEdited: function(value) { root.intDia = value; root.emitSave() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            DimensionBox {
                id: stickoutBox
                x: workpieceCanvas.width - width - workpieceCanvas.boxGap
                y: internalBox.y + internalBox.height + workpieceCanvas.boxSpacing
                label: "Stickout"
                dimensionColor: workpieceCanvas.stickoutColor
                settingName: "smart_numpad.workpiece-stickout"
                value: root.stickout
                // no longer than the stock
                onValueEdited: function(value) {
                    root.stickout = Math.min(value, root.stockLength)
                    root.emitSave()
                }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // zoom, fit to screen - top-left, as on every profile canvas
            CanvasViewButtons {
                canvas: workpieceCanvas
                // only the workpiece here: nothing to mirror
                showMirror: false
            }
        }
    }
}
