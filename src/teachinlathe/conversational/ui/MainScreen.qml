import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import theme 1.0
import common 1.0

Item {
    id: main
    objectName: "mainScreen"
    Rectangle {
        anchors.fill: parent
        color: Theme.surface
        z: -1
    }

    property var programsModel
    property bool showBack: false
    property string selectedProgramId: ""
    // The program row swiped open, and to which side: 1 Delete, -1 Duplicate
    property int openSwipeIndex: -1
    property int openSwipeSide: 0
    property string sortField: "last_edit"
    property bool createdAscending: true
    property bool lastEditAscending: false
    signal backRequested()
    signal addNewProgramRequested()
    signal editProgramRequested(var arg)
    signal deleteProgramRequested(int index)
    signal duplicateProgramRequested(int index)

    anchors.fill: parent

    function applyDefaultSort() {
        if (main.programsModel && main.programsModel.sortPrograms)
            main.programsModel.sortPrograms(main.sortField, main.lastEditAscending)
    }

    Component.onCompleted: applyDefaultSort()
    onProgramsModelChanged: applyDefaultSort()

    // Column width constants
    readonly property int colIndexW: 56
    readonly property int colNameW: 360
    readonly property int colCreatedW: 150
    readonly property int colLastEditW: 150
    readonly property int cellFontPx: 16

    ColumnLayout {
        anchors.fill: parent

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.surface
            radius: Theme.radius
            border.color: Theme.outline
            border.width: Theme.hairline

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 1
                spacing: 4

                // HEADER (fixed 40px)
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.buttonHeight
                    color: Theme.separator
                    radius: Theme.radiusSmall

                    RowLayout {
                        anchors.fill: parent
                        anchors.rightMargin: 18
                        spacing: 0

                        Label {
                            text: "#"
                            Layout.minimumWidth: main.colIndexW
                            Layout.preferredWidth: main.colIndexW
                            Layout.maximumWidth: main.colIndexW
                            font.pixelSize: main.cellFontPx
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.outline }

                        Label {
                            text: "Name"
                            Layout.minimumWidth: main.colNameW
                            Layout.preferredWidth: main.colNameW
                            Layout.maximumWidth: main.colNameW
                            font.pixelSize: main.cellFontPx
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.outline }

                        Label {
                            text: "Date Created"
                            Layout.minimumWidth: main.colCreatedW - 24
                            Layout.preferredWidth: main.colCreatedW - 24
                            Layout.maximumWidth: main.colCreatedW - 24
                            font.pixelSize: main.cellFontPx
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    main.createdAscending = (main.sortField === "created_date") ? !main.createdAscending : true
                                    main.sortField = "created_date"
                                    if (main.programsModel && main.programsModel.sortPrograms)
                                        main.programsModel.sortPrograms("created_date", main.createdAscending)
                                }
                            }
                        }

                        Label {
                            text: main.createdAscending ? "▲" : "▼"
                            Layout.minimumWidth: 24
                            Layout.maximumWidth: 24
                            font.pixelSize: main.cellFontPx
                            opacity: main.sortField === "created_date" ? 1.0 : 0.45
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.outline }

                        Label {
                            text: "Last Edited"
                            Layout.minimumWidth: main.colLastEditW - 24
                            Layout.preferredWidth: main.colLastEditW - 24
                            Layout.maximumWidth: main.colLastEditW - 24
                            font.pixelSize: main.cellFontPx
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    main.lastEditAscending = (main.sortField === "last_edit") ? !main.lastEditAscending : true
                                    main.sortField = "last_edit"
                                    if (main.programsModel && main.programsModel.sortPrograms)
                                        main.programsModel.sortPrograms("last_edit", main.lastEditAscending)
                                }
                            }
                        }

                        Label {
                            text: main.lastEditAscending ? "▲" : "▼"
                            Layout.minimumWidth: 24
                            Layout.maximumWidth: 24
                            font.pixelSize: main.cellFontPx
                            opacity: main.sortField === "last_edit" ? 1.0 : 0.45
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.outline }

                        Label {
                            text: "Program Operations"
                            Layout.fillWidth: true
                            font.pixelSize: main.cellFontPx
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                        }

                    }
                }

                // LIST
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                ListView {
                    id: list
                    anchors.fill: parent
                    clip: true
                    model: main.programsModel || programsModel
                    currentIndex: -1
                    onMovementStarted: main.openSwipeIndex = -1
                    ScrollBar.vertical: ScrollBar {
                        width: 18
                        policy: ScrollBar.AlwaysOn
                    }

                    // Swiped left a program shows Delete, right Duplicate (see SwipeRow)
                    delegate: SwipeRow {
                        id: rowRect
                        width: ListView.view ? ListView.view.width - 18 : 400
                        height: 100
                        actionWidth: height
                        swipeSide: main.openSwipeIndex === index ? main.openSwipeSide : 0

                        contentColor: rowMouseArea.pressed
                                      ? Theme.selection
                                      : (index % 2 === 0 ? Theme.surfaceSunken : Theme.outlineDisabled)
                        contentBorderWidth: (selectedProgramId === programId || rowMouseArea.pressed) ? 1 : 0
                        contentBorderColor: rowMouseArea.pressed ? Theme.accentBorder : (selectedProgramId === programId ? Theme.accentBorder : "transparent")

                        onSwipeOpened: function(side) {
                            main.openSwipeSide = side
                            main.openSwipeIndex = index
                        }
                        onSwipeClosed: {
                            if (main.openSwipeIndex === index)
                                main.openSwipeIndex = -1
                        }
                        onDeleteRequested: {
                            main.openSwipeIndex = -1
                            main.deleteProgramRequested(index)
                        }
                        onDuplicateRequested: {
                            main.openSwipeIndex = -1
                            main.duplicateProgramRequested(index)
                        }

                        MouseArea {
                            id: rowMouseArea
                            anchors.fill: parent
                            onClicked: main.editProgramRequested(index)
                        }

                        RowLayout {
                            anchors.fill: parent
                            spacing: 0

                            Label {
                                text: (index + 1) + "."
                                Layout.minimumWidth: main.colIndexW
                                Layout.preferredWidth: main.colIndexW
                                Layout.maximumWidth: main.colIndexW
                                font.pixelSize: main.cellFontPx
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                Layout.alignment: Qt.AlignVCenter
                            }

                            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.outline }

                            Label {
                                text: programName
                                Layout.minimumWidth: main.colNameW
                                Layout.preferredWidth: main.colNameW
                                Layout.maximumWidth: main.colNameW
                                leftPadding: 8
                                font.pixelSize: main.cellFontPx
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                                Layout.alignment: Qt.AlignVCenter
                            }

                            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.outline }

                            Label {
                                text: createdDate
                                Layout.minimumWidth: main.colCreatedW
                                Layout.preferredWidth: main.colCreatedW
                                Layout.maximumWidth: main.colCreatedW
                                font.pixelSize: main.cellFontPx
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                Layout.alignment: Qt.AlignVCenter
                            }

                            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.outline }

                            Label {
                                text: lastEditDate
                                Layout.minimumWidth: main.colLastEditW
                                Layout.preferredWidth: main.colLastEditW
                                Layout.maximumWidth: main.colLastEditW
                                font.pixelSize: main.cellFontPx
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                Layout.alignment: Qt.AlignVCenter
                            }

                            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.outline }

                            Label {
                                text: programOperations
                                Layout.fillWidth: true
                                visible: false
                            }

                            Item {
                                id: operationsCell
                                Layout.fillWidth: true
                                Layout.fillHeight: true

                                property string operationsText: programOperations
                                readonly property bool hasOperations: operationsText !== "No operations yet, tap to change that"
                                property var displayOperations: []
                                property bool showOverflowBadge: false

                                function badgeWidthFor(text) {
                                    badgeMetrics.text = text
                                    return Math.min(width - 24, Math.ceil(badgeMetrics.width) + 20)
                                }

                                function recomputeBadges() {
                                    if (!hasOperations || width <= 24) {
                                        displayOperations = []
                                        showOverflowBadge = false
                                        return
                                    }

                                    var ops = operationsText ? operationsText.split("||") : []
                                    var maxWidth = width - 24
                                    var gap = 8
                                    var row = 1
                                    var rowWidth = 0
                                    var visible = []
                                    var overflow = false
                                    var ellipsisWidth = badgeWidthFor(".......")

                                    for (var i = 0; i < ops.length; ++i) {
                                        var op = ops[i]
                                        var badgeWidth = badgeWidthFor(op)
                                        var needed = visible.length === 0 || rowWidth === 0 ? badgeWidth : rowWidth + gap + badgeWidth

                                        if (needed <= maxWidth) {
                                            visible.push(op)
                                            rowWidth = needed
                                            continue
                                        }

                                        if (row === 1) {
                                            row = 2
                                            rowWidth = 0
                                            i -= 1
                                            continue
                                        }

                                        overflow = true
                                        break
                                    }

                                    if (overflow) {
                                        while (visible.length > 0) {
                                            var rebuiltRow = 1
                                            var rebuiltWidth = 0
                                            for (var j = 0; j < visible.length; ++j) {
                                                var itemWidth = badgeWidthFor(visible[j])
                                                var totalNeeded = (rebuiltWidth === 0) ? itemWidth : rebuiltWidth + gap + itemWidth
                                                if (totalNeeded <= maxWidth) {
                                                    rebuiltWidth = totalNeeded
                                                    continue
                                                }
                                                rebuiltRow += 1
                                                rebuiltWidth = itemWidth
                                            }
                                            var overflowNeeded = rebuiltWidth === 0 ? ellipsisWidth : rebuiltWidth + gap + ellipsisWidth
                                            if (rebuiltRow < 2 || overflowNeeded <= maxWidth) break
                                            visible.pop()
                                        }
                                    }

                                    displayOperations = visible
                                    showOverflowBadge = overflow
                                }

                                onWidthChanged: recomputeBadges()
                                onHasOperationsChanged: recomputeBadges()
                                onOperationsTextChanged: recomputeBadges()

                                TextMetrics {
                                    id: badgeMetrics
                                    font.pixelSize: main.cellFontPx
                                }

                                Flow {
                                    visible: parent.hasOperations
                                    width: parent.width - 24
                                    anchors.left: parent.left
                                    anchors.leftMargin: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: Theme.spacingSmall

                                    Repeater {
                                        model: operationsCell.displayOperations

                                        delegate: Rectangle {
                                            readonly property var parts: String(modelData).split("::")
                                            readonly property bool enabledBadge: parts.length > 1 ? parts[0] === "1" : true
                                            readonly property string badgeText: parts.length > 1 ? parts.slice(1).join("::") : String(modelData)
                                            radius: Theme.radiusLarge
                                            border.width: Theme.hairline
                                            border.color: enabledBadge ? Theme.outline : Theme.outlineDisabled
                                            color: enabledBadge ? Theme.surfaceAlt : Theme.surfaceSunken
                                            opacity: enabledBadge ? 1.0 : 0.65
                                            implicitHeight: 32
                                            implicitWidth: Math.min(parent.width, opLabel.implicitWidth + 20)

                                            Text {
                                                id: opLabel
                                                anchors.centerIn: parent
                                                text: parent.badgeText
                                                font.pixelSize: main.cellFontPx
                                                color: parent.enabledBadge ? Theme.foregroundStrong : Theme.foregroundFaint
                                            }
                                        }
                                    }

                                    Rectangle {
                                        visible: operationsCell.showOverflowBadge
                                        radius: Theme.radiusLarge
                                        border.width: Theme.hairline
                                        border.color: Theme.outline
                                        color: Theme.surfaceAlt
                                        width: overflowText.implicitWidth + 20
                                        height: 32

                                        Text {
                                            id: overflowText
                                            anchors.centerIn: parent
                                            text: "......."
                                            font.pixelSize: main.cellFontPx
                                            color: Theme.foregroundStrong
                                        }
                                    }
                                }

                                Text {
                                    visible: !parent.hasOperations
                                    anchors.centerIn: parent
                                    text: "No operations yet, tap to change that"
                                    font.pixelSize: main.cellFontPx
                                    color: Theme.foregroundMuted
                                }
                            }

                        }
                    }
                }

                ScrollFades {
                    anchors.fill: parent
                    flickable: list
                }

                }  // Item wrapper
            }
        }
    }

    SwipeDismissArea {
        openRow: main.openSwipeIndex >= 0 ? list.itemAtIndex(main.openSwipeIndex) : null
        onDismissed: main.openSwipeIndex = -1
    }
}
