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
        _loading = false
    }

    function emitSave() {
        if (_loading) return
        root.saveRequested({
            profile_contour_strategy: {
                profiling_type: profiling_type
            }
        })
    }

    Label {
        anchors.fill: parent
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
        text: "Select a ProfileID from a Define Profile operation defined above the current operation."
        font.pixelSize: 15
        font.bold: true
        color: "#ff9800"
        visible: !root.hasResolvedProfile
    }
}
