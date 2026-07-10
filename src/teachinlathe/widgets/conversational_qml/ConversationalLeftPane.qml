import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property var operationsModel: []
    property int activeOpIndex: -1
    property bool reorderMode: false

    readonly property int colOpNumW: 50
    readonly property int colGenW: 80
    readonly property int colTypeW: 200
    readonly property int colOptW: 80
    readonly property int colDelW: 100
    readonly property int opHeaderFontSize: 14

    property real _savedContentY: 0
    property bool _restoreScrollPending: false
    property bool _scrollToLastPending: false
    property int _pendingDeleteIndex: -1

    signal programHeaderSelected()
    signal operationSelected(int index)
    signal addOperationRequested()
    signal operationTypeChosen(string type, int insertIndex)
    signal reorderModeToggled(bool on)
    signal generateToggled(int index, bool checked)
    signal optionalToggled(int index, bool checked)
    signal deleteOperationRequested(int index)
    signal moveUpRequested(int index)
    signal moveDownRequested(int index)

    function _operationIndexToListIndex(index) {
        return index >= 0 ? index + 2 : 0
    }

    function _listIndexToOperationIndex(index) {
        return index >= 2 ? index - 2 : -1
    }

    function selectedOperationIndex() {
        return _listIndexToOperationIndex(opsList.currentIndex)
    }

    function setCurrentOperationIndex(index) {
        opsList.currentIndex = _operationIndexToListIndex(index)
    }

    function saveScrollPosition() {
        _savedContentY = opsList.contentY
        _restoreScrollPending = true
    }

    function syncAfterOperationsModelChanged() {
        var targetY = _restoreScrollPending ? _savedContentY : opsList.contentY
        Qt.callLater(function() {
            if (_scrollToLastPending) {
                _restoreScrollPending = false
                _scrollToLastPending = false
                setCurrentOperationIndex(activeOpIndex)
                scrollToLastItem()
            } else if (_restoreScrollPending) {
                var maxY = Math.max(0, opsList.contentHeight - opsList.height)
                opsList.contentY = Math.max(0, Math.min(targetY, maxY))
                _restoreScrollPending = false
                setCurrentOperationIndex(activeOpIndex)
            } else {
                setCurrentOperationIndex(activeOpIndex)
            }
        })
    }

    function openAddOperationPopup() {
        root.addOperationRequested()
        if (addOpPopupLoader.active && addOpPopupLoader.item) {
            addOpPopupLoader.item.close()
            addOpPopupLoader.active = false
        }
        addOpPopupLoader.active = true
    }

    function scrollToLastItem() {
        Qt.callLater(function() {
            Qt.callLater(function() {
                if (opsList.count <= 0)
                    return
                opsList.positionViewAtIndex(opsList.count - 1, ListView.End)
            })
        })
    }

    onActiveOpIndexChanged: setCurrentOperationIndex(activeOpIndex)
    onOperationsModelChanged: syncAfterOperationsModelChanged()

    ConfirmDialog {
        id: deleteConfirmDialog
        titleText: "Delete Operation"
        confirmText: "Delete"
        messageText: {
            var idx = root._pendingDeleteIndex
            if (idx >= 0 && idx < root.operationsModel.length) {
                var name = root.operationsModel[idx].display_type
                           || root.operationsModel[idx].type
                           || "this operation"
                return "Delete \"" + name + "\"?"
            }
            return "Delete this operation?"
        }
        onCancelled: root._pendingDeleteIndex = -1
        onConfirmed: {
            if (root._pendingDeleteIndex >= 0) {
                root._scrollToLastPending =
                    root._pendingDeleteIndex === root.operationsModel.length - 1
                root.deleteOperationRequested(root._pendingDeleteIndex)
                root._pendingDeleteIndex = -1
            }
        }
    }

    Loader {
        id: addOpPopupLoader
        active: false
        visible: active

        sourceComponent: AddOperationPopup {
            id: addPopup
            onOperationChosen: function(type, insertIndex) {
                root._scrollToLastPending = true
                root.operationTypeChosen(type, insertIndex)
            }
            onClosed: addOpPopupLoader.active = false
        }

        onLoaded: {
            if (item) {
                item.operationsCount = root.operationsModel.length
                item.currentOpIndex = root.selectedOperationIndex()
                if (item.open) item.open()
            }
        }
    }

    Layout.fillWidth: true
    Layout.preferredWidth: 3.5
    Layout.fillHeight: true
    color: "#ffffff"
    radius: 6
    border.color: "#ccc"
    border.width: 0

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 1
        spacing: 6

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

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ListView {
                        id: opsList
                        anchors.fill: parent
                        clip: true
                        model: root.operationsModel.length + 2
                        currentIndex: 0

                        onCurrentIndexChanged: {
                            if (currentIndex === 0) {
                                root.programHeaderSelected()
                            } else if (currentIndex >= 2) {
                                root.operationSelected(root._listIndexToOperationIndex(currentIndex))
                            }
                        }

                        delegate: Item {
                            width: ListView.view ? ListView.view.width : 400
                            height: index === 1 ? 40 : 72
                            readonly property int operationIndex: index - 2

                            ProgramHeader {
                                anchors.fill: parent
                                visible: index === 0
                                selected: opsList.currentIndex === 0
                                onClicked: opsList.currentIndex = 0
                            }

                            OperationsListHeader {
                                anchors.fill: parent
                                visible: index === 1
                                reorderMode: root.reorderMode
                                colOpNumW: root.colOpNumW
                                colGenW: root.colGenW
                                colTypeW: root.colTypeW
                                colOptW: root.colOptW
                                colDelW: root.colDelW
                                headerFontSize: root.opHeaderFontSize
                            }

                            OperationListItem {
                                anchors.fill: parent
                                visible: index >= 2
                                operationIndex: parent.operationIndex
                                operationData: index >= 2 ? root.operationsModel[parent.operationIndex] : null
                                selected: opsList.currentIndex === index
                                operationsCount: root.operationsModel.length
                                colOpNumW: root.colOpNumW
                                colGenW: root.colGenW
                                colTypeW: root.colTypeW
                                colOptW: root.colOptW
                                colDelW: root.colDelW
                                editing: root.reorderMode

                                onGenerateToggled: function(i, checked) {
                                    root.saveScrollPosition()
                                    root.generateToggled(i, checked)
                                }
                                onOptionalToggled: function(i, checked) {
                                    root.saveScrollPosition()
                                    root.optionalToggled(i, checked)
                                }
                                onDeleteClicked: function(i) {
                                    root._pendingDeleteIndex = i
                                    deleteConfirmDialog.open()
                                }
                                onMoveUpRequested: function(i) {
                                    root.moveUpRequested(i)
                                }
                                onMoveDownRequested: function(i) {
                                    root.moveDownRequested(i)
                                }
                                onRowTapped: function(i) {
                                    opsList.currentIndex = root._operationIndexToListIndex(i)
                                }
                            }
                        }
                    }

                    Rectangle {
                        anchors { left: parent.left; right: parent.right; top: parent.top }
                        height: 40
                        visible: opsList.contentY > 0
                        z: 1
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop { position: 0.0; color: "#f8f8f8" }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                    }

                    Rectangle {
                        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                        height: 40
                        visible: opsList.contentY + opsList.height < opsList.contentHeight - 1
                        z: 1
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 1.0; color: "#f8f8f8" }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: "#e8ecf2"
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 80

                    OperationIconTextButton {
                        anchors.centerIn: parent
                        iconSource: "icons/add_op_icon.svg"
                        text: "Add New Operation"
                        tint: "#2E7D32"
                        compact: false
                        buttonHeight: 50
                        iconSize: 36
                        fontPixelSize: 15
                        onClicked: root.openAddOperationPopup()
                    }

                    OperationIconTextButton {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        iconSource: "icons/reorder_icon.svg"
                        text: "Reorder"
                        tint: root.reorderMode ? "#1E88E5" : "#4F4F4F"
                        compact: false
                        iconOnRight: true
                        enabled: root.operationsModel.length > 1
                        buttonHeight: 50
                        iconSize: 36
                        fontPixelSize: 15
                        onClicked: {
                            if (root.operationsModel.length <= 1)
                                return
                            root.reorderMode = !root.reorderMode
                            root.reorderModeToggled(root.reorderMode)
                        }
                    }
                }
            }
        }
    }
}
