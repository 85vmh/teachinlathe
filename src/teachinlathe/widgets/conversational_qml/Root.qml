import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    // URLs for screens
    readonly property url mainScreenUrl: "MainScreen.qml"
    readonly property url childScreenUrl: "ChildScreen.qml"

    // Track current screen URL
    property url currentSource: ""

    signal backRequested()

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header cu titlu și back button
        Rectangle {
            id: header
            color: "#673ab7"
            height: 50
            Layout.fillWidth: true
            Layout.preferredHeight: 50

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                Button {
                    visible: root.currentSource !== "" && root.currentSource !== mainScreenUrl
                    text: "\u25C0 Back"
                    onClicked: root.backRequested()
                    background: Rectangle { color: "transparent" }
                    font.pixelSize: 16
                    Layout.preferredWidth: 80
                }

                Label {
                    text: currentSource === "" || currentSource === mainScreenUrl ? "Conversational" : "Edit Program"
                    color: "white"
                    font.pixelSize: 20
                    font.bold: true
                    verticalAlignment: Label.AlignVCenter
                    Layout.fillWidth: true
                }
            }
        }

        Loader {
            id: loader
            Layout.fillWidth: true
            Layout.fillHeight: true
            source: root.currentSource === "" ? mainScreenUrl : root.currentSource
        }
    }

    // Backstack for navigation (simplified)
    property var history: []

    function loadScreen(url, params) {
        if (currentSource !== "") {
            history.push(currentSource)
        }
        currentSource = url
        loader.setSource(url)

        // Set context properties on the loader item after it's loaded
        loader.item && params && Object.keys(params).forEach(function(key) {
            loader.item[key] = params[key]
        })
    }

    function goBack() {
        if (history.length > 0) {
            currentSource = history.pop()
            loader.setSource(currentSource)
        }
    }

    onBackRequested: goBack()
}
