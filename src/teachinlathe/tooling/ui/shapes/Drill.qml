import QtQuick

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
    // Lungimea totală desenată [mm]; 0 = proporțională cu diametrul (vârf +
    // canale + coadă de mai sus). Altfel lungimea e impusă, iar canalele și
    // coada își păstrează raportul — așa un burghiu se poate desena la scară
    // fixă, în cât loc are, cu diametrul la mărimea lui.
    property real length: 0

    property color bodyColor:  "#e5a93b"
    property color edgeColor:  "#674c1b"

    // ---- derivate (mm) ----------------------------------------------------
    readonly property real radius: diameter / 2
    readonly property real pointLength: tipAngle >= 179.999 ? 0
                                        : radius / Math.tan(tipAngle / 2 * Math.PI / 180)
    readonly property real bodyLength: length > 0 ? Math.max(0, length - pointLength)
                                                  : (fluteLengthD + shankLengthD) * diameter
    readonly property real fluteLength: bodyLength * fluteLengthD / (fluteLengthD + shankLengthD)
    readonly property real shankLength: bodyLength - fluteLength
    readonly property real totalLength: pointLength + bodyLength
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
            var k = root.pxPerMm, r = root.radius
            var h = root.pointLength, fEnd = h + root.fluteLength, end = root.totalLength
            if (r <= 0) return

            ctx.save()
            ctx.translate(root.tipPoint.x, root.tipPoint.y)
            ctx.scale(k, k)                          // y în jos, ca pe ecran

            function outline() {
                ctx.beginPath()
                ctx.moveTo(0, 0)
                ctx.lineTo(h, -r)
                ctx.lineTo(end, -r)
                ctx.lineTo(end, r)
                ctx.lineTo(h, r)
                ctx.closePath()
            }

            outline()
            ctx.fillStyle = root.bodyColor
            ctx.fill()

            // muchiile canalelor, tăiate la vârf + canale
            ctx.save()
            ctx.beginPath()
            ctx.moveTo(0, 0)
            ctx.lineTo(h, -r)
            ctx.lineTo(fEnd, -r)
            ctx.lineTo(fEnd, r)
            ctx.lineTo(h, r)
            ctx.closePath()
            ctx.clip()
            ctx.strokeStyle = root.edgeColor
            ctx.lineWidth = root.helixLineWidth / k
            var half = root.helixLead / 2, steps = 24
            var sign = root.rightHand ? 1 : -1
            // Perechea, la helixGapPx măsurați perpendicular pe linie: pe
            // mijloc, unde linia face helixAngle cu axa, asta înseamnă
            // gap / sin(unghi) de-a lungul axei.
            var gap = root.helixGapPx / k
                      / Math.sin(root.helixAngle * Math.PI / 180)  // mm, pe axă
            function helixLine(x0) {
                ctx.beginPath()
                for (var i = 0; i <= steps; i++) {
                    var t = i / steps
                    var x = x0 + t * half
                    var y = -sign * r * Math.cos(Math.PI * t)
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                }
                ctx.stroke()
            }
            // de la o jumătate de pas înaintea vârfului, ca prima să intre
            // în con, până după capătul canalelor
            for (var x0 = fEnd - half * Math.ceil(fEnd / half + 1); x0 < fEnd; x0 += half) {
                helixLine(x0)
                helixLine(x0 + gap)
            }
            ctx.restore()

            // capătul canalelor, unde începe coada
            ctx.strokeStyle = root.edgeColor
            ctx.lineWidth = 1 / k
            ctx.beginPath()
            ctx.moveTo(fEnd, -r); ctx.lineTo(fEnd, r)
            ctx.stroke()

            outline()
            ctx.lineJoin = "round"
            ctx.lineWidth = 1.5 / k
            ctx.stroke()
            ctx.restore()
        }
    }
}
