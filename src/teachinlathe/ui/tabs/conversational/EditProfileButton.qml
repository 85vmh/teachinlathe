// EditProfileButton.qml — opens a profile's full screen editor, at the top
// right of its canvas: as the operations list's Add New is drawn, as far in
// from the canvas's top and right as the view buttons are from its top and
// left.
import QtQuick
import common
import theme

OperationIconTextButton {
    anchors {
        top: parent.top; right: parent.right
        topMargin: Theme.zoomInOutFitMirrorButtonMarginTop
        rightMargin: Theme.zoomInOutFitMirrorButtonMarginLeft
    }
    iconSource: Images.url("edit-profile.svg")
    tint: Theme.success
    color: Theme.surface
    buttonHeight: Theme.buttonHeight
    iconSize: 28
    fontPixelSize: 15
}
