import QtQuick 2.15
import QtQuick.Layouts 1.15
import theme 1.0

// Main filesystem browser panel — 4-row layout.
// Receives a FileSystemViewModel exposed from Python as 'viewModel'.
Rectangle {
    id: root
    property var viewModel
    property bool showActionBar: true
    // The file list's Actions column (delete).
    property bool showActions: true
    // The action bar only has something to offer on mounted media (copying
    // to the USB stick); deleting is in the list's Actions column.
    readonly property bool actionBarShown: showActionBar
                                           && !!viewModel && viewModel.isInMountedMedia

    color: Theme.surfaceSunken
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline

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
            height: Theme.hairline
            color: Theme.outlineDisabled
        }

        // Row 2 — FolderUp + Breadcrumb + Filter toggles
        NavigationBar {
            viewModel: root.viewModel
            Layout.fillWidth: true
            height: 38
        }

        Rectangle {
            Layout.fillWidth: true
            height: Theme.hairline
            color: Theme.outlineDisabled
        }

        // Row 3 — Sortable file list
        FileListView {
            viewModel: root.viewModel
            showActions: root.showActions
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        Rectangle {
            Layout.fillWidth: true
            height: Theme.hairline
            color: Theme.outlineDisabled
            visible: root.actionBarShown
        }

        // Row 4 — copy to the USB stick, on mounted media
        ActionBar {
            viewModel: root.viewModel
            visible: root.actionBarShown
            Layout.fillWidth: true
            Layout.preferredHeight: root.actionBarShown ? 60 : 0
        }
    }
}
