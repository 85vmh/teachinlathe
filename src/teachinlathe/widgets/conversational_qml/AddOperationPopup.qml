import QtQuick 2.15
import QtQuick.Controls 2.15

Popup {
    id: root
    parent: Overlay.overlay
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: parent

    contentWidth: 360
    contentHeight: column.implicitHeight
    padding: 0

    signal operationChosen(string type)

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
        { label: "Parting",        type: "parting"       }
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

        Repeater {
            model: root.options
            delegate: Button {
                text: modelData.label
                width: column.width - 32
                onClicked: {
                    root.operationChosen(modelData.type)
                    root.close()
                }
            }
        }

        Button {
            text: "Cancel"
            width: column.width - 32
            onClicked: root.close()
        }
    }
}
