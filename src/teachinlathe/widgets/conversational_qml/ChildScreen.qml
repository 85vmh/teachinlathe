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
    property int activeOpIndex: -1
    property real _savedContentY: 0
    property bool _restoreScrollPending: false

    onOperationsModelChanged: {
        var targetY = _restoreScrollPending ? _savedContentY : opsList.contentY
        Qt.callLater(function() {
            if (_restoreScrollPending) {
                var maxY = Math.max(0, opsList.contentHeight - opsList.height)
                opsList.contentY = Math.max(0, Math.min(targetY, maxY))
                _restoreScrollPending = false
            }
            opsList.currentIndex = activeOpIndex >= 0 ? activeOpIndex : -1
        })
    }

    function _saveScrollPosition() {
        _savedContentY = opsList.contentY
        _restoreScrollPending = true
    }

    // Navigation
    property bool showBack: true

    signal backRequested()

    signal generateGcodeRequested()

    signal addOperationTypeChosen(string type, int insertIndex)

    // Row-level toggles
    signal toggleGenerateGcode(int index, bool checked)

    signal toggleOptionalBlock(int index, bool checked)

    // Details bridge
    signal detailsRequested(int index)

    signal updateToolChange(int index, var payload)

    signal updateDefineProfile(int index, var payload)

    signal updateFacing(int index, var payload)

    signal updateKnurling(int index, var payload)

    signal updateProfiling(int index, var payload)

    signal updateCustomProfiling(int index, var payload)

    signal updateDrilling(int index, var payload)

    signal updateThreading(int index, var payload)

    signal updateParting(int index, var payload)

    signal updateTapping(int index, var payload)

    signal updateHeader(var payload)

    signal addProfilingFinishRequested(int index)

    // Numpad / teach
    signal openNumPadRequested(var field)

    signal teachXRequested(int index)

    signal teachZRequested(int index)

    // Operations toolbar
    signal addOperationRequested()

    signal reorderModeToggled(bool on)

    signal moveUpRequested(int index)

    signal moveDownRequested(int index)

    signal deleteOperationRequested(int index)

    property bool reorderMode: false

    property int _pendingDeleteIndex: -1

    ConfirmDialog {
        id: deleteConfirmDialog
        titleText: "Delete Operation"
        confirmText: "Delete"
        messageText: {
            var idx = operationEditor._pendingDeleteIndex
            if (idx >= 0 && idx < operationEditor.operationsModel.length) {
                var name = operationEditor.operationsModel[idx].display_type
                           || operationEditor.operationsModel[idx].type
                           || "this operation"
                return "Delete \"" + name + "\"?"
            }
            return "Delete this operation?"
        }
        onCancelled: operationEditor._pendingDeleteIndex = -1
        onConfirmed: {
            if (operationEditor._pendingDeleteIndex >= 0) {
                operationEditor.deleteOperationRequested(operationEditor._pendingDeleteIndex)
                operationEditor._pendingDeleteIndex = -1
            }
        }
    }

    width: parent ? parent.width : 1200
    height: parent ? parent.height : 800

    property string titleText: (selectedProgram && (selectedProgram.name || (selectedProgram.header && selectedProgram.header.name)))
        ? "Editing: " + (selectedProgram.name || selectedProgram.header.name)
        : "Creating New Program"

    // Column widths
    readonly property int colOpNumW: 50
    readonly property int colGenW: 80
    readonly property int colTypeW: 200   // min; flex fills the rest
    readonly property int colOptW: 80
    readonly property int colDelW: 100   // fixed width for Delete/Reorder
    readonly property int opHeaderFontSize: 14

    Loader {
        id: addOpPopupLoader
        active: false
        visible: active

        sourceComponent: AddOperationPopup {
            id: addPopup
            onOperationChosen: function(type, insertIndex) {
                operationEditor.addOperationTypeChosen(type, insertIndex)
            }
            onClosed: {
                addOpPopupLoader.active = false
            }
        }

        onLoaded: {
            if (item) {
                item.operationsCount = operationEditor.operationsModel.length
                item.currentOpIndex  = opsList.currentIndex
                if (item.open) item.open()
            }
        }
    }


    // Reusable Icon+Text button: content-sized, gray border, blue on press,
    // vertical centering for icon+text, with left/right padding.
    Component {
        id: iconTextButton
        Rectangle {
            id: btn
            property url   iconSource: ""
            property color tint: "#4F4F4F"
            property string text: ""
            property bool  enabled: true
            property bool  compact: false

            signal clicked()

            // Padding + implicit sizing based on content
            readonly property int hp: 8       // left/right padding
            readonly property int vp: 6       // top/bottom padding
            implicitHeight: 36
            implicitWidth: Math.max(90, Math.ceil(contentRow.implicitWidth) + hp * 2)
            Layout.preferredWidth: implicitWidth
            Layout.preferredHeight: implicitHeight

            radius: 6
            color: (enabled && area.pressed) ? "#e1f0ff" : "transparent"
            border.width: 1
            border.color: enabled ? (area.pressed ? "#8ec5ff" : "#BDBDBD") : "#E0E0E0"
            opacity: enabled ? 1.0 : 0.35

            // Use RowLayout so children can vertically center via Layout.alignment
            RowLayout {
                id: contentRow
                anchors.fill: parent
                anchors.leftMargin: btn.hp
                anchors.rightMargin: btn.hp
                anchors.topMargin: btn.vp
                anchors.bottomMargin: btn.vp
                spacing: 6

                // Icon container so overlay doesn't take an extra slot in the layout
                Item {
                    id: iconWrap
                    Layout.alignment: Qt.AlignVCenter
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                    visible: btn.iconSource !== ""

                    Image {
                        id: baseImg
                        anchors.fill: parent
                        source: btn.iconSource
                        // keep real geometry, but tint via overlay
                        opacity: 0
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                    ColorOverlay {
                        anchors.fill: baseImg
                        source: baseImg
                        color: btn.tint
                    }
                }

                Label {
                    id: lbl
                    visible: !btn.compact
                    text: btn.text
                    color: btn.tint
                    Layout.alignment: Qt.AlignVCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
            }

            MouseArea {
                id: area
                anchors.fill: parent
                enabled: btn.enabled
                onClicked: btn.clicked()
            }
        }
    }

    function receiveDetailsData(index, data) {
        if (index === -1) {
            detailsLoader.source = "HeaderDetailsView.qml"
        } else if (!data || !data.type) {
            detailsLoader.source = ""
        } else if (data.type === "changeTool") {
            detailsLoader.source = "ToolChangeDetailsView.qml"
        } else if (data.type === "facing") {
            detailsLoader.source = "FacingDetailsView.qml"
        } else if (data.type === "knurling") {
            detailsLoader.source = "KnurlingDetailsView.qml"
        } else if (data.type === "profiling") {
            detailsLoader.source = "ProfilingDetailsView.qml"
        } else if (data.type === "customProfiling") {
            detailsLoader.source = "CustomProfilingDetailsView.qml"
        } else if (data.type === "defineProfile") {
            detailsLoader.source = "define_profile/DefineProfileDetailsView.qml"
        } else if (data.type === "drilling") {
            detailsLoader.source = "DrillingDetailsView.qml"
        } else if (data.type === "threading") {
            detailsLoader.source = "ThreadingDetailsView.qml"
        } else if (data.type === "parting") {
            detailsLoader.source = "PartingDetailsView.qml"
        } else if (data.type === "tapping") {
            detailsLoader.source = "TappingDetailsView.qml"
        } else {
            detailsLoader.source = ""
        }
        Qt.callLater(function () {
            if (detailsLoader.item && detailsLoader.item.applyData) {
                detailsLoader.item.applyData(index, data)
            }
        })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.bottomMargin: 36
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            // LEFT: program header + operations box
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredWidth: 3
                Layout.fillHeight: true
                color: "#ffffff"
                radius: 6
                border.color: "#ccc"
                border.width: 0

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 1
                    spacing: 6

                    // Program Header row (selectable, index = -1)
                    Rectangle {
                        id: programHeaderRow
                        Layout.fillWidth: true
                        Layout.preferredHeight: 60
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
                                font.pixelSize: 18
                                font.bold: true
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignHCenter
                                Layout.alignment: Qt.AlignVCenter
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
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

                            // Title row + icon-text buttons (adaptive)
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 50
                                spacing: 20

                                Label {
                                    text: "Operation List"
                                    font.pixelSize: operationEditor.opHeaderFontSize
                                    font.bold: true
                                    verticalAlignment: Text.AlignVCenter
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                // Add operation
                                Loader {
                                    id: addBtn
                                    sourceComponent: iconTextButton
                                    Layout.alignment: Qt.AlignVCenter
                                    onLoaded: {
                                        item.iconSource = "icons/add_op_icon.svg"
                                        item.text = "Add New Operation"
                                        item.tint = "#2E7D32"      // green
                                        item.enabled = true
                                        item.compact = false       // show text; set true only if you want icon-only
                                        // make RowLayout honor the button width
                                        addBtn.Layout.preferredWidth = 160
                                        addBtn.Layout.preferredHeight = item.implicitHeight
                                        item.clicked.connect(function () {
                                            operationEditor.addOperationRequested()
                                            if (addOpPopupLoader.active && addOpPopupLoader.item) {
                                                addOpPopupLoader.item.close()
                                                addOpPopupLoader.active = false
                                            }
                                            addOpPopupLoader.active = true
                                        })
                                    }
                                }

                                // Reorder toggle
                                Loader {
                                    id: reorderBtn
                                    sourceComponent: iconTextButton
                                    Layout.alignment: Qt.AlignVCenter
                                    onLoaded: {
                                        item.iconSource = "icons/reorder_icon.svg"
                                        item.text = "Reorder"
                                        item.enabled = opsList.count > 1
                                        item.tint = operationEditor.reorderMode ? "#1E88E5" : "#4F4F4F"
                                        item.compact = false       // show text; set true only if you want icon-only
                                        reorderBtn.Layout.preferredWidth = item.implicitWidth
                                        reorderBtn.Layout.preferredHeight = item.implicitHeight
                                        item.clicked.connect(function () {
                                            if (!item.enabled) return
                                            operationEditor.reorderMode = !operationEditor.reorderMode
                                            item.tint = operationEditor.reorderMode ? "#1E88E5" : "#4F4F4F"
                                            operationEditor.reorderModeToggled(operationEditor.reorderMode)
                                        })
                                    }
                                    Connections {
                                        target: opsList
                                        function onCountChanged() {
                                            if (reorderBtn.item) reorderBtn.item.enabled = opsList.count > 1
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
                                spacing: 4

                                // Column header (dynamic last column)
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.minimumHeight: 40
                                    Layout.preferredHeight: 40
                                    Layout.maximumHeight: 40
                                    spacing: 0

                                    Label {
                                        text: "Order"
                                        font.pixelSize: operationEditor.opHeaderFontSize
                                        font.bold: true
                                        Layout.minimumWidth: colOpNumW
                                        Layout.preferredWidth: colOpNumW
                                        Layout.maximumWidth: colOpNumW
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Divider {
                                    }

                                    Label {
                                        text: "Generate\nGCode"
                                        font.pixelSize: operationEditor.opHeaderFontSize
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
                                    Divider {
                                    }

                                    Label {
                                        text: "Operation Type"
                                        font.pixelSize: operationEditor.opHeaderFontSize
                                        font.bold: true
                                        Layout.minimumWidth: colTypeW
                                        Layout.fillWidth: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Divider {
                                    }

                                    Label {
                                        text: "Optional\nBlock"
                                        font.pixelSize: operationEditor.opHeaderFontSize
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
                                    Divider {
                                    }

                                    Label {
                                        text: operationEditor.reorderMode ? "Change\nOrder" : "Delete"
                                        font.pixelSize: operationEditor.opHeaderFontSize
                                        font.bold: true
                                        Layout.minimumWidth: colDelW
                                        Layout.preferredWidth: colDelW
                                        Layout.maximumWidth: colDelW
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        Layout.alignment: Qt.AlignVCenter
                                    }
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
                                        if (currentIndex >= 0) operationEditor.detailsRequested(currentIndex)
                                    }

                                    delegate: OperationRowDelegate {
                                        width: ListView.view ? ListView.view.width : 400
                                        rowIndex: index
                                        op: modelData
                                        isCurrentItem: ListView.isCurrentItem

                                        colOpNumW: operationEditor.colOpNumW
                                        colGenW: operationEditor.colGenW
                                        colTypeW: operationEditor.colTypeW
                                        colOptW: operationEditor.colOptW
                                        colDelW: operationEditor.colDelW

                                        editing: operationEditor.reorderMode

                                        totalCount: opsList.count
                                        isFirstItem: index === 0
                                        isLastItem: index === (opsList.count - 1)

                                        onGenerateToggled: function (i, checked) {
                                            operationEditor._saveScrollPosition()
                                            operationEditor.toggleGenerateGcode(i, checked)
                                        }
                                        onOptionalToggled: function (i, checked) {
                                            operationEditor._saveScrollPosition()
                                            operationEditor.toggleOptionalBlock(i, checked)
                                        }
                                        onDeleteClicked: function (i) {
                                            operationEditor._pendingDeleteIndex = i
                                            deleteConfirmDialog.open()
                                        }
                                        onMoveUpRequested: function (i) {
                                            operationEditor.moveUpRequested(i)
                                        }
                                        onMoveDownRequested: function (i) {
                                            operationEditor.moveDownRequested(i)
                                        }
                                        onRowTapped: function (i) {
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
                Layout.preferredWidth: 7
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
                        else if (t === "defineProfile" && operationEditor.updateDefineProfile)
                            operationEditor.updateDefineProfile(updated.index, updated.payload)
                        else if (t === "facing" && operationEditor.updateFacing)
                            operationEditor.updateFacing(updated.index, updated.payload)
                        else if (t === "knurling" && operationEditor.updateKnurling)
                            operationEditor.updateKnurling(updated.index, updated.payload)
                        else if (t === "profiling" && operationEditor.updateProfiling)
                            operationEditor.updateProfiling(updated.index, updated.payload)
                        else if (t === "customProfiling" && operationEditor.updateCustomProfiling)
                            operationEditor.updateCustomProfiling(updated.index, updated.payload)
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

                    function onTeachXRequested(i) {
                        operationEditor.teachXRequested(i)
                    }

                    function onTeachZRequested(i) {
                        operationEditor.teachZRequested(i)
                    }

                    function onOpenNumPadRequested(field) {
                        operationEditor.openNumPadRequested(field)
                    }

                    function onAddFinishRequested(i) {
                        if (operationEditor.addProfilingFinishRequested)
                            operationEditor.addProfilingFinishRequested(i)
                    }
                }
            }
        }
    }
}
