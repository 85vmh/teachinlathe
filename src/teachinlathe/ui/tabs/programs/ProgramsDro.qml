import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0

Rectangle {
    id: root
    property var viewModel
    property int axisLabelWidth: 44
    property int valueBoxWidth: 240
    property int valueBoxHeight: 60
    property int axisLabelFontSize: 60
    property int droValueFontSize: 40
    property int headerFontSize: 18
    property int headerHeight: 30
    property int rowSpacing: 20
    property int columnSpacing: 18

    color: Theme.hover
    border.color: Theme.separator
    border.width: Theme.hairline
    radius: Theme.radius

    ColumnLayout {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: 16
        anchors.topMargin: 16
        spacing: root.columnSpacing

        RowLayout {
            spacing: root.rowSpacing

            Item {
                Layout.preferredWidth: root.axisLabelWidth
                Layout.preferredHeight: root.headerHeight
            }

            Text {
                Layout.preferredWidth: root.valueBoxWidth
                Layout.preferredHeight: root.headerHeight
                text: "G54 Position"
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
            position: programsDroViewModel.xPosition
            dtg: programsDroViewModel.xDistanceToGo
            axisLabelWidth: root.axisLabelWidth
            valueBoxWidth: root.valueBoxWidth
            valueBoxHeight: root.valueBoxHeight
            axisLabelFontSize: root.axisLabelFontSize
            valueFontSize: root.droValueFontSize
            rowSpacing: root.rowSpacing
        }

        AutoAxisDro {
            axisLabel: "Z"
            position: programsDroViewModel.zPosition
            dtg: programsDroViewModel.zDistanceToGo
            axisLabelWidth: root.axisLabelWidth
            valueBoxWidth: root.valueBoxWidth
            valueBoxHeight: root.valueBoxHeight
            axisLabelFontSize: root.axisLabelFontSize
            valueFontSize: root.droValueFontSize
            rowSpacing: root.rowSpacing
        }
    }
}
