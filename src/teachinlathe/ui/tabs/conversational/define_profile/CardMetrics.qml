// CardMetrics.qml — the sizes a Define Profile's cards share, for their dividers
// and inputs to line up from one card to the next.
pragma Singleton
import QtQuick
import theme

QtObject {
    readonly property int radius:          Theme.radiusLarge
    readonly property int padding:         Theme.margin
    readonly property int margin:          Theme.spacing
    readonly property int rowGap:          20
    readonly property int blendButtonSize: 50
    // as wide as the blend button: the dividers as far from either edge
    readonly property int iconArea:        blendButtonSize
    readonly property int iconSize:        56
    readonly property int labelWidth:      56
    readonly property int inputWidth:      120
    // after the fields: the last divider and the blend button
    readonly property int endWidth:        Theme.hairline + margin + blendButtonSize
}
