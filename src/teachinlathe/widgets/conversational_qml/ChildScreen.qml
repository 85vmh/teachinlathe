import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."   // to import local components like Divider.qml

Item {
    id: operationEditor
    objectName: "childScreen"

    property var selectedProgram: null
    property var operationsModel: []

    // selection state for the header row (no op selected)
    property bool headerSelected: false

    property bool showBack: true
    signal backRequested()
    signal generateGcodeRequested()

    signal toggleGenerateGcode(int index, bool checked)
    signal toggleOptionalBlock(int index, bool checked)

    signal detailsRequested(int index)
    signal updateToolChange(int index, var payload)
    signal updateFacing(int index, var payload)
    signal updateProfiling(int index, var payload)
    signal updateDrilling(int index, var payload)
    signal updateThreading(int index, var payload)
    signal updateParting(int index, var payload)
    signal updateTapping(int index, var payload)

    // NEW: autosave for header
    signal updateHeader(var payload)

    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)

    width: parent ? parent.width : 1200
    height: parent ? parent.height : 800

    property string titleText: (selectedProgram && (selectedProgram.name || (selectedProgram.header && selectedProgram.header.name)))
                               ? "Editing: " + (selectedProgram.name || selectedProgram.header.name)
                               : "Creating New Program"

    // Fixed widths for non-flex columns; Operation Type will fill remaining
    readonly property int colOpNumW: 50
    readonly property int colGenW:   80
    readonly property int colTypeW:  240   // minimum; the cell fills rest
    readonly property int colOptW:   80

    function receiveDetailsData(index, data) {
        // Special case: program header selection (-1)
        if (index === -1) {
            detailsLoader.source = "HeaderDetailsView.qml"
            Qt.callLater(function() {
                if (detailsLoader.item) {
                    if (detailsLoader.item.applyProgram)
                        detailsLoader.item.applyProgram(data)      // data = full program dict
                    else if (detailsLoader.item.applyData)
                        detailsLoader.item.applyData(index, data)  // fallback
                }
            })
            return
        }

        if (!data || !data.type) { detailsLoader.source = ""; return }
        if (data.type === "changeTool")      detailsLoader.source = "ToolChangeDetailsView.qml"
        else if (data.type === "facing")     detailsLoader.source = "FacingDetailsView.qml"
        else if (data.type === "profiling")  detailsLoader.source = "ProfilingDetailsView.qml"
        else if (data.type === "drilling")   detailsLoader.source = "DrillingDetailsView.qml"
        else if (data.type === "threading")  detailsLoader.source = "ThreadingDetailsView.qml"
        else if (data.type === "parting")    detailsLoader.source = "PartingDetailsView.qml"
        else if (data.type === "tapping")    detailsLoader.source = "TappingDetailsView.qml"
        else                                  detailsLoader.source = ""

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

            // LEFT: operations list + header row on top
            Rectangle {
                Layout.preferredWidth: Math.round(parent.width * 0.25)
                Layout.fillHeight: true
                color: "#ffffff"
                radius: 6
                border.color: "#ccc"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    // ======== SELECTABLE PROGRAM HEADER ROW (no columns) ========
                    Rectangle {
                        id: headerRow
                        Layout.fillWidth: true
                        Layout.minimumHeight: 60
                        Layout.preferredHeight: 60
                        Layout.maximumHeight: 60
                        radius: 0
                        color: operationEditor.headerSelected ? "#dbe9ff" : "#f7f7f7"
                        border.width: operationEditor.headerSelected ? 1 : 0
                        border.color: "#8ec5ff"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 6

                            Label {
                                text: "Program Header"
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }
                            Label {
                                text: (operationEditor.selectedProgram
                                       && (operationEditor.selectedProgram.name
                                           || (operationEditor.selectedProgram.header
                                               && operationEditor.selectedProgram.header.name)))
                                      ? (operationEditor.selectedProgram.name
                                         || operationEditor.selectedProgram.header.name)
                                      : ""
                                color: "#333"
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        TapHandler {
                            onTapped: {
                                // select header, clear op selection
                                operationEditor.headerSelected = true
                                opsList.currentIndex = -1
                                // ask Python for program details
                                operationEditor.detailsRequested(-1)
                            }
                        }
                    }

                    // ======== TABLE HEADER (Order / Generate / Operation Type / Optional) ========
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
                    }

                    // ======== LIST ========
                    ListView {
                        id: opsList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: operationEditor.operationsModel
                        currentIndex: -1
                        onCurrentIndexChanged: {
                            // if a row is selected, header must be unselected
                            if (currentIndex >= 0) {
                                operationEditor.headerSelected = false
                                operationEditor.detailsRequested(currentIndex)
                            }
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

                                // Order
                                Label {
                                    text: (op && op.order !== undefined) ? op.order : (index + 1)
                                    Layout.minimumWidth: operationEditor.colOpNumW
                                    Layout.preferredWidth: operationEditor.colOpNumW
                                    Layout.maximumWidth: operationEditor.colOpNumW
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                Divider { }

                                // Generate GCode
                                Item {
                                    Layout.minimumWidth: operationEditor.colGenW
                                    Layout.preferredWidth: operationEditor.colGenW
                                    Layout.maximumWidth: operationEditor.colGenW
                                    Layout.fillHeight: true
                                    CheckBox {
                                        id: genChk
                                        anchors.centerIn: parent
                                        checked: !!(op && op.generate_gcode)
                                        onToggled: {
                                            if (!op) return
                                            op.generate_gcode = checked
                                            typeLabel.enabled = checked
                                            optCell.enabled   = checked
                                            operationEditor.toggleGenerateGcode(index, checked)
                                        }
                                    }
                                }
                                Divider { }

                                // Operation Type (flex) + 10px left margin
                                Item {
                                    Layout.minimumWidth: operationEditor.colTypeW
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Label {
                                        id: typeLabel
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        text: (op && op.display_type) ? op.display_type : (op && op.type ? op.type : "")
                                        elide: Text.ElideRight
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                                Divider { }

                                // Optional Block
                                Item {
                                    id: optCell
                                    Layout.minimumWidth: operationEditor.colOptW
                                    Layout.preferredWidth: operationEditor.colOptW
                                    Layout.maximumWidth: operationEditor.colOptW
                                    Layout.fillHeight: true
                                    CheckBox {
                                        anchors.centerIn: parent
                                        checked: !!(op && op.is_optional_block)
                                        onToggled: {
                                            if (!op) return
                                            op.is_optional_block = checked
                                            operationEditor.toggleOptionalBlock(index, checked)
                                        }
                                    }
                                }
                            }

                            // init enabled state
                            Component.onCompleted: {
                                var en = !!(op && op.generate_gcode)
                                typeLabel.enabled = en
                                optCell.enabled   = en
                            }

                            TapHandler { onTapped: opsList.currentIndex = index }
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

                        // Header autosave
                        if (t === "header") {
                            if (operationEditor.updateHeader)
                                operationEditor.updateHeader(updated.payload.header)
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
