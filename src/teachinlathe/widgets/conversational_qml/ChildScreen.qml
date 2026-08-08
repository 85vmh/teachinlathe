import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: operationEditor
    objectName: "childScreen"

    property var selectedProgram: null
    property var operationsModel: []
    property int activeOpIndex: -1

    property bool showBack: true
    property bool reorderMode: false

    property string titleText: (selectedProgram && (selectedProgram.name || (selectedProgram.header && selectedProgram.header.name)))
        ? "Editing: " + (selectedProgram.name || selectedProgram.header.name)
        : "Creating New Program"

    signal backRequested()
    signal generateGcodeRequested()
    signal addOperationTypeChosen(string type, int insertIndex)
    signal toggleGenerateGcode(int index, bool checked)
    signal toggleOptionalBlock(int index, bool checked)
    signal detailsRequested(int index)
    signal updateToolChange(int index, var payload)
    signal updatePositionAt(int index, var payload)
    signal updateDefineProfile(int index, var payload)
    signal updateDefineRadialProfile(int index, var payload)
    signal openProfileEditorRequested(int opIndex, var opData)
    signal openRadialProfileEditorRequested(int opIndex, var opData)
    signal updateFacing(int index, var payload)
    signal updateKnurling(int index, var payload)
    signal updateProfiling(int index, var payload)
    signal updateProfileRoughing(int index, var payload)
    signal updateProfileContour(int index, var payload)
    signal updateGrooveRoughing(int index, var payload)
    signal updateGrooveFinishing(int index, var payload)
    signal addProfileContourRequested(int index)
    signal updateDrilling(int index, var payload)
    signal updateThreading(int index, var payload)
    signal updateG33Threading(int index, var payload)
    signal updateParting(int index, var payload)
    signal updateTapping(int index, var payload)
    signal updateHeader(var payload)
    signal addProfilingFinishRequested(int index)
    signal openNumPadRequested(var field)
    signal teachXRequested(int index)
    signal teachZRequested(int index)
    signal addOperationRequested()
    signal reorderModeToggled(bool on)
    signal moveUpRequested(int index)
    signal moveDownRequested(int index)
    signal deleteOperationRequested(int index)

    width: parent ? parent.width : 1200
    height: parent ? parent.height : 800

    function receiveDetailsData(index, data) {
        if (index === -1) {
            detailsLoader.source = "HeaderDetailsView.qml"
        } else if (!data || !data.type) {
            detailsLoader.source = ""
        } else if (data.type === "changeTool") {
            detailsLoader.source = "ToolChangeDetailsView.qml"
        } else if (data.type === "positionAt") {
            detailsLoader.source = "PositionAtDetailsView.qml"
        } else if (data.type === "facing") {
            detailsLoader.source = "FacingDetailsView.qml"
        } else if (data.type === "knurling") {
            detailsLoader.source = "KnurlingDetailsView.qml"
        } else if (data.type === "profiling") {
            detailsLoader.source = "ProfilingDetailsView.qml"
        } else if (data.type === "profileRoughing") {
            detailsLoader.source = "ProfileRoughingDetailsView.qml"
        } else if (data.type === "profileContour") {
            detailsLoader.source = "ProfileContourDetailsView.qml"
        } else if (data.type === "grooveRoughing") {
            detailsLoader.source = "GrooveRoughingDetailsView.qml"
        } else if (data.type === "grooveFinishing") {
            detailsLoader.source = "GrooveFinishingDetailsView.qml"
        } else if (data.type === "defineProfile") {
            detailsLoader.source = "define_profile/ProfileDetailsView.qml"
        } else if (data.type === "defineRadialProfile") {
            detailsLoader.source = "define_radial_profile/RadialProfileDetailsView.qml"
        } else if (data.type === "drilling") {
            detailsLoader.source = "DrillingDetailsView.qml"
        } else if (data.type === "threading") {
            detailsLoader.source = "ThreadingDetailsView.qml"
        } else if (data.type === "g33Threading") {
            detailsLoader.source = "ThreadingDetailsView.qml"
        } else if (data.type === "parting") {
            detailsLoader.source = "PartingDetailsView.qml"
        } else if (data.type === "tapping") {
            detailsLoader.source = "TappingDetailsView.qml"
        } else {
            detailsLoader.source = ""
        }
        Qt.callLater(function () {
            if (detailsLoader.item && detailsLoader.item.applyData) {
                detailsLoader.item.applyData(index, data)
            }
        })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 6

            ConversationalLeftPane {
                id: leftPane
                operationsModel: operationEditor.operationsModel
                activeOpIndex: operationEditor.activeOpIndex
                reorderMode: operationEditor.reorderMode

                onProgramHeaderSelected: operationEditor.detailsRequested(-1)
                onOperationSelected: function(index) {
                    operationEditor.detailsRequested(index)
                }
                onAddOperationRequested: operationEditor.addOperationRequested()
                onOperationTypeChosen: function(type, insertIndex) {
                    operationEditor.addOperationTypeChosen(type, insertIndex)
                }
                onReorderModeToggled: function(on) {
                    operationEditor.reorderMode = on
                    operationEditor.reorderModeToggled(on)
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
                onMoveUpRequested: function(index) {
                    operationEditor.moveUpRequested(index)
                }
                onMoveDownRequested: function(index) {
                    operationEditor.moveDownRequested(index)
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredWidth: 6.5
                Layout.fillHeight: true
                color: "#ffffff"
                radius: 6
                border.color: "#ccc"
                border.width: 1

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

                    function onSaveRequested(updated) {
                        if (!updated || !updated.payload) return
                        var t = updated.payload.type || ""
                        if (updated.index === -1) {
                            if (operationEditor.updateHeader)
                                operationEditor.updateHeader(updated.payload)
                            return
                        }
                        if (t === "changeTool" && operationEditor.updateToolChange)
                            operationEditor.updateToolChange(updated.index, updated.payload)
                        else if (t === "positionAt" && operationEditor.updatePositionAt)
                            operationEditor.updatePositionAt(updated.index, updated.payload)
                        else if (t === "defineProfile" && operationEditor.updateDefineProfile)
                            operationEditor.updateDefineProfile(updated.index, updated.payload)
                        else if (t === "defineRadialProfile" && operationEditor.updateDefineRadialProfile)
                            operationEditor.updateDefineRadialProfile(updated.index, updated.payload)
                        else if (t === "facing" && operationEditor.updateFacing)
                            operationEditor.updateFacing(updated.index, updated.payload)
                        else if (t === "knurling" && operationEditor.updateKnurling)
                            operationEditor.updateKnurling(updated.index, updated.payload)
                        else if (t === "profiling" && operationEditor.updateProfiling)
                            operationEditor.updateProfiling(updated.index, updated.payload)
                        else if (t === "profileRoughing" && operationEditor.updateProfileRoughing)
                            operationEditor.updateProfileRoughing(updated.index, updated.payload)
                        else if (t === "profileContour" && operationEditor.updateProfileContour)
                            operationEditor.updateProfileContour(updated.index, updated.payload)
                        else if (t === "grooveRoughing" && operationEditor.updateGrooveRoughing)
                            operationEditor.updateGrooveRoughing(updated.index, updated.payload)
                        else if (t === "grooveFinishing" && operationEditor.updateGrooveFinishing)
                            operationEditor.updateGrooveFinishing(updated.index, updated.payload)
                        else if (t === "drilling" && operationEditor.updateDrilling)
                            operationEditor.updateDrilling(updated.index, updated.payload)
                        else if (t === "threading")
                            operationEditor.updateThreading(updated.index, updated.payload)
                        else if (t === "g33Threading")
                            operationEditor.updateG33Threading(updated.index, updated.payload)
                        else if (t === "parting")
                            operationEditor.updateParting(updated.index, updated.payload)
                        else if (t === "tapping")
                            operationEditor.updateTapping(updated.index, updated.payload)
                        else if (operationEditor.updateOperation)
                            operationEditor.updateOperation(updated.index, updated.payload)
                    }

                    function onTeachXRequested(i) {
                        operationEditor.teachXRequested(i)
                    }

                    function onTeachZRequested(i) {
                        operationEditor.teachZRequested(i)
                    }

                    function onOpenNumPadRequested(field) {
                        operationEditor.openNumPadRequested(field)
                    }

                    function onAddFinishRequested(i) {
                        if (operationEditor.addProfilingFinishRequested)
                            operationEditor.addProfilingFinishRequested(i)
                    }

                    function onAddProfileContourRequested(i) {
                        if (operationEditor.addProfileContourRequested)
                            operationEditor.addProfileContourRequested(i)
                    }

                    function onOpenProfileEditorRequested(opIdx, opData) {
                        operationEditor.openProfileEditorRequested(opIdx, opData)
                    }

                    function onOpenRadialProfileEditorRequested(opIdx, opData) {
                        operationEditor.openRadialProfileEditorRequested(opIdx, opData)
                    }
                }
            }
        }
    }
}
