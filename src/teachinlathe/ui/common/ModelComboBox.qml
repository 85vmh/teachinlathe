// ModelComboBox.qml — a ComboBox that shows what its model says, and only
// asks for a change: ``selectedIndex`` is bound by its user to the model, a
// pick reports ``picked``, and the box follows once the model has it. A
// plain ComboBox sets its own currentIndex on a pick, which cuts a binding
// on it off (see the "View holds no state" rules in CLAUDE.md): here
// currentIndex is bound to selectedIndex again after each pick. Use it, not
// ComboBox.
import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    // the item the model has chosen
    property int selectedIndex: -1
    // the item picked, asked for
    signal picked(int index)

    currentIndex: selectedIndex
    onActivated: function(index) {
        control.picked(index)
        // the pick set currentIndex itself: back to the model's
        control.currentIndex = Qt.binding(function() { return control.selectedIndex })
    }
}
