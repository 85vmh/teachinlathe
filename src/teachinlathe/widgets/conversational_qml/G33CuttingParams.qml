// G33CuttingParams.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../touchable_input"
import theme 1.0

ColumnLayout {
    property var detailsRoot: null

    spacing: Theme.spacingLarge

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }
    IntValidator { id: intValNonNeg; bottom: 0; top: 99 }

    RowLayout {
        spacing: Theme.spacingLarge
        Label { text: "Initial DOC"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
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
        Label { text: "(mm/radius)"; font.pixelSize: Theme.fontSmall; Layout.alignment: Qt.AlignVCenter }
        Label {
            text: "[" + (detailsRoot ? detailsRoot.roughingPassCountText : "0 passes") + "]"
            font.pixelSize: Theme.fontSmall
            font.bold: true
            Layout.alignment: Qt.AlignVCenter
        }
    }

    RowLayout {
        spacing: Theme.spacingLarge
        Label { text: "Retract"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
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
        Label { text: "(mm)"; font.pixelSize: Theme.fontSmall; Layout.alignment: Qt.AlignVCenter }
    }

    RowLayout {
        spacing: Theme.spacingLarge
        Label { text: "Infeed Angle"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
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
        Label { text: "(deg)"; font.pixelSize: Theme.fontSmall; Layout.alignment: Qt.AlignVCenter }
    }

    RowLayout {
        spacing: Theme.spacingLarge
        Label { text: "Spring Passes"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
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
