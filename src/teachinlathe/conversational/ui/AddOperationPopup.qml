import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import theme 1.0

Popup {
    id: root
    parent: Overlay.overlay
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: parent

    contentWidth: 1000
    contentHeight: column.implicitHeight
    padding: 0

    // type = operation type string, insertIndex = position in list
    signal operationChosen(string type, int insertIndex)

    property int    operationsCount:  0
    property int    currentOpIndex:   -1
    property string selectedType:     ""
    property int    buttonsPerRow:    4
    readonly property int buttonWidth: 180
    readonly property int buttonHeight: Theme.buttonHeightTouch
    readonly property int buttonFontSize: 16
    readonly property int buttonSpacing: 40

    onAboutToShow: { selectedType = "" }

    background: Rectangle {
        radius: Theme.radiusXLarge
        color: Theme.surfaceSunken
        border.color: Theme.dialogBorder
        border.width: Theme.hairline
    }

    property var options: [
        { label: "Tool Change",      type: "changeTool"      },
        { label: "Position At",      type: "positionAt"      },
        { label: "Facing",           type: "facing"          },
        { label: "G33 Knurling",     type: "knurling"        },
        { label: "Define Profile",   type: "defineProfile"   },
        { label: "Import DXF Profile", type: "importDxfProfile" },
        { label: "Define Radial Profile", type: "defineRadialProfile" },
        { label: "G7x Cut Profile",  type: "profiling"       },
        { label: "Profile Roughing", type: "profileRoughing"  },
        { label: "Profile Contour",  type: "profileContour"   },
        { label: "Groove Roughing",  type: "grooveRoughing"   },
        { label: "Groove Finishing", type: "grooveFinishing"  },
        { label: "G76 Threading",    type: "threading"       },
        { label: "G33 Threading",    type: "g33Threading"    },
        { label: "Drilling",         type: "drilling"        },
        { label: "Tapping",          type: "tapping"         },
        { label: "Parting",          type: "parting"         }
    ]

    contentItem: Column {
        id: column
        spacing: root.buttonSpacing
        width: root.contentWidth
        padding: 16

        Text {
            text: "Add Operation"
            font.pixelSize: Theme.fontLarge
            font.bold: true
            color: Theme.foreground
        }

        // Duplicate Selected Operation button (centered)
        Item {
            width: column.width - column.padding * 2
            height: root.buttonHeight

            Button {
                id: duplicateBtn
                anchors.centerIn: parent
                readonly property bool isSelected: root.selectedType === "__duplicate__"
                width: root.buttonWidth * 2 + root.buttonSpacing
                height: root.buttonHeight
                text: "Duplicate Selected Operation"
                font.pixelSize: root.buttonFontSize

                background: Rectangle {
                    radius: Theme.radiusSmall
                    color: {
                        if (duplicateBtn.isSelected) return Theme.selection
                        if (duplicateBtn.pressed)    return Theme.accentSoft
                        if (duplicateBtn.hovered)    return Theme.hover
                        return Theme.surface
                    }
                    border.color: duplicateBtn.isSelected ? Theme.accentStrong
                                                          : Theme.dialogBorder
                    border.width: Theme.hairline
                }
                contentItem: Text {
                    text: duplicateBtn.text
                    font: duplicateBtn.font
                    color: Theme.foreground
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
            height: Theme.hairline
            color: Theme.separator
        }

        // Operation type buttons
        Flow {
            id: flowArea
            width: column.width - column.padding * 2
            spacing: root.buttonSpacing

            Repeater {
                model: root.options
                delegate: Button {
                    readonly property bool isSelected: root.selectedType === modelData.type

                    width: root.buttonWidth
                    height: root.buttonHeight
                    font.pixelSize: root.buttonFontSize
                    text: modelData.label

                    background: Rectangle {
                        radius: Theme.radiusSmall
                        color: {
                            if (isSelected)       return Theme.selection
                            if (parent.pressed)   return Theme.accentSoft
                            if (parent.hovered)   return Theme.hover
                            return Theme.surface
                        }
                        border.color: isSelected ? Theme.accentStrong
                                                 : Theme.dialogBorder
                        border.width: Theme.hairline
                    }
                    contentItem: Text {
                        text: parent.text
                        font: parent.font
                        color: Theme.foreground
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
            height: Theme.hairline
            color: Theme.separator
        }

        // Footer row
        Item {
            width: column.width - column.padding * 2
            height: root.buttonHeight

            // Cancel — always left
            Button {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "Cancel"
                width: root.buttonWidth
                height: root.buttonHeight
                font.pixelSize: root.buttonFontSize
                onClicked: root.close()
            }

            // Insert buttons — right side, only when list has ops
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: root.buttonSpacing
                visible: root.operationsCount > 0

                Button {
                    text: "Insert Above"
                    width: root.buttonWidth
                    height: root.buttonHeight
                    font.pixelSize: root.buttonFontSize
                    enabled: root.selectedType !== ""
                    onClicked: {
                        var idx = Math.max(0, root.currentOpIndex)
                        root.operationChosen(root.selectedType, idx)
                        root.close()
                    }
                }

                Button {
                    text: "Insert Below"
                    width: root.buttonWidth
                    height: root.buttonHeight
                    font.pixelSize: root.buttonFontSize
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
