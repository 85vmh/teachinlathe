import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

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
        : '<span style="color:#8b8b8b;">' + _pathPrefix + '</span><b>' + _fileName + '</b>'

    default property alias frameContent: contentColumn.data

    color: "#f9f9f9"
    radius: 6
    border.color: "#ccc"
    border.width: 1

    implicitHeight: headerText.implicitHeight + contentColumn.implicitHeight + 30

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 4

        Text {
            id: headerText
            Layout.fillWidth: true
            text: root._formattedPath
            textFormat: Text.RichText
            color: "#4f4f4f"
            font.pixelSize: 13
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
