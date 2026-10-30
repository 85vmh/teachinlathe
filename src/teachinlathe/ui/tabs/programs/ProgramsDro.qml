import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

Rectangle {
    id: root
    // workOffsetName ("G54"...), xPosition, xDistanceToGo, zPosition,
    // zDistanceToGo: the machine's (ProgramsDroViewModel) or a simulation's
    required property var viewModel
    property int axisLabelWidth: 40
    property int valueBoxHeight: 60
    property int axisLabelFontSize: 60
    property int droValueFontSize: 40
    property int headerFontSize: 18
    property int headerHeight: 22
    property int rowSpacing: 16
    property int columnSpacing: 14
    // in from the box's edges
    property int margin: 8
    // the two columns share what the axis letters leave
    readonly property int valueBoxWidth: Math.max(0, (width - 2 * margin - axisLabelWidth - 2 * rowSpacing) / 2)
    // what it needs, to the bottom of the second row
    implicitHeight: 2 * margin + headerHeight + 2 * columnSpacing + 2 * valueBoxHeight - headerGap
    // the header nearer the rows than the rows are to each other
    readonly property int headerGap: 8

    color: Theme.hover
    border.color: Theme.separator
    border.width: Theme.hairline
    radius: Theme.radius

    ColumnLayout {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: root.margin
        anchors.topMargin: root.margin
        spacing: root.columnSpacing

        RowLayout {
            spacing: root.rowSpacing
            Layout.bottomMargin: -root.headerGap

            Item {
                Layout.preferredWidth: root.axisLabelWidth
                Layout.preferredHeight: root.headerHeight
            }

            Text {
                Layout.preferredWidth: root.valueBoxWidth
                Layout.preferredHeight: root.headerHeight
                text: root.viewModel.workOffsetName + " Position"
                color: Theme.foregroundSubtle
                font.pixelSize: root.headerFontSize
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                Layout.preferredWidth: root.valueBoxWidth
                Layout.preferredHeight: root.headerHeight
                text: "Distance to Go"
                color: Theme.foregroundSubtle
                font.pixelSize: root.headerFontSize
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        AutoAxisDro {
            axisLabel: "X"
            position: root.viewModel.xPosition
            dtg: root.viewModel.xDistanceToGo
            axisLabelWidth: root.axisLabelWidth
            valueBoxWidth: root.valueBoxWidth
            valueBoxHeight: root.valueBoxHeight
            axisLabelFontSize: root.axisLabelFontSize
            valueFontSize: root.droValueFontSize
            rowSpacing: root.rowSpacing
        }

        AutoAxisDro {
            axisLabel: "Z"
            position: root.viewModel.zPosition
            dtg: root.viewModel.zDistanceToGo
            axisLabelWidth: root.axisLabelWidth
            valueBoxWidth: root.valueBoxWidth
            valueBoxHeight: root.valueBoxHeight
            axisLabelFontSize: root.axisLabelFontSize
            valueFontSize: root.droValueFontSize
            rowSpacing: root.rowSpacing
        }
    }
}
