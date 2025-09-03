// ProfilingDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "." // for NumpadField.qml

Item {
    id: root
    anchors.fill: parent

    // Contract with parent (ChildScreen)
    property int opIndex: -1
    property var opData: null
    signal saveRequested(var updated)          // { index, payload }
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)          // optional if you add Teach buttons later
    signal teachZRequested(int index)

    // State mirrors Profiling dataclass
    property int   css_value: 0
    property int   max_speed: 0
    property real  feed_rate: 0.0
    property int   profileId: 0
    property string strategy: "rough"          // "rough" | "finish"
    property real  x_start: 0.0
    property real  z_start: 0.0
    property real  doc: 0.0
    property real  retract: 0.0
    property bool  hasStockToLeave: false
    property real  stockLeaveX: 0.0
    property real  stockLeaveZ: 0.0
    property bool  useSpringPasses: false
    property int   spring_passes: 0

    function applyData(index, data) {
        opIndex = index
        opData = data || {}

        css_value = +((opData.css_value !== undefined) ? opData.css_value : 0)
        max_speed = +((opData.max_speed !== undefined) ? opData.max_speed : 0)
        feed_rate = parseFloat((opData.feed_rate !== undefined) ? opData.feed_rate : 0.0)
        profileId = +((opData.profileId !== undefined) ? opData.profileId : 0)
        strategy  = (opData.strategy !== undefined) ? String(opData.strategy) : "rough"
        x_start   = parseFloat((opData.x_start !== undefined) ? opData.x_start : 0.0)
        z_start   = parseFloat((opData.z_start !== undefined) ? opData.z_start : 0.0)
        doc       = parseFloat((opData.doc !== undefined) ? opData.doc : 0.0)
        retract   = parseFloat((opData.retract !== undefined) ? opData.retract : 0.0)

        var stl = (opData.stock_to_leave !== undefined) ? opData.stock_to_leave : null
        hasStockToLeave = !!stl
        stockLeaveX = stl && stl.x !== undefined ? parseFloat(stl.x) : 0.0
        stockLeaveZ = stl && stl.z !== undefined ? parseFloat(stl.z) : 0.0

        var sp = (opData.spring_passes !== undefined) ? opData.spring_passes : null
        useSpringPasses = (sp !== null && sp !== undefined)
        spring_passes = useSpringPasses ? +sp : 0
    }

    // Validators
    IntValidator    { id: intVal }
    DoubleValidator { id: dblVal; notation: DoubleValidator.StandardNotation }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Label {
            text: (opData && opData.type) ? ("Profiling — Op #" + (opData.order !== undefined ? opData.order : "N/A")) : "Profiling"
            font.pixelSize: 18
            font.bold: true
        }

        // Cutting parameters
        GroupBox {
            title: "Cutting Parameters"
            Layout.fillWidth: true

            GridLayout {
                columns: 4
                columnSpacing: 12
                rowSpacing: 8
                anchors.margins: 10
                anchors.fill: parent

                Label { text: "CSS"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "profiling_css"
                    validatorObject: intVal
                    value: root.css_value
                    formatter: function(v){ return (v==null)?"":String(v) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.css_value = value
                }

                Label { text: "Max RPM"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "profiling_max_rpm"
                    validatorObject: intVal
                    value: root.max_speed
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.max_speed = value
                }

                Label { text: "Feed (mm/rev)"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "profiling_feed"
                    validatorObject: dblVal
                    value: root.feed_rate
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.feed_rate = value
                }

                Label { text: "DOC (mm)"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "profiling_doc"
                    validatorObject: dblVal
                    value: root.doc
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.doc = value
                }

                Label { text: "Retract (mm)"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "profiling_retract"
                    validatorObject: dblVal
                    value: root.retract
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.retract = value
                }
            }
        }

        // Geometry
        GroupBox {
            title: "Profiling Geometry"
            Layout.fillWidth: true

            GridLayout {
                columns: 4
                columnSpacing: 12
                rowSpacing: 8
                anchors.margins: 10
                anchors.fill: parent

                Label { text: "X start"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "profiling_x_start"
                    validatorObject: dblVal
                    value: root.x_start
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.x_start = value
                }

                Label { text: "Z start"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "profiling_z_start"
                    validatorObject: dblVal
                    value: root.z_start
                    formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.z_start = value
                }
            }
        }

        // Profile + strategy
        GroupBox {
            title: "Profile Settings"
            Layout.fillWidth: true

            GridLayout {
                columns: 4
                columnSpacing: 12
                rowSpacing: 8
                anchors.margins: 10
                anchors.fill: parent

                Label { text: "Profile ID"; Layout.alignment: Qt.AlignVCenter }
                NumpadField {
                    Layout.preferredWidth: 140
                    settingName: "profiling_profile_id"
                    validatorObject: intVal
                    value: root.profileId
                    formatter: function(v){ return (v==null)?"":String(v) }
                    onOpenRequested: root.openNumPadRequested(field)
                    onValueCommitted: root.profileId = value
                }

                Label { text: "Strategy"; Layout.alignment: Qt.AlignVCenter }
                ComboBox {
                    id: cbStrategy
                    Layout.preferredWidth: 160
                    textRole: "label"
                    model: [
                        { label: "Rough",  value: "rough"  },
                        { label: "Finish", value: "finish" }
                    ]
                    Component.onCompleted: {
                        var idx = model.findIndex(function(m){ return m.value === root.strategy })
                        currentIndex = idx >= 0 ? idx : 0
                    }
                    onCurrentIndexChanged: {
                        if (currentIndex >= 0) root.strategy = model[currentIndex].value
                    }
                }
            }
        }

        // Stock to leave + spring passes
        GroupBox {
            title: "Finishing Options"
            Layout.fillWidth: true

            ColumnLayout {
                anchors.margins: 10
                spacing: 8
                anchors.fill: parent

                // Stock to leave
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    CheckBox {
                        id: cbStock
                        text: "Enable stock to leave"
                        checked: root.hasStockToLeave
                        onToggled: root.hasStockToLeave = checked
                    }

                    Label { text: "X (mm)"; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 120
                        enabled: root.hasStockToLeave
                        settingName: "profiling_stock_x"
                        validatorObject: dblVal
                        value: root.stockLeaveX
                        formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: root.stockLeaveX = value
                    }

                    Label { text: "Z (mm)"; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 120
                        enabled: root.hasStockToLeave
                        settingName: "profiling_stock_z"
                        validatorObject: dblVal
                        value: root.stockLeaveZ
                        formatter: function(v){ return (v==null)?"":Number(v).toFixed(3) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: root.stockLeaveZ = value
                    }
                }

                // Spring passes
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    CheckBox {
                        id: cbSpring
                        text: "Use spring passes"
                        checked: root.useSpringPasses
                        onToggled: root.useSpringPasses = checked
                    }

                    Label { text: "Count"; verticalAlignment: Text.AlignVCenter }
                    NumpadField {
                        Layout.preferredWidth: 120
                        enabled: root.useSpringPasses
                        settingName: "profiling_spring_passes"
                        validatorObject: intVal
                        value: root.spring_passes
                        formatter: function(v){ return (v==null)?"":String(v) }
                        onOpenRequested: root.openNumPadRequested(field)
                        onValueCommitted: root.spring_passes = value
                    }
                }
            }
        }

        // Actions
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Item { Layout.fillWidth: true }
            Button {
                text: "Reset"
                onClicked: { if (root.opData) root.applyData(root.opIndex, root.opData) }
            }
            Button {
                text: "Save"
                onClicked: {
                    var payload = {
                        order: (root.opData && root.opData.order !== undefined) ? root.opData.order : 0,
                        type: "profiling",
                        generate_gcode: (root.opData && root.opData.generate_gcode !== undefined) ? root.opData.generate_gcode : true,
                        is_optional_block: (root.opData && root.opData.is_optional_block !== undefined) ? root.opData.is_optional_block : false,

                        css_value: root.css_value,
                        max_speed: root.max_speed,
                        feed_rate: root.feed_rate,
                        profileId: root.profileId,
                        strategy: root.strategy,
                        x_start: root.x_start,
                        z_start: root.z_start,
                        doc: root.doc,
                        retract: root.retract,
                        stock_to_leave: root.hasStockToLeave ? { x: root.stockLeaveX, z: root.stockLeaveZ } : null,
                        spring_passes: root.useSpringPasses ? root.spring_passes : null
                    }
                    root.saveRequested({ index: root.opIndex, payload: payload })
                }
            }
        }
    }
}
