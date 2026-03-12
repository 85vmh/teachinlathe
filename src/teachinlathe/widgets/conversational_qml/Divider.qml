// Divider.qml
import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    // Public API
    // Qt.Vertical => vertical line (fills height in RowLayout)
    // Qt.Horizontal => horizontal line (fills width in ColumnLayout)
    property int   orientation: Qt.Vertical
    property real  thickness: 1
    property color dividerColor: "#cccccc"
    property bool  rounded: false

    color: dividerColor
    radius: rounded ? thickness / 2 : 0

    // Layout-friendly defaults (no need for anchors in Layouts)
    implicitWidth:  orientation === Qt.Vertical   ? thickness : 0
    implicitHeight: orientation === Qt.Horizontal ? thickness : 0

    // Let layouts stretch the divider in the long axis
    Layout.fillHeight: orientation === Qt.Vertical
    Layout.fillWidth:  orientation === Qt.Horizontal
}
