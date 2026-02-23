// DefineProfileDetailsView.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root
    anchors.fill: parent

    property int opIndex: -1
    property var opData:  null
    property int selectedPrimIndex: -1

    property int  profileId: 0
    property bool _loading:  false

    signal saveRequested(var updated)
    signal openNumPadRequested(var field)

    function applyData(index, data) {
        _loading = true
        opIndex  = index
        opData   = data || {}
        profileId = opData.profile_id !== undefined ? Math.round(Number(opData.profile_id)) : 0
        selectedPrimIndex = -1
        _loading = false
    }

    function mergeIntoOp(payload) {
        var out = JSON.parse(JSON.stringify(opData || {}))
        for (var k in payload) {
            if (k === "index") continue
            if (payload.hasOwnProperty(k)) out[k] = payload[k]
        }
        opData = out
        return out
    }

    function emitSave() {
        if (_loading) return
        var merged = root.mergeIntoOp({ profile_id: root.profileId })
        root.saveRequested({ index: root.opIndex, payload: merged })
    }

    IntValidator { id: intVal; bottom: 1; top: 999 }

    // ── Helper: build detail text for a primitive ─────────────────────────────
    function primitiveDetails(p) {
        if (!p) return ""
        var t = p.type || ""
        if (t === "startPoint") {
            return "x_start: " + p.x_start + ",  z_start: " + p.z_start
        }
        if (t === "lineTo") {
            var s = "x_end: " + p.x_end + ",  z_end: " + p.z_end
            if (p.blend) s += ",  blend: " + p.blend.type
            return s
        }
        if (t === "arcTo") {
            var a = "dir: " + p.direction
            a += ",  x_end: " + p.x_end + ",  z_end: " + p.z_end
            a += ",  xc: " + p.x_center + ",  zc: " + p.z_center
            a += ",  r: " + p.arc_radius
            if (p.blend) a += ",  blend: " + p.blend.type
            return a
        }
        return ""
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 16

        // ── Title ─────────────────────────────────────────────────────────────
        Label {
            text: (opData && opData.type)
                  ? ("Define Profile — Op #" + (opData.order !== undefined ? opData.order : "N/A"))
                  : "Define Profile"
            font.pixelSize: 18
            font.bold: true
            bottomPadding: 4
        }

        // ── Profile ID row ────────────────────────────────────────────────────
        RowLayout {
            spacing: 12
            Label { text: "Profile ID"; font.pixelSize: 16 }
            NumpadField {
                Layout.preferredWidth: 80
                settingName: "defineProfile.profile_id"
                validatorObject: intVal
                value: root.profileId
                formatter: function(v) { return (v == null) ? "" : String(Math.round(Number(v))) }
                hAlign: Text.AlignRight
                fontPixelSize: 16
                onOpenRequested: root.openNumPadRequested(field)
                onValueCommitted: { root.profileId = Math.round(value); root.emitSave() }
            }
        }

        // ── Profile Primitives list ───────────────────────────────────────────
        GroupBox {
            title: "Profile Primitives"
            Layout.fillWidth: true
            Layout.fillHeight: true
            font.pixelSize: 16

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Column headers
                Rectangle {
                    Layout.fillWidth: true
                    height: 32
                    color: "#e0e0e0"
                    radius: 3

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 0

                        Label {
                            text: "Id"
                            font.bold: true; font.pixelSize: 14
                            Layout.preferredWidth: 44
                            verticalAlignment: Text.AlignVCenter
                        }
                        Rectangle { width: 1; height: parent.height * 0.7; color: "#bbb"; Layout.alignment: Qt.AlignVCenter }
                        Label {
                            text: "Primitive Type"
                            font.bold: true; font.pixelSize: 14
                            Layout.preferredWidth: 120
                            leftPadding: 8
                            verticalAlignment: Text.AlignVCenter
                        }
                        Rectangle { width: 1; height: parent.height * 0.7; color: "#bbb"; Layout.alignment: Qt.AlignVCenter }
                        Label {
                            text: "Details"
                            font.bold: true; font.pixelSize: 14
                            Layout.fillWidth: true
                            leftPadding: 8
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#cccccc" }

                // Primitives list
                ListView {
                    id: primList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    currentIndex: root.selectedPrimIndex
                    model: (opData && opData.profile_primitives) ? opData.profile_primitives : []

                    delegate: Rectangle {
                        width: ListView.view ? ListView.view.width : 400
                        height: 36
                        color: ListView.isCurrentItem
                               ? "#bbdefb"
                               : (index % 2 === 0 ? "#ffffff" : "#f5f5f5")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 0

                            // Id
                            Label {
                                text: String(modelData.primitive_id !== undefined
                                             ? modelData.primitive_id : index + 1)
                                font.pixelSize: 14
                                Layout.preferredWidth: 44
                                verticalAlignment: Text.AlignVCenter
                            }
                            Rectangle { width: 1; height: parent.height * 0.6; color: "#ddd"; Layout.alignment: Qt.AlignVCenter }

                            // Primitive type
                            Label {
                                text: String(modelData.type || "")
                                font.pixelSize: 14
                                Layout.preferredWidth: 120
                                leftPadding: 8
                                verticalAlignment: Text.AlignVCenter
                            }
                            Rectangle { width: 1; height: parent.height * 0.6; color: "#ddd"; Layout.alignment: Qt.AlignVCenter }

                            // Details (key: value)
                            Label {
                                text: root.primitiveDetails(modelData)
                                font.pixelSize: 13
                                color: "#444"
                                Layout.fillWidth: true
                                leftPadding: 8
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        TapHandler {
                            onTapped: root.selectedPrimIndex = index
                        }
                    }
                }
            }
        }
    }
}