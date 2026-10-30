// FinalProfileView.qml — a G-code file's stock and the part it makes of it
// (ProgramsViewModel.finalProfile), each in a box of its own, the two boxes as
// high as each other: Initial Stock above - the stock as its program's header
// has it - and Finished Part below - what is left of it once all of the
// program has run. Each is drawn solid on both sides of a centre line of its
// own, as the backplot draws the material left; one scale for both, and Z0 -
// where each starts - at the same x in both, fitted so that both fit. The
// centre lines and the Z0 lines are as the profile canvases draw them.
// Between the two, a bar of its own: what the program is - its operations,
// its tool changes, and about how long it runs - and the Simulate button.
import QtQuick
import QtQuick.Layouts
import common
import tabs.conversational
import theme

Item {
    id: root

    // {state: "none" | "loading" | "ready" | "empty", message, rings, stock}:
    // rings and stock [[[z, r], ...], ...]
    property var profile: ({ state: "none", message: "", rings: [], stock: [] })
    property bool simulateEnabled: false

    signal simulateRequested()

    readonly property var stockRings: profile && profile.stock ? profile.stock : []
    readonly property var partRings: profile && profile.state === "ready" ? (profile.rings || []) : []

    // as the backplot's material left and its outline (backplot palette MATERIAL, STOCK)
    readonly property color materialColor: "#c8cdd5"
    readonly property color outlineColor: "#9ca3af"
    // as CenterLineActor.qml and AxesActor.qml's zero line
    readonly property color centreLineColor: Theme.success
    readonly property color zeroLineColor: Theme.accentStrong
    readonly property var dashPattern: [16, 4, 3, 4]
    // of a box's drawing area, round what is drawn in it
    readonly property real fitMargin: 0.12
    // mm an edge lies along the axis within: not outlined - a solid part is
    // solid to centre
    readonly property real onAxis: 0.001
    // between the boxes, as between the screen's panes
    readonly property real boxGap: 6
    // the bar between the drawings: as high as the Programs screen's bars
    readonly property real barHeight: Theme.barHeight

    // what the program is, once it has been read (ProgramsViewModel.finalProfile)
    readonly property var summary: profile ? profile.summary : null

    // 45s, 2m30s, 1h05m
    function duration(seconds) {
        var s = Math.max(0, Math.round(seconds))
        if (s < 60) return s + "s"
        if (s < 3600) return Math.floor(s / 60) + "m" + (s % 60 < 10 ? "0" : "") + (s % 60) + "s"
        var m = Math.floor(s / 60) % 60
        return Math.floor(s / 3600) + "h" + (m < 10 ? "0" : "") + m + "m"
    }

    // One scale for both drawings, in a drawing area ``w`` x ``h`` - the two
    // boxes' are the same - and Z0 at one x: px per mm, the x of Z0 and the
    // y of the centre line.
    function fit(w, h) {
        var zMin = 0, zMax = 0, rMax = 0     // Z0 always in view: the program is set from it
        var drawings = [root.stockRings, root.partRings]
        for (var d = 0; d < drawings.length; d++)
            for (var i = 0; i < drawings[d].length; i++)
                for (var j = 0; j < drawings[d][i].length; j++) {
                    var p = drawings[d][i][j]
                    zMin = Math.min(zMin, p[0]); zMax = Math.max(zMax, p[0]); rMax = Math.max(rMax, p[1])
                }
        var spanZ = Math.max(zMax - zMin, 1), spanX = Math.max(2 * rMax, 1)
        var usable = 1 - 2 * root.fitMargin
        var scale = Math.min(w * usable / spanZ, h * usable / spanX)
        return { scale: scale, x0: w / 2 - (zMin + zMax) / 2 * scale, y0: h / 2 }
    }

    // A box: its title over the drawing of ``rings``, or ``message`` with none.
    component ProfileBox: Rectangle {
        id: box

        property string title: ""
        property var rings: []
        property string message: ""
        property color messageColor: Theme.foregroundMuted

        color: Theme.surface
        radius: Theme.radius
        border.color: Theme.outline
        border.width: Theme.hairline
        clip: true

        onRingsChanged: canvas.requestPaint()

        Text {
            id: titleText
            anchors.top: parent.top
            anchors.topMargin: Theme.spacingSmall
            anchors.horizontalCenter: parent.horizontalCenter
            text: box.title
            color: Theme.foreground
            font.pixelSize: Theme.fontBody
            font.bold: true
        }

        Canvas {
            id: canvas
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: titleText.bottom
            anchors.bottom: parent.bottom
            anchors.margins: 1
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()

            Connections {
                // the scale is both drawings': the other one changing moves this one
                target: root
                function onProfileChanged() { canvas.requestPaint() }
            }

            function path(ctx, rings, f, side) {
                ctx.beginPath()
                for (var i = 0; i < rings.length; i++) {
                    var ring = rings[i]
                    for (var j = 0; j < ring.length; j++) {
                        var x = f.x0 + ring[j][0] * f.scale, y = f.y0 + side * ring[j][1] * f.scale
                        if (j === 0) ctx.moveTo(x, y)
                        else ctx.lineTo(x, y)
                    }
                    ctx.closePath()
                }
            }

            function outline(ctx, rings, f, side) {
                ctx.beginPath()
                for (var i = 0; i < rings.length; i++) {
                    var ring = rings[i]
                    for (var j = 0; j < ring.length; j++) {
                        var a = ring[j], b = ring[(j + 1) % ring.length]
                        if (Math.abs(a[1]) < root.onAxis && Math.abs(b[1]) < root.onAxis)
                            continue
                        ctx.moveTo(f.x0 + a[0] * f.scale, f.y0 + side * a[1] * f.scale)
                        ctx.lineTo(f.x0 + b[0] * f.scale, f.y0 + side * b[1] * f.scale)
                    }
                }
                ctx.stroke()
            }

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var rings = box.rings || []
                if (!rings.length)
                    return
                var f = root.fit(width, height)

                // solid, below the centre line and mirrored above it
                ctx.fillStyle = root.materialColor
                ctx.fillRule = Qt.OddEvenFill
                for (var side = -1; side <= 1; side += 2) {
                    path(ctx, rings, f, side)
                    ctx.fill()
                }
                ctx.strokeStyle = root.outlineColor
                ctx.lineWidth = 1
                outline(ctx, rings, f, 1)
                outline(ctx, rings, f, -1)

                // the centre line, and the Z0 line across it
                ctx.setLineDash(root.dashPattern)
                ctx.strokeStyle = root.centreLineColor
                ctx.lineWidth = 1.5
                ctx.beginPath()
                ctx.moveTo(0, f.y0)
                ctx.lineTo(width, f.y0)
                ctx.stroke()
                ctx.strokeStyle = root.zeroLineColor
                ctx.lineWidth = 0.8
                ctx.beginPath()
                ctx.moveTo(f.x0, 0)
                ctx.lineTo(f.x0, height)
                ctx.stroke()
                ctx.setLineDash([])
            }
        }

        Text {
            anchors.centerIn: canvas
            width: parent.width - 2 * Theme.spacingLarge
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            visible: text !== "" && !(box.rings || []).length
            text: box.message
            color: box.messageColor
            font.pixelSize: Theme.fontBody
        }
    }

    ProfileBox {
        id: stockBox
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: (root.height - root.barHeight - 2 * root.boxGap) / 2
        title: "Initial Stock"
        rings: root.stockRings
        message: root.profile && root.profile.state !== "none" ? "No stock in the program's header" : ""
    }

    // between the boxes: what the program is, and the Simulate button
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        y: stockBox.height + root.boxGap
        height: root.barHeight
        color: Theme.surfaceSunken
        radius: Theme.radius
        border.color: Theme.outline
        border.width: Theme.hairline

        // the counts: a table no one sees - the numbers right aligned in a
        // column two digits wide, what they count left aligned beside them.
        // No operations for a file not made by the conversational editor.
        GridLayout {
            anchors.left: parent.left
            anchors.leftMargin: Theme.spacingSmall
            anchors.verticalCenter: parent.verticalCenter
            visible: !!root.summary
            columns: 2
            columnSpacing: Theme.spacingSmall
            rowSpacing: 0

            Text {
                visible: !!root.summary && root.summary.operations > 0
                Layout.preferredWidth: twoDigits.width
                horizontalAlignment: Text.AlignRight
                text: root.summary ? root.summary.operations : ""
                color: Theme.foreground
                font.pixelSize: Theme.fontBody
                font.bold: true
            }
            Text {
                visible: !!root.summary && root.summary.operations > 0
                text: root.summary && root.summary.operations === 1 ? "Operation" : "Operations"
                color: Theme.foreground
                font.pixelSize: Theme.fontBody
            }
            Text {
                Layout.preferredWidth: twoDigits.width
                horizontalAlignment: Text.AlignRight
                text: root.summary ? root.summary.toolChanges : ""
                color: Theme.foreground
                font.pixelSize: Theme.fontBody
                font.bold: true
            }
            Text {
                text: root.summary && root.summary.toolChanges === 1 ? "Tool change" : "Tool changes"
                color: Theme.foreground
                font.pixelSize: Theme.fontBody
            }
        }
        TextMetrics {
            id: twoDigits
            text: "00"
            font.pixelSize: Theme.fontBody
            font.bold: true
        }

        // about how long it runs, about the middle: LinuxCNC's estimate - none
        // for a program it could not time
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            visible: !!root.summary && root.summary.duration >= 0
            spacing: 2

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Estimated"
                color: Theme.foregroundMuted
                font.pixelSize: Theme.fontBody
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                // icon to text as in the Simulate button (OperationIconTextButton)
                spacing: 6

                // the hourglass as high as the duration's text, the margin
                // its SVG has round it (74% of it the drawing) on top
                Image {
                    anchors.verticalCenter: parent.verticalCenter
                    source: Images.url("duration.svg")
                    width: durationText.font.pixelSize / 0.74
                    height: width
                    sourceSize.width: 2 * width
                    sourceSize.height: 2 * height
                    fillMode: Image.PreserveAspectFit
                }
                Text {
                    id: durationText
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.summary ? root.duration(root.summary.duration) : ""
                    color: Theme.foreground
                    font.pixelSize: Theme.fontBody
                    font.bold: true
                }
            }
        }

        // while the program is read
        Text {
            anchors.left: parent.left
            anchors.leftMargin: Theme.spacingLarge
            anchors.verticalCenter: parent.verticalCenter
            visible: !root.summary && !!root.profile && root.profile.state === "loading"
            text: "Reading the program…"
            color: Theme.foregroundMuted
            font.pixelSize: Theme.fontBody
        }

        // the secondary button, as the operation list's Add New
        OperationIconTextButton {
            id: simulateButton
            anchors.right: parent.right
            anchors.rightMargin: Theme.spacingLarge
            anchors.verticalCenter: parent.verticalCenter
            iconSource: Images.url("simulate.svg")
            text: "Simulate"
            tint: Theme.success
            color: Theme.surface
            buttonHeight: Theme.buttonHeight
            iconSize: 28
            fontPixelSize: 15
            enabled: root.simulateEnabled
            onClicked: root.simulateRequested()
        }
    }

    ProfileBox {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: stockBox.height
        title: "Finished Part"
        rings: root.partRings
        message: {
            var p = root.profile || {}
            if (p.state === "loading") return "Working out the part…"
            if (p.state === "empty") return p.message
            if (p.state === "none") return "Select a G-code program"
            return ""
        }

        // the interpreter stopped short: the part is what it read up to there
        Text {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: Theme.spacing
            wrapMode: Text.Wrap
            visible: root.profile && root.profile.state === "ready" && root.profile.message !== ""
            text: root.profile ? root.profile.message : ""
            color: Theme.danger
            font.pixelSize: Theme.fontSmall
        }
    }
}
