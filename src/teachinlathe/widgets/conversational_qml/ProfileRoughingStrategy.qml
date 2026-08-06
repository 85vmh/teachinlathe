// ProfileRoughingStrategy.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

GroupBox {
    id: root
    title: root.hasResolvedProfile ? ("Profiling Type: " + root.profilingTypeLabel) : "Profiling Type"
    Layout.fillWidth: true
    font.pixelSize: 16

    // "od" | "id" — resolved automatically from the selected DefineProfile
    property string profiling_type: "od"
    property int profile_id: 0
    property int op_index: -1
    property bool profile_found: false
    readonly property bool hasProfileId: profile_id > 0
    readonly property bool hasResolvedProfile: hasProfileId && profile_found
    readonly property string profilingTypeLabel: root.profiling_type === "id" ? "ID (Boring)" : "OD (Turning)"
    // "axial" | "radial" | "diagonal_interior" | "diagonal_exterior"
    property string pass_type: "axial"

    property bool _loading: false

    signal saveRequested(var payload)

    function applyData(data, profileId, opIndex) {
        _loading = true
        profile_id = parseInt(profileId !== undefined ? profileId : 0)
        op_index = parseInt(opIndex !== undefined ? opIndex : -1)
        var resolvedType = (root.hasProfileId && typeof conversationalQml !== "undefined")
                         ? conversationalQml.resolveProfileType(profile_id, op_index)
                         : ""
        profile_found = resolvedType !== ""
        profiling_type = profile_found ? resolvedType : ((data && data.profiling_type) ? String(data.profiling_type) : "od")
        pass_type      = (data && data.pass_type)      ? String(data.pass_type)      : "axial"
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            profile_roughing_strategy: {
                profiling_type: profiling_type,
                pass_type:      pass_type
            }
        })
    }

    ButtonGroup { id: passGroup }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Label {
            Layout.fillWidth: true
            Layout.preferredHeight: 92
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
            text: "Select a ProfileID from a Define Profile operation defined above the current operation."
            font.pixelSize: 15
            font.bold: true
            color: "#ff9800"
            visible: !root.hasResolvedProfile
        }

        // Pass type selection — 2×2 grid; diagonal buttons only visible for ID
        GridLayout {
            columns: 2
            columnSpacing: 24
            rowSpacing: 6
            visible: root.hasResolvedProfile

            RadioButton {
                text: "Axial Passes"
                font.pixelSize: 15
                checked: root.pass_type === "axial"
                ButtonGroup.group: passGroup
                onToggled: if (checked) { root.pass_type = "axial"; root.emitSave() }
            }
            RadioButton {
                text: "45° Passes toward interior"
                font.pixelSize: 15
                opacity: root.profiling_type === "id" ? 1.0 : 0.0
                enabled: root.profiling_type === "id"
                checked: root.pass_type === "diagonal_interior"
                ButtonGroup.group: passGroup
                onToggled: if (checked) { root.pass_type = "diagonal_interior"; root.emitSave() }
            }

            RadioButton {
                text: "Radial Passes"
                font.pixelSize: 15
                checked: root.pass_type === "radial"
                ButtonGroup.group: passGroup
                onToggled: if (checked) { root.pass_type = "radial"; root.emitSave() }
            }
            RadioButton {
                text: "45° Passes toward exterior"
                font.pixelSize: 15
                opacity: root.profiling_type === "id" ? 1.0 : 0.0
                enabled: root.profiling_type === "id"
                checked: root.pass_type === "diagonal_exterior"
                ButtonGroup.group: passGroup
                onToggled: if (checked) { root.pass_type = "diagonal_exterior"; root.emitSave() }
            }
        }
    }
}
