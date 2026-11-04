import QtQuick
import "drill.js" as DrillShape

/*
 * Drill.qml — burghiu elicoidal, parametric, văzut din lateral
 * ---------------------------------------------------------------------------
 * Toate cotele sunt în MILIMETRI; conversia în pixeli se face o singură dată,
 * prin `pxPerMm`.
 *
 * Desenat cu vârful în stânga, pe mijlocul laturii din stânga a item-ului
 * (`tipPoint`), corpul spre dreapta — cum stă la orientarea 7, spre -Z.
 *
 *   1. Vârful = con cu unghiul `tipAngle`; lungimea lui e (D/2) / tan(unghi/2),
 *      0 la 180° (fund plat, U drill).
 *   2. Canalele = `fluteLengthD` diametre, cu două canale elicoidale.
 *   3. Coada = `shankLengthD` diametre, netedă.
 *
 * ELICEA: unghiul `helixAngle` față de axă (30° = burghiu tip N). Pasul unui
 * canal, cât avansează pe axă într-o rotație completă, e  π·D / tan(unghi),
 * deci liniile se răresc cu diametrul. Văzută din lateral, muchia canalului e
 * proiecția elicei, o cosinusoidă: de sus până jos pe jumătate de pas. Cu
 * două canale, câte una la fiecare jumătate de pas. Fiecare muchie are o
 * pereche, la `helixGapPx` pixeli de ea (perpendicular, pe mijlocul
 * liniei): cele două margini ale fâșiei de lângă canal.
 *
 * Elice dreapta (RH) coboară de la stânga la dreapta "\", stânga (LH) urcă "/".
 *
 * Desenul e în drill.js, ca să-l poată desena la fel și canvasul unei
 * operații (Drilling).
 */
Item {
    id: root

    // ---- intrări ----------------------------------------------------------
    property real diameter:   10        // mm
    property real tipAngle:   118       // grade
    property bool rightHand:  true
    property real pxPerMm:    10
    property real helixAngle: 30        // grade față de axă
    property real helixLineWidth: 1     // px
    // Distanța dintre cele două linii ale unei perechi [px], perpendicular pe
    // ele, la mijloc. De aici se reglează.
    property real helixGapPx: 3
    property real fluteLengthD: 5       // lungimea canalelor, în diametre
    property real shankLengthD: 2       // lungimea cozii, în diametre
    // Cât din burghiu se desenează [mm], de la vârf; 0 = tot (vârf + canale +
    // coadă de mai sus). Doar îl taie: canalele, elicea și coada rămân unde
    // sunt, așa că un burghiu arată la fel în orice loc e desenat.
    property real length: 0

    property color bodyColor:  "#e5a93b"
    property color edgeColor:  "#674c1b"

    // ---- derivate (mm), din drill.js ------------------------------------
    readonly property var _lengths: DrillShape.lengths({ diameter: diameter, tipAngle: tipAngle,
                                                         fluteLengthD: fluteLengthD,
                                                         shankLengthD: shankLengthD, length: length })
    readonly property real radius: diameter / 2
    readonly property real pointLength: _lengths.point
    readonly property real fluteLength: _lengths.flute
    readonly property real shankLength: _lengths.shank
    // cât se desenează: tot burghiul, sau cât taie `length`
    readonly property real totalLength: _lengths.drawn
    readonly property real helixLead: Math.PI * diameter / Math.tan(helixAngle * Math.PI / 180)

    // vârful, în pixeli, în item
    readonly property point tipPoint: Qt.point(0, height / 2)

    implicitWidth:  totalLength * pxPerMm
    implicitHeight: diameter * pxPerMm

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        readonly property var inputs: [root.diameter, root.tipAngle, root.rightHand, root.pxPerMm,
                                       root.helixAngle, root.helixLineWidth, root.helixGapPx,
                                       root.fluteLengthD, root.shankLengthD,
                                       root.length]
        onInputsChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            DrillShape.paint(ctx, {
                diameter: root.diameter, tipAngle: root.tipAngle, rightHand: root.rightHand,
                helixAngle: root.helixAngle, helixLineWidth: root.helixLineWidth,
                helixGapPx: root.helixGapPx, fluteLengthD: root.fluteLengthD,
                shankLengthD: root.shankLengthD, length: root.length,
                bodyColor: root.bodyColor, edgeColor: root.edgeColor,
                pxPerMm: root.pxPerMm, tipX: root.tipPoint.x, tipY: root.tipPoint.y
            })
        }
    }
}
