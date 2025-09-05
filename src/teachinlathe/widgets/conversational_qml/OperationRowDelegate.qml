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

    // Column widths (last column fixed to 100px)
    property int colOpNumW: 50
    property int colGenW:   80
    property int colTypeW:  200
    property int colOptW:   80
    property int colDelW:   100

    // Edit/Reorder mode toggle
    property bool editing: false

    // Icon sources / tints
    property url  deleteIconSource:   "delete_icon.svg"
    property url  moveUpIconSource:   "move_up_icon.svg"
    property url  moveDownIconSource: "move_down_icon.svg"
    property color deleteTint:   "#C62828"
    property color reorderTint:  "#4F4F4F"

    // Signals back to parent
    signal generateToggled(int rowIndex, bool checked)
    signal optionalToggled(int rowIndex, bool checked)
    signal deleteClicked(int rowIndex)
    signal moveUpRequested(int rowIndex)
    signal moveDownRequested(int rowIndex)
    signal rowTapped(int rowIndex)

    width: parent ? parent.width : 400
    height: 60
    radius: 0
    color: (rowIndex % 2 === 0 ? "#fafafa" : "#f0f0f0")
    border.width: isCurrentItem ? 1 : 0
    border.color: "#8ec5ff"

    // Simple reusable icon button with press feedback and tint
    Component {
        id: pressableIcon
        Rectangle {
            id: iconBtn
            width: 36
            height: 36
            radius: 6
            color: pressedArea.pressed ? "#e1f0ff" : "transparent"
            border.color: pressedArea.pressed ? "#8ec5ff" : "transparent"
            border.width: pressedArea.pressed ? 1 : 0

            property alias source: baseImg.source
            property color tint: "#4F4F4F"
            signal clicked()

            // Base image (hidden) + color overlay for tinting
            Image {
                id: baseImg
                anchors.centerIn: parent
                sourceSize.width: 24
                sourceSize.height: 24
                visible: false
                fillMode: Image.PreserveAspectFit
                smooth: true
            }
            ColorOverlay {
                anchors.centerIn: baseImg
                width: baseImg.width
                height: baseImg.height
                source: baseImg
                color: iconBtn.tint
            }

            MouseArea {
                id: pressedArea
                anchors.fill: parent
                onClicked: iconBtn.clicked()
            }
        }
    }

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

        // Delete / Reorder column (fixed 100px)
        Item {
            Layout.minimumWidth: colDelW
            Layout.preferredWidth: colDelW
            Layout.maximumWidth: colDelW
            Layout.fillHeight: true

            // NORMAL MODE: single delete icon centered
            Loader {
                anchors.centerIn: parent
                active: !root.editing
                sourceComponent: pressableIcon
                onLoaded: {
                    item.source = root.deleteIconSource
                    item.tint   = root.deleteTint
                    item.clicked.connect(function() { root.deleteClicked(rowIndex) })
                }
            }

            // EDIT MODE: two icons (up/down) side-by-side centered
            Row {
                anchors.centerIn: parent
                spacing: 6
                visible: root.editing

                Loader {
                    sourceComponent: pressableIcon
                    onLoaded: {
                        item.source = root.moveUpIconSource
                        item.tint   = root.reorderTint
                        item.clicked.connect(function() { root.moveUpRequested(rowIndex) })
                    }
                }
                Loader {
                    sourceComponent: pressableIcon
                    onLoaded: {
                        item.source = root.moveDownIconSource
                        item.tint   = root.reorderTint
                        item.clicked.connect(function() { root.moveDownRequested(rowIndex) })
                    }
                }
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
