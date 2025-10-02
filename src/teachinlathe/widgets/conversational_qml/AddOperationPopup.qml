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

    signal operationChosen(string type)

    // How many buttons per row in the flow area
    property int buttonsPerRow: 4

    background: Rectangle {
        radius: 10
        color: "#202225"
        border.color: "#3A3D41"
        border.width: 1
    }

    property var options: [
        { label: "Tool Change",    type: "changeTool"    },
        { label: "Facing",         type: "facing"        },
        { label: "Define Profile", type: "define_profile"},
        { label: "Cut Profile",    type: "profiling"     },
        { label: "Threading",      type: "threading"     },
        { label: "Drilling",       type: "drilling"      },
        { label: "Tapping",        type: "tapping"       },
        { label: "Parting",        type: "parting"       },
        { label: "KeySlot",        type: "keyslot"       }
    ]

    contentItem: Column {
        id: column
        spacing: 12
        width: root.contentWidth
        padding: 16

        Text {
            text: "Add operation"
            font.pixelSize: 18
            color: "white"
        }

        // Flow area for operation buttons
        Flow {
            id: flowArea
            width: column.width - column.padding * 2
            spacing: 8

            Repeater {
                model: root.options
                delegate: Button {
                    // Fixed height, computed width to fit N per row accounting for spacing
                    readonly property int itemWidth: Math.floor(
                        (flowArea.width - flowArea.spacing * (root.buttonsPerRow - 1)) / root.buttonsPerRow
                    )
                    width: itemWidth
                    height: 40
                    font.pixelSize: Theme.fontSizeNormal
                    text: modelData.label
                    onClicked: {
                        root.operationChosen(modelData.type)
                        root.close()
                    }
                }
            }
        }

        // Separator between the flow grid and the footer (cancel)
        Rectangle {
            width: column.width - column.padding * 2
            height: 1
            color: "#3A3D41"
        }

        // Footer with Cancel button
        Button {
            text: "Cancel"
            width: column.width - column.padding * 2
            onClicked: root.close()
        }
    }
}
