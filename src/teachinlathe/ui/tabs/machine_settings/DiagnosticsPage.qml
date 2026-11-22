import QtQuick
import TeachInLathe

// The Performance page of Machine Settings: the diagnostics panel, scrolled.
Flickable {
    id: root

    contentHeight: diagnostics.implicitHeight + 48
    clip: true

    DiagnosticsPanel {
        id: diagnostics
        viewModel: DiagnosticsViewModel
        x: 24
        width: root.width - 48
    }
}
