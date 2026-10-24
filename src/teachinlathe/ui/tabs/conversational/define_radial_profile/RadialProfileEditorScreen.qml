import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational
import common.touchable_input
import theme

Item {
    id: root
    objectName: "radialProfileEditorScreen"

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null
    property int profileId: 0
    property string profileType: "od"
    property var primitives: []
    property var workpiece: ({})
    property int selectedIndex: -1
    property bool _loading: false
    // The card swiped open on its Delete (a SwipeRow), or null
    property var openSwipeRow: null

    // The first groove, whose points the canvas names: its index, or -1
    readonly property int grooveIndex: {
        for (var i = 0; i < primitives.length; i++)
            if (primitives[i] && primitives[i].type === "groove") return i
        return -1
    }
    readonly property var groove: grooveIndex >= 0 ? primitives[grooveIndex] : null

    signal backRequested()
    signal openNumPadRequested(var field)

    function applyData(index, data) {
        _loading = true
        opIndex = index
        opData = data || {}
        profileId = opData.profile_id !== undefined ? Math.round(Number(opData.profile_id)) : 0
        profileType = opData.profile_type !== undefined ? String(opData.profile_type) : "od"
        primitives = JSON.parse(JSON.stringify(opData.profile_primitives || []))
        workpiece = JSON.parse(JSON.stringify(opData.workpiece || {}))
        selectedIndex = primitives.length > 0 ? 0 : -1
        _loading = false
        profileCanvas.resetView()
    }

    function emitSave() {
        if (_loading) return
        var merged = JSON.parse(JSON.stringify(opData || {}))
        merged.profile_id = root.profileId
        merged.profile_type = root.profileType
        merged.profile_primitives = root._renumber(root.primitives)
        opData = merged
        root.editor.save(merged)
    }

    function _renumber(arr) {
        var out = JSON.parse(JSON.stringify(arr || []))
        var ordered = []
        for (var i = 0; i < out.length; i++)
            ordered.push(_orderPrimitive(out[i], i + 1))
        return ordered
    }

    function _orderPrimitive(primitive, primitiveId) {
        var p = primitive || {}
        var ordered = {
            primitive_id: primitiveId,
            type: p.type || "groove"
        }
        if (ordered.type === "groove") {
            ordered.right_flank = p.right_flank || {}
            ordered.bottom = p.bottom || {}
            ordered.left_flank = p.left_flank || {}
        }
        for (var key in p) {
            if (ordered[key] === undefined)
                ordered[key] = p[key]
        }
        return ordered
    }

    function primUpdated(idx, data) {
        var arr = JSON.parse(JSON.stringify(root.primitives || []))
        arr[idx] = data
        root.primitives = root._renumber(arr)
        root.emitSave()
    }

    function primDeleted(idx) {
        var arr = JSON.parse(JSON.stringify(root.primitives || []))
        if (idx < 0 || idx >= arr.length) return
        arr.splice(idx, 1)
        root.primitives = root._renumber(arr)
        root.selectedIndex = root.primitives.length > 0 ? Math.min(idx, root.primitives.length - 1) : -1
        root.emitSave()
    }

    function _emptyBlend() {
        return { type: "none", chamfer_width: 0.0, fillet_radius: 0.0 }
    }

    function _newGroove() {
        return {
            primitive_id: 0,
            type: "groove",
            right_flank: {
                x_start: 30.0,
                z_start: 0.0,
                angle: 0.0,
                start_blend: _emptyBlend()
            },
            bottom: {
                x_end_right: 20.0,
                x_end_left: 20.0,
                blend_right: _emptyBlend(),
                blend_left: _emptyBlend()
            },
            left_flank: {
                x_start: 30.0,
                z_start: -5.0,
                angle: 0.0,
                start_blend: _emptyBlend()
            }
        }
    }

    function _newRepeat() {
        return {
            primitive_id: 0,
            type: "repeat",
            repeat_primitive_id: 1,
            repeat_count: 1,
            z_offset: -5.0
        }
    }

    function addPrimitive(type) {
        var arr = JSON.parse(JSON.stringify(root.primitives || []))
        arr.push(type === "repeat" ? _newRepeat() : _newGroove())
        root.primitives = root._renumber(arr)
        root.selectedIndex = root.primitives.length - 1
        root.emitSave()
    }

    IntValidator { id: intVal; bottom: 1; top: 999 }

    Rectangle { anchors.fill: parent; color: Theme.surfaceAlt }

    Item {
        anchors.fill: parent

        Rectangle {
            id: leftPanelBg
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            // as wide as a groove's card and the row over the list need
            width: Math.max(headerRow.implicitWidth + 24, widthProbe.implicitWidth + 2 * 8 + 12)
            color: Theme.surface

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.spacingSmall

                RowLayout {
                    id: headerRow
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.rowHeight
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    spacing: 10

                    Label {
                        text: "Profile ID:"
                        font.pixelSize: Theme.fontBody
                    }

                    NumpadField {
                        Layout.preferredWidth: 82
                        settingName: "defineRadialProfile.profile_id"
                        validatorObject: intVal
                        value: root.profileId
                        formatter: function(v) { return v == null ? "" : String(Math.round(Number(v))) }
                        hAlign: Text.AlignHCenter
                        onOpenRequested: function(field) { root.openNumPadRequested(field) }
                        onValueCommitted: function(value) { root.profileId = Math.round(value); root.emitSave() }
                    }

                    Rectangle {
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: Theme.buttonHeight
                        color: Theme.separator
                    }

                    Label {
                        text: "Type:"
                        font.pixelSize: Theme.fontBody
                    }

                    ButtonGroup { id: profileTypeGroup }

                    RadioButton {
                        text: "OD"
                        font.pixelSize: Theme.fontSmall
                        checked: root.profileType === "od"
                        ButtonGroup.group: profileTypeGroup
                        onToggled: if (checked) { root.profileType = "od"; root.emitSave() }
                    }

                    RadioButton {
                        text: "ID"
                        font.pixelSize: Theme.fontSmall
                        checked: root.profileType === "id"
                        ButtonGroup.group: profileTypeGroup
                        onToggled: if (checked) { root.profileType = "id"; root.emitSave() }
                    }

                    Item { Layout.fillWidth: true }

                    Button {
                        text: "Groove"
                        Layout.preferredWidth: 110
                        onClicked: root.addPrimitive("groove")
                    }

                    Button {
                        text: "Repeat"
                        Layout.preferredWidth: 110
                        onClicked: root.addPrimitive("repeat")
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: Theme.hairline
                    color: Theme.surfaceAlt
                }

                ScrollView {
                    id: cardScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Connections {
                        target: cardScroll.contentItem
                        function onMovementStarted() { root.openSwipeRow = null }
                    }
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    contentWidth: availableWidth

                    Column {
                        width: cardScroll.availableWidth
                        spacing: Theme.spacingSmall
                        padding: 8

                        Repeater {
                            model: root.primitives
                            // Swiped left a card shows Delete (see SwipeRow)
                            delegate: SwipeRow {
                                id: primSwipe
                                width: parent.width - 16
                                height: cardLoader.height
                                duplicateEnabled: false
                                actionGap: Theme.spacingSmall
                                actionRadius: 8
                                swipeSide: root.openSwipeRow === primSwipe ? 1 : 0
                                onSwipeOpened: root.openSwipeRow = primSwipe
                                onSwipeClosed: if (root.openSwipeRow === primSwipe) root.openSwipeRow = null
                                onDeleteRequested: {
                                    root.openSwipeRow = null
                                    root.primDeleted(index)
                                }

                                Loader {
                                    id: cardLoader
                                    width: parent.width
                                    sourceComponent: {
                                        if (!modelData) return null
                                        if (modelData.type === "repeat") return repeatCardComp
                                        return grooveCardComp
                                    }
                                    onLoaded: {
                                        item.primData = modelData
                                        item.primIdx = index
                                        item.isSelected = Qt.binding(function() { return root.selectedIndex === index })
                                        item.tapped.connect(function() { root.selectedIndex = index })
                                        item.primUpdated.connect(root.primUpdated)
                                        item.openNumPadRequested.connect(root.openNumPadRequested)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            anchors.left: leftPanelBg.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: Theme.hairline
            color: Theme.separator
        }

        RadialProfileCanvas {
            id: profileCanvas
            anchors.left: leftPanelBg.right
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.margins: 12
            primitives: root.primitives
            workpiece: root.workpiece
            profileType: root.profileType
            editable: true
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onGrooveEdited: function(section, values) {
                if (root.grooveIndex < 0) return
                var d = JSON.parse(JSON.stringify(root.groove))
                if (!d[section]) d[section] = {}
                for (var key in values) d[section][key] = values[key]
                root.primUpdated(root.grooveIndex, d)
            }

            // the first groove's points, each a dot with an arrow to its tag,
            // all at 45 degrees: on the right P2 up and P1 down, on the left
            // P3 up and P4 down, each pair's tips in line - ``reach`` px past
            // the pair's outer point - their tags' near sides' middles on them
            readonly property var points: groovePoints
            readonly property real reach: 56
            readonly property real rightZ: points.length === 4 ? Math.max(points[0].z, points[1].z) : 0
            readonly property real leftZ: points.length === 4 ? Math.min(points[2].z, points[3].z) : 0
            readonly property var leaders: [
                { toZ: rightZ, dx: reach, slope: 1 },
                { toZ: rightZ, dx: reach, slope: -1 },
                { toZ: leftZ, dx: -reach, slope: -1 },
                { toZ: leftZ, dx: -reach, slope: 1 }
            ]
            markers: {
                var out = []
                for (var i = 0; i < points.length && i < 4; i++)
                    out.push({ leader: true, x: points[i].x, z: points[i].z, color: tags[i].accent,
                               toZ: leaders[i].toZ, dx: leaders[i].dx, slope: leaders[i].slope })
                return out
            }
            readonly property var tags: [p1Tag, p2Tag, p3Tag, p4Tag]
            // the tip of point ``i``'s arrow, in px, as MarkersActor draws it
            function tip(i) {
                if (points.length !== 4) return { x: 0, y: 0 }
                var l = leaders[i]
                var sx = px(points[i].z), sy = py(points[i].x)
                var ex = px(l.toZ) + l.dx
                return { x: ex, y: sy + l.slope * Math.abs(ex - sx) }
            }
            // room around the drawing for the tags
            fitPadding: root.groove ? reach + 80 : 0

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: Theme.outline
                border.width: Theme.hairline
            }

            GroovePointTag {
                id: p1Tag
                visible: !!root.groove
                point: 1
                axes: "XZ"
                x: profileCanvas.tip(0).x
                y: profileCanvas.tip(0).y - height / 2
            }
            GroovePointTag {
                id: p2Tag
                visible: !!root.groove
                point: 2
                axes: "X"
                x: profileCanvas.tip(1).x
                y: profileCanvas.tip(1).y - height / 2
            }
            GroovePointTag {
                id: p3Tag
                visible: !!root.groove
                point: 3
                axes: "X"
                x: profileCanvas.tip(2).x - width
                y: profileCanvas.tip(2).y - height / 2
            }
            GroovePointTag {
                id: p4Tag
                visible: !!root.groove
                point: 4
                axes: "XZ"
                x: profileCanvas.tip(3).x - width
                y: profileCanvas.tip(3).y - height / 2
            }

            // zoom, fit to screen and mirror - top-left, as on every profile canvas
            CanvasViewButtons {
                id: viewButtons
                canvas: profileCanvas
            }
        }
    }

    // A press anywhere but on the open card's Delete closes it
    SwipeDismissArea {
        openRow: root.openSwipeRow
        onDismissed: root.openSwipeRow = null
    }

    // never shown: how wide a groove's card is, for the list's width
    GrooveProfileCard { id: widthProbe; visible: false }

    Component { id: grooveCardComp; GrooveProfileCard {} }
    Component { id: repeatCardComp; RepeatProfileCard {} }
}
