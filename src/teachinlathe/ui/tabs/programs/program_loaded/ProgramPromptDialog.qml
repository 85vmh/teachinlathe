import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

// What the Program Loaded screen asks the operator while a program runs - a
// tool to load, the program done - over the G-code pane (``area``), as wide
// as it, its middle at ``centreY`` in it: low on the screen, clear of the
// backplot beside it. Light text on dark, the machine's Cycle Start in green
// and Cycle Abort in red where a line names them; what it says goes in as a
// Title and Lines. Nothing on screen closes it: the machine's buttons answer
// it. Modal, what is behind dimmed: till it is answered, nothing else on the
// screen takes a touch.
Popup {
    id: root

    // the G-code pane it is over
    property Item area: null
    // where its middle goes, in the pane
    property real centreY: area ? area.height / 2 : 0
    readonly property color startColor: "#22c55e"
    readonly property color abortColor: "#ef4444"
    // what it says, top down
    default property alias content: column.data

    parent: area
    width: parent ? parent.width - 2 * Theme.spacing : 0
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? Math.max(0, Math.min(parent.height - height, centreY - height / 2)) : 0
    closePolicy: Popup.NoAutoClose
    modal: true
    dim: true
    padding: 24

    background: Rectangle {
        radius: Theme.radiusLarge
        color: "#303030"
    }

    contentItem: ColumnLayout {
        id: column
        spacing: Theme.spacingLarge
    }

    // "Press <button> <what it does>", the button in its colour
    function press(button, color, what) {
        return "Press <font color=\"" + color + "\"><b>" + button + "</b></font> " + what
    }

    function escapeHtml(value) {
        return String(value === undefined || value === null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;")
    }

    // A line of what it says: centred, wrapped to the pane's width.
    component Line: Text {
        Layout.fillWidth: true
        textFormat: Text.RichText
        color: Theme.surface
        font.pixelSize: Theme.fontPromptLine
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
    }

    // What it is about, on top: read from the machine, larger than the rest.
    component Title: Line {
        font.pixelSize: Theme.fontPromptTitle
        font.bold: true
    }
}
