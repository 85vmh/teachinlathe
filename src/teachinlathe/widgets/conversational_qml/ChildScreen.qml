import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: operationEditor
    objectName: "childScreen"

    // Inputs from Python
    property var selectedProgram: null            // { id, name, last_edit }
    property var operationsModel: []              // [{ order, type, display_type, generate_gcode, is_optional_block, ... }]

    // Navigation
    property bool showBack: true
    signal backRequested()

    // Persist changes to Python (list-level toggles)
    signal toggleGenerateGcode(int index, bool checked)
    signal toggleOptionalBlock(int index, bool checked)

    // Detail view <-> Python bridge
    signal detailsRequested(int index)                 // ask Python for full op dict
    signal updateToolChange(int index, var payload)    // send edited ToolChange back to Python
    signal updateFacing(int index, var payload)
    signal updateProfiling(int index, var payload)

    signal teachXRequested(int index)
    signal teachZRequested(int index)
    signal openNumPadRequested(var field)

    width: parent ? parent.width : 1000
    height: parent ? parent.height : 700

    // Title
    property string titleText: selectedProgram && selectedProgram.name
                               ? "Edit: " + selectedProgram.name
                               : "New Program"

    // Column width constants (kept in sync between header and rows)
    readonly property int colOpNumW: 40
    readonly property int colGenW:   100
    readonly property int colTypeW:  200
    readonly property int colOptW:   100

    // Called by Python with a full operation dict; decides which details view to load
    function receiveDetailsData(index, data) {
        if (!data || !data.type) {
            detailsLoader.source = ""
            return
        }
        if (data.type === "changeTool") {
            detailsLoader.source = "ToolChangeDetailsView.qml"
        } else if (data.type === "facing") {
            detailsLoader.source = "FacingDetailsView.qml"
        } else if (data.type === "profiling") {
            detailsLoader.source = "ProfilingDetailsView.qml"
        } else {
            detailsLoader.source = ""   // TODO: set other operation detail QMLs here
        }
        // Apply data after the component is constructed
        Qt.callLater(function() {
            if (detailsLoader.item && detailsLoader.item.applyData) {
                detailsLoader.item.applyData(index, data)
            }
        })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        // Top bar
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: "Back"
                visible: operationEditor.showBack
                onClicked: operationEditor.backRequested()
            }

            Label {
                text: operationEditor.titleText
                font.pixelSize: 22
                font.bold: true
                Layout.fillWidth: true
            }
        }

        // Content: left list + right details
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            // LEFT: operations table (header above the ListView) – 0.33 of parent width
            Rectangle {
                Layout.preferredWidth: Math.round(parent.width * 0.33)
                Layout.fillHeight: true
                color: "#ffffff"
                radius: 6
                border.color: "#ccc"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    // HEADER (fixed 40px)
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.minimumHeight: 40
                        Layout.preferredHeight: 40
                        Layout.maximumHeight: 40
                        spacing: 0

                        // Op #
                        Label {
                            text: "Op #"
                            Layout.minimumWidth: operationEditor.colOpNumW
                            Layout.preferredWidth: operationEditor.colOpNumW
                            Layout.maximumWidth: operationEditor.colOpNumW
                            leftPadding: 8
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                        // Generate GCode
                        Label {
                            text: "Generate\nG-Code"
                            Layout.minimumWidth: operationEditor.colGenW
                            Layout.preferredWidth: operationEditor.colGenW
                            Layout.maximumWidth: operationEditor.colGenW
                            leftPadding: 8
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                        // OperationType
                        Label {
                            text: "Operation Type"
                            Layout.minimumWidth: operationEditor.colTypeW
                            Layout.preferredWidth: operationEditor.colTypeW
                            Layout.maximumWidth: operationEditor.colTypeW
                            leftPadding: 8
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                            elide: Text.ElideRight
                        }

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                        // OptionalBlock
                        Label {
                            text: "Optional Block"
                            Layout.minimumWidth: operationEditor.colOptW
                            Layout.preferredWidth: operationEditor.colOptW
                            Layout.maximumWidth: operationEditor.colOptW
                            leftPadding: 8
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                        }

                        // Flexible spacer so header and rows share the same leftover space
                        Item { Layout.fillWidth: true }
                    }

                    // LIST
                    ListView {
                        id: opsList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: operationEditor.operationsModel
                        currentIndex: -1
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0)
                                operationEditor.detailsRequested(currentIndex) // Python will call receiveDetailsData(...)
                        }

                        delegate: Rectangle {
                            width: ListView.view ? ListView.view.width : 400
                            height: 60
                            radius: 0

                            // Alternating background; unchanged on selection
                            color: (index % 2 === 0 ? "#fafafa" : "#f0f0f0")

                            // Only a 1px light-blue border when selected
                            border.width: ListView.isCurrentItem ? 1 : 0
                            border.color: "#8ec5ff"

                            // Easier binding alias
                            property var op: modelData

                            RowLayout {
                                anchors.fill: parent
                                spacing: 0

                                // Op #
                                Label {
                                    text: (op && op.order !== undefined) ? op.order : (index + 1)
                                    Layout.minimumWidth: operationEditor.colOpNumW
                                    Layout.preferredWidth: operationEditor.colOpNumW
                                    Layout.maximumWidth: operationEditor.colOpNumW
                                    leftPadding: 8
                                    verticalAlignment: Text.AlignVCenter
                                    Layout.alignment: Qt.AlignVCenter
                                }

                                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                                // Generate GCode (checkbox centered in cell)
                                Item {
                                    Layout.minimumWidth: operationEditor.colGenW
                                    Layout.preferredWidth: operationEditor.colGenW
                                    Layout.maximumWidth: operationEditor.colGenW
                                    Layout.fillHeight: true

                                    CheckBox {
                                        anchors.centerIn: parent    // centered horizontally & vertically
                                        checked: !!(op && op.generate_gcode)
                                        onToggled: {
                                            if (op) {
                                                op.generate_gcode = checked;        // reflect in UI model
                                                operationEditor.toggleGenerateGcode(index, checked) // notify Python
                                            }
                                        }
                                    }
                                }

                                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                                // OperationType (pre-computed in Python as 'display_type')
                                Label {
                                    text: (op && op.display_type) ? op.display_type : (op && op.type ? op.type : "")
                                    Layout.minimumWidth: operationEditor.colTypeW
                                    Layout.preferredWidth: operationEditor.colTypeW
                                    Layout.maximumWidth: operationEditor.colTypeW
                                    leftPadding: 8
                                    elide: Text.ElideRight
                                    verticalAlignment: Text.AlignVCenter
                                    Layout.alignment: Qt.AlignVCenter
                                }

                                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                                // OptionalBlock (checkbox centered in cell)
                                Item {
                                    Layout.minimumWidth: operationEditor.colOptW
                                    Layout.preferredWidth: operationEditor.colOptW
                                    Layout.maximumWidth: operationEditor.colOptW
                                    Layout.fillHeight: true

                                    CheckBox {
                                        anchors.centerIn: parent    // centered horizontally & vertically
                                        checked: !!(op && op.is_optional_block)
                                        onToggled: {
                                            if (op) {
                                                op.is_optional_block = checked;     // reflect in UI model
                                                operationEditor.toggleOptionalBlock(index, checked) // notify Python
                                            }
                                        }
                                    }
                                }

                                // Flexible spacer to consume the same leftover space as header
                                Item { Layout.fillWidth: true }
                            }

                            TapHandler { onTapped: opsList.currentIndex = index }
                        }
                    }
                }
            }

            // RIGHT: details pane (Loader switches per operation type)
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#f5f5f5"
                radius: 6
                border.color: "#ccc"
                border.width: 1

                Loader {
                    id: detailsLoader
                    anchors.fill: parent
                    asynchronous: false  // ensure component is ready before we wire signals

                    // When a details component is loaded, connect its signals
                    onLoaded: {
                        if (!item) return

                        // Bridge child's Save -> ChildScreen -> Python
                        if (item.saveRequested) {
                            item.saveRequested.connect(function(updated) {
                                if (!updated || !updated.payload) return
                                var t = updated.payload.type || ""
                                if (t === "changeTool" && operationEditor.updateToolChange) {
                                    operationEditor.updateToolChange(updated.index, updated.payload)
                                } else if (t === "facing" && operationEditor.updateFacing) {
                                    operationEditor.updateFacing(updated.index, updated.payload)
                                } else if (operationEditor.updateOperation) {
                                    // optional catch-all if you add it later
                                    operationEditor.updateOperation(updated.index, updated.payload)
                                }
                            })
                        }

                        if (item.openNumPadRequested)
                            item.openNumPadRequested.connect(function(field) { operationEditor.openNumPadRequested(field) })

                        if (item.saveRequested) {
                            item.saveRequested.connect(function(updated) {
                                if (!updated || !updated.payload) return
                                if (updated.payload.type === "profiling" && operationEditor.updateProfiling)
                                    operationEditor.updateProfiling(updated.index, updated.payload)
                            })
                        }
                        if (item.openNumPadRequested)
                            item.openNumPadRequested.connect(function(field){ operationEditor.openNumPadRequested(field) })

                        // Optional teach hooks (present on ToolChangeDetailsView)
                        if (item.teachXRequested)
                            item.teachXRequested.connect(function(i) { operationEditor.teachXRequested(i) })
                        if (item.teachZRequested)
                            item.teachZRequested.connect(function(i) { operationEditor.teachZRequested(i) })

                        // Do NOT auto-apply shallow data from operationsModel here.
                        // receiveDetailsData(index, data) already calls item.applyData(...) with the FULL dict.
                    }
                }
            }
        }
    }
}
