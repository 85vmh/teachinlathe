// BlendPicker.qml — an edge's blend, picked and sized in one row: none, a
// chamfer or a fillet in a narrow drop-down that shows only the blend's icon
// (Define Profile's) - nothing for none - and opens wider, each kind with its
// name; then its size, and (mm) - with none, ``noneText`` in their place,
// which keeps the same room. Parting's edge break (EdgeBreakBox) and a
// groove's corners (GroovePointBox).
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import common.touchable_input
import theme
import common

RowLayout {
    id: root

    property string blendType: "none"     // "none" | "chamfer" | "fillet"
    property real   chamferWidth: 0.0
    property real   filletRadius: 0.0
    // the icons flipped top to bottom: the part's edge as Parting has it
    property bool   iconsFlipped: false
    // the numpad's settings for the chamfer's width and the fillet's radius
    property string chamferSettingName: ""
    property string filletSettingName: ""
    // in place of the size and its unit with no blend, pointing at the drop-down
    property string noneText: "\u2190 Add Blend"
    property color  noneTextColor: Theme.foreground
    property bool   noneTextBold: false
    // the drop-down's column, laid out as a label: the drop-down at its
    // right, by what it sets - so a box can line the size up with its other
    // fields, and its other labels with the drop-down
    property real   leadWidth: comboWidth
    readonly property real comboWidth: Theme.inputHeight + 28

    // the blend as it is to be: its kind, and both sizes
    signal edited(string blendType, real chamferWidth, real filletRadius)
    signal openNumPadRequested(var field)

    spacing: 20

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
        var chamfer = chamferWidth, fillet = filletRadius
        if (value === undefined || value === null) {
            // a chamfer turned into a fillet, or back: the same size
            var was = blendType === "chamfer" ? chamferWidth : blendType === "fillet" ? filletRadius : 0
            if (type === "chamfer" && blendType === "fillet") chamfer = was
            if (type === "fillet" && blendType === "chamfer") fillet = was
        } else {
            if (type === "chamfer") chamfer = value
            if (type === "fillet") fillet = value
        }
        root.edited(type, chamfer, fillet)
    }

    DoubleValidator { id: dblVal; bottom: 0; notation: DoubleValidator.StandardNotation }

    // as narrow as its icon and the arrow; the list it opens as wide as
    // the names need
    ComboBox {
        id: kindCombo
        Layout.preferredWidth: root.comboWidth
        Layout.leftMargin: root.leadWidth - root.comboWidth
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
                                mirrorVertically: root.iconsFlipped
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
                        mirrorVertically: root.iconsFlipped
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

    // the size and its unit, or with none ``noneText``: as wide either way
    Item {
        Layout.preferredWidth: valueField.width + root.spacing + unitLabel.implicitWidth
        Layout.preferredHeight: valueField.height

        Label {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.blendType === "none"
            text: root.noneText
            color: root.noneTextColor
            font.pixelSize: Theme.fontBody
            font.bold: root.noneTextBold
        }

        NumpadField {
            id: valueField
            width: 100
            visible: root.blendType !== "none"
            settingName: root.blendType === "fillet" ? root.filletSettingName : root.chamferSettingName
            description: root.blendType === "fillet" ? "Fillet radius" : "Chamfer width"
            validatorObject: dblVal
            // none: no value, the field empty
            value: root.blendType === "fillet" ? root.filletRadius
                 : root.blendType === "chamfer" ? root.chamferWidth : null
            formatter: function (v) { return (v == null || root.blendType === "none") ? "" : Number(v).toFixed(3) }
            hAlign: Text.AlignRight
            onOpenRequested: function(field) { root.openNumPadRequested(field) }
            onValueCommitted: function(value) { root._emit(root.blendType, Math.abs(Number(value))) }
        }
        Label {
            id: unitLabel
            anchors.left: valueField.right
            anchors.leftMargin: root.spacing
            anchors.verticalCenter: parent.verticalCenter
            visible: root.blendType !== "none"
            text: "(mm)"
            font.pixelSize: Theme.fontBody
        }
    }
}
