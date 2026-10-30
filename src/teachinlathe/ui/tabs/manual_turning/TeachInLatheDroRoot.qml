import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

Rectangle {
    id: root

    color: Theme.surface

    required property var viewModel
    // The title bar's area (AppShell.titleBarArea): the boxes' titles and
    // the work offset choice are there, each over its box. None, not shown.
    property Item titleBar: null

    signal toastRequested(string message)
    //: The preset positions tapped: the limits panel turns over, to the
    //: machine limits' drawing and back (ManualTurningRoot).
    signal presetPositionsClicked()
    signal openNumPadRequested(var field)

    QtObject {
        id: zDatumField

        property string settingName: "manual.z-set-datum"
        property string description: "Set Z datum value"
        property var value: 0.0

        function commit(v) {
            value = v
            if (root.viewModel) {
                root.viewModel.zSetDatumValueSelected(v)
            }
            return true
        }

        function defocus() {
        }
    }

    // The value measured with the current tool: a diameter in X, the
    // distance to Z0 in Z.
    component TouchOffField: QtObject {
        property string axis
        property string settingName
        property string description
        property var value: 0.0

        function commit(v) {
            value = v
            if (root.viewModel) {
                root.viewModel.touchOff(axis, v)
            }
            return true
        }

        function defocus() {
        }
    }

    TouchOffField {
        id: xTouchOffField
        axis: "x"
        settingName: "smart_numpad.x-offset"
        description: "Measured diameter with current tool"
    }

    TouchOffField {
        id: zTouchOffField
        axis: "z"
        settingName: "smart_numpad.z-offset"
        description: "Distance to Z0 with current tool"
    }

    // The two boxes the axes' values are in, round both rows: the machine
    // coordinates (G53, no offset at all; X a radius), and the work
    // coordinates - the inputs - with the buttons on their right, out to the
    // edge the Limits panel under it has. Drawn under the rows, where the
    // rows put their values (ManualModeAxisDro's geometry).
    // A row's values (primaryHeight) are centred in it: this far from its
    // top and its bottom.
    readonly property real rowInset: (xDro.height - xDro.primaryHeight) / 2
    // between the rows
    readonly property int rowGap: 5
    // the predefined positions' column, in the machine coordinates' box
    // after a divider
    readonly property int predefinedWidth: 92
    // over the preset positions' title, and under their last
    readonly property int presetPadding: 12
    readonly property int predefinedExtra: Theme.droBoxPadding + 1 + Theme.droBoxPadding + predefinedWidth
    // the boxes, from the top - level with the tool list's - to the padding
    // under the second row's values (ManualTurningRoot sizes the DRO by it)
    readonly property real boxesHeight: zDro.y + rowInset + xDro.primaryHeight + Theme.droBoxPadding

    component ValuesBox: Rectangle {
        y: 0
        height: root.boxesHeight
        radius: Theme.radius
        color: Theme.surfaceAlt
        border.color: Theme.outline
        border.width: Theme.hairline
    }

    ValuesBox {
        id: machineBox
        x: xDro.machineLeft - xDro.boxPadding
        width: xDro.machineWidth + root.predefinedExtra + 2 * xDro.boxPadding

        Rectangle {
            id: predefinedDivider
            x: xDro.boxPadding + xDro.machineWidth + Theme.droBoxPadding
            y: Theme.droBoxPadding
            width: 1
            height: parent.height - 2 * Theme.droBoxPadding
            color: Theme.outline
        }

        // M6, G28 and G30: a check when set, a warning when not
        // (TeachInLatheDroViewModel, predefined_positions_repository). The
        // title presetPadding under the box's top, the last position as far
        // over its bottom, the positions spread evenly between: a table - the
        // icons in the first column, the names in the second - centred in the
        // space after the divider.
        ColumnLayout {
            x: predefinedDivider.x + 1
            y: root.presetPadding
            width: parent.width - x
            height: parent.height - 2 * root.presetPadding
            spacing: 0

            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: "Preset\nPositions"
                color: Theme.foregroundSubtle
                font.pixelSize: Theme.fontBody
                font.bold: true
            }
            Item { Layout.fillHeight: true }
            PresetPosition { label: "M6"; set: root.viewModel.toolChangeSet }
            Item { Layout.fillHeight: true }
            PresetPosition { label: "G28"; set: root.viewModel.g28Set }
            Item { Layout.fillHeight: true }
            PresetPosition { label: "G30"; set: root.viewModel.g30Set }
        }

        // the whole box: tapped, the limits panel turns over
        MouseArea {
            anchors.fill: parent
            onClicked: root.presetPositionsClicked()
        }
    }

    // the preset positions' table: its icon column, and its names column as
    // wide as the widest name
    readonly property int presetIconSize: 22
    TextMetrics {
        id: presetNameMetrics
        font.pixelSize: Theme.fontBody
        font.bold: true
        text: "G28"
    }

    // A preset position, a row of their table: set - a green check - or not
    // - a warning sign, the name in the warning colour - centred in the
    // first column, its name, bold, in the second
    component PresetPosition: Row {
        property string label
        property bool set: false

        Layout.alignment: Qt.AlignHCenter
        spacing: Theme.spacingSmall

        Image {
            width: root.presetIconSize
            height: root.presetIconSize
            source: Images.url(parent.set ? "check_set.svg" : "warning_unset.svg")
            sourceSize.width: 2 * width
            sourceSize.height: 2 * height
        }
        Text {
            width: Math.ceil(presetNameMetrics.advanceWidth)
            anchors.verticalCenter: parent.verticalCenter
            text: parent.label
            color: parent.set ? Theme.foreground : Theme.warning
            font.pixelSize: Theme.fontBody
            font.bold: true
        }
    }

    ValuesBox {
        id: workBox
        x: xDro.valueLeft - xDro.boxPadding
        // as far right as LimitsPanel: the column's edge
        width: root.width - x
    }

    // The boxes' titles, in the title bar over them - while this tab is up
    // (a hidden tab hides this; what is in the title bar is not this) - each
    // centred over its box.
    component BoxTitle: Text {
        color: Theme.foregroundSubtle
        font.pixelSize: Theme.fontLarge
        font.bold: true
    }

    // Where the axis letters go: under the title bar's menu, as wide as it
    // (AppShellTopBar: its actions Theme.titleBarMargin in, square)
    readonly property real axisLeft: {
        var resized = root.width + (root.titleBar ? root.titleBar.width : 0)
        return root.titleBar ? root.mapFromItem(root.titleBar, Theme.titleBarMargin, 0).x : 0
    }

    // the x in the title bar the middle of what is at ``left`` and ``width``
    // in this item is under
    function titleBarCentre(left, width) {
        // both sides' widths too, so the binding follows them - the window
        // resized moves them all
        var middle = left + width / 2
        var resized = root.width + (root.titleBar ? root.titleBar.width : 0)
        return root.titleBar ? root.mapToItem(root.titleBar, middle, 0).x : 0
    }

    BoxTitle {
        parent: root.titleBar
        visible: root.titleBar !== null && root.visible
        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
        // over the machine coordinates' fields
        x: root.titleBarCentre(xDro.machineLeft, xDro.machineWidth) - width / 2
        text: "Machine Coordinates (G53)"
    }

    // the work offset the tool coordinates are in, to choose another from:
    // by MDI, not while feeding (TeachInLatheDroViewModel)
    Row {
        parent: root.titleBar
        visible: root.titleBar !== null && root.visible
        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
        // over the tool coordinates' big fields
        x: root.titleBarCentre(xDro.primaryLeft, xDro.primaryWidth) - width / 2
        spacing: Theme.spacingSmall

        BoxTitle {
            anchors.verticalCenter: parent.verticalCenter
            text: "Tool Coordinates in"
        }

        ComboBox {
            id: workOffsetCombo
            anchors.verticalCenter: parent.verticalCenter
            // as wide as the program header's Datum (HeaderDetailsView's
            // Choice): its text and the arrow, the padding on the right
            // holding the arrow
            implicitWidth: leftPadding + contentItem.implicitWidth + rightPadding
            implicitHeight: Theme.buttonHeight
            font.pixelSize: Theme.fontTitle
            contentItem: Text {
                leftPadding: 8
                rightPadding: 8
                text: workOffsetCombo.displayText
                font: workOffsetCombo.font
                color: Theme.foregroundStrong
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            model: root.viewModel.workOffsets
            // as in use - G59.1 and past, not offered, are shown as they are
            currentIndex: model.indexOf(root.viewModel.workOffsetName)
            displayText: root.viewModel.workOffsetName
            enabled: root.viewModel.workOffsetSelectable
            onActivated: function(index) {
                root.viewModel.selectWorkOffset(textAt(index))
                // back to the one in use, until the machine says it changed
                currentIndex = Qt.binding(function() {
                    return workOffsetCombo.model.indexOf(root.viewModel.workOffsetName)
                })
            }
        }
    }

    ManualModeAxisDro {
        id: xDro
        x: 0
        // its values the boxes' padding under their tops
        y: Theme.droBoxPadding - root.rowInset
        width: parent.width
        axisLabel: "X"
        toolSet: root.viewModel.xToolSet
        machineBoxExtra: root.predefinedExtra
        axisLeft: root.axisLeft
        axisWidth: Theme.buttonHeight
        machineVisible: true
        machineValue: root.viewModel.xMachineValue
        primaryValue: root.viewModel.xPrimaryValue
        secondaryValue: root.viewModel.xSecondaryValue
        secondaryVisible: root.viewModel.xSecondaryVisible
        unit: root.viewModel.units
        onPrimaryClicked: root.viewModel.xPrimaryClicked()
        onZeroClicked: root.viewModel.xZeroClicked()
        isAbs: root.viewModel.xIsAbs
        onAbsRelClicked: root.viewModel.xAbsRelClicked()
    }

    ManualModeAxisDro {
        id: zDro
        x: 0
        y: xDro.y + xDro.height + root.rowGap
        width: parent.width
        axisLabel: "Z"
        toolSet: root.viewModel.zToolSet
        machineBoxExtra: root.predefinedExtra
        axisLeft: root.axisLeft
        axisWidth: Theme.buttonHeight
        machineVisible: true
        machineValue: root.viewModel.zMachineValue
        primaryValue: root.viewModel.zPrimaryValue
        secondaryValue: root.viewModel.zSecondaryValue
        secondaryVisible: root.viewModel.zSecondaryVisible
        unit: root.viewModel.units
        onPrimaryClicked: root.viewModel.zPrimaryClicked()
        onZeroClicked: root.viewModel.zZeroClicked()
        isAbs: root.viewModel.zIsAbs
        onAbsRelClicked: root.viewModel.zAbsRelClicked()
        setDatumVisible: true
        datumLabel: root.viewModel.workOffsetName
        onSetDatumClicked: root.viewModel.zSetDatumClicked()
        onSetDatumLongPressed: root.viewModel.zSetDatumLongPressed()
    }

    Connections {
        target: root.viewModel
        function onActionRejected(message) {
            root.toastRequested(message)
        }
        function onNoticeShown(message) {
            root.toastRequested(message)
        }
        function onSetDatumValueInputRequested() {
            root.openNumPadRequested(zDatumField)
        }
        function onTouchOffValueInputRequested(axis) {
            root.openNumPadRequested(axis === "x" ? xTouchOffField : zTouchOffField)
        }
    }
}
