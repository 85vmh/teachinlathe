import QtQuick
import tabs.conversational

Item {
    id: root

    property var primitives: []
    property var workpiece: ({})
    property string profileType: "od"
    // taps select what is drawn - the bottom's diameter, a blend, an angled
    // flank - and its tag edits it (grooveEdited)
    property bool editable: false
    // the upper half too, above the centre line
    property alias mirrorAcrossCenterline: profileCanvas.mirrorAcrossCenterline
    // marks drawn on the profile, each with its arrow to a box laid over the
    // canvas (see MarkersActor), and the room fitToScreen leaves the boxes
    property alias markers: profileCanvas.markers
    property alias fitInsetLeft: profileCanvas.fitInsetLeft
    property alias fitInsetRight: profileCanvas.fitInsetRight
    property alias fitPadding: profileCanvas.fitPadding
    // more points fitted in - a tool drawn over the canvas
    property alias fitExtraPositions: profileCanvas.fitExtraPositions
    // what a roughing of it will cut, as ProfileCanvas draws it, and the box
    // its stock to leave points an arrow to
    property alias roughingPreview: profileCanvas.roughingPreview
    property alias stockToLeaveArrowRect: profileCanvas.stockToLeaveArrowRect
    // dimensions drawn on it (DimensionActor), and whether each of the
    // profile's transitions is joined to its mirror
    property alias dimensions: profileCanvas.dimensions
    property alias showTransitions: profileCanvas.showTransitions
    property alias showProfileEnds: profileCanvas.showProfileEnds
    property alias fillProfile: profileCanvas.fillProfile
    readonly property color feedColor: profileCanvas.feedColor
    readonly property real toolpathArrowLength: profileCanvas.toolpathArrowLength
    readonly property color stockToLeaveColor: profileCanvas.stockToLeaveColor
    // px per mm, and how far in from the edges the ticks reach
    readonly property real pxPerMm: profileCanvas._scale
    readonly property real tickBand: profileCanvas.tickBand

    // where Z ``z`` and diameter ``x`` are drawn, in px - bound to, they
    // follow the view as it is panned and zoomed
    function px(z) { return profileCanvas._cx(z) }
    function py(x) { return profileCanvas._cy(x) }
    property var _profilePrimitives: []
    // what of the first groove each of _profilePrimitives draws:
    // {key, section, from, to, anchor} - key "start", "p1Blend", "rightFlank",
    // "bottom", "leftFlank" or "p4Blend"; a flank's from and to its points, a
    // start blend's anchor the middle of it ({z, x: diameter})
    property var _roles: []
    // what is selected on the canvas: a primitive, or the blend one carries
    property int _selectedPrim: -1
    property int _selectedBlend: -1

    // the first groove's ``section`` with ``values`` set in it, to be saved
    signal grooveEdited(string section, var values)
    signal openNumPadRequested(var field)

    // the first groove's points, [{x: diameter, z}]: P1 where its right
    // flank starts, P2 that flank's bottom, P3 the left flank's bottom, P4
    // where the left flank starts; [] with no groove
    readonly property var groovePoints: _groovePoints(_firstGroove())

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
            return { start: cornerD, end: cornerD }

        var amount = b.type === "fillet" ? b.fillet_radius : b.chamfer_width
        if (amount <= 0.0001)
            return { start: cornerD, end: cornerD }

        var dot = Math.max(-0.9999, Math.min(0.9999, ua.z * ub.z + ua.xh * ub.xh))
        var theta = Math.acos(dot)
        if (theta < 0.001)
            return { start: cornerD, end: cornerD }

        var tangentDistance = b.type === "fillet" ? amount / Math.tan(theta / 2.0) : amount
        tangentDistance = Math.min(tangentDistance, ua.len, ub.len)
        var t1 = _point(corner.z + ua.z * tangentDistance, corner.xh + ua.xh * tangentDistance)
        var t2 = _point(corner.z + ub.z * tangentDistance, corner.xh + ub.xh * tangentDistance)

        if (b.type !== "fillet")
            return { start: t1, end: t2 }

        var bisZ = ua.z + ub.z
        var bisX = ua.xh + ub.xh
        var bisLen = Math.sqrt(bisZ * bisZ + bisX * bisX)
        if (bisLen < 0.0001)
            return { start: t1, end: t2 }

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

        // one arc from t1 to t2 - clockwise as drawn (X down) when its angle
        // grows - so the profile has a transition only at its ends
        return { start: t1, end: t2, center: center, radius: amount, clockwise: delta > 0 }
    }

    // The fillet ``blend`` (from _cornerBlend) as an arcTo to its end.
    function _appendArc(out, pid, blend) {
        out.push({
            primitive_id: pid,
            type: "arcTo",
            x_end: blend.end.x,
            z_end: blend.end.z,
            x_center: blend.center.x,
            z_center: blend.center.z,
            arc_radius: blend.radius,
            direction: blend.clockwise ? "cw" : "ccw",
            blend: _blend(null)
        })
        return pid + 1
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
        var before = _roles
        _buildProfilePrimitives()
        // a selection kept only on what it was on: a blend added or taken
        // off moves what follows it
        function same(i) { return i < 0 || (i < before.length && i < _roles.length && before[i].key === _roles[i].key) }
        if (!same(_selectedPrim) || !same(_selectedBlend)) {
            _selectedPrim = -1
            _selectedBlend = -1
        }
    }

    // the middle of a start blend (_cornerBlend's), as {z, x: diameter}
    function _blendMiddle(b) {
        if (!b.center) return { z: (b.start.z + b.end.z) / 2, x: (b.start.x + b.end.x) / 2 }
        var dz = (b.start.z - b.center.z) + (b.end.z - b.center.z)
        var dx = (b.start.xh - b.center.xh) + (b.end.xh - b.center.xh)
        var len = Math.sqrt(dz * dz + dx * dx)
        if (len < 1e-9) return { z: b.start.z, x: b.start.x }
        return { z: b.center.z + dz / len * b.radius, x: 2 * (b.center.xh + dx / len * b.radius) }
    }

    function _buildProfilePrimitives() {
        var g = _firstGroove()
        var pts = _groovePoints(g)
        if (!g || pts.length < 4) {
            _profilePrimitives = []
            _roles = []
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
        var roles = []
        var pid = 1
        // what the primitive appended last draws, if one was
        function role(r) { if (out.length > roles.length) roles.push(r) }
        out.push({
            primitive_id: pid++,
            type: "startPoint",
            x_start: rightBlend.start.x,
            z_start: rightBlend.start.z,
            blend: _blend(null)
        })
        role({ key: "start" })
        if (rightBlend.center)
            pid = _appendArc(out, pid, rightBlend)
        else
            pid = _appendLine(out, pid, rightBlend.end, _blend(null))
        role({ key: "p1Blend", section: "right_flank", anchor: _blendMiddle(rightBlend) })
        pid = _appendLine(out, pid, rightBottom, _blend(bottom.blend_right))
        role({ key: "rightFlank", section: "right_flank", from: rightCorner, to: rightBottom })
        pid = _appendLine(out, pid, leftBottom, _blend(bottom.blend_left))
        role({ key: "bottom", section: "bottom" })
        pid = _appendLine(out, pid, leftBlend.start, _blend(null))
        role({ key: "leftFlank", section: "left_flank", from: leftCorner, to: leftBottom })
        if (leftBlend.center)
            pid = _appendArc(out, pid, leftBlend)
        else
            pid = _appendLine(out, pid, leftBlend.end, _blend(null))
        role({ key: "p4Blend", section: "left_flank", anchor: _blendMiddle(leftBlend) })
        _roles = roles
        _profilePrimitives = out
    }

    // The tag for primitive ``index`` the canvas has none of its own for: a
    // start blend's size, an angled flank's angle (ProfileCanvas.extraTag)
    function _extraTag(index) {
        var r = _roles[index], g = _firstGroove()
        if (!r || !g) return null
        if (r.key === "p1Blend" || r.key === "p4Blend") {
            var b = _blend((g[r.section] || {}).start_blend)
            var point = r.key === "p1Blend" ? 1 : 4
            if (b.type === "fillet")
                return { value: b.fillet_radius, prefix: "r", field: "fillet_radius",
                         description: "P" + point + " fillet radius", z: r.anchor.z, x: r.anchor.x }
            if (b.type === "chamfer")
                return { value: b.chamfer_width, prefix: "w", field: "chamfer_width",
                         description: "P" + point + " chamfer width", z: r.anchor.z, x: r.anchor.x }
            return null
        }
        if (r.key === "rightFlank" || r.key === "leftFlank") {
            var angle = Number((g[r.section] || {}).angle || 0)
            if (Math.abs(angle) < 1e-9) return null
            return { value: angle, prefix: "\u2220", unit: "\u00b0", field: "angle", min: 0,
                     description: (r.key === "rightFlank" ? "Right" : "Left") + " flank angle",
                     z: (r.from.z + r.to.z) / 2, x: (r.from.x + r.to.x) / 2 }
        }
        return null
    }

    // the first groove's blend ``key`` of ``section`` with ``field`` set to ``value``
    function _blendWith(section, key, field, value) {
        var b = JSON.parse(JSON.stringify(_blend(((_firstGroove() || {})[section] || {})[key])))
        b[field] = value
        var values = {}
        values[key] = b
        return values
    }

    ProfileCanvas {
        id: profileCanvas
        anchors.fill: parent
        primitives: root._profilePrimitives
        workpiece: root.workpiece
        profileType: root.profileType
        selectable: root.editable
        tagEditable: root.editable
        selectedPrimIndex: root._selectedPrim
        selectedBlendIndex: root._selectedBlend
        extraTag: function(index) { return root._extraTag(index) }
        onFitExtraPositionsChanged: if (!_manualView) _scheduleFit()

        onPrimitiveSelected: function(index) { root._selectedPrim = index; root._selectedBlend = -1 }
        onBlendSelected: function(index) { root._selectedBlend = index; root._selectedPrim = -1 }
        onSelectionCleared: { root._selectedPrim = -1; root._selectedBlend = -1 }
        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }

        // the bottom, a cylinder: both its corners to the new diameter
        onDiameterEdited: function(index, diameter) {
            if (root._roles[index] && root._roles[index].key === "bottom")
                root.grooveEdited("bottom", { x_end_left: diameter, x_end_right: diameter })
        }
        // P2's blend is carried by the right flank, P3's by the bottom
        onBlendEdited: function(index, field, value) {
            var r = root._roles[index]
            if (!r) return
            if (r.key === "rightFlank") root.grooveEdited("bottom", root._blendWith("bottom", "blend_right", field, value))
            if (r.key === "bottom") root.grooveEdited("bottom", root._blendWith("bottom", "blend_left", field, value))
        }
        onTagEdited: function(index, field, value) {
            var r = root._roles[index]
            if (!r) return
            if (field === "angle") root.grooveEdited(r.section, { angle: value })
            else root.grooveEdited(r.section, root._blendWith(r.section, "start_blend", field, value))
        }
    }
}
