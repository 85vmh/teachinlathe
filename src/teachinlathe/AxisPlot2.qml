import QtQuick 2.15
import QtQuick.Window 2.15

Window {
    visible: true
    width: 900
    height: 450
    title: qsTr("Lathe Axes Plot V2")

    property int pixelsPerMm: 2
    property int plotWidthMm: 700
    property int plotHeightMm: 300

    // Derived pixel sizes
    property int plotWidthPx: plotWidthMm * pixelsPerMm
    property int plotHeightPx: plotHeightMm * pixelsPerMm
    property int halfHeightPx: plotHeightPx / 2

    // Limits
    property int machineLimitLeftMm: 76
    property int machineLimitRightMm: 622
    property int machineLimitLeftPx: machineLimitLeftMm * pixelsPerMm
    property int machineLimitRightPx: machineLimitRightMm * pixelsPerMm

    property int toolLimitYPositiveMm: 115
    property int toolLimitYPositivePx: toolLimitYPositiveMm * pixelsPerMm

    property int toolLimitXPositiveMm: 150
    property int toolLimitXPositivePx: toolLimitXPositiveMm * pixelsPerMm

    // Colors
    property color redColor: "#FF0000"
    property color orangeColor: "#FF7F00"
    property color greenColor: "#008000"
    property color blackColor: "#000000"
    property color grayColor: "#BBBBBB"
    property color lightGrayColor: "#DCDCDC"

    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.clearRect(0, 0, width, height)

            // Translate origin and scale for margins
            // Leave 40px margin left and right, and 40 top and bottom for labels/boxes
            ctx.translate(40, 40)

            // Draw white background
            ctx.fillStyle = "white"
            ctx.fillRect(0, 0, plotWidthPx, plotHeightPx)

            // Draw green border rectangle (including labels margin)
            ctx.strokeStyle = greenColor
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(-40, -40)
            ctx.lineTo(plotWidthPx + 40, -40)
            ctx.lineTo(plotWidthPx + 40, plotHeightPx + 40)
            ctx.lineTo(-40, plotHeightPx + 40)
            ctx.closePath()
            ctx.stroke()

            // Helper function for drawing hashed rectangle
            function drawHatchedRect(x, y, w, h, angleUp) {
                ctx.save()
                ctx.beginPath()
                ctx.rect(x, y, w, h)
                ctx.clip()
                ctx.lineWidth = 0.7
                ctx.strokeStyle = lightGrayColor
                ctx.globalAlpha = 0.2
                var spacing = 7
                var maxLength = Math.sqrt(w*w + h*h)*2
                ctx.beginPath()
                if (angleUp) {
                    for (var i = -maxLength; i < maxLength; i += spacing) {
                        ctx.moveTo(x + i, y + h)
                        ctx.lineTo(x + i + maxLength, y + h - maxLength)
                    }
                } else {
                    for (var i = -maxLength; i < maxLength; i += spacing) {
                        ctx.moveTo(x + i, y)
                        ctx.lineTo(x + i + maxLength, y + maxLength)
                    }
                }
                ctx.stroke()
                ctx.restore()
            }

            // Draw hashed inactive areas
            // Left inactive area (x:0 to machineLimitLeftPx)
            drawHatchedRect(0, 0, machineLimitLeftPx, halfHeightPx, true)
            drawHatchedRect(0, halfHeightPx, machineLimitLeftPx, plotHeightPx - halfHeightPx, false)

            // Right inactive area (x:machineLimitRightPx to plotWidthPx)
            drawHatchedRect(machineLimitRightPx, 0, plotWidthPx - machineLimitRightPx, halfHeightPx, true)
            drawHatchedRect(machineLimitRightPx, halfHeightPx, plotWidthPx - machineLimitRightPx, plotHeightPx - halfHeightPx, false)

            // Top inactive (above toolLimitYPositivePx)
            drawHatchedRect(machineLimitLeftPx, halfHeightPx + toolLimitYPositivePx, machineLimitRightPx - machineLimitLeftPx, plotHeightPx - (halfHeightPx + toolLimitYPositivePx), false)

            // Bottom inactive (below toolLimitYPositivePx)
            drawHatchedRect(machineLimitLeftPx, 0, machineLimitRightPx - machineLimitLeftPx, halfHeightPx - toolLimitYPositivePx, true)

            // Draw machine limits (red lines)
            ctx.strokeStyle = redColor
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(machineLimitLeftPx, 0)
            ctx.lineTo(machineLimitLeftPx, plotHeightPx)
            ctx.moveTo(machineLimitRightPx, 0)
            ctx.lineTo(machineLimitRightPx, plotHeightPx)
            ctx.stroke()

            // Draw machine limits boxes outside green border
            function drawBox(x, y, text, color, above) {
                var boxW = 50
                var boxH = 24
                ctx.fillStyle = "white"
                ctx.strokeStyle = color
                ctx.lineWidth = 1.5
                ctx.beginPath()
                if (above) {
                    ctx.rect(x - boxW/2, y, boxW, boxH)
                } else {
                    ctx.rect(x - boxW/2, y - boxH, boxW, boxH)
                }
                ctx.fill()
                ctx.stroke()
                ctx.fillStyle = color
                ctx.font = "bold 10px sans-serif"
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                if (above) ctx.fillText(text, x, y + boxH/2)
                else ctx.fillText(text, x, y - boxH/2)
            }
            drawBox(machineLimitLeftPx, -40, machineLimitLeftMm.toString(), redColor, false)
            drawBox(machineLimitLeftPx, plotHeightPx + 40, machineLimitLeftMm.toString(), redColor, true)
            drawBox(machineLimitRightPx, -40, machineLimitRightMm.toString(), redColor, false)
            drawBox(machineLimitRightPx, plotHeightPx + 40, machineLimitRightMm.toString(), redColor, true)

            // Draw center zero line with dash pattern
            ctx.strokeStyle = lightGrayColor
            ctx.lineWidth = 1
            ctx.setLineDash([3,3,6,6,3,3,3,3,6,6])
            ctx.beginPath()
            ctx.moveTo(0, halfHeightPx)
            ctx.lineTo(plotWidthPx, halfHeightPx)
            ctx.stroke()
            ctx.setLineDash([])

            // Draw tool limits horizontal dashed lines (orange)
            ctx.strokeStyle = orangeColor
            ctx.lineWidth = 1
            ctx.setLineDash([4,2,4,6])
            ctx.beginPath()
            ctx.moveTo(-40, halfHeightPx + toolLimitYPositivePx)
            ctx.lineTo(plotWidthPx + 40, halfHeightPx + toolLimitYPositivePx)
            ctx.moveTo(-40, halfHeightPx - toolLimitYPositivePx)
            ctx.lineTo(plotWidthPx + 40, halfHeightPx - toolLimitYPositivePx)
            ctx.stroke()
            ctx.setLineDash([])

            // Draw tool limit vertical line x=150mm (orange dashed)
            ctx.setLineDash([4,2,4,6])
            ctx.beginPath()
            ctx.moveTo(toolLimitXPositivePx, -40)
            ctx.lineTo(toolLimitXPositivePx, plotHeightPx + 40)
            ctx.stroke()
            ctx.setLineDash([])

            // Draw tool limit boxes outside chart (orange)
            function drawToolBox(x, y, text, above) {
                var boxW = 40
                var boxH = 24
                ctx.fillStyle = "white"
                ctx.strokeStyle = orangeColor
                ctx.lineWidth = 1.5
                ctx.beginPath()
                if (above) {
                    ctx.rect(x, y, boxW, boxH)
                } else {
                    ctx.rect(x, y - boxH, boxW, boxH)
                }
                ctx.fill()
                ctx.stroke()
                ctx.fillStyle = orangeColor
                ctx.font = "bold 10px sans-serif"
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                if (above) ctx.fillText(text, x + boxW/2, y + boxH/2)
                else ctx.fillText(text, x + boxW/2, y - boxH/2)
            }
            drawToolBox(plotWidthPx+45, halfHeightPx + toolLimitYPositivePx - 12, toolLimitYPositiveMm.toString(), true)
            drawToolBox(-85, halfHeightPx + toolLimitYPositivePx - 12, toolLimitYPositiveMm.toString(), true)
            drawToolBox(plotWidthPx+45, halfHeightPx - toolLimitYPositivePx - 12, toolLimitYPositiveMm.toString(), false)
            drawToolBox(-85, halfHeightPx - toolLimitYPositivePx - 12, toolLimitYPositiveMm.toString(), false)

            // Draw solid orange boxes inside chart with white text
            function drawSolidBox(x, y, text) {
                var boxW = 90
                var boxH = 30
                ctx.fillStyle = orangeColor
                ctx.strokeStyle = orangeColor
                ctx.lineWidth = 1
                ctx.beginPath()
                ctx.roundRect(x - boxW/2, y - boxH/2, boxW, boxH, 6)
                ctx.fill()
                ctx.stroke()
                ctx.fillStyle = "white"
                ctx.font = "bold 14px sans-serif"
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                ctx.fillText(text, x, y)
            }
            drawSolidBox((machineLimitLeftPx + machineLimitRightPx)/2, halfHeightPx + toolLimitYPositivePx, "200.231")
            drawSolidBox((machineLimitLeftPx + machineLimitRightPx)/2, halfHeightPx - toolLimitYPositivePx, "200.231")

            // Draw X axis ticks and labels
            ctx.fillStyle = blackColor
            ctx.strokeStyle = blackColor
            ctx.lineWidth = 1
            for (var x=0; x <= plotWidthPx; x += grid_size_mm * pixelsPerMm) {
                var active = (x >= machineLimitLeftPx && x <= machineLimitRightPx)
                var color = active ? blackColor : grayColor
                var length = 5
                if (x % (100 * pixelsPerMm) == 0) {
                    length = 15
                    var label = (x / (100 * pixelsPerMm)) * 100
                    ctx.fillStyle = color
                    ctx.textAlign = "center"
                    ctx.textBaseline = "top"
                    ctx.font = "8px sans-serif"
                    ctx.fillText(label.toString(), x, plotHeightPx + 10)
                    ctx.textBaseline = "bottom"
                    ctx.fillText(label.toString(), x, -10)
                } else if (x % (50 * pixelsPerMm) == 0) {
                    length = 10
                }
                ctx.strokeStyle = color
                ctx.beginPath()
                ctx.moveTo(x, 0)
                ctx.lineTo(x, length)
                ctx.moveTo(x, plotHeightPx)
                ctx.lineTo(x, plotHeightPx - length)
                ctx.stroke()
            }

            // Draw Y axis ticks and labels
            for (var y = 0; y <= halfHeightPx; y += grid_size_mm * pixelsPerMm) {
                var active_pos = (y >= halfHeightPx - toolLimitYPositivePx) && (y <= halfHeightPx + toolLimitYPositivePx)
                var color_pos = active_pos ? blackColor : grayColor
                var active_neg = active_pos // symmetrical for negative
                var color_neg = color_pos
                var length_pos = 5
                var length_neg = 5
                if (y % (50 * pixelsPerMm) == 0 || y == 0) {
                    length_pos = 15
                    length_neg = 15
                    var label_pos = Math.abs((y - halfHeightPx) / pixelsPerMm)
                    var label_neg = label_pos
                    ctx.fillStyle = color_pos
                    ctx.textAlign = "right"
                    ctx.textBaseline = "middle"
                    ctx.font = "8px sans-serif"
                    ctx.fillText(label_pos.toString(), -10, y)
                    ctx.fillText(label_neg.toString(), -10, 2*halfHeightPx - y)
                    ctx.textAlign = "left"
                    ctx.fillText(label_pos.toString(), plotWidthPx + 10, y)
                    ctx.fillText(label_neg.toString(), plotWidthPx + 10, 2*halfHeightPx - y)
                }
                ctx.strokeStyle = color_pos
                ctx.beginPath()
                ctx.moveTo(0, y)
                ctx.lineTo(length_pos, y)
                ctx.moveTo(plotWidthPx, y)
                ctx.lineTo(plotWidthPx - length_pos, y)
                ctx.stroke()
                ctx.strokeStyle = color_neg
                ctx.beginPath()
                ctx.moveTo(0, 2*halfHeightPx - y)
                ctx.lineTo(length_neg, 2*halfHeightPx - y)
                ctx.moveTo(plotWidthPx, 2*halfHeightPx - y)
                ctx.lineTo(plotWidthPx - length_neg, 2*halfHeightPx - y)
                ctx.stroke()

            }

            // Draw zero labels on Y axis
            ctx.fillStyle = blackColor
            ctx.font = "8px sans-serif"
            ctx.textAlign = "right"
            ctx.textBaseline = "middle"
            ctx.fillText("0", -10, halfHeightPx)
            ctx.textAlign = "left"
            ctx.fillText("0", plotWidthPx + 10, halfHeightPx)
        }
    }
}
