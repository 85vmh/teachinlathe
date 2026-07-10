// ToolEditForm.qml — Add / Edit tool form.
//
// Properties:  toolData  — tool dict for editing, null for add mode
// Signals:     saved(var formData)   — { toolNo, tipRadius, frontAngle, backAngle, comment,
//                                        orientation, toolType, <type-specific extras> }
//              cancelled()
//              openNumPadRequested(var field)
//
// Call populate(data) explicitly to load data into fields.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../touchable_input"

Item {
    id: root

    property var toolData: null
    property int _currentOrientation: 1
    property string _currentToolType: "generic"

    signal saved(var formData)
    signal cancelled()
    signal openNumPadRequested(var field)

    readonly property var _toolTypes6: [
        { key: "generic",       label: "Generic"       },
        { key: "parting_blade", label: "Parting Blade" },
    ]
    readonly property var _toolTypes7: [
        { key: "drill",         label: "Drill"          },
        { key: "reamer",        label: "Reamer"         },
        { key: "tap",           label: "Tap"            },
        { key: "boring_bar",    label: "Boring Bar"     },
        { key: "trepaning",     label: "Trepaning Tool" },
    ]

    // Call this to load a tool into the form (or null to reset for add mode).
    // defaultToolNo is used when data is null to pre-fill the tool number field.
    function populate(data, defaultToolNo) {
        toolData = data
        toolNoError.visible = false
        if (data) {
            _currentOrientation  = Math.max(1, Math.min(9, parseInt(data.q) || 1))
            _currentToolType     = data.tool_type || "generic"
            editToolNo.value     = data.t
            editTipRadius.value  = data.d
            editFrontAngle.value = data.i
            editBackAngle.value  = data.j
            editComment.text     = data.r || ""

            // Type-specific extras
            if (data.diameter  !== undefined) extraDiameter.value  = data.diameter
            if (data.length    !== undefined) extraLength.value    = data.length
            if (data.pitch     !== undefined) extraPitch.value     = data.pitch
            if (data.min_diameter !== undefined) extraMinDiam.value = data.min_diameter
            if (data.max_undercut !== undefined) extraUndercut.value = data.max_undercut
            if (data.max_depth !== undefined)  extraMaxDepth.value  = data.max_depth
            if (data.width     !== undefined)  extraWidth.value     = data.width
            if (data.left_radius  !== undefined) extraLR.value     = data.left_radius
            if (data.right_radius !== undefined) extraRR.value     = data.right_radius
            if (data.material  !== undefined)  extraMaterial.text  = data.material || ""
        } else {
            _currentOrientation  = 1
            _currentToolType     = "generic"
            editToolNo.value     = defaultToolNo !== undefined ? defaultToolNo : null
            editTipRadius.value  = 0.0
            editFrontAngle.value = 0.0
            editBackAngle.value  = 0.0
            editComment.text     = ""
            _resetExtras()
        }
    }

    function _resetExtras() {
        extraDiameter.value  = 0.0
        extraLength.value    = 0.0
        extraPitch.value     = 0.0
        extraMinDiam.value   = 0.0
        extraUndercut.value  = 0.0
        extraMaxDepth.value  = 0.0
        extraWidth.value     = 0.0
        extraLR.value        = 0.0
        extraRR.value        = 0.0
        extraMaterial.text   = ""
    }

    // Build the formData object for the saved() signal
    function _buildFormData() {
        var toolNo, newToolNo = null
        if (!root.toolData) {
            // add mode — user picks the number
            toolNo = editToolNo.value !== null ? parseInt(editToolNo.value) : -1
        } else {
            // edit mode — original number is the key; detect renumber
            toolNo = root.toolData.t
            if (!root.toolData.isCurrent && editToolNo.value !== null) {
                var edited = parseInt(editToolNo.value)
                if (edited !== toolNo) newToolNo = edited
            }
        }
        if (toolNo < 0) return null

        var orient = root._currentOrientation
        var ttype = (orient === 6 || orient === 7) ? root._currentToolType : "generic"

        var d = {
            toolNo:      toolNo,
            tipRadius:   editTipRadius.value  !== null ? editTipRadius.value  : 0.0,
            frontAngle:  editFrontAngle.value !== null ? editFrontAngle.value : 0.0,
            backAngle:   editBackAngle.value  !== null ? editBackAngle.value  : 0.0,
            comment:     editComment.text,
            orientation: orient,
            toolType:    ttype
        }
        if (newToolNo !== null) d.newToolNo = newToolNo

        if (ttype === "drill" || ttype === "reamer") {
            d.diameter = extraDiameter.value !== null ? extraDiameter.value : 0.0
            d.material = extraMaterial.text
            d.length   = extraLength.value   !== null ? extraLength.value   : 0.0
        } else if (ttype === "tap") {
            d.diameter = extraDiameter.value !== null ? extraDiameter.value : 0.0
            d.pitch    = extraPitch.value    !== null ? extraPitch.value    : 0.0
        } else if (ttype === "boring_bar") {
            d.min_diameter = extraMinDiam.value  !== null ? extraMinDiam.value  : 0.0
            d.max_undercut = extraUndercut.value !== null ? extraUndercut.value : 0.0
            d.max_depth    = extraMaxDepth.value !== null ? extraMaxDepth.value : 0.0
        } else if (ttype === "trepaning") {
            d.diameter = extraDiameter.value !== null ? extraDiameter.value : 0.0
        } else if (ttype === "parting_blade") {
            d.width        = extraWidth.value    !== null ? extraWidth.value    : 0.0
            d.max_depth    = extraMaxDepth.value !== null ? extraMaxDepth.value : 0.0
            d.left_radius  = extraLR.value       !== null ? extraLR.value       : 0.0
            d.right_radius = extraRR.value       !== null ? extraRR.value       : 0.0
        }
        return d
    }

    // ── Hidden NumpadField "registers" for extras ──────────────────
    // All kept invisible; only the relevant ones are shown via the
    // ExtraFieldsPanel.  They still hold their values regardless.

    NumpadField { id: extraDiameter;  visible: false; settingName: ""; value: 0.0; formatter: function(v){return v===null?"":Number(v).toFixed(3)}; parser: function(s){var x=parseFloat(s);return isNaN(x)?null:x} }
    NumpadField { id: extraLength;    visible: false; settingName: ""; value: 0.0; formatter: function(v){return v===null?"":Number(v).toFixed(3)}; parser: function(s){var x=parseFloat(s);return isNaN(x)?null:x} }
    NumpadField { id: extraPitch;     visible: false; settingName: ""; value: 0.0; formatter: function(v){return v===null?"":Number(v).toFixed(3)}; parser: function(s){var x=parseFloat(s);return isNaN(x)?null:x} }
    NumpadField { id: extraMinDiam;   visible: false; settingName: ""; value: 0.0; formatter: function(v){return v===null?"":Number(v).toFixed(3)}; parser: function(s){var x=parseFloat(s);return isNaN(x)?null:x} }
    NumpadField { id: extraUndercut;  visible: false; settingName: ""; value: 0.0; formatter: function(v){return v===null?"":Number(v).toFixed(3)}; parser: function(s){var x=parseFloat(s);return isNaN(x)?null:x} }
    NumpadField { id: extraMaxDepth;  visible: false; settingName: ""; value: 0.0; formatter: function(v){return v===null?"":Number(v).toFixed(3)}; parser: function(s){var x=parseFloat(s);return isNaN(x)?null:x} }
    NumpadField { id: extraWidth;     visible: false; settingName: ""; value: 0.0; formatter: function(v){return v===null?"":Number(v).toFixed(3)}; parser: function(s){var x=parseFloat(s);return isNaN(x)?null:x} }
    NumpadField { id: extraLR;        visible: false; settingName: ""; value: 0.0; formatter: function(v){return v===null?"":Number(v).toFixed(3)}; parser: function(s){var x=parseFloat(s);return isNaN(x)?null:x} }
    NumpadField { id: extraRR;        visible: false; settingName: ""; value: 0.0; formatter: function(v){return v===null?"":Number(v).toFixed(3)}; parser: function(s){var x=parseFloat(s);return isNaN(x)?null:x} }
    TextField   { id: extraMaterial;  visible: false }

    Rectangle {
        anchors.fill: parent
        color: "#f0f0f0"

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // ── Header bar: Cancel | Title | Save ─────────────────
            Item {
                Layout.fillWidth: true
                height: 60

                Rectangle { anchors.fill: parent; color: "#e0e0e0" }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#bbbbbb" }

                // Cancel
                Rectangle {
                    anchors.left: parent.left; anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: 130; height: 46; radius: 6
                    color: cancelMA.pressed ? "#b8b8b8" : "#d8d8d8"; border.color: "#999999"; border.width: 1
                    Text { anchors.centerIn: parent; text: "Cancel"; font.pixelSize: 16; color: "#222222" }
                    MouseArea { id: cancelMA; anchors.fill: parent; onClicked: root.cancelled() }
                }

                // Title — absolutely centered
                Text {
                    anchors.centerIn: parent
                    text: root.toolData ? ("Edit Tool  T" + root.toolData.t) : "Add Tool"
                    font.pixelSize: 20; font.bold: true; color: "#1a1a1a"
                }

                // Save
                Rectangle {
                    anchors.right: parent.right; anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: 130; height: 46; radius: 6
                    color: saveMA.pressed ? "#145a30" : "#1e8449"
                    Text { anchors.centerIn: parent; text: "Save"; font.pixelSize: 16; font.bold: true; color: "white" }
                    MouseArea {
                        id: saveMA; anchors.fill: parent
                        onClicked: {
                            var isToolNoEditable = !root.toolData || !root.toolData.isCurrent
                            if (isToolNoEditable && editToolNo.value !== null) {
                                var newNo = parseInt(editToolNo.value)
                                var origNo = root.toolData ? root.toolData.t : -1
                                if (newNo !== origNo && toolLibraryViewModel && toolLibraryViewModel.toolExists(newNo)) {
                                    toolNoError.visible = true
                                    return
                                }
                            }
                            toolNoError.visible = false
                            var fd = root._buildFormData()
                            if (fd !== null) root.saved(fd)
                        }
                    }
                }
            }

            // ── Content row: fields | separator | orientation ──────
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.leftMargin: 16; Layout.rightMargin: 16
                Layout.topMargin: 12; Layout.bottomMargin: 16
                spacing: 0

                // Left column — common fields + type-specific extras
                ColumnLayout {
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true
                    spacing: 0

                    // Common fields
                    GridLayout {
                        Layout.alignment: Qt.AlignTop
                        Layout.leftMargin: 4
                        columns: 2; rowSpacing: 16; columnSpacing: 14

                        // Tool No — add mode, or edit mode when tool is not current
                        Text {
                            visible: !root.toolData || !root.toolData.isCurrent
                            text: "Tool No:"; font.pixelSize: 15
                            Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                        }
                        NumpadField {
                            id: editToolNo
                            visible: !root.toolData || !root.toolData.isCurrent
                            Layout.preferredWidth: 100
                            settingName: "tool_edit.tool_no"; hAlign: Text.AlignLeft
                            formatter: function(v) { return (v === null || v === undefined) ? "" : String(parseInt(v)) }
                            parser:    function(s) { var n = parseInt(s); return isNaN(n) ? null : n }
                            onOpenRequested: root.openNumPadRequested(field)
                            onValueChanged: toolNoError.visible = false
                        }

                        // Error row (spans both columns visually via empty label + error text)
                        Item { visible: toolNoError.visible; height: toolNoError.visible ? toolNoError.implicitHeight : 0; Layout.preferredWidth: 130 }
                        Text {
                            id: toolNoError
                            visible: false
                            text: "Tool number already exists"
                            color: "#c62828"; font.pixelSize: 13
                            Layout.preferredWidth: 160
                        }

                        // Tip Radius
                        Text { text: "Tip Radius:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130 }
                        NumpadField {
                            id: editTipRadius
                            Layout.preferredWidth: 100
                            settingName: "tool_library.tool_tip_radius"
                            formatter: function(v) { return (v === null || v === undefined) ? "" : Number(v).toFixed(3) }
                            parser:    function(s) { var x = parseFloat(s); return isNaN(x) ? null : x }
                            onOpenRequested: root.openNumPadRequested(field)
                        }

                        // Front Angle
                        Text { text: "Front Angle:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130 }
                        NumpadField {
                            id: editFrontAngle
                            Layout.preferredWidth: 100
                            settingName: "tool_edit.front_angle"
                            formatter: function(v) { return (v === null || v === undefined) ? "" : String(Math.round(v)) + "°" }
                            parser:    function(s) { var x = parseFloat(s); return isNaN(x) ? null : x }
                            onOpenRequested: root.openNumPadRequested(field)
                        }

                        // Back Angle
                        Text { text: "Back Angle:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130 }
                        NumpadField {
                            id: editBackAngle
                            Layout.preferredWidth: 100
                            settingName: "tool_edit.back_angle"
                            formatter: function(v) { return (v === null || v === undefined) ? "" : String(Math.round(v)) + "°" }
                            parser:    function(s) { var x = parseFloat(s); return isNaN(x) ? null : x }
                            onOpenRequested: root.openNumPadRequested(field)
                        }

                        // Comment
                        Text { text: "Comment:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130 }
                        TextField {
                            id: editComment
                            Layout.preferredWidth: 280; Layout.preferredHeight: 44
                            font.pixelSize: 15; placeholderText: "Description..."
                        }
                    }

                    // ── Type selector + extras (orientations 6 and 7) ──
                    Item {
                        Layout.fillWidth: true
                        Layout.topMargin: 12
                        implicitHeight: typeBlock.visible ? typeBlock.implicitHeight : 0
                        visible: root._currentOrientation === 6 || root._currentOrientation === 7

                        ColumnLayout {
                            id: typeBlock
                            anchors { left: parent.left; right: parent.right; leftMargin: 4 }
                            spacing: 10
                            visible: root._currentOrientation === 6 || root._currentOrientation === 7

                            Rectangle { Layout.fillWidth: true; height: 1; color: "#bbbbbb" }

                            // Type chips
                            RowLayout {
                                spacing: 8
                                Text { text: "Type:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter }

                                Repeater {
                                    model: root._currentOrientation === 6 ? root._toolTypes6 : root._toolTypes7
                                    delegate: Rectangle {
                                        implicitWidth:  typeLabel.implicitWidth + 20
                                        implicitHeight: 34
                                        radius: 6
                                        color:        (root._currentToolType === modelData.key) ? "#dbeafe" : "#e8e8e8"
                                        border.color: (root._currentToolType === modelData.key) ? "#3b82f6" : "#aaaaaa"
                                        border.width: (root._currentToolType === modelData.key) ? 2 : 1

                                        Text {
                                            id: typeLabel
                                            anchors.centerIn: parent
                                            text: modelData.label; font.pixelSize: 13
                                            color: (root._currentToolType === modelData.key) ? "#1d4ed8" : "#333333"
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: root._currentToolType = modelData.key
                                        }
                                    }
                                }
                            }

                            // Extra fields grid (changes per type)
                            GridLayout {
                                columns: 2; rowSpacing: 12; columnSpacing: 14
                                Layout.leftMargin: 4

                                // Diameter — drill / reamer / tap / trepaning
                                Text {
                                    visible: ["drill","reamer","tap","trepaning"].indexOf(root._currentToolType) >= 0
                                    text: "Diameter:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: ["drill","reamer","tap","trepaning"].indexOf(root._currentToolType) >= 0
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.diameter"
                                    value:     extraDiameter.value
                                    formatter: extraDiameter.formatter
                                    parser:    extraDiameter.parser
                                    onValueChanged: { if (extraDiameter.value !== value) extraDiameter.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }

                                // Pitch — tap only
                                Text {
                                    visible: root._currentToolType === "tap"
                                    text: "Pitch:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: root._currentToolType === "tap"
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.pitch"
                                    value:     extraPitch.value
                                    formatter: extraPitch.formatter
                                    parser:    extraPitch.parser
                                    onValueChanged: { if (extraPitch.value !== value) extraPitch.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }

                                // Material — drill / reamer
                                Text {
                                    visible: ["drill","reamer"].indexOf(root._currentToolType) >= 0
                                    text: "Material:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                TextField {
                                    visible: ["drill","reamer"].indexOf(root._currentToolType) >= 0
                                    Layout.preferredWidth: 100; Layout.preferredHeight: 44
                                    font.pixelSize: 15; placeholderText: "e.g. HSS"
                                    text: extraMaterial.text
                                    onTextChanged: extraMaterial.text = text
                                }

                                // Length — drill / reamer
                                Text {
                                    visible: ["drill","reamer"].indexOf(root._currentToolType) >= 0
                                    text: "Length:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: ["drill","reamer"].indexOf(root._currentToolType) >= 0
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.length"
                                    value:     extraLength.value
                                    formatter: extraLength.formatter
                                    parser:    extraLength.parser
                                    onValueChanged: { if (extraLength.value !== value) extraLength.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }

                                // Min Diameter — boring bar
                                Text {
                                    visible: root._currentToolType === "boring_bar"
                                    text: "Min Diam.:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: root._currentToolType === "boring_bar"
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.min_diameter"
                                    value:     extraMinDiam.value
                                    formatter: extraMinDiam.formatter
                                    parser:    extraMinDiam.parser
                                    onValueChanged: { if (extraMinDiam.value !== value) extraMinDiam.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }

                                // Max Undercut — boring bar
                                Text {
                                    visible: root._currentToolType === "boring_bar"
                                    text: "Max Undercut:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: root._currentToolType === "boring_bar"
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.max_undercut"
                                    value:     extraUndercut.value
                                    formatter: extraUndercut.formatter
                                    parser:    extraUndercut.parser
                                    onValueChanged: { if (extraUndercut.value !== value) extraUndercut.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }

                                // Max Depth — boring bar
                                Text {
                                    visible: root._currentToolType === "boring_bar"
                                    text: "Max Depth:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: root._currentToolType === "boring_bar"
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.max_depth"
                                    value:     extraMaxDepth.value
                                    formatter: extraMaxDepth.formatter
                                    parser:    extraMaxDepth.parser
                                    onValueChanged: { if (extraMaxDepth.value !== value) extraMaxDepth.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }

                                // Width — parting blade
                                Text {
                                    visible: root._currentToolType === "parting_blade"
                                    text: "Width:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: root._currentToolType === "parting_blade"
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.width"
                                    value:     extraWidth.value
                                    formatter: extraWidth.formatter
                                    parser:    extraWidth.parser
                                    onValueChanged: { if (extraWidth.value !== value) extraWidth.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }

                                // Max Depth — parting blade
                                Text {
                                    visible: root._currentToolType === "parting_blade"
                                    text: "Max Depth:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: root._currentToolType === "parting_blade"
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.max_depth_pb"
                                    value:     extraMaxDepth.value
                                    formatter: extraMaxDepth.formatter
                                    parser:    extraMaxDepth.parser
                                    onValueChanged: { if (extraMaxDepth.value !== value) extraMaxDepth.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }

                                // Left Radius — parting blade
                                Text {
                                    visible: root._currentToolType === "parting_blade"
                                    text: "Left Radius:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: root._currentToolType === "parting_blade"
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.left_radius"
                                    value:     extraLR.value
                                    formatter: extraLR.formatter
                                    parser:    extraLR.parser
                                    onValueChanged: { if (extraLR.value !== value) extraLR.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }

                                // Right Radius — parting blade
                                Text {
                                    visible: root._currentToolType === "parting_blade"
                                    text: "Right Radius:"; font.pixelSize: 15; Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 130
                                }
                                NumpadField {
                                    visible: root._currentToolType === "parting_blade"
                                    Layout.preferredWidth: 100
                                    settingName: "tool_edit.right_radius"
                                    value:     extraRR.value
                                    formatter: extraRR.formatter
                                    parser:    extraRR.parser
                                    onValueChanged: { if (extraRR.value !== value) extraRR.value = value }
                                    onOpenRequested: root.openNumPadRequested(field)
                                }
                            }
                        }
                    }
                }

                Item { Layout.preferredWidth: 12 }

                Rectangle { width: 1; Layout.fillHeight: true; color: "#bbbbbb" }

                // Orientation picker
                ColumnLayout {
                    Layout.alignment: Qt.AlignTop
                    Layout.leftMargin: 12
                    Layout.rightMargin: 4
                    spacing: 10

                    Text {
                        text: "Orientation"; font.pixelSize: 15; font.bold: true
                        horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true
                    }

                    GridLayout {
                        columns: 3; rowSpacing: 6; columnSpacing: 6

                        Repeater {
                            model: [4, 8, 3, 5, 9, 7, 1, 6, 2]
                            delegate: Rectangle {
                                width: 80; height: 80; radius: 6
                                color:        (root._currentOrientation === modelData) ? "#dbeafe" : "#ffffff"
                                border.color: (root._currentOrientation === modelData) ? "#3b82f6" : "#aaaaaa"
                                border.width: (root._currentOrientation === modelData) ? 2 : 1

                                Image {
                                    anchors.centerIn: parent; width: 60; height: 60
                                    source: "../../images/lathe_control_point_" + modelData + ".png"
                                    fillMode: Image.PreserveAspectFit
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        root._currentOrientation = modelData
                                        var valid6 = ["generic", "parting_blade"]
                                        var valid7 = ["drill", "reamer", "tap", "boring_bar", "trepaning"]
                                        if (modelData === 6 && valid6.indexOf(root._currentToolType) < 0)
                                            root._currentToolType = "generic"
                                        else if (modelData === 7 && valid7.indexOf(root._currentToolType) < 0)
                                            root._currentToolType = "drill"
                                        else if (modelData !== 6 && modelData !== 7)
                                            root._currentToolType = "generic"
                                    }
                                }
                            }
                        }
                    }
                }
            }

        }
    }
}
