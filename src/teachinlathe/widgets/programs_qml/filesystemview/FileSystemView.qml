import QtQuick 2.15
import QtQuick.Layouts 1.15

// Main filesystem browser panel — 4-row layout.
// Receives a FileSystemViewModel exposed from Python as 'viewModel'.
Rectangle {
    id: root
    property var viewModel

    color: "#252526"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Row 1 — Predefined location selector
        // Layout.preferredHeight is computed here (not in LocationBar) so
        // ColumnLayout always gets a concrete value on first pass.
        LocationBar {
            viewModel: root.viewModel
            Layout.fillWidth: true
            Layout.preferredHeight: 42
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#3a3a3a"
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
            color: "#333333"
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
            color: "#333333"
        }

        // Row 4 — Context-sensitive actions + copy progress
        ActionBar {
            viewModel: root.viewModel
            Layout.fillWidth: true
            height: 60
        }
    }
}
