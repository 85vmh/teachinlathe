import QtQuick
import QtQuick.Layouts
import tabs.programs
import theme

// Row 4 — shown on mounted media only: [Copy to USB Stick Programs]
// (disabled while copying), with a progress bar along the top while it copies.
// Deleting is per file, a swipe on the list's rows.
Rectangle {
    id: root
    required property var viewModel

    color: Theme.surfaceSunken
    implicitHeight: 60

    // ---- Copy progress bar (top edge, shown while copying) ----
    Rectangle {
        id: progressBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 3
        color: Theme.outlineDisabled
        visible: root.viewModel.isCopying

        Rectangle {
            height: parent.height
            width: parent.width * (root.viewModel.copyProgress)
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
        spacing: Theme.spacingSmall

        Item { Layout.fillWidth: true }

        ProgramButton {
            enabled: root.viewModel
                     ? (root.viewModel.selectedIsFile && !root.viewModel.isCopying)
                     : false
            text: (root.viewModel.isCopying)
                  ? "Copying…" : "Copy to USB Stick Programs"
            onClicked: root.viewModel.copySelectedToUsbStickPrograms()
        }

    }
}
