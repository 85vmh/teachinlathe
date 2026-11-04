// UndercutDin509BlendCard.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational.profile_canvas
import theme

BlendCard {
    id: root

    // why it is neither drawn nor cut, or ""
    readonly property string _problem: corner ? corner.undercutProblem : ""

    function _commitUndercutField(field, v) {
        var d = JSON.parse(JSON.stringify(primData))
        if (!d.blend) d.blend = { type: "undercut_din509" }
        d.blend[field] = v
        root.primUpdated(primIdx, d)
    }

    function _undercutValue(field) {
        var fallback = BlendDefaults.values.undercut_din509[field]
        if (!primData || !primData.blend) return fallback
        return primData.blend[field] !== undefined ? primData.blend[field] : fallback
    }

    blendType: "undercut_din509"
    border.color: _problem !== "" ? Theme.danger : Theme.blendStroke

    ColumnLayout {
        spacing: CardMetrics.rowGap
        Layout.fillWidth: true

        RowLayout {
            spacing: 0
            Layout.fillWidth: true

            UndercutField { label: "Length"; field: "undercut_length"; description: "Undercut overall length" }
            UndercutField { label: "Depth"; field: "undercut_depth"; description: "Undercut depth in mm/radius" }
        }

        RowLayout {
            spacing: 0
            Layout.fillWidth: true

            UndercutField { label: "Radius"; field: "undercut_radius"; description: "Undercut blend radius" }

            // the second field's place
            Item {
                Layout.fillWidth: true
                Layout.preferredWidth: 0
                Layout.fillHeight: true

                Label {
                    anchors.fill: parent
                    anchors.leftMargin: CardMetrics.margin
                    anchors.rightMargin: CardMetrics.margin
                    visible: root._problem !== ""
                    text: root._problem
                    color: Theme.danger
                    font.pixelSize: Theme.fontBody
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }

    component UndercutField: ProfileField {
        id: cell

        property string field: ""

        settingName: "blend." + root.primIdx + "." + field
        value: root._undercutValue(field)
        onOpenRequested: function(numpadField) { root.openNumPadRequested(numpadField) }
        onCommitted: function(value) { root._commitUndercutField(cell.field, value) }
    }
}
