import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#787878"

    readonly property color clrCardBg: "white"
    readonly property color clrCardBgSel: "#dbeafe"
    readonly property color clrBorder: "#cccccc"
    readonly property color clrBorderSel: "#3b82f6"
    readonly property color clrSeparator: "#d0d0d0"
    readonly property color clrBtnBorder: "#BDBDBD"
    readonly property color clrDeleteHover: "#ffebee"
    readonly property color clrDeleteBorder: "#C62828"

    readonly property int szCardRadius: 4
    readonly property int szMargin: 12
    readonly property int szSpacing: 8
    readonly property int szFont: 14
    readonly property int szBtn: 40
    readonly property int szBtnIcon: 28
    readonly property int szBtnIconSrc: 112

    property int rowWidth: 800

    function orientAngle(value) {
        if (value === 1) return 315
        if (value === 2) return 225
        if (value === 3) return 135
        if (value === 4) return 45
        if (value === 5) return 0
        if (value === 6) return -90
        if (value === 7) return 180
        if (value === 8) return 90
        return 0
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn
        ScrollBar.vertical.width: 16

        ListView {
            id: listView
            width: parent.width
            height: parent.height
            spacing: 5
            model: toolsProvider ? toolsProvider.tools : []
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                id: card
                width: Math.min(root.rowWidth, listView.width - 2)
                height: contentRow.implicitHeight + root.szMargin * 2
                radius: root.szCardRadius
                color: modelData.isCurrent ? root.clrCardBgSel : root.clrCardBg
                border.color: modelData.isCurrent ? root.clrBorderSel : root.clrBorder
                border.width: modelData.isCurrent ? 2 : 1

                anchors.horizontalCenter: parent.horizontalCenter

                MouseArea {
                    anchors.fill: parent
                    onClicked: toolsProvider.loadTool(modelData.t)
                }

                RowLayout {
                    id: contentRow
                    anchors { left: parent.left; right: parent.right; top: parent.top; bottom: parent.bottom; margins: root.szMargin }
                    spacing: root.szSpacing

                    ColumnLayout {
                        Layout.preferredWidth: 37
                        Layout.alignment: Qt.AlignVCenter

                        Text {
                            text: "T" + modelData.t
                            font.pixelSize: 18
                            font.bold: true
                        }
                    }

                    Rectangle { width: 1; Layout.fillHeight: true; color: root.clrSeparator }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        RowLayout {
                            spacing: 12
                            Layout.fillWidth: true

                            ColumnLayout {
                                spacing: 4
                                Layout.preferredWidth: 140

                                GridLayout {
                                    columns: 2
                                    rowSpacing: 4
                                    columnSpacing: 12
                                    Layout.fillWidth: true

                                    Text { text: "X Offset:"; font.pixelSize: root.szFont; horizontalAlignment: Text.AlignLeft; Layout.fillWidth: true }
                                    Text { text: Number(modelData.x).toFixed(3); font.pixelSize: root.szFont; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }

                                    Text { text: "Z Offset:"; font.pixelSize: root.szFont; horizontalAlignment: Text.AlignLeft; Layout.fillWidth: true }
                                    Text { text: Number(modelData.z).toFixed(3); font.pixelSize: root.szFont; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                                }
                            }

                            Rectangle { width: 1; Layout.fillHeight: true; color: root.clrSeparator }

                            ColumnLayout {
                                spacing: 4
                                Layout.preferredWidth: 170

                                GridLayout {
                                    columns: 2
                                    rowSpacing: 4
                                    columnSpacing: 12
                                    Layout.fillWidth: true

                                    Text { text: "Tip Radius:"; font.pixelSize: root.szFont; horizontalAlignment: Text.AlignLeft; Layout.fillWidth: true }
                                    Text { text: Number(modelData.d).toFixed(1); font.pixelSize: root.szFont; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }

                                    Text { text: "Orientation:"; font.pixelSize: root.szFont; horizontalAlignment: Text.AlignLeft; Layout.fillWidth: true }
                                    Item {
                                        Layout.fillWidth: true
                                        height: 20

                                        Row {
                                            anchors.right: parent.right
                                            spacing: 6

                                            Canvas {
                                                width: 20
                                                height: 20

                                                onPaint: {
                                                    var ctx = getContext("2d")
                                                    ctx.reset()
                                                    ctx.clearRect(0, 0, width, height)

                                                    var value = parseInt(modelData.q)
                                                    var color = "#000000"
                                                    ctx.strokeStyle = color
                                                    ctx.fillStyle = color
                                                    ctx.lineWidth = 2

                                                    if (value === 9) {
                                                        ctx.beginPath()
                                                        ctx.arc(width/2, height/2, 4, 0, Math.PI*2, false)
                                                        ctx.fill()
                                                    } else {
                                                        ctx.save()
                                                        ctx.translate(width/2, height/2)
                                                        ctx.rotate(orientAngle(value) * Math.PI / 180)
                                                        ctx.translate(-width/2, -height/2)

                                                        var startX = width/2 - 6
                                                        var endX = width/2 + 6
                                                        var centerY = height/2

                                                        ctx.beginPath()
                                                        ctx.moveTo(startX, centerY)
                                                        ctx.lineTo(endX, centerY)
                                                        ctx.stroke()

                                                        ctx.beginPath()
                                                        ctx.moveTo(endX, centerY)
                                                        ctx.lineTo(endX - 3, centerY - 3)
                                                        ctx.lineTo(endX - 3, centerY + 3)
                                                        ctx.closePath()
                                                        ctx.fill()

                                                        ctx.restore()
                                                    }
                                                }
                                            }

                                            Text { text: String(modelData.q); font.pixelSize: root.szFont }
                                        }
                                    }
                                }
                            }

                            Rectangle { width: 1; Layout.fillHeight: true; color: root.clrSeparator }

                            ColumnLayout {
                                spacing: 4
                                Layout.preferredWidth: 140

                                GridLayout {
                                    columns: 2
                                    rowSpacing: 4
                                    columnSpacing: 12
                                    Layout.fillWidth: true

                                    Text { text: "FrontAngle:"; font.pixelSize: root.szFont; horizontalAlignment: Text.AlignLeft; Layout.fillWidth: true }
                                    Text { text: Math.round(modelData.i) + "°"; font.pixelSize: root.szFont; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }

                                    Text { text: "BackAngle:"; font.pixelSize: root.szFont; horizontalAlignment: Text.AlignLeft; Layout.fillWidth: true }
                                    Text { text: Math.round(modelData.j) + "°"; font.pixelSize: root.szFont; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: root.clrSeparator
                        }

                        Text {
                            text: modelData.r
                            font.pixelSize: root.szFont + 1
                            font.bold: true
                            font.italic: true
                            color: "#000000"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle {
                        width: 1
                        Layout.fillHeight: true
                        color: root.clrSeparator
                    }

                    RowLayout {
                        spacing: 18
                        Layout.alignment: Qt.AlignVCenter

                        Rectangle {
                            implicitWidth: root.szBtn
                            implicitHeight: root.szBtn
                            radius: root.szCardRadius
                            color: "transparent"
                            border.width: 1
                            border.color: root.clrBtnBorder
                            opacity: 0.4

                            Image {
                                anchors.centerIn: parent
                                width: root.szBtnIcon
                                height: root.szBtnIcon
                                sourceSize.width: root.szBtnIconSrc
                                sourceSize.height: root.szBtnIconSrc
                                source: "conversational_qml/icons/edit_icon.svg"
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }
                        }

                        Rectangle {
                            id: deleteBtn
                            implicitWidth: root.szBtn
                            implicitHeight: root.szBtn
                            radius: root.szCardRadius
                            color: deleteMA.pressed ? root.clrDeleteHover : "transparent"
                            border.width: 1
                            border.color: deleteMA.pressed ? root.clrDeleteBorder : root.clrBtnBorder
                            enabled: !modelData.isCurrent
                            opacity: enabled ? 1.0 : 0.35

                            Image {
                                anchors.centerIn: parent
                                width: root.szBtnIcon
                                height: root.szBtnIcon
                                sourceSize.width: root.szBtnIconSrc
                                sourceSize.height: root.szBtnIconSrc
                                source: "conversational_qml/icons/delete_icon.svg"
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }

                            MouseArea {
                                id: deleteMA
                                anchors.fill: parent
                                enabled: parent.enabled
                                onClicked: {
                                    deleteDialog.toolNo = modelData.t
                                    deleteDialog.open()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteDialog
        modal: true
        title: "Confirm Delete"
        standardButtons: Dialog.Yes | Dialog.No
        property int toolNo: -1
        onAccepted: {
            if (toolNo >= 0) {
                toolsProvider.deleteTool(toolNo)
            }
        }
        contentItem: Text {
            text: toolNo >= 0 ? "Delete tool T" + toolNo + "?" : "Delete tool?"
            wrapMode: Text.WordWrap
            padding: 16
        }
    }
}
