import QtQuick
import QtQuick.Layouts
import theme
import common
import app_shell_qml as Shell
import TeachInLathe.Diagnostics

// Performance Diagnostics: the profiling mode, the window of history shown,
// Reset History and Export, the last bucket's summary, three charts on one
// time axis and the slow operations. Everything is the view model's
// (DiagnosticsViewModel); it is told whether the panel is in sight, and
// brings it up to date only then - every 5 s, as a bucket closes.
ColumnLayout {
    id: root

    required property var viewModel

    spacing: 16

    onVisibleChanged: root.viewModel.setPanelVisible(visible)
    Component.onCompleted: root.viewModel.setPanelVisible(visible)

    GroupPanel {
        title: "Performance Diagnostics"
        Layout.fillWidth: true

        content: ColumnLayout {
            spacing: Theme.spacing

            RowLayout {
                spacing: Theme.spacingLarge
                Text { text: "Profiling"; font.pixelSize: Theme.fontBody; color: Theme.foreground }
                SegmentedTabs {
                    Layout.preferredWidth: 360
                    labels: root.viewModel.modeLabels
                    currentIndex: root.viewModel.modeIndex
                    onActivated: function(index) { root.viewModel.setModeIndex(index) }
                }
                Text { text: "Window"; font.pixelSize: Theme.fontBody; color: Theme.foreground }
                SegmentedTabs {
                    Layout.preferredWidth: 420
                    labels: root.viewModel.windowLabels
                    currentIndex: root.viewModel.windowIndex
                    onActivated: function(index) { root.viewModel.setWindowIndex(index) }
                }
                Shell.ShellActionButton {
                    text: "Reset History"
                    secondary: true
                    onClicked: root.viewModel.resetHistory()
                }
                Shell.ShellActionButton {
                    text: "Export"
                    secondary: true
                    onClicked: root.viewModel.exportHistory()
                }
            }

            Text {
                visible: text !== ""
                text: root.viewModel.exportStatus
                font.pixelSize: Theme.fontSmall
                color: Theme.foreground
            }

            GridLayout {
                columns: 3
                columnSpacing: Theme.spacingLarge
                rowSpacing: 4
                Repeater {
                    model: root.viewModel.summary
                    delegate: RowLayout {
                        required property var modelData
                        spacing: 6
                        Text { text: modelData.label + ":"; font.pixelSize: Theme.fontSmall; color: Theme.foreground }
                        Text { text: modelData.value; font.pixelSize: Theme.fontSmall; font.bold: true; color: Theme.foregroundStrong }
                    }
                }
            }
        }
    }

    Repeater {
        model: root.viewModel.charts
        delegate: GroupPanel {
            required property var modelData
            Layout.fillWidth: true
            title: modelData.title
            content: DiagnosticsChart {
                id: chart
                // the panel's width; GroupPanel sizes its content by its height
                width: parent ? parent.width : 0
                height: implicitHeight
                implicitHeight: modelData.height
                viewModel: root.viewModel
                series: modelData.series
                revision: root.viewModel.revision
                cursorTime: root.viewModel.cursorTime

                MouseArea {
                    anchors.fill: parent
                    onPressed: function(mouse) { root.viewModel.setCursorTime(chart.timeAt(mouse.x)) }
                    onPositionChanged: function(mouse) { root.viewModel.setCursorTime(chart.timeAt(mouse.x)) }
                    onDoubleClicked: root.viewModel.setCursorTime(-1)
                }
            }
        }
    }

    GroupPanel {
        title: "Slow operations (the newest " + root.viewModel.slowOperations.length + ")"
        Layout.fillWidth: true

        content: Column {
            spacing: 2
            Text {
                visible: root.viewModel.slowOperations.length === 0
                text: "None - timed operations are recorded in the Detailed mode."
                font.pixelSize: Theme.fontSmall
                color: Theme.foreground
            }
            Repeater {
                model: root.viewModel.slowOperations
                delegate: Row {
                    required property var modelData
                    spacing: Theme.spacingLarge
                    Text { width: 80; text: modelData.time; font.pixelSize: Theme.fontSmall; color: Theme.foreground }
                    Text { width: 300; text: modelData.name; font.pixelSize: Theme.fontSmall; color: Theme.foregroundStrong }
                    Text { width: 90; text: modelData.duration; font.pixelSize: Theme.fontSmall; font.bold: true; color: Theme.foregroundStrong }
                    Text { width: 60; text: modelData.status; font.pixelSize: Theme.fontSmall; color: modelData.ok ? Theme.foreground : Theme.warning }
                    Text { text: modelData.meta; font.pixelSize: Theme.fontSmall; color: Theme.foreground }
                }
            }
        }
    }
}
