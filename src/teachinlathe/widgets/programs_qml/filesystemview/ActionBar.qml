import QtQuick 2.15
import QtQuick.Layouts 1.15
import ".."

// Row 4 — Context-sensitive action buttons + copy progress bar.
//
// Mounted Media context:
//   [Copy to USB Stick Programs]  (disabled while copying)
//   Progress bar shown at top when isCopying = true
//
// All other contexts:
//   [Delete]  [Load Program ← green, rightmost]
Rectangle {
    id: root
    property var viewModel

    color: "#f5f5f5"
    implicitHeight: 60

    // ---- Copy progress bar (top edge, shown while copying) ----
    Rectangle {
        id: progressBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 3
        color: "#e0e0e0"
        visible: root.viewModel ? root.viewModel.isCopying : false

        Rectangle {
            height: parent.height
            width: parent.width * (root.viewModel ? root.viewModel.copyProgress : 0)
            color: "#4ec9b0"
            Behavior on width { NumberAnimation { duration: 80 } }
        }
    }

    // ---- Buttons ----
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.topMargin: 7
        spacing: 8

        Item { Layout.fillWidth: true }

        // "Copy to USB Stick Programs" — only in Mounted Media
        ProgramButton {
            visible: root.viewModel ? root.viewModel.isInMountedMedia : false
            enabled: root.viewModel
                     ? (root.viewModel.selectedIsFile && !root.viewModel.isCopying)
                     : false
            text: (root.viewModel ? root.viewModel.isCopying : false)
                  ? "Copying…" : "Copy to USB Stick Programs"
            onClicked: if (root.viewModel) root.viewModel.copySelectedToUsbStickPrograms()
        }

        // "Delete" — only outside Mounted Media
        ProgramButton {
            visible: root.viewModel ? !root.viewModel.isInMountedMedia : false
            enabled: root.viewModel ? root.viewModel.selectedEntryPath !== "" : false
            text: "Delete"
            onClicked: if (root.viewModel) root.viewModel.deleteSelected()
        }

        // "Load Program" — only outside Mounted Media, green, rightmost
        ProgramButton {
            visible: root.viewModel ? !root.viewModel.isInMountedMedia : false
            enabled: root.viewModel ? root.viewModel.selectedIsFile : false
            text: "Load Program"
            accentColor: (root.viewModel ? root.viewModel.selectedIsFile : false)
                         ? "#1a5c2c" : "#e8e8e8"
            borderColor: (root.viewModel ? root.viewModel.selectedIsFile : false)
                         ? "#52b788" : "#cccccc"
            onClicked: if (root.viewModel) root.viewModel.openSelectedFile()
        }
    }
}
