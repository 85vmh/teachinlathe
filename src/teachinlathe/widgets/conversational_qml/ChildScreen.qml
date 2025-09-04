import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."   // to import local components like Divider.qml


Item {
    id: operationEditor
    objectName: "childScreen"

    // Inputs from Python
    property var selectedProgram: null
    property var operationsModel: []

    // Navigation
    property bool showBack: true
    signal backRequested()
    signal generateGcodeRequested()


    // List-level toggles (autosave in Python)
    signal toggleGenerateGcode(int index, bool checked)
    signal toggleOptionalBlock(int index, bool checked)

    // Details bridge
    signal detailsRequested(int index)
    signal updateToolChange(int index, var payload)
    signal updateFacing(int index, var payload)
    signal updateProfiling(int index, var payload)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    width: parent ? parent.width : 1200
    height: parent ? parent.height : 800

    property string titleText: (selectedProgram && (selectedProgram.name || (selectedProgram.header && selectedProgram.header.name)))
                               ? "Editing: " + (selectedProgram.name || selectedProgram.header.name)
                               : "Creating New Program"

    // Column widths
    readonly property int colOpNumW: 50
    readonly property int colGenW:   80
    readonly property int colTypeW:  240
    readonly property int colOptW:   80

    // Called by Python with full op dict; decides which details view to load
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
            detailsLoader.source = ""
        }
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

        // Top bar (Back left, centered title, Generate GCode button right)
        Item {
            Layout.fillWidth: true
            height: 48

            // Left: Back
            Button {
                text: "Back"
                visible: operationEditor.showBack
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                onClicked: operationEditor.backRequested()
            }

            // Center: Title (always visually centered)
            Label {
                text: operationEditor.titleText
                font.pixelSize: 22
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
            }

            // Right: Generate GCode (for the whole current program)
            Button {
                text: "Build G-Code Program"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                enabled: operationEditor.operationsModel
                         && operationEditor.operationsModel.length > 0
                onClicked: operationEditor.generateGcodeRequested()
            }
        }

        // Content
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            // LEFT: operations list (~1/3)
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

                    // Header
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.minimumHeight: 40
                        Layout.preferredHeight: 40
                        Layout.maximumHeight: 40
                        spacing: 0

                        Label {
                            text: "Order"
                            Layout.minimumWidth: operationEditor.colOpNumW
                            Layout.preferredWidth: operationEditor.colOpNumW
                            Layout.maximumWidth: operationEditor.colOpNumW
                            leftPadding: 8
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Divider { }

                        Label {
                            text: "Generate\nGCode"
                            Layout.minimumWidth: operationEditor.colGenW
                            Layout.preferredWidth: operationEditor.colGenW
                            Layout.maximumWidth: operationEditor.colGenW

                            // center text in the cell, even on multiple lines
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter

                            // let it wrap if needed
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2

                            // no offset that would pull it left
                            leftPadding: 0
                            rightPadding: 0
                            font.bold: true

                            // keeps the Label itself centered on the row’s height
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Divider { }

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
                        Divider { }

                        Label {
                            text: "Optional\nBlock"
                            Layout.minimumWidth: operationEditor.colOptW
                            Layout.preferredWidth: operationEditor.colOptW
                            Layout.maximumWidth: operationEditor.colOptW
                             // center text in the cell, even on multiple lines
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter

                            // let it wrap if needed
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2

                            // no offset that would pull it left
                            leftPadding: 0
                            rightPadding: 0
                            font.bold: true

                            // keeps the Label itself centered on the row’s height
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Item { Layout.fillWidth: true }
                    }

                    // List
                    ListView {
                        id: opsList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: operationEditor.operationsModel
                        currentIndex: -1
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0)
                                operationEditor.detailsRequested(currentIndex)
                        }

                        delegate: Rectangle {
                            width: ListView.view ? ListView.view.width : 400
                            height: 60
                            radius: 0
                            color: (index % 2 === 0 ? "#fafafa" : "#f0f0f0")
                            border.width: ListView.isCurrentItem ? 1 : 0
                            border.color: "#8ec5ff"

                            property var op: modelData

                            RowLayout {
                                anchors.fill: parent
                                spacing: 0

                                Label {
                                    text: (op && op.order !== undefined) ? op.order : (index + 1)

                                    Layout.minimumWidth:  operationEditor.colOpNumW
                                    Layout.preferredWidth: operationEditor.colOpNumW
                                    Layout.maximumWidth:  operationEditor.colOpNumW
                                    Layout.alignment: Qt.AlignVCenter   // keep vertical centering of the control
                                    // Layout.fillHeight: true           // optional

                                    // center text inside the cell
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment:   Text.AlignVCenter
                                    leftPadding: 0
                                    rightPadding: 0
                                }

                                Divider { }

                                Item {
                                    Layout.minimumWidth: operationEditor.colGenW
                                    Layout.preferredWidth: operationEditor.colGenW
                                    Layout.maximumWidth: operationEditor.colGenW
                                    Layout.fillHeight: true
                                    CheckBox {
                                        anchors.centerIn: parent
                                        checked: !!(op && op.generate_gcode)
                                        onToggled: {
                                            if (op) {
                                                op.generate_gcode = checked
                                                operationEditor.toggleGenerateGcode(index, checked)
                                            }
                                        }
                                    }
                                }
                                Divider { }

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
                                Divider { }

                                Item {
                                    Layout.minimumWidth: operationEditor.colOptW
                                    Layout.preferredWidth: operationEditor.colOptW
                                    Layout.maximumWidth: operationEditor.colOptW
                                    Layout.fillHeight: true
                                    CheckBox {
                                        anchors.centerIn: parent
                                        checked: !!(op && op.is_optional_block)
                                        onToggled: {
                                            if (op) {
                                                op.is_optional_block = checked
                                                operationEditor.toggleOptionalBlock(index, checked)
                                            }
                                        }
                                    }
                                }
                                Item { Layout.fillWidth: true }
                            }

                            TapHandler { onTapped: opsList.currentIndex = index }
                        }
                    }
                }
            }

            // RIGHT: details (Loader + single Connections)
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
                    asynchronous: false
                }

                Connections {
                    id: detailsCon
                    target: detailsLoader.item
                    ignoreUnknownSignals: true   // ignore signals that some detail views don't define
                    enabled: !!target            // safety: only active when a component is loaded

                    // Any change in details view calls saveRequested(updated) → autosave
                    function onSaveRequested(updated) {
                        if (!updated || !updated.payload) return
                        var t = updated.payload.type || ""
                        if (t === "changeTool" && operationEditor.updateToolChange)
                            operationEditor.updateToolChange(updated.index, updated.payload)
                        else if (t === "facing" && operationEditor.updateFacing)
                            operationEditor.updateFacing(updated.index, updated.payload)
                        else if (t === "profiling" && operationEditor.updateProfiling)
                            operationEditor.updateProfiling(updated.index, updated.payload)
                        else if (operationEditor.updateOperation)
                            operationEditor.updateOperation(updated.index, updated.payload)
                    }

                    // ToolChange extras
                    function onTeachXRequested(i) { operationEditor.teachXRequested(i) }
                    function onTeachZRequested(i) { operationEditor.teachZRequested(i) }

                    // Numpad
                    function onOpenNumPadRequested(field) { operationEditor.openNumPadRequested(field) }
                }
            }
        }
    }
}
