import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Popup {
    id: root
    parent: Overlay.overlay
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: parent

    contentWidth: 500
    contentHeight: column.implicitHeight
    padding: 0

    // type = operation type string, insertIndex = position in list
    signal operationChosen(string type, int insertIndex)

    property int    operationsCount:  0
    property int    currentOpIndex:   -1
    property string selectedType:     ""
    property int    buttonsPerRow:    4

    onAboutToShow: { selectedType = "" }

    background: Rectangle {
        radius: 10
        color: "#202225"
        border.color: "#3A3D41"
        border.width: 1
    }

    property var options: [
        { label: "Tool Change",      type: "changeTool"      },
        { label: "Position At",      type: "positionAt"      },
        { label: "Facing",           type: "facing"          },
        { label: "SinglePoint Knurling", type: "knurling"    },
        { label: "Define Profile",   type: "defineProfile"   },
        { label: "G7x Cut Profile",  type: "profiling"       },
        { label: "Custom Profiling", type: "customProfiling" },
        { label: "Profile Boring",   type: "profileBoring"   },
        { label: "G76 Threading",    type: "threading"       },
        { label: "Drilling",         type: "drilling"        },
        { label: "Tapping",          type: "tapping"         },
        { label: "Parting",          type: "parting"         }
    ]

    contentItem: Column {
        id: column
        spacing: 12
        width: root.contentWidth
        padding: 16

        Text {
            text: "Add Operation"
            font.pixelSize: 18
            font.bold: true
            color: "white"
        }

        // Duplicate Selected Operation button (centered)
        Item {
            width: column.width - column.padding * 2
            height: 40

            Button {
                id: duplicateBtn
                anchors.centerIn: parent
                readonly property bool isSelected: root.selectedType === "__duplicate__"
                width: 240
                height: 40
                text: "Duplicate Selected Operation"
                font.pixelSize: Theme.fontSizeNormal

                background: Rectangle {
                    radius: 4
                    color: {
                        if (duplicateBtn.isSelected) return "#1E88E5"
                        if (duplicateBtn.pressed)    return "#3A4A5A"
                        if (duplicateBtn.hovered)    return "#2A3540"
                        return "#2D3035"
                    }
                    border.color: duplicateBtn.isSelected ? "#1565C0" : "#4A4D52"
                    border.width: 1
                }
                contentItem: Text {
                    text: duplicateBtn.text
                    font: duplicateBtn.font
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: {
                    root.selectedType = (root.selectedType === "__duplicate__") ? "" : "__duplicate__"
                }
            }
        }

        // Separator between Duplicate button and operation type buttons
        Rectangle {
            width: column.width - column.padding * 2
            height: 1
            color: "#3A3D41"
        }

        // Operation type buttons
        Flow {
            id: flowArea
            width: column.width - column.padding * 2
            spacing: 8

            Repeater {
                model: root.options
                delegate: Button {
                    readonly property int itemWidth: Math.floor(
                        (flowArea.width - flowArea.spacing * (root.buttonsPerRow - 1)) / root.buttonsPerRow
                    )
                    readonly property bool isSelected: root.selectedType === modelData.type

                    width: itemWidth
                    height: 40
                    font.pixelSize: Theme.fontSizeNormal
                    text: modelData.label

                    background: Rectangle {
                        radius: 4
                        color: {
                            if (isSelected)       return "#1E88E5"
                            if (parent.pressed)   return "#3A4A5A"
                            if (parent.hovered)   return "#2A3540"
                            return "#2D3035"
                        }
                        border.color: isSelected ? "#1565C0" : "#4A4D52"
                        border.width: 1
                    }
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    onClicked: {
                        if (root.operationsCount === 0) {
                            // No existing ops: add at position 0 immediately
                            root.operationChosen(modelData.type, 0)
                            root.close()
                        } else {
                            // Selecting a type always clears duplicate selection
                            root.selectedType = (root.selectedType === modelData.type) ? "" : modelData.type
                        }
                    }
                }
            }
        }

        Rectangle {
            width: column.width - column.padding * 2
            height: 1
            color: "#3A3D41"
        }

        // Footer row
        Item {
            width: column.width - column.padding * 2
            height: 44

            // Cancel — always left
            Button {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "Cancel"
                width: 100
                height: 40
                onClicked: root.close()
            }

            // Insert buttons — right side, only when list has ops
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                visible: root.operationsCount > 0

                Button {
                    text: "Insert Above"
                    width: 130
                    height: 40
                    enabled: root.selectedType !== ""
                    onClicked: {
                        var idx = Math.max(0, root.currentOpIndex)
                        root.operationChosen(root.selectedType, idx)
                        root.close()
                    }
                }

                Button {
                    text: "Insert Below"
                    width: 130
                    height: 40
                    enabled: root.selectedType !== ""
                    onClicked: {
                        root.operationChosen(root.selectedType, root.currentOpIndex + 1)
                        root.close()
                    }
                }
            }
        }
    }
}
