import QtQuick
import QtQuick.Layouts
import theme

// The filesystem browser: cards one under another, the window's background
// between them - the predefined locations and the path in them
// (PredefinedPaths), the file list (FileListView) and, on mounted media, the
// copy to the USB stick (ActionBar).
// Receives a FileSystemViewModel exposed from Python as 'viewModel'.
Item {
    id: root
    required property var viewModel
    property bool showActionBar: true
    // The file list's swipe to delete.
    property bool showActions: true
    // The action bar only has something to offer on mounted media (copying
    // to the USB stick); deleting is a swipe on the list's rows.
    readonly property bool actionBarShown: showActionBar
                                           && viewModel.isInMountedMedia

    ColumnLayout {
        anchors.fill: parent
        // as far apart as the cards elsewhere
        spacing: Theme.spacingSmall

        PredefinedPaths {
            id: predefinedPaths
            viewModel: root.viewModel
            Layout.fillWidth: true
            Layout.preferredHeight: predefinedPaths.implicitHeight
        }

        FileListView {
            viewModel: root.viewModel
            showActions: root.showActions
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        // copy to the USB stick, on mounted media
        ActionBar {
            viewModel: root.viewModel
            visible: root.actionBarShown
            Layout.fillWidth: true
            Layout.preferredHeight: 60
        }
    }
}
