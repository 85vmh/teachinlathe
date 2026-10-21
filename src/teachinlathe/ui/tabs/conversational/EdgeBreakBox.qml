// EdgeBreakBox.qml — Parting's edge break, laid over the profile canvas:
// none, a chamfer or a fillet, picked in a narrow drop-down that shows only
// the blend's icon (Define Profile's) - nothing for none - and opens wider,
// each kind with its name; then its size, and (mm).
import QtQuick
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import common.touchable_input 1.0
import theme 1.0
import common 1.0

CanvasBox {
    id: root

    property string label: "Edge Break"
    property color  color: Theme.foreground
    property string blendType: "none"     // "none" | "chamfer" | "fillet"
    property real   chamferWidth: 0.0
    property real   filletRadius: 0.0

    // a whole edge_break, as the op keeps it
    signal edited(var edgeBreak)
    signal openNumPadRequested(var field)

    accent: color

    // the field shows the new kind's value - or nothing - even when the
    // number itself is the same
    onBlendTypeChanged: valueField.text = valueField.formatter(valueField.value)

    readonly property var kinds: [
        { type: "none",    text: "None",    icon: "" },
        { type: "fillet",  text: "Fillet",  icon: Images.url("fillet.svg") },
        { type: "chamfer", text: "Chamfer", icon: Images.url("chamfer.svg") }
    ]

    function _index(type) {
        for (var i = 0; i < kinds.length; i++) if (kinds[i].type === type) return i
        return 0
    }

    function _emit(type, value) {
        var e = { blend_type: type, chamfer_width: chamferWidth, fillet_radius: filletRadius }
        if (value === undefined || value === null) {
            // a chamfer turned into a fillet, or back: the same size
            var was = blendType === "chamfer" ? chamferWidth : blendType === "fillet" ? filletRadius : 0
            if (type === "chamfer" && blendType === "fillet") e.chamfer_width = was
            if (type === "fillet" && blendType === "chamfer") e.fillet_radius = was
        } else {
            if (type === "chamfer") e.chamfer_width = value
            if (type === "fillet") e.fillet_radius = value
        }
        root.edited(e)
    }

    DoubleValidator { id: dblVal; bottom: 0; notation: DoubleValidator.StandardNotation }

    RowLayout {
        spacing: 20

        Label { text: root.label; color: root.color; font.pixelSize: Theme.fontBody }

        // as narrow as its icon and the arrow; the list it opens as wide as
        // the names need
        ComboBox {
            id: kindCombo
            Layout.preferredWidth: Theme.inputHeight + 28
            Layout.preferredHeight: valueField.height
            model: root.kinds
            textRole: "text"
            currentIndex: root._index(root.blendType)
            onActivated: function(index) { root._emit(root.kinds[index].type) }

            contentItem: Item {
                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    x: 6
                    width: Theme.inputHeight - 16
                    height: width
                    visible: source !== ""
                    source: root.kinds[kindCombo.currentIndex].icon
                    sourceSize.width: width
                    sourceSize.height: height
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    // flipped top to bottom: the part's edge as Parting has it
                    mirrorVertically: true
                }
            }

            popup: Popup {
                y: kindCombo.height
                width: Math.max(kindCombo.width, 200)
                padding: 1
                contentItem: ListView {
                    implicitHeight: contentHeight
                    clip: true
                    model: kindCombo.popup.visible ? kindCombo.delegateModel : null
                    currentIndex: kindCombo.highlightedIndex
                }
                background: Rectangle {
                    color: Theme.surface
                    border.color: Theme.outline
                    border.width: Theme.hairline
                    radius: Theme.radiusSmall
                }
            }

            delegate: ItemDelegate {
                width: Math.max(kindCombo.width, 200)
                height: Theme.inputHeight
                highlighted: kindCombo.highlightedIndex === index
                contentItem: Row {
                    spacing: 12
                    Item {
                        width: Theme.inputHeight - 16
                        height: width
                        anchors.verticalCenter: parent.verticalCenter
                        Image {
                            anchors.fill: parent
                            visible: modelData.icon !== ""
                            source: modelData.icon
                            sourceSize.width: width
                            sourceSize.height: height
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mirrorVertically: true
                        }
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.text
                        font.pixelSize: Theme.fontBody
                        color: Theme.foregroundStrong
                    }
                }
            }
        }

        NumpadField {
            id: valueField
            Layout.preferredWidth: 100
            enabled: root.blendType !== "none"
            opacity: enabled ? 1 : 0.4
            settingName: root.blendType === "fillet" ? "parting.edge_break_radius" : "parting.edge_break_chamfer"
            description: root.blendType === "fillet" ? "Fillet radius" : "Chamfer width"
            validatorObject: dblVal
            // none: no value, the field empty
            value: root.blendType === "fillet" ? root.filletRadius
                 : root.blendType === "chamfer" ? root.chamferWidth : null
            formatter: function (v) { return (v == null || root.blendType === "none") ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: root._emit(root.blendType, Math.abs(Number(value)))
        }
        Label { text: "(mm)"; font.pixelSize: Theme.fontBody; opacity: valueField.opacity }
    }
}
