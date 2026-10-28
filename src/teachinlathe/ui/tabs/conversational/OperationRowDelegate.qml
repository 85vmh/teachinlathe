import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

// An operation in the program's list: swipes to Delete or Duplicate (see
// SwipeRow), and lifts on a long press to be dragged to a new place.
SwipeRow {
    id: root

    // Inputs from the ListView delegate: the operation's row
    // (OperationListModel's roles) and where it is
    property int    number: 0
    property string title: ""
    property string toolLabel: ""
    property bool   generateGcode: false
    property bool   optionalBlock: false
    property int    rowIndex: -1
    property bool   isCurrentItem: false

    // Column widths
    property int colOpNumW: 50
    property int colGenW:   80
    property int colTypeW:  200
    property int colOptW:   80
    property int colDelW:   100       // the Delete and Duplicate swipe buttons
    property int itemFontSize: 16

    // Being dragged to a new place, after a long press
    property bool lifted: false

    // Bound to the row, never set: the list hands a row another
    // operation's when operations move, and it must follow.
    readonly property bool gcodeEnabled: generateGcode
    readonly property int operationLabelMinW: colOpNumW + colTypeW
    readonly property string operationLabel: {
        var numberText = number >= 1 && number <= 9 ? "0" + number : "" + number
        return "[#" + numberText + "]    " + title
    }

    // Signals back to parent
    signal generateToggled(int rowIndex, bool checked)
    signal optionalToggled(int rowIndex, bool checked)
    signal deleteClicked(int rowIndex)
    signal duplicateClicked(int rowIndex)
    signal rowTapped(int rowIndex)
    // Long pressed, the row lifts and follows the finger up or down: dy is
    // how far it has been dragged, in scene pixels. The list moves the rows.
    signal reorderStarted(int rowIndex)
    signal reorderMoved(int rowIndex, real dy)
    signal reorderFinished(int rowIndex)

    width: parent ? parent.width : 400
    height: Theme.rowHeight
    actionWidth: colDelW
    swipeEnabled: !reorderArea.lifted
    onDeleteRequested: deleteClicked(rowIndex)
    onDuplicateRequested: duplicateClicked(rowIndex)

    contentColor: root.lifted ? Theme.lifted
                : root.isCurrentItem ? Theme.selection
                : (root.rowIndex % 2 === 0 ? Theme.surfaceSunken : Theme.outlineDisabled)
    contentBorderWidth: root.lifted || root.isCurrentItem ? 2 : 0
    contentBorderColor: root.lifted ? Theme.warning : root.isCurrentItem ? Theme.accent : "transparent"

    // Under the row's own controls, so a long press on a checkbox does not
    // lift it. It takes the press, so it is also what selects the row.
    MouseArea {
        id: reorderArea
        anchors.fill: parent
        pressAndHoldInterval: 500
        property bool lifted: false
        property real startSceneY: 0

        function finish() {
            if (!lifted)
                return
            lifted = false
            preventStealing = false
            root.reorderFinished(rowIndex)
        }

        onPressAndHold: function(mouse) {
            if (root.swipeOffset !== 0)
                return
            lifted = true
            preventStealing = true      // the list must not take the drag over to scroll
            startSceneY = mapToItem(null, mouse.x, mouse.y).y
            root.reorderStarted(rowIndex)
        }
        onPositionChanged: function(mouse) {
            if (lifted)
                root.reorderMoved(rowIndex, mapToItem(null, mouse.x, mouse.y).y - startSceneY)
        }
        onClicked: root.rowTapped(rowIndex)   // not after a press and hold
        onReleased: finish()
        onCanceled: finish()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Operation label combines order and operation name.
        Item {
            Layout.minimumWidth: root.operationLabelMinW
            Layout.fillWidth: true
            Layout.fillHeight: true
            Label {
                id: typeLabel
                anchors.left: parent.left
                anchors.right: toolNumber.visible ? toolNumber.left : parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                // stays put while the row slides left over Delete
                anchors.leftMargin: 10 + Math.max(0, root.swipeOffset)
                anchors.rightMargin: toolNumber.visible ? 8 : 0
                text: root.operationLabel
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: root.itemFontSize
                color: root.gcodeEnabled ? "black" : Theme.outlineStrong
            }
            Label {
                id: toolNumber
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                visible: root.toolLabel !== ""
                text: root.toolLabel
                font.pixelSize: root.itemFontSize
                font.bold: true
                color: root.gcodeEnabled ? "black" : Theme.outlineStrong
            }
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
                checked: root.gcodeEnabled
                onToggled: {
                    root.generateToggled(rowIndex, checked)
                    // a click breaks the binding; the save above has already
                    // put the new value in the operation
                    checked = Qt.binding(function() { return root.gcodeEnabled })
                }
            }
        }
        Divider { }

        // Optional Block
        Item {
            id: optCell
            enabled: root.gcodeEnabled
            Layout.minimumWidth: colOptW
            Layout.preferredWidth: colOptW
            Layout.maximumWidth: colOptW
            Layout.fillHeight: true
            CheckBox {
                anchors.centerIn: parent
                checked: root.optionalBlock
                onToggled: {
                    root.optionalToggled(rowIndex, checked)
                    checked = Qt.binding(function() { return root.optionalBlock })
                }
            }
        }
    }
}
