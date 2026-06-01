// ToolCard.qml — displays a single tool entry in the tool list.
//
// Properties:  toolData  — tool dict { t, x, z, d, q, i, j, r, isCurrent }
// Signals:     editRequested(var toolData)
//              deleteRequested(int toolNo)
//              loadRequested(int toolNo)
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var toolData: null

    signal editRequested(var toolData)
    signal deleteRequested(int toolNo)
    signal loadRequested(int toolNo)

    // ── Colors ────────────────────────────────────────────────────
    readonly property color clrBg:        "white"
    readonly property color clrBgSel:     "#dbeafe"
    readonly property color clrBorder:    "#cccccc"
    readonly property color clrBorderSel: "#3b82f6"
    readonly property color clrSep:       "#d0d0d0"
    readonly property color clrBtnBorder: "#BDBDBD"
    readonly property color clrDelHover:  "#ffebee"
    readonly property color clrDelBorder: "#C62828"

    // ── Sizes ─────────────────────────────────────────────────────
    readonly property int szR:    4    // border radius
    readonly property int szM:   12    // outer margin
    readonly property int szSp:   8    // spacing
    readonly property int szF:   14    // font size
    readonly property int szBtn: 40    // button side
    readonly property int szI:   28    // icon display size
    readonly property int szIS: 112    // icon source size

    radius:       szR
    color:        toolData && toolData.isCurrent ? clrBgSel     : clrBg
    border.color: toolData && toolData.isCurrent ? clrBorderSel : clrBorder
    border.width: toolData && toolData.isCurrent ? 2 : 1
    height:       contentRow.implicitHeight + szM * 2

    // ── Orientation helper ────────────────────────────────────────
    function orientAngle(value) {
        if (value === 1) return 315
        if (value === 2) return 225
        if (value === 3) return 135
        if (value === 4) return  45
        if (value === 5) return   0
        if (value === 6) return -90
        if (value === 7) return 180
        if (value === 8) return  90
        return 0
    }

    // Card tap → load tool
    MouseArea {
        anchors.fill: parent
        onClicked: if (root.toolData) root.loadRequested(root.toolData.t)
    }

    // ── Content ───────────────────────────────────────────────────
    RowLayout {
        id: contentRow
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: root.szM }
        spacing: root.szSp

        // Tool number
        Text {
            text: toolData ? ("T" + toolData.t) : ""
            font.pixelSize: 18; font.bold: true
            Layout.preferredWidth: 37
            Layout.alignment: Qt.AlignVCenter
        }

        Rectangle { width: 1; Layout.fillHeight: true; color: root.clrSep }

        // Data columns
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8

            RowLayout {
                spacing: 12; Layout.fillWidth: true

                // X / Z offsets
                ColumnLayout {
                    spacing: 4; Layout.preferredWidth: 140
                    GridLayout {
                        columns: 2; rowSpacing: 4; columnSpacing: 12; Layout.fillWidth: true
                        Text { text: "X Offset:"; font.pixelSize: root.szF; Layout.fillWidth: true }
                        Text { text: toolData ? Number(toolData.x).toFixed(3) : ""; font.pixelSize: root.szF; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                        Text { text: "Z Offset:"; font.pixelSize: root.szF; Layout.fillWidth: true }
                        Text { text: toolData ? Number(toolData.z).toFixed(3) : ""; font.pixelSize: root.szF; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                    }
                }

                Rectangle { width: 1; Layout.fillHeight: true; color: root.clrSep }

                // Tip radius + orientation indicator
                ColumnLayout {
                    spacing: 4; Layout.preferredWidth: 170
                    GridLayout {
                        columns: 2; rowSpacing: 4; columnSpacing: 12; Layout.fillWidth: true

                        Text { text: "Tip Radius:"; font.pixelSize: root.szF; Layout.fillWidth: true }
                        Text { text: toolData ? Number(toolData.d).toFixed(1) : ""; font.pixelSize: root.szF; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }

                        Text { text: "Orientation:"; font.pixelSize: root.szF; Layout.fillWidth: true }
                        Item {
                            Layout.fillWidth: true; height: 20
                            Row {
                                anchors.right: parent.right; spacing: 6
                                Canvas {
                                    id: orientCanvas
                                    width: 20; height: 20

                                    property int orientValue: toolData ? parseInt(toolData.q) : 0
                                    onOrientValueChanged: requestPaint()
                                    Component.onCompleted:  requestPaint()

                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.reset(); ctx.clearRect(0, 0, width, height)
                                        var v = orientValue
                                        ctx.strokeStyle = "#000000"; ctx.fillStyle = "#000000"; ctx.lineWidth = 2
                                        if (v === 9) {
                                            ctx.beginPath()
                                            ctx.arc(width/2, height/2, 4, 0, Math.PI*2, false)
                                            ctx.fill()
                                        } else {
                                            ctx.save()
                                            ctx.translate(width/2, height/2)
                                            ctx.rotate(root.orientAngle(v) * Math.PI / 180)
                                            ctx.translate(-width/2, -height/2)
                                            var sx = width/2-6, ex = width/2+6, cy = height/2
                                            ctx.beginPath(); ctx.moveTo(sx, cy); ctx.lineTo(ex, cy); ctx.stroke()
                                            ctx.beginPath(); ctx.moveTo(ex, cy); ctx.lineTo(ex-3, cy-3); ctx.lineTo(ex-3, cy+3); ctx.closePath(); ctx.fill()
                                            ctx.restore()
                                        }
                                    }
                                }
                                Text { text: toolData ? String(toolData.q) : ""; font.pixelSize: root.szF }
                            }
                        }
                    }
                }

                Rectangle { width: 1; Layout.fillHeight: true; color: root.clrSep }

                // Front / Back angles
                ColumnLayout {
                    spacing: 4; Layout.preferredWidth: 140
                    GridLayout {
                        columns: 2; rowSpacing: 4; columnSpacing: 12; Layout.fillWidth: true
                        Text { text: "FrontAngle:"; font.pixelSize: root.szF; Layout.fillWidth: true }
                        Text { text: toolData ? (Math.round(toolData.i) + "°") : ""; font.pixelSize: root.szF; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                        Text { text: "BackAngle:";  font.pixelSize: root.szF; Layout.fillWidth: true }
                        Text { text: toolData ? (Math.round(toolData.j) + "°") : ""; font.pixelSize: root.szF; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: root.clrSep }

            Text {
                text: toolData ? toolData.r : ""
                font.pixelSize: root.szF + 1; font.bold: true; font.italic: true
                elide: Text.ElideRight; Layout.fillWidth: true
            }
        }

        Rectangle { width: 1; Layout.fillHeight: true; color: root.clrSep }

        // ── Action buttons ────────────────────────────────────────
        RowLayout {
            spacing: 18; Layout.alignment: Qt.AlignVCenter

            // Edit
            Rectangle {
                implicitWidth: root.szBtn; implicitHeight: root.szBtn; radius: root.szR
                color:        editMA.pressed ? "#e3f2fd" : "transparent"
                border.width: 1
                border.color: editMA.pressed ? "#1565c0" : root.clrBtnBorder

                Image {
                    anchors.centerIn: parent
                    width: root.szI; height: root.szI
                    sourceSize.width: root.szIS; sourceSize.height: root.szIS
                    source: "../conversational_qml/icons/edit_icon.svg"
                    fillMode: Image.PreserveAspectFit; smooth: true
                }
                MouseArea {
                    id: editMA; anchors.fill: parent
                    onClicked: root.editRequested(root.toolData)
                }
            }

            // Delete
            Rectangle {
                implicitWidth: root.szBtn; implicitHeight: root.szBtn; radius: root.szR
                color:        delMA.pressed ? root.clrDelHover  : "transparent"
                border.width: 1
                border.color: delMA.pressed ? root.clrDelBorder : root.clrBtnBorder
                enabled: toolData ? !toolData.isCurrent : false
                opacity: enabled ? 1.0 : 0.35

                Image {
                    anchors.centerIn: parent
                    width: root.szI; height: root.szI
                    sourceSize.width: root.szIS; sourceSize.height: root.szIS
                    source: "../conversational_qml/icons/delete_icon.svg"
                    fillMode: Image.PreserveAspectFit; smooth: true
                }
                MouseArea {
                    id: delMA; anchors.fill: parent; enabled: parent.enabled
                    onClicked: root.deleteRequested(root.toolData.t)
                }
            }
        }
    }
}
