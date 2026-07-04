import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.0
import "."

Item {
    id: main
    objectName: "mainScreen"

    property var programsModel
    property bool showBack: false
    property string selectedProgramId: ""
    property int pendingDeleteIndex: -1
    property string pendingDeleteName: ""
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
    readonly property int colCreatedW: 230
    readonly property int colLastEditW: 230
    readonly property int colActionsW: 180
    readonly property int cellFontPx: 16

    Component {
        id: iconButton
        Rectangle {
            id: btn
            width: 56
            height: 56
            radius: 6
            color: mouseArea.pressed ? "#e1f0ff" : "transparent"
            border.width: 1
            border.color: mouseArea.pressed ? "#8ec5ff" : "#BDBDBD"

            property url iconSource: ""
            property color tint: "#C62828"
            signal clicked()

            Image {
                id: baseImg
                anchors.centerIn: parent
                source: btn.iconSource
                sourceSize.width: 28
                sourceSize.height: 28
                visible: false
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            ColorOverlay {
                anchors.centerIn: baseImg
                width: baseImg.width
                height: baseImg.height
                source: baseImg
                color: btn.tint
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                onClicked: btn.clicked()
            }
        }
    }

    ConfirmDialog {
        id: deleteProgramDialog
        titleText: "Delete Program"
        confirmText: "Delete"
        messageText: {
            if (main.pendingDeleteName.length > 0)
                return "Delete \"" + main.pendingDeleteName + "\"?"
            return "Delete this program?"
        }
        onCancelled: {
            main.pendingDeleteIndex = -1
            main.pendingDeleteName = ""
        }
        onConfirmed: {
            if (main.pendingDeleteIndex >= 0)
                main.deleteProgramRequested(main.pendingDeleteIndex)
            main.pendingDeleteIndex = -1
            main.pendingDeleteName = ""
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.bottomMargin: 36

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#f5f5f5"
            radius: 6
            border.color: "#ccc"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 1
                spacing: 4

                // HEADER (fixed 40px)
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    color: "#d6d6d6"
                    radius: 4

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

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

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

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                        Label {
                            text: "Date Created"
                            Layout.minimumWidth: main.colCreatedW
                            Layout.preferredWidth: main.colCreatedW
                            Layout.maximumWidth: main.colCreatedW
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

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

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

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                        Label {
                            text: "Program Operations"
                            Layout.fillWidth: true
                            font.pixelSize: main.cellFontPx
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                        Label {
                            text: "Actions"
                            Layout.minimumWidth: main.colActionsW
                            Layout.preferredWidth: main.colActionsW
                            Layout.maximumWidth: main.colActionsW
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
                    ScrollBar.vertical: ScrollBar {
                        width: 18
                        policy: ScrollBar.AlwaysOn
                    }

                    delegate: Rectangle {
                        id: rowRect
                        width: ListView.view ? ListView.view.width - 18 : 400
                        height: 100
                        radius: 0

                        color: rowMouseArea.pressed
                               ? "#dbeafe"
                               : (index % 2 === 0 ? "#f0f0f0" : "#e5e5e5")
                        border.width: (selectedProgramId === programId || rowMouseArea.pressed) ? 1 : 0
                        border.color: rowMouseArea.pressed ? "#8ec5ff" : (selectedProgramId === programId ? "#8ec5ff" : "transparent")

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

                            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

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

                            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                            Label {
                                text: createdDate
                                Layout.minimumWidth: main.colCreatedW + 24
                                Layout.preferredWidth: main.colCreatedW + 24
                                Layout.maximumWidth: main.colCreatedW + 24
                                font.pixelSize: main.cellFontPx
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                Layout.alignment: Qt.AlignVCenter
                            }

                            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

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

                            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

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
                                    spacing: 8

                                    Repeater {
                                        model: operationsCell.displayOperations

                                        delegate: Rectangle {
                                            readonly property var parts: String(modelData).split("::")
                                            readonly property bool enabledBadge: parts.length > 1 ? parts[0] === "1" : true
                                            readonly property string badgeText: parts.length > 1 ? parts.slice(1).join("::") : String(modelData)
                                            radius: 8
                                            border.width: 1
                                            border.color: enabledBadge ? "#d6d6d6" : "#dcdcdc"
                                            color: enabledBadge ? "#f9f9f9" : "#efefef"
                                            opacity: enabledBadge ? 1.0 : 0.65
                                            implicitHeight: 32
                                            implicitWidth: Math.min(parent.width, opLabel.implicitWidth + 20)

                                            Text {
                                                id: opLabel
                                                anchors.centerIn: parent
                                                text: parent.badgeText
                                                font.pixelSize: main.cellFontPx
                                                color: parent.enabledBadge ? "#202020" : "#7a7a7a"
                                            }
                                        }
                                    }

                                    Rectangle {
                                        visible: operationsCell.showOverflowBadge
                                        radius: 8
                                        border.width: 1
                                        border.color: "#d6d6d6"
                                        color: "#f9f9f9"
                                        width: overflowText.implicitWidth + 20
                                        height: 32

                                        Text {
                                            id: overflowText
                                            anchors.centerIn: parent
                                            text: "......."
                                            font.pixelSize: main.cellFontPx
                                            color: "#202020"
                                        }
                                    }
                                }

                                Text {
                                    visible: !parent.hasOperations
                                    anchors.centerIn: parent
                                    text: "No operations yet, tap to change that"
                                    font.pixelSize: main.cellFontPx
                                    color: "#4f4f4f"
                                }
                            }

                            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#cccccc" }

                            Item {
                                Layout.minimumWidth: main.colActionsW
                                Layout.preferredWidth: main.colActionsW
                                Layout.maximumWidth: main.colActionsW
                                Layout.fillHeight: true
                                z: 2

                                Row {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 24
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 20

                                    Loader {
                                        sourceComponent: iconButton
                                        onLoaded: {
                                            item.iconSource = "icons/duplicate_item.svg"
                                            item.tint = "#4F4F4F"
                                            item.clicked.connect(function() {
                                                main.duplicateProgramRequested(index)
                                            })
                                        }
                                    }

                                    Loader {
                                        sourceComponent: iconButton
                                        onLoaded: {
                                            item.iconSource = "icons/delete_icon.svg"
                                            item.tint = "#C62828"
                                            item.clicked.connect(function() {
                                                main.pendingDeleteIndex = index
                                                main.pendingDeleteName = programName
                                                deleteProgramDialog.open()
                                            })
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Top fade
                Rectangle {
                    anchors { left: parent.left; right: parent.right; top: parent.top }
                    height: 100
                    visible: list.contentY > 0
                    z: 1
                    gradient: Gradient {
                        orientation: Gradient.Vertical
                        GradientStop { position: 0.0; color: "#f5f5f5" }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                }

                // Bottom fade
                Rectangle {
                    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                    height: 100
                    visible: list.contentY + list.height < list.contentHeight - 1
                    z: 1
                    gradient: Gradient {
                        orientation: Gradient.Vertical
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 1.0; color: "#f5f5f5" }
                    }
                }

                }  // Item wrapper
            }
        }
    }
}
