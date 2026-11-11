import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import common

Item {
    id: operationEditor
    objectName: "childScreen"

    required property var selectedProgram
    required property var operationsModel
    required property int activeOpIndex
    // The selected operation's editor view model (or the header's), or null.
    required property var editor

    property string titleText: (selectedProgram && (selectedProgram.name || (selectedProgram.header && selectedProgram.header.name)))
        ? "Editing: " + (selectedProgram.name || selectedProgram.header.name)
        : "Creating New Program"

    signal backRequested()
    signal generateGcodeRequested()
    signal addOperationTypeChosen(string type, int insertIndex)
    signal addDefineProfileChosen(string profileType, int insertIndex)
    signal toggleGenerateGcode(int index, bool checked)
    signal toggleOptionalBlock(int index, bool checked)
    signal detailsRequested(int index)
    signal openNumPadRequested(var field)
    signal openKeyboardRequested(var field)
    signal moveOperationRequested(int fromIndex, int toIndex)
    signal deleteOperationRequested(int index)
    signal duplicateOperationRequested(int index)

    // The details pane for each kind of editor.
    readonly property var editorViews: ({
        "header": "HeaderDetailsView.qml",
        "positionAt": "PositionAtDetailsView.qml",
        "facing": "FacingVisualDetailsView.qml",
        "turning": "TurningVisualDetailsView.qml",
        "turningFinish": "TurningFinishVisualDetailsView.qml",
        "knurling": "KnurlingDetailsView.qml",
        "profiling": "ProfilingDetailsView.qml",
        "profileRoughing": "ProfileRoughingVisualDetailsView.qml",
        "profileContour": "ProfileContourVisualDetailsView.qml",
        "grooveRoughing": "GrooveRoughingVisualDetailsView.qml",
        "grooveBidirectional": "GrooveBidirectionalVisualDetailsView.qml",
        "grooveFinishing": "GrooveFinishingVisualDetailsView.qml",
        "defineProfile": "define_profile/ProfileDetailsView.qml",
        "importDxfProfile": "define_profile/ProfileDetailsView.qml",
        "defineRadialProfile": "define_radial_profile/RadialProfileDetailsView.qml",
        "drilling": "DrillingVisualDetailsView.qml",
        "threading": "ThreadingDetailsView.qml",
        "g33Threading": "G33ThreadingVisualDetailsView.qml",
        "parting": "PartingVisualDetailsView.qml",
        "tapping": "TappingVisualDetailsView.qml"
    })

    // A new editor: the pane for its kind, made with it - or, the same kind,
    // kept, so the pane keeps its scroll, and handed it. A pane shows only
    // what its editor says.
    function showEditor() {
        var view = editor ? (editorViews[editor.operationType] || "") : ""
        if (view === "")
            detailsLoader.source = ""
        else if (!String(detailsLoader.source).endsWith("/" + view))
            detailsLoader.setSource(Qt.resolvedUrl(view), { editor: editor })
        else if (detailsLoader.item)
            detailsLoader.item.editor = editor
    }

    onEditorChanged: showEditor()
    Component.onCompleted: showEditor()

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacingSmall

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.paneGap

            ConversationalLeftPane {
                id: leftPane
                operationsModel: operationEditor.operationsModel
                programDatum: (operationEditor.selectedProgram && operationEditor.selectedProgram.datum) || 1
                activeOpIndex: operationEditor.activeOpIndex

                onProgramHeaderSelected: operationEditor.detailsRequested(-1)
                onOperationSelected: function(index) {
                    operationEditor.detailsRequested(index)
                }
                onOperationTypeChosen: function(type, insertIndex) {
                    operationEditor.addOperationTypeChosen(type, insertIndex)
                }
                onDefineProfileChosen: function(profileType, insertIndex) {
                    operationEditor.addDefineProfileChosen(profileType, insertIndex)
                }
                onGenerateToggled: function(index, checked) {
                    operationEditor.toggleGenerateGcode(index, checked)
                }
                onOptionalToggled: function(index, checked) {
                    operationEditor.toggleOptionalBlock(index, checked)
                }
                onDeleteOperationRequested: function(index) {
                    operationEditor.deleteOperationRequested(index)
                }
                onDuplicateOperationRequested: function(index) {
                    operationEditor.duplicateOperationRequested(index)
                }
                onMoveOperationRequested: function(fromIndex, toIndex) {
                    operationEditor.moveOperationRequested(fromIndex, toIndex)
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.preferredWidth: 7
                Layout.fillHeight: true

                Flickable {
                    id: detailsFlick
                    anchors.fill: parent
                    anchors.margins: 1
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    contentWidth: width
                    contentHeight: detailsContent.height
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                    Item {
                        id: detailsContent
                        width: detailsFlick.width
                        height: Math.max(
                            detailsFlick.height,
                            detailsLoader.item && detailsLoader.item.implicitHeight > 0
                                ? detailsLoader.item.implicitHeight
                                : detailsLoader.implicitHeight
                        )

                        Loader {
                            id: detailsLoader
                            width: parent.width
                            height: parent.height
                            asynchronous: false
                            onSourceChanged: detailsFlick.contentY = 0
                        }
                    }
                }

                Connections {
                    id: detailsCon
                    target: detailsLoader.item
                    ignoreUnknownSignals: true
                    enabled: !!target

                    function onOpenNumPadRequested(field) {
                        operationEditor.openNumPadRequested(field)
                    }

                    function onOpenKeyboardRequested(field) {
                        operationEditor.openKeyboardRequested(field)
                    }
                }
            }
        }
    }

    SwipeDismissArea {
        openRow: leftPane.openSwipeRow
        onDismissed: leftPane.openSwipeIndex = -1
    }
}
