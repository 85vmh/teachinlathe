import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."   // Divider.qml and OperationRowDelegate.qml

Item {
    id: operationEditor
    objectName: "childScreen"

    // Context from Python
    property var selectedProgram: null
    property var operationsModel: []

    // Navigation
    property bool showBack: true
    signal backRequested()
    signal generateGcodeRequested()

    // Row-level toggles
    signal toggleGenerateGcode(int index, bool checked)
    signal toggleOptionalBlock(int index, bool checked)
    signal deleteOperationRequested(int index)

    // Details bridge
    signal detailsRequested(int index)
    signal updateToolChange(int index, var payload)
    signal updateFacing(int index, var payload)
    signal updateProfiling(int index, var payload)
    signal updateDrilling(int index, var payload)
    signal updateThreading(int index, var payload)
    signal updateParting(int index, var payload)
    signal updateTapping(int index, var payload)

    // Numpad / teach
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    // Operations toolbar
    signal addOperationRequested()
    signal reorderModeToggled(bool on)
    property bool reorderMode: false

    width: parent ? parent.width : 1200
    height: parent ? parent.height : 800

    property string titleText: (selectedProgram && (selectedProgram.name || (selectedProgram.header && selectedProgram.header.name)))
                               ? "Editing: " + (selectedProgram.name || selectedProgram.header.name)
                               : "Creating New Program"

    // Column widths
    readonly property int colOpNumW: 50
    readonly property int colGenW:   80
    readonly property int colTypeW:  200   // used as minimum only
    readonly property int colOptW:   80
    readonly property int colDelW:   44

    function receiveDetailsData(index, data) {
        if (index === -1) {
            detailsLoader.source = "HeaderDetailsView.qml"
        } else if (!data || !data.type) {
            detailsLoader.source = ""
        } else if (data.type === "changeTool") {
            detailsLoader.source = "ToolChangeDetailsView.qml"
        } else if (data.type === "facing") {
            detailsLoader.source = "FacingDetailsView.qml"
        } else if (data.type === "profiling")  {
            detailsLoader.source = "ProfilingDetailsView.qml"
        } else if (data.type === "drilling")   {
            detailsLoader.source = "DrillingDetailsView.qml"
        } else if (data.type === "threading")  {
            detailsLoader.source = "ThreadingDetailsView.qml"
        } else if (data.type === "parting")    {
            detailsLoader.source = "PartingDetailsView.qml"
        } else if (data.type === "tapping")    {
            detailsLoader.source = "TappingDetailsView.qml"
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

            Button {
                text: "Back"
                visible: operationEditor.showBack
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                onClicked: operationEditor.backRequested()
            }

            Label {
                text: operationEditor.titleText
                font.pixelSize: 22
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
            }

            Button {
                text: "Build G-Code Program"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                enabled: operationEditor.operationsModel && operationEditor.operationsModel.length > 0
                onClicked: operationEditor.generateGcodeRequested()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            // LEFT: program header + operations box
            Rectangle {
                Layout.preferredWidth: Math.round(parent.width * 0.4)
                Layout.fillHeight: true
                color: "#ffffff"
                radius: 6
                border.color: "#ccc"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6

                    // Program Header row (selectable, index = -1)
                    Rectangle {
                        id: programHeaderRow
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        radius: 4
                        color: (opsList.currentIndex === -1 ? "#e9f4ff" : "#f9f9f9")
                        border.width: 1
                        border.color: (opsList.currentIndex === -1 ? "#8ec5ff" : "#dddddd")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8

                            Label {
                                text: "Program Header"
                                font.bold: true
                                Layout.fillWidth: true
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        TapHandler {
                            onTapped: {
                                opsList.currentIndex = -1
                                operationEditor.detailsRequested(-1)
                            }
                        }
                    }

                    // Operations box
                    Rectangle {
                        id: operationsBox
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 4
                        color: "#f8f8f8"
                        border.width: 1
                        border.color: "#dddddd"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 6

                            // Title row + actions
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 40
                                spacing: 8

                                Label {
                                    text: "Operations"
                                    font.bold: true
                                    verticalAlignment: Text.AlignVCenter
                                    Layout.fillWidth: true
                                }

                                Button {
                                    text: "Add New"
                                    Layout.alignment: Qt.AlignVCenter
                                    onClicked: operationEditor.addOperationRequested()
                                }

                                Switch {
                                    id: reorderSwitch
                                    text: "Reorder"
                                    checked: operationEditor.reorderMode
                                    Layout.alignment: Qt.AlignVCenter
                                    onToggled: {
                                        operationEditor.reorderMode = checked
                                        operationEditor.reorderModeToggled(checked)
                                    }
                                }
                            }

                            // Divider under title row
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: "#dddddd"
                            }

                            // Header + list (with left margin)
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.leftMargin: 10
                                spacing: 4

                                // Column header (now includes Delete)
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.minimumHeight: 40
                                    Layout.preferredHeight: 40
                                    Layout.maximumHeight: 40
                                    spacing: 0

                                    Label {
                                        text: "Order"
                                        font.bold: true
                                        Layout.minimumWidth: operationEditor.colOpNumW
                                        Layout.preferredWidth: operationEditor.colOpNumW
                                        Layout.maximumWidth: operationEditor.colOpNumW
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Divider { }

                                    Label {
                                        text: "Generate\nGCode"
                                        font.bold: true
                                        Layout.minimumWidth: operationEditor.colGenW
                                        Layout.preferredWidth: operationEditor.colGenW
                                        Layout.maximumWidth: operationEditor.colGenW
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Divider { }

                                    Label {
                                        text: "Operation Type"
                                        font.bold: true
                                        Layout.minimumWidth: operationEditor.colTypeW
                                        Layout.fillWidth: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Divider { }

                                    Label {
                                        text: "Optional\nBlock"
                                        font.bold: true
                                        Layout.minimumWidth: operationEditor.colOptW
                                        Layout.preferredWidth: operationEditor.colOptW
                                        Layout.maximumWidth: operationEditor.colOptW
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Divider { }

                                    Label {
                                        text: "Delete"
                                        font.bold: true
                                        Layout.minimumWidth: operationEditor.colDelW
                                        Layout.preferredWidth: operationEditor.colDelW
                                        Layout.maximumWidth: operationEditor.colDelW
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                }

                                // LIST (uses OperationRowDelegate)
                                ListView {
                                    id: opsList
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    model: operationEditor.operationsModel
                                    currentIndex: -1
                                    onCurrentIndexChanged: {
                                        if (currentIndex >= 0) operationEditor.detailsRequested(currentIndex)
                                    }

                                    delegate: OperationRowDelegate {
                                        // sizing & selection
                                        width: ListView.view ? ListView.view.width : 400
                                        isCurrentItem: ListView.isCurrentItem

                                        // data
                                        op: modelData
                                        rowIndex: index

                                        // columns
                                        colOpNumW: operationEditor.colOpNumW
                                        colGenW:   operationEditor.colGenW
                                        colTypeW:  operationEditor.colTypeW
                                        colOptW:   operationEditor.colOptW
                                        colDelW:   operationEditor.colDelW

                                        // events -> parent
                                        onGenerateToggled: operationEditor.toggleGenerateGcode(rowIndex, checked)
                                        onOptionalToggled: operationEditor.toggleOptionalBlock(rowIndex, checked)
                                        onDeleteClicked:   operationEditor.deleteOperationRequested(rowIndex)
                                        onRowTapped:       opsList.currentIndex = rowIndex
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // RIGHT: details
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
                    ignoreUnknownSignals: true
                    enabled: !!target

                    function onSaveRequested(updated) {
                        if (!updated || !updated.payload) return
                        var t = updated.payload.type || ""
                        if (updated.index === -1) {
                            if (operationEditor.updateHeader)
                                operationEditor.updateHeader(updated.payload)
                            return
                        }
                        if (t === "changeTool" && operationEditor.updateToolChange)
                            operationEditor.updateToolChange(updated.index, updated.payload)
                        else if (t === "facing" && operationEditor.updateFacing)
                            operationEditor.updateFacing(updated.index, updated.payload)
                        else if (t === "profiling" && operationEditor.updateProfiling)
                            operationEditor.updateProfiling(updated.index, updated.payload)
                        else if (t === "drilling" && operationEditor.updateDrilling)
                            operationEditor.updateDrilling(updated.index, updated.payload)
                        else if (t === "threading")
                            operationEditor.updateThreading(updated.index, updated.payload)
                        else if (t === "parting")
                            operationEditor.updateParting(updated.index, updated.payload)
                        else if (t === "tapping")
                            operationEditor.updateTapping(updated.index, updated.payload)
                        else if (operationEditor.updateOperation)
                            operationEditor.updateOperation(updated.index, updated.payload)
                    }

                    function onTeachXRequested(i) { operationEditor.teachXRequested(i) }
                    function onTeachZRequested(i) { operationEditor.teachZRequested(i) }
                    function onOpenNumPadRequested(field) { operationEditor.openNumPadRequested(field) }
                }
            }
        }
    }
}
