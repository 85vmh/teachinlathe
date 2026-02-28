import QtQuick 2.12
import QtQuick.Controls 2.5

Rectangle {
    id: root
    color: "#787878"

    property int rowHeight: 60
    property int headerHeight: 36
    property int colT: 32
    property int colXZ: 120
    property int colD: 60
    property int colQ: 70
    property int colIJ: 120
    property int colSpacing: 6
    property int sidePadding: 8
    property color separatorColor: "#bcbcbc"

    function colR() {
        var used = colT + colXZ + colD + colQ + colIJ + sidePadding * 2 + colSpacing * 5
        return Math.max(120, root.width - used)
    }

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

    Column {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: header
            height: root.headerHeight
            width: parent.width
            color: "#dcdcdc"

            Row {
                anchors.fill: parent
                anchors.leftMargin: root.sidePadding
                anchors.rightMargin: root.sidePadding
                spacing: root.colSpacing

                Text { text: "T"; width: root.colT; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Noto"; font.pointSize: 11; color: "#000000" }
                Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                Text { text: "Offsets"; width: root.colXZ; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Noto"; font.pointSize: 11; color: "#000000" }
                Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                Text { text: "Radius"; width: root.colD; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Noto"; font.pointSize: 11; color: "#000000" }
                Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                Text { text: "Orient"; width: root.colQ; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Noto"; font.pointSize: 11; color: "#000000" }
                Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                Text { text: "Tip Angle"; width: root.colIJ; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Noto"; font.pointSize: 11; color: "#000000" }
                Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                Text { text: "Description"; width: root.colR(); horizontalAlignment: Text.AlignLeft; verticalAlignment: Text.AlignVCenter; font.family: "Noto"; font.pointSize: 11; color: "#000000" }
            }
        }

        ScrollView {
            id: listContainer
            width: parent.width
            height: parent.height - header.height
            clip: true

            ScrollBar.vertical.policy: ScrollBar.AlwaysOn
            ScrollBar.vertical.width: 16

            ListView {
                id: listView
                model: toolsProvider ? toolsProvider.tools : []
                boundsBehavior: Flickable.StopAtBounds
                clip: true
                spacing: 0

                delegate: Rectangle {
                    width: listView.width
                    height: root.rowHeight
                    color: (index % 2 === 0) ? "#787878" : "#5a5a5a"

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: root.sidePadding
                        anchors.rightMargin: root.sidePadding
                        spacing: root.colSpacing

                        Text {
                            text: modelData.t
                            width: root.colT
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.family: "Noto Sans Mono"
                            font.pointSize: 11
                            font.bold: modelData.isCurrent
                            color: modelData.isCurrent ? "#006400" : "#ffffff"
                        }
                        Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                        Text {
                            text: modelData.xz
                            width: root.colXZ
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                            font.family: "Noto Sans Mono"
                            font.pointSize: 10
                            color: modelData.isCurrent ? "#006400" : "#ffffff"
                        }
                        Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                        Text {
                            text: modelData.d
                            width: root.colD
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.family: "Noto Sans Mono"
                            font.pointSize: 11
                            color: modelData.isCurrent ? "#006400" : "#ffffff"
                        }
                        Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                        Item {
                            width: root.colQ
                            height: parent.height

                            Canvas {
                                id: orientCanvas
                                anchors.left: parent.left
                                anchors.leftMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                width: 28
                                height: 28

                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.reset()
                                    ctx.clearRect(0, 0, width, height)

                                    var value = parseInt(modelData.q)
                                    var color = modelData.isCurrent ? "#006400" : "#ffffff"
                                    ctx.strokeStyle = color
                                    ctx.fillStyle = color
                                    ctx.lineWidth = 2

                                    if (value === 9) {
                                        ctx.beginPath()
                                        ctx.arc(width/2, height/2, 5, 0, Math.PI*2, false)
                                        ctx.fill()
                                    } else {
                                        ctx.save()
                                        ctx.translate(width/2, height/2)
                                        ctx.rotate(orientAngle(value) * Math.PI / 180)
                                        ctx.translate(-width/2, -height/2)

                                        var startX = width/2 - 8
                                        var endX = width/2 + 8
                                        var centerY = height/2

                                        ctx.beginPath()
                                        ctx.moveTo(startX, centerY)
                                        ctx.lineTo(endX, centerY)
                                        ctx.stroke()

                                        ctx.beginPath()
                                        ctx.moveTo(endX, centerY)
                                        ctx.lineTo(endX - 4, centerY - 4)
                                        ctx.lineTo(endX - 4, centerY + 4)
                                        ctx.closePath()
                                        ctx.fill()

                                        ctx.restore()
                                    }
                                }
                            }
                        }
                        Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                        Text {
                            text: modelData.ij
                            width: root.colIJ
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                            font.family: "Noto Sans Mono"
                            font.pointSize: 10
                            color: modelData.isCurrent ? "#006400" : "#ffffff"
                        }
                        Rectangle { width: 1; color: root.separatorColor; anchors.top: parent.top; anchors.bottom: parent.bottom }
                        Text {
                            text: modelData.r
                            width: root.colR()
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                            font.family: "Noto Sans Mono"
                            font.pointSize: 10
                            color: modelData.isCurrent ? "#006400" : "#ffffff"
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
