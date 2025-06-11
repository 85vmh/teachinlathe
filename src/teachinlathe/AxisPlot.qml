import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root
    width: 1100
    height: 600

    property int chart_perimeter_width: 700
    property int chart_perimeter_height: 300
    property int grid_step: 10

    property int chuck_limit: 76
    property int tailstock_limit: 622
    property int tool_x_plus_limit: 115
    property int tool_z_minus_limit: 150

    property real pxPerMm: 2.0
    property real marginLeft: 60
    property real marginRight: 60
    property real marginTop: 60
    property real marginBottom: 60

    Canvas {
        id: canvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.clearRect(0, 0, width, height)

            var chartWidthPx = chart_perimeter_width * pxPerMm
            var chartHeightPx = chart_perimeter_height * pxPerMm
            var originX = marginLeft
            var originY = marginTop + chartHeightPx / 2
            var halfHeightPx = chartHeightPx / 2

            // Background white
            ctx.fillStyle = "white"
            ctx.fillRect(originX, marginTop, chartWidthPx, chartHeightPx)

            // Green perimeter box including margins for labels
            ctx.lineWidth = 2
            ctx.strokeStyle = "green"
            ctx.beginPath()
            ctx.moveTo(originX - marginLeft + 10, marginTop - marginTop + 10)  // top-left outer corner
            ctx.lineTo(originX + chartWidthPx + marginRight - 10, marginTop - marginTop + 10)
            ctx.lineTo(originX + chartWidthPx + marginRight - 10, marginTop + chartHeightPx + marginBottom - 10)
            ctx.lineTo(originX - marginLeft + 10, marginTop + chartHeightPx + marginBottom - 10)
            ctx.closePath()
            ctx.stroke()

            // Draw hashed inactive zones
            function drawHatchedArea(xStart, xEnd, yStart, yEnd, angleUp) {
                ctx.save()
                ctx.beginPath()
                ctx.rect(xStart, yStart, xEnd - xStart, yEnd - yStart)
                ctx.clip()
                ctx.lineWidth = 0.7
                ctx.strokeStyle = "#dcdcdc"
                ctx.globalAlpha = 0.3
                var spacing = 7
                var maxLength = Math.sqrt(Math.pow(xEnd - xStart, 2) + Math.pow(yEnd - yStart, 2)) * 2
                ctx.beginPath()
                if (angleUp) {
                    for (var i = -maxLength; i < maxLength; i += spacing) {
                        ctx.moveTo(xStart + i, yEnd)
                        ctx.lineTo(xStart + i + maxLength, yEnd - maxLength)
                    }
                } else {
                    for (var i = -maxLength; i < maxLength; i += spacing) {
                        ctx.moveTo(xStart + i, yStart)
                        ctx.lineTo(xStart + i + maxLength, yStart + maxLength)
                    }
                }
                ctx.stroke()
                ctx.restore()
            }

            // Left inactive zone
            drawHatchedArea(originX, originX + chuck_limit * pxPerMm, marginTop - 40, originY, true)
            drawHatchedArea(originX, originX + chuck_limit * pxPerMm, originY, marginTop + chartHeightPx + 40, false)

            // Right inactive zone
            drawHatchedArea(originX + tailstock_limit * pxPerMm, originX + chartWidthPx, marginTop - 40, originY, true)
            drawHatchedArea(originX + tailstock_limit * pxPerMm, originX + chartWidthPx, originY, marginTop + chartHeightPx + 40, false)

            // Top inactive zone above tool limit Y+
            drawHatchedArea(originX + chuck_limit * pxPerMm, originX + tailstock_limit * pxPerMm, originY + tool_x_plus_limit * pxPerMm, marginTop + chartHeightPx + 40, false)

            // Bottom inactive zone below tool limit Y-
            drawHatchedArea(originX + chuck_limit * pxPerMm, originX + tailstock_limit * pxPerMm, marginTop - 40, originY - tool_x_plus_limit * pxPerMm, true)

            // Machine limits (solid red lines)
            ctx.strokeStyle = "red"
            ctx.lineWidth = 1
            var machineLimits = [chuck_limit, tailstock_limit];
            for (var i = 0; i < machineLimits.length; i++) {
                var val = machineLimits[i];
                var x = originX + val * pxPerMm;
                ctx.beginPath();
                ctx.moveTo(x, marginTop);
                ctx.lineTo(x, marginTop + chartHeightPx);
                ctx.stroke();
            }

            // Machine limit boxes top and bottom
            function drawRedBox(x, y, text, above) {
                var boxW = 50
                var boxH = 24
                ctx.fillStyle = "white"
                ctx.strokeStyle = "red"
                ctx.lineWidth = 1.5
                if (above)
                    ctx.strokeRect(x - boxW / 2, y - boxH, boxW, boxH)
                else
                    ctx.strokeRect(x - boxW / 2, y, boxW, boxH)
                ctx.fillRect(x - boxW / 2, above ? y - boxH : y, boxW, boxH)
                ctx.fillStyle = "red"
                ctx.font = "bold 12px sans-serif"
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                ctx.fillText(text.toString(), x, above ? y - boxH / 2 : y + boxH / 2)
            }
            drawRedBox(originX + chuck_limit * pxPerMm, marginTop - 10, chuck_limit, true)
            drawRedBox(originX + chuck_limit * pxPerMm, marginTop + chartHeightPx + 10, chuck_limit, false)
            drawRedBox(originX + tailstock_limit * pxPerMm, marginTop - 10, tailstock_limit, true)
            drawRedBox(originX + tailstock_limit * pxPerMm, marginTop + chartHeightPx + 10, tailstock_limit, false)

            // Center zero line (dashed pattern)
            ctx.strokeStyle = "#dcdcdc"
            ctx.lineWidth = 1
            ctx.setLineDash([3,3,6,6,3,3,3,3,6,6])
            ctx.beginPath()
            ctx.moveTo(originX, originY)
            ctx.lineTo(originX + chartWidthPx, originY)
            ctx.stroke()
            ctx.setLineDash([])

            // Tool limits (orange dashed lines)
            ctx.strokeStyle = "#ff7f00"
            ctx.lineWidth = 1
            ctx.setLineDash([4,2,4,6])
            var yUpper = originY + tool_x_plus_limit * pxPerMm
            var yLower = originY - tool_x_plus_limit * pxPerMm

            ctx.beginPath()
            ctx.moveTo(originX - 40, yUpper)
            ctx.lineTo(originX + chartWidthPx + 40, yUpper)
            ctx.moveTo(originX - 40, yLower)
            ctx.lineTo(originX + chartWidthPx + 40, yLower)
            ctx.stroke()

            var toolZ = originX + tool_z_minus_limit * pxPerMm
            ctx.beginPath()
            ctx.moveTo(toolZ, marginTop - 40)
            ctx.lineTo(toolZ, marginTop + chartHeightPx + 40)
            ctx.stroke()
            ctx.setLineDash([])

            // Tool limit boxes (orange)
            function drawOrangeBox(x, y, val) {
                var boxW = 40
                var boxH = 24
                ctx.fillStyle = "white"
                ctx.strokeStyle = "#ff7f00"
                ctx.lineWidth = 1.5
                ctx.fillRect(x - boxW / 2, y - boxH / 2, boxW, boxH)
                ctx.strokeRect(x - boxW / 2, y - boxH / 2, boxW, boxH)
                ctx.fillStyle = "#ff7f00"
                ctx.font = "bold 10px sans-serif"
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                ctx.fillText(val.toString(), x, y)
            }

            var toolLimits = [yUpper, yLower];
            for (var j = 0; j < toolLimits.length; j++) {
                var y = toolLimits[j];
                drawOrangeBox(originX + (chuck_limit + tailstock_limit) / 2 * pxPerMm, y, "200.231");
            }

            // Vertical solid orange box with white text (tool limit on Z)
            var boxWidthBig = 90
            var boxHeightBig = 30
            var boxXVert = toolZ - boxWidthBig / 2
            var boxYVert = originY - boxHeightBig / 2
            ctx.fillStyle = "#ff7f00"
            ctx.strokeStyle = "#ff7f00"
            ctx.fillRect(boxXVert, boxYVert, boxWidthBig, boxHeightBig)
            ctx.strokeRect(boxXVert, boxYVert, boxWidthBig, boxHeightBig)
            ctx.fillStyle = "white"
            ctx.fillText("12.212", boxXVert + boxWidthBig / 2, boxYVert + boxHeightBig / 2)

            // Draw grid ticks and labels on X axis
            for (var x = 0; x <= chart_perimeter_width; x += grid_step) {
                var pxX = originX + x * pxPerMm
                var tickHeight = 5
                var activeX = x >= chuck_limit && x <= tailstock_limit
                var colorX = activeX ? "black" : "#bbbbbb"

                if (x % 100 === 0) tickHeight = 15
                else if (x % 50 === 0) tickHeight = 10

                ctx.strokeStyle = colorX
                ctx.beginPath()
                ctx.moveTo(pxX, marginTop + chartHeightPx)
                ctx.lineTo(pxX, marginTop + chartHeightPx + tickHeight)
                ctx.stroke()

                ctx.beginPath()
                ctx.moveTo(pxX, marginTop)
                ctx.lineTo(pxX, marginTop - tickHeight)
                ctx.stroke()

                if (x % 100 === 0) {
                    ctx.fillStyle = colorX
                    ctx.font = "10px sans-serif"
                    ctx.textAlign = "center"
                    ctx.fillText(x.toString(), pxX, marginTop + chartHeightPx + 30)
                    ctx.fillText(x.toString(), pxX, marginTop - 10)
                }
            }

            // Draw grid ticks and labels on Y axis (+ and -)
            var maxY = chart_perimeter_height / 2
            for (var ymm = 0; ymm <= maxY; ymm += grid_step) {
                var pxY_pos = originY - ymm * pxPerMm
                var pxY_neg = originY + ymm * pxPerMm
                var tickWidth = 5

                if (ymm % 50 === 0) tickWidth = 15

                var colorPos = ymm <= tool_x_plus_limit ? "black" : "#bbbbbb"
                var colorNeg = ymm <= tool_x_plus_limit ? "black" : "#bbbbbb"

                ctx.strokeStyle = colorPos
                ctx.beginPath()
                ctx.moveTo(originX, pxY_pos)
                ctx.lineTo(originX - tickWidth, pxY_pos)
                ctx.stroke()

                ctx.beginPath()
                ctx.moveTo(originX + chartWidthPx, pxY_pos)
                ctx.lineTo(originX + chartWidthPx + tickWidth, pxY_pos)
                ctx.stroke()

                ctx.strokeStyle = colorNeg
                ctx.beginPath()
                ctx.moveTo(originX, pxY_neg)
                ctx.lineTo(originX - tickWidth, pxY_neg)
                ctx.stroke()

                ctx.beginPath()
                ctx.moveTo(originX + chartWidthPx, pxY_neg)
                ctx.lineTo(originX + chartWidthPx + tickWidth, pxY_neg)
                ctx.stroke()

                if (ymm % 50 === 0) {
                    ctx.fillStyle = colorPos
                    ctx.font = "10px sans-serif"
                    ctx.textAlign = "right"
                    ctx.fillText(ymm.toString(), originX - tickWidth - 5, pxY_pos + 4)
                    ctx.textAlign = "left"
                    ctx.fillText(ymm.toString(), originX + chartWidthPx + tickWidth + 5, pxY_pos + 4)

                    ctx.fillStyle = colorNeg
                    ctx.textAlign = "right"
                    ctx.fillText(ymm.toString(), originX - tickWidth - 5, pxY_neg + 4)
                    ctx.textAlign = "left"
                    ctx.fillText(ymm.toString(), originX + chartWidthPx + tickWidth + 5, pxY_neg + 4)
                }

                if (ymm === 0) {
                    ctx.fillStyle = "black"
                    ctx.textAlign = "right"
                    ctx.fillText("0", originX - tickWidth - 5, originY + 4)
                    ctx.textAlign = "left"
                    ctx.fillText("0", originX + chartWidthPx + tickWidth + 5, originY + 4)
                }
            }
        }
    }
}
