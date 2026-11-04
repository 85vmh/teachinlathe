// CardDivider.qml — a primitive card's divider, from the card's border at the
// top to its border at the bottom: past the row it is in by ``overhang``.
import QtQuick
import QtQuick.Layouts
import theme

Item {
    property int overhang: 0

    Layout.preferredWidth: Theme.hairline
    Layout.fillHeight: true

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: -parent.overhang
        anchors.bottomMargin: -parent.overhang
        color: Theme.cardDivider
    }
}
