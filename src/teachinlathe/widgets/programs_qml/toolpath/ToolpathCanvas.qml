import QtQuick 2.15

Canvas {
    id: root

    property var batches: []
    property var extents: ({})
    property var workpiece: ({})
    property var stockProfile: []
    property string errorText: ""
    property bool loading: false

    property real _scale: 5.0
    property real _originX: 0
    property real _originY: 0
    property bool _manualView: false
    readonly property real _circleR: 8

    function _cx(z) { return _originX + z * _scale }
    function _cy(x) { return _originY + (x / 2) * _scale }

    onBatchesChanged: {
        if (!_manualView) Qt.callLater(fitToScreen)
        else requestPaint()
    }
    onExtentsChanged: {
        if (!_manualView) Qt.callLater(fitToScreen)
        else requestPaint()
    }
    onWorkpieceChanged: {
        if (!_manualView) Qt.callLater(fitToScreen)
        else requestPaint()
    }
    onStockProfileChanged: requestPaint()
    onWidthChanged: if (!_manualView) fitToScreen()
    onHeightChanged: if (!_manualView) fitToScreen()

    function resetView() {
        _manualView = false
        Qt.callLater(fitToScreen)
    }

    function zoomIn() {
        _zoomAround(width / 2, height / 2, 1.3)
    }

    function zoomOut() {
        _zoomAround(width / 2, height / 2, 1.0 / 1.3)
    }

    function _zoomAround(px, py, factor) {
        var worldZ = (px - _originX) / _scale
        var worldX = (py - _originY) * 2 / _scale
        var newScale = Math.max(0.05, Math.min(200.0, _scale * factor))
        _originX = px - worldZ * newScale
        _originY = py - (worldX / 2) * newScale
        _scale = newScale
        _manualView = true
        requestPaint()
    }

    function fitToScreen() {
        if (!extents || extents.zMin === undefined || width <= 0 || height <= 0) {
            requestPaint()
            return
        }

        var zMin = Number(extents.zMin)
        var zMax = Number(extents.zMax)
        var xMin = Number(extents.xMin)
        var xMax = Number(extents.xMax)
        var stockLength = workpiece && workpiece.stock_length !== undefined ? Number(workpiece.stock_length) : 0
        var stockDiameter = workpiece && workpiece.external_diameter !== undefined ? Number(workpiece.external_diameter) : 0
        if (stockLength > 0) {
            zMin = Math.min(zMin, -stockLength)
            zMax = Math.max(zMax, 0)
        }
        if (stockDiameter > 0) {
            xMin = Math.min(xMin, 0)
            xMax = Math.max(xMax, stockDiameter)
        }

        var leftBound = zMin - 20
        var rightBound = Math.max(zMax, 30)
        var topBound = Math.min(xMin, 0) - 20
        var bottomBound = Math.max(xMax, 20)
        var nextScale = Math.min(
            width / Math.max(rightBound - leftBound, 1),
            height / Math.max(bottomBound - topBound, 1)
        )

        _scale = nextScale
        _originX = -leftBound * nextScale
        _originY = -topBound * nextScale
        _manualView = false
        requestPaint()
    }

    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        paintBackground(ctx)
        paintGrid(ctx)
        paintTicks(ctx)
        stockActor.paintStock(ctx)
        paintAxes(ctx)
        paintOrigin(ctx)
        toolpathActor.paint(ctx)
        stockActor.paintHatch(ctx)
    }

    function paintBackground(ctx) {
        ctx.fillStyle = "#f5f5f5"
        ctx.fillRect(0, 0, width, height)
    }

    function _steps(scale) {
        if (scale >= 2) return { minor: 1, major: 10 }
        if (scale >= 0.4) return { minor: 10, major: 50 }
        return { minor: 50, major: 100 }
    }

    function _isMajor(val, step) {
        return Math.round(Math.abs(val) * 1000) % Math.round(step * 1000) < 1
    }

    function _tickStyle(val, steps) {
        if (_isMajor(val, steps.major)) return { len: 7, label: true }
        if (_isMajor(val, 5)) return { len: 7, label: false }
        return { len: 3, label: false }
    }

    function paintGrid(ctx) {
        var steps = _steps(_scale)
        var xSteps = _steps(_scale / 2)
        ctx.strokeStyle = "#e0e0e0"
        ctx.lineWidth = 0.5
        ctx.setLineDash([])

        var zMin = -_originX / _scale
        var zMax = (width - _originX) / _scale
        var z0 = Math.floor(zMin / steps.major) * steps.major
        for (var z = z0; z <= zMax; z += steps.major) {
            var px = _cx(z)
            ctx.beginPath()
            ctx.moveTo(px, 0)
            ctx.lineTo(px, height)
            ctx.stroke()
        }

        var xMin = -_originY * 2 / _scale
        var xMax = (height - _originY) * 2 / _scale
        var x0 = Math.floor(xMin / xSteps.major) * xSteps.major
        for (var x = x0; x <= xMax; x += xSteps.major) {
            var py = _cy(x)
            ctx.beginPath()
            ctx.moveTo(0, py)
            ctx.lineTo(width, py)
            ctx.stroke()
        }
    }

    function paintTicks(ctx) {
        var steps = _steps(_scale)
        var xSteps = _steps(_scale / 2)
        ctx.lineWidth = 1
        ctx.setLineDash([])

        ctx.font = "10px sans-serif"
        ctx.strokeStyle = "#2E7D32"
        ctx.fillStyle = "#2E7D32"
        ctx.textAlign = "center"
        var zMin = -_originX / _scale
        var zMax = (width - _originX) / _scale
        var z0 = Math.floor(zMin / steps.minor) * steps.minor
        for (var z = z0; z <= zMax; z += steps.minor) {
            var zStyle = _tickStyle(z, steps)
            var canvasX = _cx(z)
            ctx.beginPath()
            ctx.moveTo(canvasX, 0)
            ctx.lineTo(canvasX, zStyle.len)
            ctx.stroke()
            ctx.beginPath()
            ctx.moveTo(canvasX, height)
            ctx.lineTo(canvasX, height - zStyle.len)
            ctx.stroke()
            if (zStyle.label) {
                ctx.textBaseline = "top"
                ctx.fillText(Math.round(z).toString(), canvasX, zStyle.len + 2)
                ctx.textBaseline = "bottom"
                ctx.fillText(Math.round(z).toString(), canvasX, height - zStyle.len - 2)
            }
        }

        ctx.strokeStyle = "#1565C0"
        ctx.fillStyle = "#1565C0"
        ctx.textAlign = "left"
        var xMin = -_originY * 2 / _scale
        var xMax = (height - _originY) * 2 / _scale
        var x0 = Math.floor(xMin / xSteps.minor) * xSteps.minor
        for (var x = x0; x <= xMax; x += xSteps.minor) {
            var xStyle = _tickStyle(x, xSteps)
            var canvasY = _cy(x)
            ctx.beginPath()
            ctx.moveTo(0, canvasY)
            ctx.lineTo(xStyle.len, canvasY)
            ctx.stroke()
            ctx.beginPath()
            ctx.moveTo(width, canvasY)
            ctx.lineTo(width - xStyle.len, canvasY)
            ctx.stroke()
            if (xStyle.label) {
                ctx.textBaseline = "middle"
                ctx.textAlign = "left"
                ctx.fillText(Math.round(x).toString(), xStyle.len + 2, canvasY)
                ctx.textAlign = "right"
                ctx.fillText(Math.round(x).toString(), width - xStyle.len - 2, canvasY)
            }
        }
    }

    function paintAxes(ctx) {
        var axisLength = 60
        var arrowHeadLen = 14
        var arrowHeadWidth = 7

        ctx.setLineDash([8, 5, 2, 5])
        ctx.lineWidth = 0.8
        ctx.strokeStyle = "#999999"
        ctx.beginPath()
        ctx.moveTo(_originX, 0)
        ctx.lineTo(_originX, height)
        ctx.moveTo(0, _originY)
        ctx.lineTo(width, _originY)
        ctx.stroke()
        ctx.setLineDash([])

        ctx.font = "bold 11px sans-serif"
        ctx.textBaseline = "middle"
        ctx.strokeStyle = "#2E7D32"
        ctx.fillStyle = "#2E7D32"
        ctx.lineWidth = 1.5
        var zTipX = _originX + axisLength
        var zShaft = zTipX - arrowHeadLen
        var zStart = _originX + _circleR + 1
        if (zShaft > zStart) {
            ctx.beginPath()
            ctx.moveTo(zStart, _originY)
            ctx.lineTo(zShaft, _originY)
            ctx.stroke()
        }
        ctx.beginPath()
        ctx.moveTo(zTipX, _originY)
        ctx.lineTo(zShaft, _originY - arrowHeadWidth)
        ctx.lineTo(zShaft, _originY + arrowHeadWidth)
        ctx.closePath()
        ctx.fill()
        ctx.textAlign = "center"
        ctx.textBaseline = "bottom"
        ctx.fillText("Z+", zTipX - arrowHeadLen / 2, _originY - arrowHeadWidth - 2)

        ctx.strokeStyle = "#1565C0"
        ctx.fillStyle = "#1565C0"
        var xTipY = _originY + axisLength
        var xShaft = xTipY - arrowHeadLen
        var xStart = _originY + _circleR + 1
        if (xShaft > xStart) {
            ctx.beginPath()
            ctx.moveTo(_originX, xStart)
            ctx.lineTo(_originX, xShaft)
            ctx.stroke()
        }
        ctx.beginPath()
        ctx.moveTo(_originX, xTipY)
        ctx.lineTo(_originX - arrowHeadWidth, xShaft)
        ctx.lineTo(_originX + arrowHeadWidth, xShaft)
        ctx.closePath()
        ctx.fill()
        ctx.textAlign = "right"
        ctx.textBaseline = "middle"
        ctx.fillText("X+", _originX - arrowHeadWidth - 4, xTipY - arrowHeadLen / 2)
    }

    function paintOrigin(ctx) {
        var quads = [
            { start: -Math.PI / 2, end: 0, fill: true },
            { start: 0, end: Math.PI / 2, fill: false },
            { start: Math.PI / 2, end: Math.PI, fill: true },
            { start: Math.PI, end: 3 * Math.PI / 2, fill: false }
        ]
        ctx.lineWidth = 1.5
        ctx.fillStyle = "#222222"
        ctx.strokeStyle = "#222222"
        ctx.setLineDash([])
        for (var i = 0; i < quads.length; i++) {
            var q = quads[i]
            ctx.beginPath()
            ctx.moveTo(_originX, _originY)
            ctx.arc(_originX, _originY, _circleR, q.start, q.end, false)
            ctx.closePath()
            if (q.fill) ctx.fill()
            ctx.stroke()
        }
    }

    ToolpathStockActor {
        id: stockActor
        workpiece: root.workpiece
        stockProfile: root.stockProfile
        cx: root._cx
        cy: root._cy
    }

    ToolpathActor {
        id: toolpathActor
        batches: root.batches
        scale: root._scale
        cx: root._cx
        cy: root._cy
    }

    MouseArea {
        anchors.fill: parent

        property bool _wasDrag: false
        property real _dragStartX: 0
        property real _dragStartY: 0
        property real _originXAtDragStart: 0
        property real _originYAtDragStart: 0

        readonly property real _DEAD_ZONE: 4

        onPressed: function(mouse) {
            _wasDrag = false
            _dragStartX = mouse.x
            _dragStartY = mouse.y
            _originXAtDragStart = root._originX
            _originYAtDragStart = root._originY
        }

        onPositionChanged: function(mouse) {
            var dx = mouse.x - _dragStartX
            var dy = mouse.y - _dragStartY
            if (!_wasDrag && (Math.abs(dx) > _DEAD_ZONE || Math.abs(dy) > _DEAD_ZONE)) {
                _wasDrag = true
                root._manualView = true
            }
            if (_wasDrag) {
                root._originX = _originXAtDragStart + dx
                root._originY = _originYAtDragStart + dy
                root.requestPaint()
            }
        }

        onDoubleClicked: function(mouse) {
            root.fitToScreen()
        }

        onWheel: function(wheel) {
            var factor = wheel.angleDelta.y > 0 ? 1.15 : 1.0 / 1.15
            root._zoomAround(wheel.x, wheel.y, factor)
        }
    }

    Row {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 8

        ToolButton { label: "+"; onClicked: root.zoomIn() }
        ToolButton { label: "-"; onClicked: root.zoomOut() }
        ToolButton { label: "Fit"; width: 58; onClicked: root.fitToScreen() }
    }

    Rectangle {
        visible: root.loading || root.errorText.length > 0 || !root.batches || root.batches.length === 0
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, statusText.implicitWidth + 40)
        height: statusText.implicitHeight + 28
        radius: 6
        color: "#ddffffff"
        border.color: "#cccccc"

        Text {
            id: statusText
            anchors.centerIn: parent
            width: parent.width - 24
            text: root.loading ? "Loading toolpath..." : root.errorText.length > 0 ? root.errorText : "No toolpath"
            color: root.errorText.length > 0 ? "#b00020" : "#555555"
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
    }

    component ToolButton: Rectangle {
        signal clicked()
        property string label: ""

        width: 44
        height: 36
        radius: 6
        color: buttonMouse.pressed ? "#dddddd" : "#ffffff"
        border.color: "#c8c8c8"
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: parent.label
            color: "#333333"
            font.pixelSize: 14
            font.bold: true
        }

        MouseArea {
            id: buttonMouse
            anchors.fill: parent
            onClicked: parent.clicked()
        }
    }
}
