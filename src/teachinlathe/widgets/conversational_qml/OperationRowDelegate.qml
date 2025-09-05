import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.0
import "."   // for Divider.qml

Rectangle {
    id: root
    // Inputs from the ListView delegate
    property var  op
    property int  rowIndex: -1
    property bool isCurrentItem: false

    // Column widths
    property int colOpNumW: 50
    property int colGenW:   80
    property int colTypeW:  200
    property int colOptW:   80
    property int colDelW:   80

    // Delete icon customization
    property url  deleteIconSource: "delete_icon.svg"
    property color deleteTint: "#C62828"
    property color deletePressedTint: "#AD2121"
    property color pressedBgColor: "#E6F0FF"  // soft blue highlight on press

    // Signals back to parent
    signal generateToggled(int rowIndex, bool checked)
    signal optionalToggled(int rowIndex, bool checked)
    signal deleteClicked(int rowIndex)
    signal rowTapped(int rowIndex)

    width: parent ? parent.width : 400
    height: 60
    radius: 0
    color: (rowIndex % 2 === 0 ? "#fafafa" : "#f0f0f0")
    border.width: isCurrentItem ? 1 : 0
    border.color: "#8ec5ff"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Order
        Label {
            text: (op && op.order !== undefined) ? op.order : (rowIndex + 1)
            Layout.minimumWidth: colOpNumW
            Layout.preferredWidth: colOpNumW
            Layout.maximumWidth: colOpNumW
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            Layout.alignment: Qt.AlignVCenter
        }
        Divider { }

        // Generate GCode
        Item {
            Layout.minimumWidth: colGenW
            Layout.preferredWidth: colGenW
            Layout.maximumWidth: colGenW
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
                    root.generateToggled(rowIndex, checked)
                }
            }
        }
        Divider { }

        // Operation Type (flex) + margin
        Item {
            Layout.minimumWidth: colTypeW
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
            Layout.minimumWidth: colOptW
            Layout.preferredWidth: colOptW
            Layout.maximumWidth: colOptW
            Layout.fillHeight: true
            CheckBox {
                anchors.centerIn: parent
                checked: !!(op && op.is_optional_block)
                onToggled: {
                    if (!op) return
                    op.is_optional_block = checked
                    root.optionalToggled(rowIndex, checked)
                }
            }
        }
        Divider { }

        // Delete "icon button" (touch friendly, with pressed feedback)
        Item {
            Layout.minimumWidth: colDelW
            Layout.preferredWidth: colDelW
            Layout.maximumWidth: colDelW
            Layout.fillHeight: true

            // Button container (fixed touch target)
            Item {
                id: delBtn
                width: 40
                height: 40
                anchors.centerIn: parent
                scale: tap.pressed ? 0.92 : 1.0

                // Pressed background highlight
                Rectangle {
                    id: pressedBg
                    anchors.fill: parent
                    radius: 8
                    color: tap.pressed ? pressedBgColor : "transparent"
                }

                // Source image (hidden, feeds the overlay)
                Image {
                    id: delImg
                    anchors.centerIn: parent
                    source: deleteIconSource
                    sourceSize.width: 24
                    sourceSize.height: 24
                    visible: false
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                // Tint overlay; darken a bit when pressed
                ColorOverlay {
                    anchors.centerIn: delImg
                    width: delImg.width
                    height: delImg.height
                    source: delImg
                    color: tap.pressed ? deletePressedTint : deleteTint
                }

                // Tap handler (no mouse cursor; touch-first)
                TapHandler {
                    id: tap
                    acceptedButtons: Qt.LeftButton
                    onTapped: root.deleteClicked(rowIndex)
                }

                // Smooth scale transition
                Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }
            }
        }
    }

    // Sync initial enabled state on creation
    Component.onCompleted: {
        var en = !!(op && op.generate_gcode)
        typeLabel.enabled = en
        optCell.enabled   = en
    }

    TapHandler { onTapped: root.rowTapped(rowIndex) }
}
