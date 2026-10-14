import QtQuick 2.15
import "../"

Item {
    id: root

    property var primitives: []
    property var workpiece: ({})
    property string profileType: "od"
    property int selectedIndex: -1
    property var _profilePrimitives: []

    onPrimitivesChanged: _rebuildProfilePrimitives()
    Component.onCompleted: _rebuildProfilePrimitives()

    function resetView() { profileCanvas.resetView() }
    function zoomIn() { profileCanvas.zoomIn() }
    function zoomOut() { profileCanvas.zoomOut() }
    function fitToScreen() { profileCanvas.fitToScreen() }

    function _firstGroove() {
        if (!primitives) return null
        for (var i = 0; i < primitives.length; i++) {
            if (primitives[i] && primitives[i].type === "groove")
                return primitives[i]
        }
        return null
    }

    function _blend(blend) {
        var b = blend || {}
        var t = b.type || "none"
        if (t === "radius") t = "fillet"
        return {
            type: t,
            chamfer_width: Number(b.chamfer_width || 0),
            fillet_radius: Number(b.fillet_radius || 0)
        }
    }

    function _groovePoints(g) {
        if (!g) return []
        var rf = g.right_flank || {}
        var lf = g.left_flank || {}
        var b = g.bottom || {}
        var rx0 = Number(rf.x_start || 0)
        var rz0 = Number(rf.z_start || 0)
        var lx0 = Number(lf.x_start || 0)
        var lz0 = Number(lf.z_start || 0)
        var rxe = Number(b.x_end_right || 0)
        var lxe = Number(b.x_end_left || 0)
        var ra = Math.abs(Number(rf.angle || 0)) * Math.PI / 180.0
        var la = Math.abs(Number(lf.angle || 0)) * Math.PI / 180.0
        var rdz = Math.abs((rx0 - rxe) / 2.0 * Math.tan(ra))
        var ldz = Math.abs((lx0 - lxe) / 2.0 * Math.tan(la))
        return [
            { x: rx0, z: rz0 },
            { x: rxe, z: rz0 - rdz },
            { x: lxe, z: lz0 + ldz },
            { x: lx0, z: lz0 }
        ]
    }

    function _dist(a, b) {
        var dz = b.z - a.z
        var dx = b.xh - a.xh
        return Math.sqrt(dz * dz + dx * dx)
    }

    function _unitFrom(corner, point) {
        var dz = point.z - corner.z
        var dx = point.xh - corner.xh
        var len = Math.sqrt(dz * dz + dx * dx)
        if (len < 0.0001) return null
        return { z: dz / len, xh: dx / len, len: len }
    }

    function _point(z, xh) {
        return { z: z, x: xh * 2.0, xh: xh }
    }

    function _samePoint(a, b) {
        if (!a || !b) return false
        return Math.abs(a.z - b.z) < 0.0001 && Math.abs(a.x - b.x) < 0.0001
    }

    function _cornerBlend(cornerD, legAEndD, legBEndD, blend) {
        var b = _blend(blend)
        var corner = _point(cornerD.z, cornerD.x / 2.0)
        var legAEnd = _point(legAEndD.z, legAEndD.x / 2.0)
        var legBEnd = _point(legBEndD.z, legBEndD.x / 2.0)
        var ua = _unitFrom(corner, legAEnd)
        var ub = _unitFrom(corner, legBEnd)
        if (!ua || !ub || b.type === "none")
            return { start: cornerD, end: cornerD, arc: [] }

        var amount = b.type === "fillet" ? b.fillet_radius : b.chamfer_width
        if (amount <= 0.0001)
            return { start: cornerD, end: cornerD, arc: [] }

        var dot = Math.max(-0.9999, Math.min(0.9999, ua.z * ub.z + ua.xh * ub.xh))
        var theta = Math.acos(dot)
        if (theta < 0.001)
            return { start: cornerD, end: cornerD, arc: [] }

        var tangentDistance = b.type === "fillet" ? amount / Math.tan(theta / 2.0) : amount
        tangentDistance = Math.min(tangentDistance, ua.len, ub.len)
        var t1 = _point(corner.z + ua.z * tangentDistance, corner.xh + ua.xh * tangentDistance)
        var t2 = _point(corner.z + ub.z * tangentDistance, corner.xh + ub.xh * tangentDistance)

        if (b.type !== "fillet")
            return { start: t1, end: t2, arc: [] }

        var bisZ = ua.z + ub.z
        var bisX = ua.xh + ub.xh
        var bisLen = Math.sqrt(bisZ * bisZ + bisX * bisX)
        if (bisLen < 0.0001)
            return { start: t1, end: t2, arc: [] }

        var centerDistance = amount / Math.sin(theta / 2.0)
        var center = _point(
            corner.z + bisZ / bisLen * centerDistance,
            corner.xh + bisX / bisLen * centerDistance
        )
        var startAngle = Math.atan2(t1.xh - center.xh, t1.z - center.z)
        var endAngle = Math.atan2(t2.xh - center.xh, t2.z - center.z)
        var delta = endAngle - startAngle
        while (delta > Math.PI) delta -= Math.PI * 2.0
        while (delta < -Math.PI) delta += Math.PI * 2.0

        var arc = []
        var steps = 10
        for (var i = 1; i <= steps; i++) {
            var a = startAngle + delta * i / steps
            arc.push(_point(center.z + Math.cos(a) * amount, center.xh + Math.sin(a) * amount))
        }
        return { start: t1, end: t2, arc: arc }
    }

    function _appendLine(out, pid, point, blend) {
        if (out.length > 0) {
            var last = out[out.length - 1]
            var lastPoint = last.type === "startPoint"
                ? { z: Number(last.z_start || 0), x: Number(last.x_start || 0) }
                : { z: Number(last.z_end || 0), x: Number(last.x_end || 0) }
            if (_samePoint(lastPoint, point) && (!blend || blend.type === "none"))
                return pid
        }
        out.push({
            primitive_id: pid,
            type: "lineTo",
            input: "xz",
            x_end: point.x,
            z_end: point.z,
            blend: blend || _blend(null)
        })
        return pid + 1
    }

    function _rebuildProfilePrimitives() {
        var g = _firstGroove()
        var pts = _groovePoints(g)
        if (!g || pts.length < 4) {
            _profilePrimitives = []
            return
        }
        var rf = g.right_flank || {}
        var lf = g.left_flank || {}
        var bottom = g.bottom || {}
        var rightCorner = pts[0]
        var rightBottom = pts[1]
        var leftBottom = pts[2]
        var leftCorner = pts[3]
        var imaginarySpan = 10000.0

        var rightBlend = _cornerBlend(
            rightCorner,
            { z: rightCorner.z + imaginarySpan, x: rightCorner.x },
            rightBottom,
            rf.start_blend
        )
        var leftBlend = _cornerBlend(
            leftCorner,
            leftBottom,
            { z: leftCorner.z - imaginarySpan, x: leftCorner.x },
            lf.start_blend
        )

        var out = []
        var pid = 1
        out.push({
            primitive_id: pid++,
            type: "startPoint",
            x_start: rightBlend.start.x,
            z_start: rightBlend.start.z,
            blend: _blend(null)
        })
        if (rightBlend.arc && rightBlend.arc.length > 0) {
            for (var ri = 0; ri < rightBlend.arc.length; ri++)
                pid = _appendLine(out, pid, rightBlend.arc[ri], _blend(null))
        } else {
            pid = _appendLine(out, pid, rightBlend.end, _blend(null))
        }
        pid = _appendLine(out, pid, rightBottom, _blend(bottom.blend_right))
        pid = _appendLine(out, pid, leftBottom, _blend(bottom.blend_left))
        pid = _appendLine(out, pid, leftBlend.start, _blend(null))
        if (leftBlend.arc && leftBlend.arc.length > 0) {
            for (var li = 0; li < leftBlend.arc.length; li++)
                pid = _appendLine(out, pid, leftBlend.arc[li], _blend(null))
        } else {
            pid = _appendLine(out, pid, leftBlend.end, _blend(null))
        }
        _profilePrimitives = out
    }

    ProfileCanvas {
        id: profileCanvas
        anchors.fill: parent
        primitives: root._profilePrimitives
        workpiece: root.workpiece
        profileType: root.profileType
        selectedPrimIndex: root.selectedIndex >= 0 ? 0 : -1
    }
}
