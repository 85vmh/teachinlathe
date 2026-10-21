import QtQuick
import theme

Item {
    id: root
    required property var controller
    property var markers: ({})
    z: 1000000
    visible: controller.showTouches

    function clear() {
        for (var i = 0; i < children.length; ++i)
            children[i].destroy()
        markers = ({})
    }

    Connections {
        target: root.controller
        function onTouchesCleared() { root.clear() }
        function onTouchUpdated(id, sceneX, sceneY, down) {
            var marker = root.markers[id]
            var position = root.mapFromItem(null, sceneX, sceneY)
            if (down) {
                if (!marker) {
                    marker = touchMarker.createObject(root)
                    root.markers[id] = marker
                }
                marker.x = position.x - marker.width / 2
                marker.y = position.y - marker.height / 2
            } else if (marker) {
                marker.x = position.x - marker.width / 2
                marker.y = position.y - marker.height / 2
                delete root.markers[id]
                marker.release()
            }
        }
    }

    Component {
        id: touchMarker
        Rectangle {
            id: marker
            width: 40
            height: 40
            radius: 20
            color: Qt.rgba(Theme.success.r, Theme.success.g, Theme.success.b, 0.25)
            border.color: Qt.rgba(Theme.success.r, Theme.success.g, Theme.success.b, 0.6)
            border.width: 2

            function release() {
                appear.stop()
                fade.start()
            }

            NumberAnimation on scale {
                id: appear
                from: 0.65
                to: 1
                duration: 120
                easing.type: Easing.OutQuad
            }

            SequentialAnimation {
                id: fade
                ParallelAnimation {
                    NumberAnimation { target: marker; property: "opacity"; to: 0; duration: 220 }
                    NumberAnimation { target: marker; property: "scale"; to: 1.25; duration: 220 }
                }
                ScriptAction { script: marker.destroy() }
            }
        }
    }
}
