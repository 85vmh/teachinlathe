// ProfileRoughingVisualDetailsView.qml — Profile Roughing with a profile viewer.
// It keeps nothing of its own: all it shows is its editor's operation, and
// every change is the editor's edit, which the operation then shows.
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
    readonly property var _pp: op.profiling_parameters || ({})
    readonly property var _cp: op.cutting_parameters || ({})
    readonly property var _st: op.stock_to_leave || ({})

    // the last profile defined above this operation
    readonly property var _profileOp: editor.lastProfile || ({})
    readonly property var primitives: _profileOp.profile_primitives || []
    readonly property string profileType: _profileOp.profile_type !== undefined ? String(_profileOp.profile_type) : "od"
    // the stock broken off right after the profile, as the Program Header
    // draws its stock
    readonly property var workpiece: {
        var stock = JSON.parse(JSON.stringify(_profileOp.workpiece || {}))
        stock.break_after_profile = true
        return stock
    }
    // the tool it cuts with, as its Tool Library card shows it: editor.toolCard,
    // a ToolCard
    readonly property var toolCard: editor.toolCard

    // what the boxes on the canvas show; X Start the editor gives a value
    // from the profile when it has none
    readonly property real xStart: Number(_pp.x_start || 0)
    readonly property real zStart: Number(_pp.z_start || 0)
    readonly property real stockRadial: Number(_st.radial || 0)
    readonly property real stockAxial: Number(_st.axial || 0)
    readonly property real doc: Number(_cp.doc || 0)
    readonly property real retract: Number(_cp.retract || 0)
    readonly property string passType: op.profile_roughing_strategy && op.profile_roughing_strategy.pass_type
                                       ? String(op.profile_roughing_strategy.pass_type) : "axial"
    readonly property bool isIdProfile: String(profileType).toLowerCase() === "id"

    // Rest material: it cuts what the roughings above it leave, keeping to
    // their stock to leave and start position - neither is set here.
    readonly property bool restMaterial: !!op.rest_material

    // what roughing cuts, worked out in the planning worker, off the GUI
    // thread: the screen goes on - an opening program's slide too - and the
    // drawing follows
    readonly property var roughingPreview: primitives.length > 0 ? editor.plannedPreview : null
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    function editProfiling(changes) { editor.edit({ profiling_parameters: changes }) }
    function editCutting(changes) { editor.edit({ cutting_parameters: changes }) }
    function editStock(changes) { editor.edit({ stock_to_leave: changes }) }

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
                        onPassTypeEdited: function(value) { root.editor.edit({ profile_roughing_strategy: { profiling_type: root.profileType, pass_type: value } }) }
                    }
                    DimensionBox {
                        id: clearanceBox
                        visible: root.primitives.length > 0
                        Layout.alignment: Qt.AlignRight
                        label: "Tool Clearance"
                        dimensionColor: profileCanvas.rapidColor
                        settingName: "profile_roughing.tool_clearance"
                        value: root.retract
                        onValueEdited: function(value) { root.editCutting({ retract: value }) }
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
                            root.editProfiling(axis === "x" ? { x_start: value } : { z_start: value })
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
                        onValueEdited: function(value) { root.editCutting({ doc: value }) }
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                    }
                    StockToLeaveBox {
                        id: stockBox
                        visible: root.primitives.length > 0 && !root.restMaterial
                        Layout.alignment: Qt.AlignRight
                        labelColor: profileCanvas.stockToLeaveColor
                        radial: root.stockRadial
                        axial: root.stockAxial
                        onRadialEdited: function(value) { root.editStock({ radial: value }) }
                        onAxialEdited: function(value) { root.editStock({ axial: value }) }
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
