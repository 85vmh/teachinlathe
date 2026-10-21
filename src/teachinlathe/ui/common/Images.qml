pragma Singleton
import QtQuick

/*
 * Every image and icon lives in images/ beside this file, in one flat folder.
 * Screens ask for one by name - Images.url("delete_icon.svg") - instead of
 * counting ".." back to it, so a screen can move without its icons breaking.
 */
QtObject {
    function url(name) {
        return Qt.resolvedUrl("images/" + name)
    }
}
