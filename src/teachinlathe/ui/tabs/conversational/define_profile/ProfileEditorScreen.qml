// ProfileEditorScreen.qml — full-screen editor for Define Profile primitives
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import tabs.conversational
import tabs.conversational.define_radial_profile
import tabs.conversational.profile_canvas
import common.touchable_input
import theme
import common

Item {
    id: root
    objectName: "profileEditorScreen"

    // ── Public API ──────────────────────────────────────────────────────────────
    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place the profile shown comes from, and every edit goes to. The
    // screen keeps nothing of the profile: an edit is a new list of
    // primitives, sent to the editor, which the profile then shows.
    required property var editor
    readonly property var op: editor.operation
    readonly property bool isDxfProfile: op.type === "importDxfProfile"
    readonly property int    profileId: op.profile_id !== undefined ? Math.round(Number(op.profile_id)) : 0
    readonly property string profileType: op.profile_type !== undefined ? String(op.profile_type) : "od"
    readonly property var    primitives: op.profile_primitives || []
    readonly property var    workpiece: op.workpiece || ({})
    // view state: which primitive or blend is selected, on the cards and the canvas
    property int    selectedPrimIndex:   -1
    // view state: see selectedPrimIndex
    property int    selectedBlendIndex:  -1
    // view state: the selected primitive shown on the canvas by its end point
    // alone, as when chosen on its card; picked on the canvas, its whole stretch.
    property bool   selectedEndOnly:     true
    // view state: the card swiped open on its Delete (a SwipeRow), or null
    property var    openSwipeRow:        null
    // What each primitive's end corner can have, and how its blend's icon turns
    readonly property var _corners: cornerGeometry.cornersOf(root.primitives, root.profileType)

    readonly property int addRowHeight:    80
    readonly property int addButtonHeight: 60

    Geometry { id: cornerGeometry }

    signal backRequested()
    signal openNumPadRequested(var field)

    // ── Data functions ──────────────────────────────────────────────────────────
    // another operation: the drawing fitted to it, nothing selected
    onEditorChanged: {
        selectedPrimIndex = -1
        selectedBlendIndex = -1
        profileCanvas.resetView()
    }

    // What is done to the primitives is the editor's (profile_editing.py): a
    // card's edit, a blend, a new primitive where the one before ends, one
    // deleted. The screen only keeps the selection on them.
    function primUpdated(idx, newData) {
        root.editor.updatePrimitive(idx, newData)
    }

    function _selectPrimitive(idx, endOnly) {
        root.selectedEndOnly    = endOnly
        root.selectedPrimIndex  = idx
        root.selectedBlendIndex = -1
    }

    // A primitive's blend button: which blend, then on it with what that starts with
    function _chooseBlend(idx) {
        blendPopup.primIdx = idx
        blendPopup.corner = root._corners[idx] || null
        blendPopup.open()
    }

    // the selection moved to ``idx`` and scrolled to it, once its card is in place
    function _selectAndShow(idx, scrollBottom) {
        _selectPrimitive(idx, true)
        if (idx < 0) return
        Qt.callLater(function() {
            Qt.callLater(function() { root._scrollTo(idx, scrollBottom) })
        })
    }

    function primDeleted(idx) {
        if (idx <= 0) return
        var wasLast = idx >= root.primitives.length - 1
        _selectAndShow(root.editor.deletePrimitive(idx), wasLast)
    }

    function addPrimitiveAbove(primType) {
        if (root.selectedPrimIndex <= 0) return
        _selectAndShow(root.editor.insertPrimitive(root.selectedPrimIndex, primType), true)
    }

    function addPrimitiveBelow(primType) {
        var idx = root.selectedPrimIndex < 0 ? root.primitives.length : root.selectedPrimIndex + 1
        _selectAndShow(root.editor.insertPrimitive(idx, primType), true)
    }

    onSelectedPrimIndexChanged:  Qt.callLater(_scrollToSelected)
    onSelectedBlendIndexChanged: Qt.callLater(_scrollToBlend)

    function _scrollToSelected() {
        if (root.selectedPrimIndex < 0) return
        _scrollTo(root.selectedPrimIndex, false)
    }
    function _scrollToBlend() {
        if (root.selectedBlendIndex < 0) return
        _scrollTo(root.selectedBlendIndex, true)
    }

    function _scrollTo(targetIdx, scrollBottom) {
        var col = primRepeater.parent
        if (!col) return
        for (var i = 0; i < col.children.length; i++) {
            var child = col.children[i]
            if (typeof child.mi !== "undefined" && child.mi === targetIdx) {
                var childY = child.y
                var childH = child.height
                var fl     = primScroll.contentItem
                var visTop = fl.contentY
                var visBot = visTop + primScroll.height
                if (scrollBottom) {
                    if (childY + childH > visBot)
                        fl.contentY = childY + childH - primScroll.height + 8
                    else if (childY < visTop)
                        fl.contentY = Math.max(0, childY - 8)
                } else {
                    if (childY < visTop)
                        fl.contentY = Math.max(0, childY - 8)
                    else if (childY + childH > visBot)
                        fl.contentY = childY + childH - primScroll.height + 8
                }
                break
            }
        }
    }

    IntValidator { id: intVal; bottom: 1; top: 999 }

    // ── Screen background ────────────────────────────────────────────────────────
    // the window's, round the two panes - as on the program's screen (ChildScreen)
    Rectangle {
        anchors.fill: parent
        color: Theme.windowBackground
    }

    // ── Full layout ──────────────────────────────────────────────────────────────
    // No title bar here — the AppShell QML title bar is used (Back/Done driven via headerState)
    Item {
        anchors.fill: parent

        // ── Editor area: 35% list | 65% canvas ───────────────────────────────────
        Item {
            anchors.fill: parent

            // ── Left panel ────────────────────────────────────────────────────────
            // the primitives' cards in a box, rounded and outlined as the
            // program screen's panes, and the add buttons a card of their own
            // under it - the box ending a card's spacing above it
            Item {
                id: leftPanelBg
                anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                width: (parent.width - Theme.paneGap) * 0.35

                Card {
                    id: listBox
                    width: parent.width
                    height: addButtonsCard.y - leftPanel.spacing
                }

                ColumnLayout {
                    id: leftPanel
                    anchors.fill: parent
                    // the gap between the box and the buttons' card: the
                    // spacing between two cards
                    spacing: Theme.spacingSmall

                    // Profile ID + Type row: a DXF's alone. A Define Profile
                    // got its id and its type when it was created.
                    Item {
                        visible: root.isDxfProfile
                        Layout.fillWidth: true
                        Layout.preferredHeight: 80
                        Layout.leftMargin: 12; Layout.rightMargin: 12

                        // Left half: Profile ID
                        RowLayout {
                            anchors { left: parent.left; right: centerDivider.left; top: parent.top; bottom: parent.bottom }
                            spacing: Theme.spacingSmall
                            Label {
                                text: "Profile ID:"
                                font.pointSize: 11; font.family: "Noto Sans"
                                color: Theme.foreground
                            }
                            NumpadField {
                                Layout.preferredWidth: 70
                                settingName: "defineProfile.profile_id"
                                validatorObject: intVal
                                value: root.profileId
                                formatter: function(v) { return (v == null) ? "" : String(Math.round(Number(v))) }
                                hAlign: Text.AlignHCenter
                                onOpenRequested: function(field) { root.openNumPadRequested(field) }
                                onValueCommitted: function(value) { root.editor.edit({ profile_id: Math.round(value) }) }
                            }
                        }

                        Rectangle {
                            id: centerDivider
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.verticalCenter
                            width: Theme.hairline; height: Theme.inputHeight; color: Theme.separator
                        }

                        // Right half: Type OD/ID
                        RowLayout {
                            anchors { left: centerDivider.right; right: parent.right; top: parent.top; bottom: parent.bottom }
                            spacing: Theme.spacingSmall
                            Item { Layout.preferredWidth: 8 }
                            Label {
                                text: "Type:"
                                font.pointSize: 11; font.family: "Noto Sans"
                                color: Theme.foreground
                            }
                            ModelRadioButton {
                                text: "OD"
                                font.pointSize: 11; font.family: "Noto Sans"
                                checked: root.profileType === "od"
                                onChosen: root.editor.edit({ profile_type: "od" })
                            }
                            ModelRadioButton {
                                text: "ID"
                                font.pointSize: 11; font.family: "Noto Sans"
                                checked: root.profileType === "id"
                                onChosen: root.editor.edit({ profile_type: "id" })
                            }
                        }
                    }

                    // Divider
                    Rectangle {
                        visible: root.isDxfProfile
                        Layout.fillWidth: true; height: 1
                        color: Theme.surfaceAlt
                        Layout.leftMargin: 4; Layout.rightMargin: 4
                    }

                    // Scrollable primitive cards
                    // in the box, as far in from its edges as two cards are apart
                    Item {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        Layout.margins: Theme.spacingSmall

                    ScrollView {
                        id: primScroll
                        anchors.fill: parent

                        Connections {
                            target: primScroll.contentItem
                            function onMovementStarted() { root.openSwipeRow = null }
                        }
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        contentWidth: availableWidth
                        background: Rectangle { color: Theme.surface }

                        Column {
                            width: primScroll.availableWidth
                            spacing: Theme.spacingSmall

                            Repeater {
                                id: primRepeater
                                // by their number, not the array: an edit, a new array,
                                // keeps the cards; only adding and deleting remake them
                                model: root.primitives.length

                                delegate: Column {
                                    property var md: root.primitives[index]
                                    property int mi: index
                                    width: parent ? parent.width : 0
                                    spacing: Theme.spacingSmall

                                    onMdChanged: {
                                        // past the end, for a moment, as a card is deleted
                                        if (!md) return
                                        if (primLdr.item)  primLdr.item.primData  = md
                                        if (blendLdr.item) blendLdr.item.primData = md
                                    }

                                    // Swiped left a card shows Delete (see SwipeRow);
                                    // the start point is never deleted
                                    SwipeRow {
                                        id: primSwipe
                                        width: parent.width
                                        height: primLdr.height
                                        swipeEnabled: mi > 0
                                        duplicateEnabled: false
                                        actionGap: Theme.spacingSmall
                                        actionRadius: 8
                                        swipeSide: root.openSwipeRow === primSwipe ? 1 : 0
                                        onSwipeOpened: root.openSwipeRow = primSwipe
                                        onSwipeClosed: if (root.openSwipeRow === primSwipe) root.openSwipeRow = null
                                        onDeleteRequested: {
                                            root.openSwipeRow = null
                                            root.primDeleted(mi)
                                        }

                                    Loader {
                                        id: primLdr
                                        width: parent.width
                                        sourceComponent: {
                                            if (!md) return null
                                            if (md.type === "startPoint") return startPointComp
                                            if (md.type === "lineTo")     return lineToComp
                                            if (md.type === "arcTo")      return arcToComp
                                            if (md.type === "grooveTo")   return grooveToComp
                                            return null
                                        }
                                        onLoaded: {
                                            item.primData   = md
                                            item.primIdx    = mi
                                            item.isSelected = Qt.binding(function() { return root.selectedPrimIndex === mi })
                                            if ("corner" in item) {
                                                item.corner = Qt.binding(function() { return root._corners[mi] || null })
                                                item.blendRequested.connect(root._chooseBlend)
                                            }
                                            item.tapped.connect(function() {
                                                root._selectPrimitive(mi, true)
                                            })
                                            item.primUpdated.connect(root.primUpdated)
                                            item.openNumPadRequested.connect(root.openNumPadRequested)
                                        }
                                    }
                                    }

                                    // Swiped left a blend's card shows Delete, which clears the blend
                                    SwipeRow {
                                        id: blendSwipe
                                        width: parent.width
                                        height: blendLdr.height
                                        visible: blendLdr.active
                                        duplicateEnabled: false
                                        actionGap: Theme.spacingSmall
                                        actionRadius: 8
                                        swipeSide: root.openSwipeRow === blendSwipe ? 1 : 0
                                        onSwipeOpened: root.openSwipeRow = blendSwipe
                                        onSwipeClosed: if (root.openSwipeRow === blendSwipe) root.openSwipeRow = null
                                        onDeleteRequested: {
                                            root.openSwipeRow = null
                                            if (root.selectedBlendIndex === mi)
                                                root.selectedBlendIndex = -1
                                            root.editor.addBlend(mi, "none")
                                        }

                                    Loader {
                                        id: blendLdr
                                        width: parent.width
                                        active:  md !== null && md !== undefined &&
                                                 md.blend !== undefined && md.blend !== null &&
                                                 md.blend.type !== "none"
                                        sourceComponent: {
                                            if (!md || !md.blend) return null
                                            if (md.blend.type === "undercut_din509") return undercutDin509BlendComp
                                            if (md.blend.type === "chamfer" || md.blend.type === "fillet") return chamferFilletBlendComp
                                            return null
                                        }
                                        onLoaded: {
                                            item.primData   = md
                                            item.primIdx    = mi
                                            item.isSelected = Qt.binding(function() { return root.selectedBlendIndex === mi })
                                            item.corner     = Qt.binding(function() { return root._corners[mi] || null })
                                            item.tapped.connect(function() {
                                                root.selectedBlendIndex = mi
                                                root.selectedPrimIndex  = -1
                                            })
                                            item.primUpdated.connect(root.primUpdated)
                                            item.openNumPadRequested.connect(root.openNumPadRequested)
                                        }
                                    }
                                    }
                                }
                            }
                        }
                    }

                    ScrollFades {
                        anchors.fill: parent
                        flickable: primScroll.contentItem
                        color: Theme.surface
                    }

                    } // Item wrapper for scroll + fades

                    // Add primitive buttons: a card of their own, as wide as
                    // the list's box
                    Card {
                        id: addButtonsCard
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.addRowHeight

                        RowLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            spacing: Theme.margin

                            Repeater {
                                model: [
                                    { label: "LineTo", direction: "Above", type: "lineTo", iconEnd: Images.url("move_up_icon.svg") },
                                    { label: "ArcTo", direction: "Above", type: "arcTo", iconEnd: Images.url("move_up_icon.svg") },
                                    { label: "LineTo", direction: "Below", type: "lineTo", iconEnd: Images.url("move_down_icon.svg") },
                                    { label: "ArcTo", direction: "Below", type: "arcTo", iconEnd: Images.url("move_down_icon.svg") }
                                ]

                                delegate: Button {
                                    id: addPrimitiveButton
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: root.addButtonHeight
                                    enabled: modelData.direction === "Above" ? root.selectedPrimIndex > 0 : root.primitives.length > 0
                                    font.pixelSize: Theme.fontBody
                                    font.family: "Noto Sans"

                                    contentItem: RowLayout {
                                        spacing: 4

                                        Image {
                                            Layout.preferredWidth: 36
                                            Layout.preferredHeight: Theme.buttonHeightSmall
                                            sourceSize.width: 36
                                            sourceSize.height: 36
                                            source: Images.url("add_op_icon.svg")
                                            fillMode: Image.PreserveAspectFit
                                            opacity: addPrimitiveButton.enabled ? 1.0 : Theme.disabledOpacity
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.label
                                            font: addPrimitiveButton.font
                                            color: Theme.foreground
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                            wrapMode: Text.WordWrap
                                            maximumLineCount: 1
                                            opacity: addPrimitiveButton.enabled ? 1.0 : Theme.disabledOpacity
                                        }

                                        Image {
                                            Layout.preferredWidth: 32
                                            Layout.preferredHeight: 32
                                            sourceSize.width: 32
                                            sourceSize.height: 32
                                            source: modelData.iconEnd
                                            fillMode: Image.PreserveAspectFit
                                            opacity: addPrimitiveButton.enabled ? 1.0 : Theme.disabledOpacity
                                        }
                                    }

                                    background: Rectangle {
                                        radius: Theme.radius
                                        color: parent.pressed ? Theme.selection : parent.hovered ? Theme.hover : Theme.surfaceAlt
                                        border.color: Theme.separator
                                        border.width: Theme.hairline
                                        opacity: parent.enabled ? 1.0 : 0.55
                                    }

                                    onClicked: {
                                        if (modelData.direction === "Above")
                                            root.addPrimitiveAbove(modelData.type)
                                        else
                                            root.addPrimitiveBelow(modelData.type)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ── Right panel: canvas, in its own box, the window's background
            // between the two ─────────────────────────────────────────────────
            Card {
                id: rightPanelBg
                anchors {
                    left: leftPanelBg.right; right: parent.right
                    top: parent.top; bottom: parent.bottom
                    leftMargin: Theme.paneGap
                }
            }

            ColumnLayout {
                anchors {
                    fill: rightPanelBg
                    margins: Theme.paneInset
                }
                spacing: Theme.spacingSmall

                Item {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true

                    ProfileCanvas {
                        id: profileCanvas
                        anchors.fill: parent
                        // the profile in the stock's outline colour and
                        // weight, as the operations draw it
                        profileLineColor: "#6b7280"
                        profileLineWidth: 1.5
                        primitives:         root.primitives
                        profileType:        root.profileType
                        workpiece:          root.workpiece
                        selectedPrimIndex:  root.selectedPrimIndex
                        selectedBlendIndex: root.selectedBlendIndex
                        selectionEndOnly:   root.selectedEndOnly
                        onPrimitiveSelected: function(idx) {
                            root._selectPrimitive(idx, false)
                        }
                        onBlendSelected: function(idx) {
                            root.selectedBlendIndex = idx
                            root.selectedPrimIndex  = -1
                        }
                        tagEditable: true
                        onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
                        onDiameterEdited: function(idx, diameter) {
                            var arr = profileCanvas.primitivesWithDiameter(idx, diameter)
                            if (arr) root.editor.setPrimitives(arr)
                        }
                        onBlendEdited: function(idx, field, value) {
                            var d = JSON.parse(JSON.stringify(root.primitives[idx]))
                            d.blend[field] = value
                            root.primUpdated(idx, d)
                        }
                        onSelectionCleared: {
                            root.selectedPrimIndex = -1
                            root.selectedBlendIndex = -1
                        }

                        Rectangle {
                            anchors.fill: parent
                            color: "transparent"
                            border.color: Theme.separator; border.width: Theme.hairline
                        }
                    }

                    // zoom, fit to screen and mirror - top-left, as on every profile canvas
                    CanvasViewButtons {
                        canvas: profileCanvas
                    }
                }
            }
        }
    }

    // A press anywhere but on the open card's Delete closes it
    SwipeDismissArea {
        openRow: root.openSwipeRow
        onDismissed: root.openSwipeRow = null
    }

    // ── Card component references ────────────────────────────────────────────────
    BlendTypePopup {
        id: blendPopup
        property int primIdx: -1
        onBlendChosen: function(blendType) { root.editor.addBlend(primIdx, blendType) }
    }

    Component { id: startPointComp; StartPointCard {} }
    Component { id: lineToComp;     LineToCard {}     }
    Component { id: arcToComp;      ArcToCard {}      }
    Component { id: grooveToComp;   GrooveProfileCard { startFromProfile: true } }
    Component { id: chamferFilletBlendComp; ChamferFilletBlendCard {} }
    Component { id: undercutDin509BlendComp; UndercutDin509BlendCard {} }
}
