import QtQuick
import "tap.js" as TapShape

/*
 * Tap.qml — tarod, parametric, văzut din lateral
 * ---------------------------------------------------------------------------
 * Toate cotele sunt în MILIMETRI; conversia în pixeli se face o singură dată,
 * prin `pxPerMm`. Desenat ca Drill.qml: vârful în stânga, pe mijlocul laturii
 * din stânga a item-ului (`tipPoint`), corpul spre dreapta — orientarea 7.
 *
 *   1. Dinții = profil în V de 60°. Adâncimea lor e înălțimea triunghiului
 *      echilateral cu latura cât pasul:  H = P·√3/2  (1.299 la P = 1.5).
 *      Vârful dinților e pe diametrul D, fundul pe D − 2H.
 *   2. Conicitatea de atac = `leadThreads` pași la vârf, unde dinții cresc de
 *      la fundul filetului până la D. Vârful tarodului e plat, pe D − 2H.
 *   3. Partea filetată = `threadLengthD` diametre, dar cel puțin
 *      `minThreads` pași; apoi coada, netedă, pe `shankRatio`·D.
 *
 * ELICEA: sus și jos dinții sunt decalați cu P/2 — jos e jumătatea de tură de
 * după. Pe fața văzută, fiecare vârf de dinte de sus e legat de cel de jos
 * de după el: spre dreapta la filet dreapta (RH) "\", spre stânga la filet
 * stânga (LH) "/".
 *
 * Desenul e în tap.js, ca să-l poată desena la fel și canvasul unei
 * operații (Tapping).
 */
Item {
    id: root

    // ---- intrări ----------------------------------------------------------
    property real diameter:   10        // mm
    property real pitch:      1.5       // mm
    property bool rightHand:  true
    property real pxPerMm:    10
    property real leadThreads: 3        // pași în conicitatea de atac
    property real threadLengthD: 2      // partea filetată, în diametre
    property real minThreads: 8
    property real shankRatio: 0.8       // diametrul cozii / D
    property real helixLineWidth: 1     // px
    // Lungimea totală desenată [mm]; 0 = filet + coadă de `shankLengthD`
    // diametre. Altfel e impusă: filetul rămâne cât e, coada ia restul.
    property real length: 0
    property real shankLengthD: 2

    property color bodyColor:  "#e5a93b"
    property color edgeColor:  "#674c1b"

    // ---- derivate (mm), din tap.js --------------------------------------
    readonly property var _shape: ({ diameter: diameter, pitch: pitch, leadThreads: leadThreads,
                                     threadLengthD: threadLengthD, minThreads: minThreads,
                                     shankRatio: shankRatio, shankLengthD: shankLengthD,
                                     length: length })
    readonly property var _geometry: TapShape.geometry(_shape)
    readonly property real radius: diameter / 2
    readonly property real threadDepth: _geometry.depth
    readonly property real rootRadius: _geometry.root
    readonly property real leadLength: _geometry.lead
    readonly property real threadLength: _geometry.thread
    readonly property real totalLength: _geometry.total
    readonly property real shankRadius: _geometry.shank

    readonly property point tipPoint: Qt.point(0, height / 2)

    implicitWidth:  totalLength * pxPerMm
    implicitHeight: diameter * pxPerMm

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        readonly property var inputs: [root.diameter, root.pitch, root.rightHand, root.pxPerMm,
                                       root.leadThreads, root.threadLengthD, root.minThreads,
                                       root.shankRatio, root.helixLineWidth, root.length]
        onInputsChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            TapShape.paint(ctx, {
                diameter: root.diameter, pitch: root.pitch, rightHand: root.rightHand,
                leadThreads: root.leadThreads, threadLengthD: root.threadLengthD,
                minThreads: root.minThreads, shankRatio: root.shankRatio,
                shankLengthD: root.shankLengthD, helixLineWidth: root.helixLineWidth,
                length: root.length, bodyColor: root.bodyColor, edgeColor: root.edgeColor,
                pxPerMm: root.pxPerMm, tipX: root.tipPoint.x, tipY: root.tipPoint.y
            })
        }
    }
}
