import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Inserts"

/*
 * InsertsDemo.qml — exemplu de utilizare a modulului.
 * Structura de fișiere:
 *     InsertsDemo.qml
 *     Inserts/
 *         qmldir
 *         TurningInsertBase.qml
 *         CCMT.qml  DCMT.qml  VBMT.qml  TCMT.qml  WNMG.qml  SNMG.qml  RCMT.qml
 * Rulare:  qml InsertsDemo.qml
 */
ApplicationWindow {
    visible: true
    width: 980; height: 660
    color: "#12161b"
    title: "Plăcuțe de strunjire — module QML"

    // toate familiile, ca să pot comuta între ele
    property var families: ["CCMT", "DCMT", "VBMT", "TCMT", "WNMG", "SNMG", "RCMT"]

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        ColumnLayout {
            Layout.preferredWidth: 230
            Layout.alignment: Qt.AlignTop
            spacing: 10

            Label { text: "Familie"; color: "#8a97a5" }
            ComboBox {
                id: famBox
                Layout.fillWidth: true
                model: families
                onCurrentTextChanged: sizeBox.currentIndex = 0
            }

            Label { text: "Mărime (cerc înscris)"; color: "#8a97a5" }
            ComboBox {
                id: sizeBox
                Layout.fillWidth: true
                model: loader.item ? loader.item.sizeCodes : []
            }

            Label { text: "Rază la vârf [mm]"; color: "#8a97a5" }
            ComboBox {
                id: noseBox
                Layout.fillWidth: true
                model: [0.2, 0.4, 0.8, 1.2, 1.6]
                currentIndex: 2
                enabled: famBox.currentText !== "RCMT"
            }

            Label { text: "Orientare: " + rot.value.toFixed(0) + "°"; color: "#3fb7c2" }
            Slider { id: rot; Layout.fillWidth: true; from: 0; to: 360; value: 215 }

            Label { text: "Scară: " + zoom.value.toFixed(0) + " px/mm"; color: "#3fb7c2" }
            Slider { id: zoom; Layout.fillWidth: true; from: 6; to: 60; value: 20 }

            CheckBox { id: cbIC;  text: "Cerc înscris"; checked: true }
            CheckBox { id: cbTip; text: "Vârf sculă";   checked: true }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#dfe6ec"
                font.family: "monospace"; font.pixelSize: 11
                text: loader.item
                      ? "IC   = " + loader.item.ic.toFixed(3) + " mm" +
                        "\nformă = " + loader.item.shape +
                        "\ntip   = " + loader.item.insertType +
                        "\nmuchie= " + loader.item.sideLength.toFixed(2) + " mm" +
                        "\nvârf  = (" + loader.item.activeTip().x.toFixed(2) + ", " +
                                        loader.item.activeTip().y.toFixed(2) + ")"
                      : ""
            }
            Item { Layout.fillHeight: true }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true
            color: "#1a2027"; radius: 8

            Loader {
                id: loader
                anchors.centerIn: parent
                // încarcă dinamic familia aleasă
                source: "Inserts/" + famBox.currentText + ".qml"
                onLoaded: bind()
                function bind() {
                    if (!item) return;
                    item.size = Qt.binding(function () { return sizeBox.currentIndex });
                    item.noseRadius = Qt.binding(function () { return noseBox.currentValue });
                    item.orientation = Qt.binding(function () { return rot.value });
                    item.pxPerMm = Qt.binding(function () { return zoom.value });
                    item.showInscribedCircle = Qt.binding(function () { return cbIC.checked });
                    item.showToolTip = Qt.binding(function () { return cbTip.checked });
                }
            }
        }
    }
}
