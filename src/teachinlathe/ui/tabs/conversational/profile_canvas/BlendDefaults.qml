// BlendDefaults.qml — what a blend starts with, by its type. The G-code's defaults
// for a saved blend that lacks a value are conversational/model/data_types.py's
// ProfileBlend: an undercut's there have to stay these.
pragma Singleton
import QtQuick

QtObject {
    readonly property var values: ({
        chamfer:         { chamfer_width: 1.0 },
        fillet:          { fillet_radius: 1.0 },
        undercut_din509: { undercut_radius: 0.4, undercut_depth: 0.4, undercut_length: 2.5 }
    })
}
