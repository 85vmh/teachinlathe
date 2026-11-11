// G76CuttingParams.qml — G76 Threading's passes: what ``operation`` - the
// operation as its editor has it - says, and the edits to it (``edited``)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common

ColumnLayout {
    id: root
    property var operation: ({})
    readonly property var _op: operation || {}
    readonly property real initialDoc: Number(_op.initial_doc || 0)
    readonly property real retract: Number(_op.retract || 0)
    readonly property real compoundAngle: Number(_op.compound_angle || 0)
    readonly property real depthDegression: _op.depth_degression !== undefined ? Number(_op.depth_degression) : 1.0
    readonly property int taperType: Math.round(Number(_op.taper_type || 0))
    readonly property int springPasses: Math.round(Number(_op.spring_passes || 0))
    readonly property var depthOptions: (function() {
        var a = [];
        for (var v = 1.0; v <= 2.0001; v += 0.1) a.push(v.toFixed(1));
        return a;
    })()

    // a change to the operation: only the fields in it
    signal edited(var changes)
    signal openNumPadRequested(var field)

    spacing: Theme.spacingLarge

    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }
    IntValidator { id: intValNonNeg; bottom: 0; top: 99 }

    RowLayout {
        spacing: Theme.spacing
        Label { text: "Initial DOC"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        NumpadField {
            Layout.preferredWidth: 110
            settingName: "threading.first_pass_depth"
            validatorObject: dblVal
            value: root.initialDoc
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ initial_doc: value }) }
        }
        Label { text: "(mm/radius)"; font.pixelSize: Theme.fontSmall; Layout.alignment: Qt.AlignVCenter }
    }

    RowLayout {
        spacing: Theme.spacing
        Label { text: "Retract"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        NumpadField {
            Layout.preferredWidth: 110
            settingName: "threading.x_retract"
            validatorObject: dblVal
            value: root.retract
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ retract: value }) }
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
            value: root.compoundAngle
            formatter: function(v) { return (v == null) ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ compound_angle: value }) }
        }
        Label { text: "(deg)"; font.pixelSize: Theme.fontSmall; Layout.alignment: Qt.AlignVCenter }
    }

    RowLayout {
        spacing: Theme.spacingLarge
        Label { text: "Degression"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        ModelComboBox {
            Layout.preferredWidth: 110
            Layout.preferredHeight: Theme.inputHeight
            font.pixelSize: Theme.fontTitle
            model: root.depthOptions
            selectedIndex: Math.max(0, root.depthOptions.indexOf(Number(root.depthDegression).toFixed(1)))
            contentItem: Text {
                leftPadding: 8
                rightPadding: 8
                text: parent.displayText
                font: parent.font
                color: Theme.foregroundStrong
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            delegate: ItemDelegate {
                width: parent.width
                height: Theme.inputHeight
                text: modelData
                font.pixelSize: Theme.fontTitle
            }
            onPicked: function(index) { root.edited({ depth_degression: Number(root.depthOptions[index]) }) }
        }
        Item { Layout.fillWidth: true }
    }

    RowLayout {
        spacing: Theme.spacingLarge
        Label { text: "Thread Taper"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        ModelComboBox {
            Layout.preferredWidth: 165
            Layout.preferredHeight: Theme.inputHeight
            font.pixelSize: Theme.fontTitle
            model: ["None", "On entry", "On exit", "Both"]
            selectedIndex: Math.max(0, Math.min(3, root.taperType))
            contentItem: Text {
                leftPadding: 8
                rightPadding: 8
                text: parent.displayText
                font: parent.font
                color: Theme.foregroundStrong
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            delegate: ItemDelegate {
                width: parent.width
                height: Theme.inputHeight
                text: modelData
                font.pixelSize: Theme.fontTitle
            }
            onPicked: function(index) { root.edited({ taper_type: index }) }
        }
        Item { Layout.fillWidth: true }
    }

    RowLayout {
        spacing: Theme.spacingLarge
        Label { text: "Spring Passes"; font.pixelSize: Theme.fontBody; Layout.alignment: Qt.AlignVCenter; Layout.minimumWidth: 120 }
        NumpadField {
            Layout.preferredWidth: 110
            settingName: "threading.spring_passes"
            validatorObject: intValNonNeg
            value: root.springPasses
            formatter: function(v) { return (v == null) ? "" : String(Math.round(Number(v))) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root.edited({ spring_passes: Math.round(value) }) }
        }
        Item { Layout.fillWidth: true }
    }
}
