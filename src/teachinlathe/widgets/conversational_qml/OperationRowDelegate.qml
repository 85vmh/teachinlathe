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

    // Position info for enabling/disabling reorder buttons
    property bool isFirstItem: false
    property bool isLastItem: false
    property int  totalCount: 0

    // Column widths (last column fixed to 100px)
    property int colOpNumW: 50
    property int colGenW:   80
    property int colTypeW:  200
    property int colOptW:   80
    property int colDelW:   100

    // Edit/Reorder mode toggle
    property bool editing: false
    property int itemFontSize: 16

    property bool gcodeEnabled: !!(op && op.generate_gcode)

    // Icon sources / tints
    property url  deleteIconSource:   "icons/delete_icon.svg"
    property url  moveUpIconSource:   "icons/move_up_icon.svg"
    property url  moveDownIconSource: "icons/move_down_icon.svg"
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
    height: 72
    radius: 0
    color: isCurrentItem ? "#dbeafe" : (rowIndex % 2 === 0 ? "#f0f0f0" : "#e5e5e5")
    border.width: isCurrentItem ? 2 : 0
    border.color: isCurrentItem ? "#3b82f6" : "transparent"

    // Reusable icon button with press feedback, tint, and enabled state
    Component {
        id: pressableIcon
        Rectangle {
            id: iconBtn
            width: 40
            height: 40
            radius: 6

            // Background stays transparent, flashes light blue when pressed
            color: (!enabled ? "transparent"
                             : (pressedArea.pressed ? "#e1f0ff" : "transparent"))

            // Always show a border when enabled: gray by default, blue when pressed
            border.width: enabled ? 1 : 0
            border.color: !enabled ? "transparent"
                                   : (pressedArea.pressed ? "#8ec5ff" : "#BDBDBD")

            opacity: enabled ? 1.0 : 0.35

            property alias source: baseImg.source
            property color tint: "#4F4F4F"
            property bool  enabled: true
            signal clicked()

            Image {
                id: baseImg
                anchors.centerIn: parent
                sourceSize.width: 30
                sourceSize.height: 30
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
                enabled: iconBtn.enabled
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
            font.pixelSize: root.itemFontSize
            color: root.gcodeEnabled ? "black" : "#c4c4c4"
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
                    root.gcodeEnabled = checked
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
                font.pixelSize: root.itemFontSize
                color: root.gcodeEnabled ? "black" : "#c4c4c4"
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
                    item.enabled = true
                    item.clicked.connect(function() { root.deleteClicked(rowIndex) })
                }
            }

            // EDIT MODE: two icons (up/down) side-by-side centered
            Row {
                anchors.centerIn: parent
                spacing: 6
                visible: root.editing

                // Move Up
                Loader {
                    sourceComponent: pressableIcon
                    onLoaded: {
                        item.source  = root.moveUpIconSource
                        item.tint    = root.reorderTint
                        item.enabled = (root.totalCount > 1 && !root.isFirstItem)
                        item.clicked.connect(function() { root.moveUpRequested(rowIndex) })
                    }
                }
                // Move Down
                Loader {
                    sourceComponent: pressableIcon
                    onLoaded: {
                        item.source  = root.moveDownIconSource
                        item.tint    = root.reorderTint
                        item.enabled = (root.totalCount > 1 && !root.isLastItem)
                        item.clicked.connect(function() { root.moveDownRequested(rowIndex) })
                    }
                }
            }
        }
    }

    // Sync initial enabled state on creation
    Component.onCompleted: {
        var en = !!(op && op.generate_gcode)
        root.gcodeEnabled = en
        optCell.enabled   = en
    }

    TapHandler { onTapped: root.rowTapped(rowIndex) }
}
