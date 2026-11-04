import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme

Rectangle {
    id: root
    property string filePath: ""
    property real headerConnectorX: headerText.x + 12
    property real headerMidY: headerText.y + (headerText.height / 2)

    readonly property string _normalizedPath: filePath || ""
    readonly property int _slashIndex: _normalizedPath.lastIndexOf("/")
    readonly property string _pathPrefix: _slashIndex >= 0 ? _normalizedPath.substring(0, _slashIndex + 1) : ""
    readonly property string _fileName: _slashIndex >= 0 ? _normalizedPath.substring(_slashIndex + 1) : _normalizedPath
    readonly property string _formattedPath: _normalizedPath === ""
        ? "No file loaded"
        : '<font color="#8b8b8b">' + _pathPrefix + '</font><b>' + _fileName + '</b>'

    default property alias frameContent: contentColumn.data
    // the header the path is in
    property int headerHeight: 32

    color: Theme.surfaceAlt
    radius: Theme.radius
    border.color: Theme.outline
    border.width: Theme.hairline

    implicitHeight: root.headerHeight + contentColumn.implicitHeight + 30

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 4

        // the path, cut at its start when it is too long: the file's name,
        // at its end, is what matters. StyledText, not RichText: rich text
        // is never elided.
        Text {
            id: headerText
            Layout.fillWidth: true
            Layout.preferredHeight: root.headerHeight
            verticalAlignment: Text.AlignVCenter
            text: root._formattedPath
            textFormat: Text.StyledText
            color: Theme.foregroundMuted
            font.pixelSize: Theme.fontSmall
            elide: Text.ElideLeft
        }

        ColumnLayout {
            id: contentColumn
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0
        }
    }
}
