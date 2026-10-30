import QtQuick
import TeachInLathe
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
    // the first groove as it is drawn, worked out where its G-code's is
    // (qml_adapter.groove_outline_payload): its points, the profile
    // primitives it is drawn along, and what of it each draws -
    // {key, section, from, to, anchor} - key "start", "p1Blend",
    // "rightFlank", "bottom", "leftFlank" or "p4Blend"; a flank's from and to
    // its points, a top blend's anchor the middle of it ({z, x: diameter})
    property var _outline: ({ points: [], primitives: [], roles: [] })
    readonly property var _profilePrimitives: _outline.primitives
    readonly property var _roles: _outline.roles
    // what is selected on the canvas: a primitive, or the blend one carries
    property int _selectedPrim: -1
    property int _selectedBlend: -1

    // the first groove's ``section`` with ``values`` set in it, to be saved
    signal grooveEdited(string section, var values)
    signal openNumPadRequested(var field)

    // the first groove's points, [{x: diameter, z}]: P1 where its right
    // flank starts, P2 that flank's bottom, P3 the left flank's bottom, P4
    // where the left flank starts; [] with no groove
    readonly property var groovePoints: _outline.points

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

    function _rebuildProfilePrimitives() {
        var before = _roles
        _outline = ConversationalViewModel.grooveOutline(primitives || [])
        // a selection kept only on what it was on: a blend added or taken
        // off moves what follows it
        function same(i) { return i < 0 || (i < before.length && i < _roles.length && before[i].key === _roles[i].key) }
        if (!same(_selectedPrim) || !same(_selectedBlend)) {
            _selectedPrim = -1
            _selectedBlend = -1
        }
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
