import QtQuick 2.15
import QtQuick.Layouts 1.15

// Main filesystem browser panel — 4-row layout.
// Receives a FileSystemViewModel exposed from Python as 'viewModel'.
Rectangle {
    id: root
    property var viewModel

    color: "#f5f5f5"
    radius: 6
    border.color: "#ccc"
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 0

        // Row 1 — Predefined location selector
        // Layout.preferredHeight is computed here (not in LocationBar) so
        // ColumnLayout always gets a concrete value on first pass.
        LocationBar {
            viewModel: root.viewModel
            Layout.fillWidth: true
            Layout.preferredHeight: 60
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#dddddd"
        }

        // Row 2 — FolderUp + Breadcrumb + Filter toggles
        NavigationBar {
            viewModel: root.viewModel
            Layout.fillWidth: true
            height: 38
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#e0e0e0"
        }

        // Row 3 — Sortable file list
        FileListView {
            viewModel: root.viewModel
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#e0e0e0"
        }

        // Row 4 — Context-sensitive actions + copy progress
        ActionBar {
            viewModel: root.viewModel
            Layout.fillWidth: true
            height: 60
        }
    }
}
