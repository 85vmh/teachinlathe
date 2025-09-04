import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: operationEditor
    objectName: "childScreen"

    // Inputs from Python
    property var selectedProgram: null
    property var operationsModel: []

    // Navigation
    property bool showBack: true
    signal backRequested()

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
    readonly property int colOpNumW: 30
    readonly property int colGenW:   120
    readonly property int colTypeW:  240
    readonly property int colOptW:   120

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

                        Label {
                            text: "Generate GCode"
                            Layout.minimumWidth: operationEditor.colGenW
                            Layout.preferredWidth: operationEditor.colGenW
                            Layout.maximumWidth: operationEditor.colGenW
                            leftPadding: 8
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                        Label {
                            text: "OperationType"
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

                        Label {
                            text: "OptionalBlock"
                            Layout.minimumWidth: operationEditor.colOptW
                            Layout.preferredWidth: operationEditor.colOptW
                            Layout.maximumWidth: operationEditor.colOptW
                            leftPadding: 8
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
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
                                    Layout.minimumWidth: operationEditor.colOpNumW
                                    Layout.preferredWidth: operationEditor.colOpNumW
                                    Layout.maximumWidth: operationEditor.colOpNumW
                                    leftPadding: 8
                                    verticalAlignment: Text.AlignVCenter
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

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
                                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

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
                    target: detailsLoader.item

                    // Any change in details view calls saveRequested(updated) → autosave
                    onSaveRequested: function(updated) {
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
                    onTeachXRequested: function(i) { operationEditor.teachXRequested(i) }
                    onTeachZRequested: function(i) { operationEditor.teachZRequested(i) }

                    // Numpad
                    onOpenNumPadRequested: function(field) { operationEditor.openNumPadRequested(field) }
                }
            }
        }
    }
}
