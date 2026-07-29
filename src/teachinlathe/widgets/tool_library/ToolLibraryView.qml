// ToolLibraryView.qml — tool list with flip-card Add / Edit form.
//
// Layout:
//   Front face — header ("Tools" + "+ Add Tool") + scrollable ToolCard list
//   Back face  — ToolEditForm (flips in on edit/add, flips out on save/cancel)
//
// Context property required: toolLibraryViewModel (ToolLibraryViewModel)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#f5f5f5"
    radius: 6
    border.color: "#ccc"
    border.width: 1

    signal openNumPadRequested(var field)
    readonly property int toolListSpacing: 5

    // ── Edit / Add state ──────────────────────────────────────────
    property var _editTool: null    // null = add mode, tool dict = edit mode

    // ── Flip helpers ──────────────────────────────────────────────
    function _startAdd() {
        if (!toolLibraryViewModel || !toolLibraryViewModel.addToolEnabled)
            return
        root._editTool = null
        var nextNo = toolLibraryViewModel ? toolLibraryViewModel.nextToolNo : 1
        editForm.populate(null, nextNo)
        flipAnim.stop(); flipAnim.from = 0; flipAnim.to = 180; flipAnim.start()
    }

    function _startEdit(toolData) {
        if (!toolLibraryViewModel || !toolData || !toolData.actionsEnabled)
            return
        root._editTool = toolData
        editForm.populate(toolData)
        flipAnim.stop(); flipAnim.from = 0; flipAnim.to = 180; flipAnim.start()
    }

    function _flipToFront() {
        flipAnim.stop(); flipAnim.from = 180; flipAnim.to = 0; flipAnim.start()
    }

    // ── Flip animation ─────────────────────────────────────────────
    NumberAnimation {
        id: flipAnim
        target: flipRot; property: "angle"
        duration: 400; easing.type: Easing.InOutCubic
    }

    // ── Flip container ─────────────────────────────────────────────
    Item {
        id: flipper
        anchors.fill: parent
        anchors.margins: 1

        transform: Rotation {
            id: flipRot
            axis { x: 0; y: 1; z: 0 }
            origin.x: flipper.width  / 2
            origin.y: flipper.height / 2
            angle: 0
        }

        // ══════════════════════════════════════════════════════════
        // FRONT FACE — tool list
        // ══════════════════════════════════════════════════════════
        Item {
            id: frontFace
            anchors.fill: parent
            visible: flipRot.angle < 90

            property int activeTab: 0  // 0 = All tools, 1 = Recently used

            // Light background for the front face
            Rectangle { anchors.fill: parent; color: "#f5f5f5" }

            ColumnLayout {
                anchors.fill: parent; spacing: 0

                // Header
                Rectangle {
                    Layout.fillWidth: true; height: 60; color: "#d6d6d6"

                    // Title — absolutely centered over the full header width
                    Text {
                        anchors.centerIn: parent
                        text: "Tool Library"; color: "#222222"
                        font.pixelSize: 18; font.bold: true
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 6

                        // Tab: All tools
                        Rectangle {
                            width: 120; height: 46; radius: 8
                            color: frontFace.activeTab === 0 ? "#f5f5f5" : "#c4c4c4"
                            border.color: frontFace.activeTab === 0 ? "#999999" : "#b0b0b0"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "All tools"; color: "#222222"
                                font.pixelSize: 14; font.bold: frontFace.activeTab === 0
                            }
                            MouseArea { anchors.fill: parent; onClicked: frontFace.activeTab = 0 }
                        }

                        // Tab: Recently used
                        Rectangle {
                            width: 150; height: 46; radius: 8
                            color: frontFace.activeTab === 1 ? "#f5f5f5" : "#c4c4c4"
                            border.color: frontFace.activeTab === 1 ? "#999999" : "#b0b0b0"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "Recently used"; color: "#222222"
                                font.pixelSize: 14; font.bold: frontFace.activeTab === 1
                            }
                            MouseArea { anchors.fill: parent; onClicked: frontFace.activeTab = 1 }
                        }

                        Item { Layout.fillWidth: true }

                        // Add Tool button
                        Rectangle {
                            id: addToolButton
                            width: 130; height: 46; radius: 8
                            enabled: toolLibraryViewModel ? toolLibraryViewModel.addToolEnabled : false
                            opacity: enabled ? 1.0 : 0.45
                            color: !enabled ? "#9e9e9e" : addMA.pressed ? "#145a30" : "#1e8449"

                            Text { anchors.centerIn: parent; text: "+ Add Tool"; color: "white"; font.pixelSize: 14; font.bold: true }
                            MouseArea { id: addMA; anchors.fill: parent; enabled: parent.enabled; onClicked: root._startAdd() }
                        }
                    }
                }

                // Tool list
                Item {
                    Layout.fillWidth: true; Layout.fillHeight: true

                    ListView {
                        id: listView
                        anchors.fill: parent
                        clip: true
                        spacing: root.toolListSpacing
                        topMargin: root.toolListSpacing
                        bottomMargin: root.toolListSpacing
                        model: {
                            if (!toolLibraryViewModel) return []
                            return frontFace.activeTab === 1
                                   ? toolLibraryViewModel.recentTools
                                   : toolLibraryViewModel.tools
                        }

                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AlwaysOn
                            width: 16
                        }

                        delegate: ToolCard {
                            toolData: modelData
                            enabled: toolData ? toolData.isEnabled : false
                            actionsEnabled: toolData ? toolData.actionsEnabled : false
                            width: Math.min(800, ListView.view.width - 16 - root.toolListSpacing * 2)
                            x: root.toolListSpacing + Math.max(0, (ListView.view.width - 16 - root.toolListSpacing * 2 - width) / 2)

                            onLoadRequested:   toolLibraryViewModel.loadTool(toolNo)
                            onEditRequested:   root._startEdit(toolData)
                            onDeleteRequested: {
                                if (toolLibraryViewModel && toolData && toolData.actionsEnabled) {
                                    deleteDialog.toolNo = toolNo
                                    deleteDialog.open()
                                }
                            }
                        }
                    }

                    // Top fade
                    Rectangle {
                        anchors { left: parent.left; right: parent.right; top: parent.top }
                        height: 80
                        visible: listView.contentY > 0
                        z: 1
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop { position: 0.0; color: "#f5f5f5" }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                    }

                    // Bottom fade
                    Rectangle {
                        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                        height: 80
                        visible: listView.contentY + listView.height < listView.contentHeight - 1
                        z: 1
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 1.0; color: "#f5f5f5" }
                        }
                    }
                }
            }
        }

        // ══════════════════════════════════════════════════════════
        // BACK FACE — Add / Edit form
        // ══════════════════════════════════════════════════════════
        Item {
            id: backFace
            anchors.fill: parent
            visible: flipRot.angle >= 90

            transform: Rotation {
                axis { x: 0; y: 1; z: 0 }
                origin.x: backFace.width  / 2
                origin.y: backFace.height / 2
                angle: 180
            }

            ToolEditForm {
                id: editForm
                anchors.fill: parent

                onSaved: {
                    if (toolLibraryViewModel && toolLibraryViewModel.saveToolFull(formData.toolNo, formData)) {
                        root._flipToFront()
                    }
                }

                onCancelled: root._flipToFront()
                onOpenNumPadRequested: root.openNumPadRequested(field)
            }
        }
    }

    // ── Delete confirmation dialog ─────────────────────────────────
    Dialog {
        id: deleteDialog
        modal: true; title: "Confirm Delete"
        standardButtons: Dialog.Yes | Dialog.No
        property int toolNo: -1

        onAccepted: {
            if (toolNo >= 0) toolLibraryViewModel.deleteTool(toolNo)
        }

        contentItem: Text {
            text: deleteDialog.toolNo >= 0
                ? "Delete tool T" + deleteDialog.toolNo + "?"
                : "Delete tool?"
            wrapMode: Text.WordWrap; padding: 16
        }
    }
}
