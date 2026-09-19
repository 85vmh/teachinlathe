import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// A Popup in the window's overlay, not an Item in the screen.
//
// As an Item it could only dim as far as its parent reached - the Programs
// screen, inside the tab, inside the app shell's content area - so the top and
// bottom bars stayed lit while a tool change was waiting. The confirmation
// dialogs (ConfirmDialog.qml) were already Popups in Overlay.overlay, which is
// why those dim the whole screen; this now matches them.
//
// It was also pushed off to one side, over the G-code pane. That was to keep
// clear of the backplot, which used to be a QOpenGLWidget composited over the
// whole window and would have covered any dialog under it. The backplot is a
// scene-graph item now and obeys stacking like everything else, so the dialog
// can sit in the middle.
Popup {
    id: root

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    // A tool change is answered at the machine, with CycleStart or CycleAbort.
    // Nothing on screen dismisses it - a stray tap must not.
    closePolicy: Popup.NoAutoClose
    visible: viewModel ? viewModel.requested : false
    padding: 0

    property var viewModel
    readonly property color textColor: "#1e2430"
    readonly property color confirmColor: "#2e7d32"
    readonly property color cancelColor: "#c62828"

    contentWidth: 620
    contentHeight: card.implicitHeight + 48

    function escapeHtml(value) {
        return String(value === undefined || value === null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;")
    }

    // The scrim is the Popup's own, so no dimming rectangle here.
    background: Rectangle {
        radius: 10
        color: "#ffffff"
        border.color: "#cbd5e1"
        border.width: 1
    }

    contentItem: Item {
        implicitWidth: root.contentWidth
        implicitHeight: card.implicitHeight + 48

        ColumnLayout {
            id: card
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                margins: 24
            }
            spacing: 18

            Text {
                Layout.fillWidth: true
                text: "Tool Change"
                font.pixelSize: 20
                font.bold: true
                color: root.textColor
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                Layout.fillWidth: true
                textFormat: Text.RichText
                text: "Please load <b>" + root.escapeHtml(root.viewModel ? root.viewModel.toolNoText : "T?") + "</b>"
                    + ((root.viewModel && root.viewModel.toolDescription.length > 0)
                        ? " [" + root.escapeHtml(root.viewModel.toolDescription) + "]"
                        : "")
                font.pixelSize: 18
                color: root.textColor
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            Item { Layout.preferredHeight: 16 }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 0

                Text {
                    text: "Press "
                    font.pixelSize: 18
                    color: root.textColor
                }

                Text {
                    id: cycleStartText
                    text: "CycleStart"
                    font.pixelSize: 18
                    font.bold: true
                    color: root.confirmColor
                    opacity: cycleStartMouse.pressed ? 0.65 : 1.0

                    MouseArea {
                        id: cycleStartMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onPressed: if (root.viewModel) root.viewModel.confirmPressed()
                        onReleased: if (root.viewModel) root.viewModel.confirmReleased()
                        onCanceled: if (root.viewModel) root.viewModel.confirmReleased()
                    }
                }

                Text {
                    text: " to confirm the tool change"
                    font.pixelSize: 18
                    color: root.textColor
                }
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 0

                Text {
                    text: "Press "
                    font.pixelSize: 18
                    color: root.textColor
                }

                Text {
                    id: cycleAbortText
                    text: "CycleAbort"
                    font.pixelSize: 18
                    font.bold: true
                    color: root.cancelColor
                    opacity: cycleAbortMouse.pressed ? 0.65 : 1.0

                    MouseArea {
                        id: cycleAbortMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onPressed: if (root.viewModel) root.viewModel.cancelPressed()
                        onReleased: if (root.viewModel) root.viewModel.cancelReleased()
                        onCanceled: if (root.viewModel) root.viewModel.cancelReleased()
                    }
                }

                Text {
                    text: " to stop the program."
                    font.pixelSize: 18
                    color: root.textColor
                }
            }
        }
    }
}
