import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import theme 1.0
import common 1.0

Rectangle {
    id: root

    property bool selected: false
    property int  datum: 1               // the work offset's P number: 1 is G54 ... 6 is G59
    // as the operations' rows: their font, their "[#NN]" and gap, their margin
    property int  itemFontSize: 16
    property int  colDelW: 100           // the operations' Delete column, at the right

    signal clicked()

    width: parent ? parent.width : 400
    height: Theme.rowHeight
    radius: 0
    color: selected ? Theme.selection : Theme.outlineDisabled
    border.width: selected ? 2 : 0
    border.color: selected ? Theme.accent : "transparent"

    component Part: Label {
        font.pixelSize: root.itemFontSize
        color: "black"
    }

    Part {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        text: "[#00]    Program Header"
    }

    // the work coordinate system - the origin symbol and its G code in bold -
    // centred on the operations' Delete column below
    RowLayout {
        anchors.horizontalCenter: parent.right
        anchors.horizontalCenterOffset: -root.colDelW / 2
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0

        Image {
            source: Images.url("set_datum.svg")
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            sourceSize.width: 20
            sourceSize.height: 20
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
        Part { text: " G" + (53 + root.datum); font.bold: true }
    }

    TapHandler {
        onTapped: root.clicked()
    }
}
