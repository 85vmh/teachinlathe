import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.0
import "."   // Divider.qml + OperationRowDelegate.qml

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

    // Details bridge
    signal detailsRequested(int index)
    signal updateToolChange(int index, var payload)
    signal updateFacing(int index, var payload)
    signal updateProfiling(int index, var payload)
    signal updateDrilling(int index, var payload)
    signal updateThreading(int index, var payload)
    signal updateParting(int index, var payload)
    signal updateTapping(int index, var payload)
    signal updateHeader(var payload)

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
    readonly property int colTypeW:  200   // min; flex fills the rest
    readonly property int colOptW:   80
    readonly property int colDelW:   100   // new fixed width for Delete/Reorder

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
                Layout.preferredWidth: Math.round(parent.width * 0.3)
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

                            // Title row + icon buttons
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

                                // Add operation (icon-only button)
                                Rectangle {
                                    id: addBtn
                                    width: 36; height: 36; radius: 6
                                    color: addArea.pressed ? "#e1f0ff" : "transparent"
                                    border.width: addArea.pressed ? 1 : 0
                                    border.color: addArea.pressed ? "#8ec5ff" : "transparent"
                                    Layout.alignment: Qt.AlignVCenter

                                    Image {
                                        id: addImg
                                        anchors.centerIn: parent
                                        source: "add_op_icon.svg"
                                        sourceSize.width: 36
                                        sourceSize.height: 36
                                        visible: false
                                        smooth: true
                                    }
                                    ColorOverlay {
                                        anchors.centerIn: addImg
                                        width: addImg.width
                                        height: addImg.height
                                        source: addImg
                                        color: "#4F4F4F"
                                    }
                                    MouseArea {
                                        id: addArea
                                        anchors.fill: parent
                                        onClicked: operationEditor.addOperationRequested()
                                    }
                                }

                                // Reorder toggle (icon-only, grey when off, blue when on)
                                Rectangle {
                                    id: reorderBtn
                                    width: 36; height: 36; radius: 6
                                    color: reorderArea.pressed ? "#e1f0ff" : "transparent"
                                    border.width: reorderArea.pressed ? 1 : 0
                                    border.color: reorderArea.pressed ? "#8ec5ff" : "transparent"
                                    Layout.alignment: Qt.AlignVCenter

                                    Image {
                                        id: reorderImg
                                        anchors.centerIn: parent
                                        source: "reorder_icon.svg"
                                        sourceSize.width: 36
                                        sourceSize.height: 36
                                        visible: false
                                        smooth: true
                                    }
                                    ColorOverlay {
                                        anchors.centerIn: reorderImg
                                        width: reorderImg.width
                                        height: reorderImg.height
                                        source: reorderImg
                                        color: operationEditor.reorderMode ? "#1E88E5" : "#4F4F4F"
                                    }
                                    MouseArea {
                                        id: reorderArea
                                        anchors.fill: parent
                                        onClicked: {
                                            operationEditor.reorderMode = !operationEditor.reorderMode
                                            operationEditor.reorderModeToggled(operationEditor.reorderMode)
                                        }
                                    }
                                }
                            }

                            // Divider under title row
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: "#dddddd"
                            }

                            // Container for header + list with left margin
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.leftMargin: 10
                                spacing: 4

                                // Column header (now includes dynamic last column)
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.minimumHeight: 40
                                    Layout.preferredHeight: 40
                                    Layout.maximumHeight: 40
                                    spacing: 0

                                    Label {
                                        text: "Order"
                                        font.bold: true
                                        Layout.minimumWidth: colOpNumW
                                        Layout.preferredWidth: colOpNumW
                                        Layout.maximumWidth: colOpNumW
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Divider { }

                                    Label {
                                        text: "Generate\nGCode"
                                        font.bold: true
                                        Layout.minimumWidth: colGenW
                                        Layout.preferredWidth: colGenW
                                        Layout.maximumWidth: colGenW
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
                                        Layout.minimumWidth: colTypeW
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
                                        Layout.minimumWidth: colOptW
                                        Layout.preferredWidth: colOptW
                                        Layout.maximumWidth: colOptW
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Divider { }

                                    // Dynamic last column header
                                    Label {
                                        text: operationEditor.reorderMode ? "Reorder" : "Delete"
                                        font.bold: true
                                        Layout.minimumWidth: colDelW
                                        Layout.preferredWidth: colDelW
                                        Layout.maximumWidth: colDelW
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
                                        width: ListView.view ? ListView.view.width : 400
                                        rowIndex: index
                                        op: modelData
                                        isCurrentItem: ListView.isCurrentItem

                                        colOpNumW: operationEditor.colOpNumW
                                        colGenW:   operationEditor.colGenW
                                        colTypeW:  operationEditor.colTypeW
                                        colOptW:   operationEditor.colOptW
                                        colDelW:   operationEditor.colDelW

                                        editing: operationEditor.reorderMode

                                        onGenerateToggled: function(i, checked) {
                                            operationEditor.toggleGenerateGcode(i, checked)
                                        }
                                        onOptionalToggled: function(i, checked) {
                                            operationEditor.toggleOptionalBlock(i, checked)
                                        }
                                        onDeleteClicked: function(i) {
                                            console.log("Delete clicked for row", i)
                                        }
                                        onMoveUpRequested: function(i) {
                                            console.log("Move UP requested for row", i)
                                        }
                                        onMoveDownRequested: function(i) {
                                            console.log("Move DOWN requested for row", i)
                                        }
                                        onRowTapped: function(i) {
                                            opsList.currentIndex = i
                                        }
                                    }
                                }
                            } // end list container
                        } // end operationsBox ColumnLayout
                    } // end operationsBox
                } // end outer ColumnLayout
            } // end left Rectangle

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
