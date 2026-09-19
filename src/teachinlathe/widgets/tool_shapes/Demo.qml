import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

/*
 * Demo.qml — exemplu minimal de utilizare a ThreadingInsert.qml
 * Pune ambele fișiere în același director și rulează:  qml Demo.qml
 */
ApplicationWindow {
    visible: true
    width: 900; height: 640
    color: "#12161b"
    title: "Plăcuță filetare ER/EL — parametric"

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        ColumnLayout {
            Layout.preferredWidth: 240
            Layout.alignment: Qt.AlignTop
            spacing: 10

            Label { text: "Mărime"; color: "#8a97a5" }
            ComboBox {
                id: sizeBox
                Layout.fillWidth: true
                model: ["11", "16", "22"]
                currentIndex: 1
            }

            Label { text: "Pas [mm]"; color: "#8a97a5" }
            ComboBox {
                id: pitchBox
                Layout.fillWidth: true
                // lista se reface când se schimbă mărimea
                model: insert.availablePitches(sizeBox.currentText)
                currentIndex: Math.min(4, count - 1)
            }

            Label { text: "Mână"; color: "#8a97a5" }
            ComboBox {
                id: handBox
                Layout.fillWidth: true
                model: [ { k: "R", t: "ER — dreapta" }, { k: "L", t: "EL — stânga" } ]
                textRole: "t"; valueRole: "k"
            }

            Label { text: "Scară: " + zoom.value.toFixed(0) + " px/mm"; color: "#3fb7c2" }
            Slider { id: zoom; Layout.fillWidth: true; from: 6; to: 60; value: 20 }

            Label { text: "Orientare: " + rot.value.toFixed(0) + "°"; color: "#3fb7c2" }
            Slider { id: rot; Layout.fillWidth: true; from: 0; to: 360; value: 0 }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: insert.spec && insert.spec.exact ? "#5fd39a" : "#e6a24b"
                font.family: "monospace"; font.pixelSize: 11
                text: insert.spec
                      ? (insert.spec.exact ? "MĂSURAT din DXF" : "INTERPOLAT") +
                        "\nIC = " + insert.ic.toFixed(3) + " mm" +
                        "\nL  = " + insert.sideLength.toFixed(3) + " mm" +
                        "\nr  = " + insert.spec.r + " mm" +
                        "\nX  = " + insert.spec.X + " mm" +
                        "\nY  = " + insert.spec.Y + " mm" +
                        "\nh  = " + insert.spec.h + " mm" +
                        "\nV  = " + insert.spec.a + "°"
                      : "pas indisponibil"
            }
            Item { Layout.fillHeight: true }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true
            color: "#1a2027"; radius: 8

            ThreadingInsert {
                id: insert
                anchors.centerIn: parent
                insertSize: sizeBox.currentText
                pitch: parseFloat(pitchBox.currentText)
                hand: handBox.currentValue
                pxPerMm: zoom.value
                orientation: rot.value
                showInscribedCircle: true
            }

            // marcaj pe vârful activ — punctul care urmărește toolpath-ul
            Rectangle {
                width: 9; height: 9; radius: 4.5
                color: "#e6a24b"
                visible: insert.specValid
                // vârful, rotit cu orientarea și convertit în pixeli
                x: insert.x + insert.width  / 2 - width  / 2
                   + insert.pxPerMm * ( insert.activeTip().x * Math.cos(insert.orientation * Math.PI / 180)
                                      - insert.activeTip().y * Math.sin(insert.orientation * Math.PI / 180))
                y: insert.y + insert.height / 2 - height / 2
                   - insert.pxPerMm * ( insert.activeTip().x * Math.sin(insert.orientation * Math.PI / 180)
                                      + insert.activeTip().y * Math.cos(insert.orientation * Math.PI / 180))
            }
        }
    }
}
