import QtQuick
import QtQuick.Layouts
import theme

// The one simulation-only addition to the common full-screen run bar.
// Playback speed deliberately stays out until the final layout is chosen.
Item {
    id: root

    required property var run
    required property var simulationViewModel

    implicitWidth: 620
    implicitHeight: 108

    RowLayout {
        anchors.fill: parent
        spacing: Theme.spacing

        SimulateSeekBar {
            Layout.fillWidth: true
            duration: root.run.duration
            time: root.run.time
            marks: root.run.marks
            collisions: root.simulationViewModel.collisions
            seekable: root.run.seekable
            onSeekRequested: function(time) { root.run.seek(time) }
        }
    }
}
