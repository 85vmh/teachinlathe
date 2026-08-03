// G33CuttingParams.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../touchable_input"

ColumnLayout {
    property var detailsRoot: null

    spacing: 16

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }
    IntValidator { id: intValNonNeg; bottom: 0; top: 99 }

    RowLayout {
        spacing: 16
        Label { text: "Initial DOC"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        NumpadField {
            Layout.preferredWidth: 110
            settingName: "threading.first_pass_depth"
            validatorObject: dblVal
            value: detailsRoot ? detailsRoot.initialDoc : 0.0
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: if (detailsRoot) detailsRoot.openNumPadRequested(field)
            onValueCommitted: {
                if (detailsRoot) {
                    detailsRoot.initialDoc = value
                    detailsRoot.emitSave()
                }
            }
        }
        Label { text: "(mm/radius)"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter }
        Label {
            text: "[" + (detailsRoot ? detailsRoot.roughingPassCountText : "0 passes") + "]"
            font.pixelSize: 15
            font.bold: true
            Layout.alignment: Qt.AlignVCenter
        }
    }

    RowLayout {
        spacing: 16
        Label { text: "Retract"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        NumpadField {
            Layout.preferredWidth: 110
            settingName: "threading.x_retract"
            validatorObject: dblVal
            value: detailsRoot ? detailsRoot.retract : 0.0
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: if (detailsRoot) detailsRoot.openNumPadRequested(field)
            onValueCommitted: {
                if (detailsRoot) {
                    detailsRoot.retract = value
                    detailsRoot.emitSave()
                }
            }
        }
        Label { text: "(mm)"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter }
    }

    RowLayout {
        spacing: 16
        Label { text: "Infeed Angle"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        NumpadField {
            Layout.preferredWidth: 110
            settingName: "threading.compound_angle"
            validatorObject: dblVal
            value: detailsRoot ? detailsRoot.compoundAngle : 0.0
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: if (detailsRoot) detailsRoot.openNumPadRequested(field)
            onValueCommitted: {
                if (detailsRoot) {
                    detailsRoot.compoundAngle = value
                    detailsRoot.emitSave()
                }
            }
        }
        Label { text: "(deg)"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter }
    }

    RowLayout {
        spacing: 16
        Label { text: "Thread Taper"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        ComboBox {
            Layout.preferredWidth: 165
            Layout.preferredHeight: 48
            font.pixelSize: 20
            model: ["None", "On entry", "On exit", "Both"]
            currentIndex: detailsRoot ? Math.max(0, Math.min(3, detailsRoot.taperType)) : 0
            contentItem: Text {
                leftPadding: 8
                rightPadding: 8
                text: parent.displayText
                font: parent.font
                color: "#0f172a"
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            delegate: ItemDelegate {
                width: parent.width
                height: 48
                text: modelData
                font.pixelSize: 20
            }
            onActivated: {
                if (detailsRoot) {
                    detailsRoot.taperType = index
                    detailsRoot.emitSave()
                }
            }
        }
        Item { Layout.fillWidth: true }
    }

    RowLayout {
        spacing: 16
        Label { text: "Spring Passes"; font.pixelSize: 16; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        NumpadField {
            Layout.preferredWidth: 110
            settingName: "threading.spring_passes"
            validatorObject: intValNonNeg
            value: detailsRoot ? detailsRoot.springPasses : 0
            formatter: function(v) { return (v == null) ? "" : String(Math.round(Number(v))) }
            hAlign: Text.AlignRight
            onOpenRequested: if (detailsRoot) detailsRoot.openNumPadRequested(field)
            onValueCommitted: {
                if (detailsRoot) {
                    detailsRoot.springPasses = Math.round(value)
                    detailsRoot.emitSave()
                }
            }
        }
        Item { Layout.fillWidth: true }
    }
}
