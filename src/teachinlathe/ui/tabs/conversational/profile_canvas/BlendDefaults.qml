// BlendDefaults.qml — what a blend starts with, by its type: the domain's
// (conversational/model/profile_editing.py BLEND_DEFAULTS), for what the
// cards and the canvas show of a blend saved without a value.
pragma Singleton
import QtQuick
import TeachInLathe

QtObject {
    readonly property var values: ConversationalViewModel.blendDefaults
}
