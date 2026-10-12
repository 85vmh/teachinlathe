import QtQuick

/*
 * Reamer.qml — alezor, parametric, văzut din lateral
 * ---------------------------------------------------------------------------
 * Toate cotele sunt în MILIMETRI; conversia în pixeli se face o singură dată,
 * prin `pxPerMm`. Desenat ca Drill.qml: vârful în stânga, pe mijlocul laturii
 * din stânga a item-ului (`tipPoint`), corpul spre dreapta — orientarea 7.
 *
 *   1. Capătul = plat, cu o teșitură de atac la 45°, de `chamferRatio`·D
 *      (cel puțin `minChamfer`, cel mult un sfert din rază).
 *   2. Canalele = `fluteLengthD` diametre, `flutes` canale pe circumferință,
 *      încheiate cu o teșitură la 45° în jos, până la coadă.
 *   3. Coada = `shankLengthD` diametre, subțiată la `shankRatio`·D.
 *
 * CANALELE: elice dreapta mică, `helixAngle` față de axă. Canalul i e la
 * unghiul  φ = 2π·i/n + 2π·x/pas  pe circumferință, cu pasul π·D/tan(unghi).
 * Se vede doar fața dinspre privitor, φ între 0 și π, unde muchia e la
 * y = −r·cos φ:  de sus în jos — elice dreapta "\", ca la Drill.qml. Fiecare
 * muchie are o pereche la `helixGapPx` pixeli: marginea faţetei de lângă
 * canal.
 */
Item {
    id: root

    // ---- intrări ----------------------------------------------------------
    property real diameter:   10        // mm
    property real helixAngle: 10        // grade față de axă
    property real pxPerMm:    10
    property int  flutes:     6
    property real helixLineWidth: 1     // px
    property real helixGapPx: 3         // distanța dintre liniile unei perechi [px]
    property real chamferRatio: 0.08    // teșitura de atac / D
    property real minChamfer:  0.3      // mm
    property real fluteLengthD: 4       // lungimea canalelor, în diametre
    property real shankLengthD: 2.6     // lungimea cozii, în diametre
    property real shankRatio:   0.8     // diametrul cozii / D
    // Lungimea totală desenată [mm]; 0 = proporțională cu diametrul (canale +
    // coadă de mai sus). Altfel e impusă: canalele rămân cât sunt (cel mult
    // 70% din ea), coada ia restul — ca la Tap.qml.
    property real length: 0

    property color bodyColor:  "#e5a93b"
    property color edgeColor:  "#674c1b"

    // ---- derivate (mm) ----------------------------------------------------
    readonly property real radius: diameter / 2
    readonly property real chamfer: Math.min(radius / 4, Math.max(minChamfer, chamferRatio * diameter))
    readonly property real shankRadius: shankRatio * radius
    // teșitura din spatele canalelor, la 45°: de la D la coadă
    readonly property real backChamfer: radius - shankRadius
    readonly property real totalLength: length > 0 ? length
                                        : (fluteLengthD + shankLengthD) * diameter
    // până la începutul teșiturii din spate
    readonly property real fluteLength: Math.min(fluteLengthD * diameter, 0.7 * totalLength)
    readonly property real helixLead: Math.PI * diameter
                                      / Math.tan(Math.max(0.1, helixAngle) * Math.PI / 180)

    readonly property point tipPoint: Qt.point(0, height / 2)

    implicitWidth:  totalLength * pxPerMm
    implicitHeight: diameter * pxPerMm

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        readonly property var inputs: [root.diameter, root.helixAngle, root.pxPerMm, root.flutes,
                                       root.helixLineWidth, root.helixGapPx, root.chamferRatio,
                                       root.minChamfer, root.fluteLengthD, root.shankLengthD,
                                       root.shankRatio, root.length]
        onInputsChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var k = root.pxPerMm, r = root.radius, c = root.chamfer
            var fEnd = root.fluteLength, bEnd = fEnd + root.backChamfer, end = root.totalLength
            var rs = root.shankRadius
            if (r <= 0) return

            ctx.save()
            ctx.translate(root.tipPoint.x, root.tipPoint.y)
            ctx.scale(k, k)                          // y în jos, ca pe ecran

            // partea cu canale: teșitura de atac, diametrul plin, teșitura
            // din spate
            function flutedOutline() {
                ctx.beginPath()
                ctx.moveTo(0, -(r - c))
                ctx.lineTo(c, -r)
                ctx.lineTo(fEnd, -r)
                ctx.lineTo(bEnd, -rs)
                ctx.lineTo(bEnd, rs)
                ctx.lineTo(fEnd, r)
                ctx.lineTo(c, r)
                ctx.lineTo(0, r - c)
                ctx.closePath()
            }

            function outline() {
                ctx.beginPath()
                ctx.moveTo(0, -(r - c))
                ctx.lineTo(c, -r)
                ctx.lineTo(fEnd, -r)
                ctx.lineTo(bEnd, -rs)
                ctx.lineTo(end, -rs)
                ctx.lineTo(end, rs)
                ctx.lineTo(bEnd, rs)
                ctx.lineTo(fEnd, r)
                ctx.lineTo(c, r)
                ctx.lineTo(0, r - c)
                ctx.closePath()
            }

            outline()
            ctx.fillStyle = root.bodyColor
            ctx.fill()

            // muchiile canalelor, tăiate la partea cu canale
            ctx.save()
            flutedOutline()
            ctx.clip()
            ctx.strokeStyle = root.edgeColor
            ctx.lineWidth = root.helixLineWidth / k
            var n = Math.max(1, root.flutes), lead = root.helixLead
            // Perechea, la helixGapPx pe ecran, perpendicular pe linie: pe
            // mijloc, unde linia face helixAngle cu axa, asta înseamnă
            // gap / sin(unghi) de-a lungul axei (ca la Drill.qml).
            var gapPhase = 2 * Math.PI * (root.helixGapPx / k
                           / Math.sin(Math.max(0.1, root.helixAngle) * Math.PI / 180)) / lead
            var steps = 48
            function fluteLine(phase0) {
                var drawing = false
                ctx.beginPath()
                for (var j = 0; j <= steps; j++) {
                    var x = bEnd * j / steps
                    var phi = phase0 + 2 * Math.PI * x / lead
                    phi = ((phi % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)
                    if (phi > Math.PI) { drawing = false; continue }   // fața din spate
                    var y = -r * Math.cos(phi)
                    if (!drawing) { ctx.moveTo(x, y); drawing = true } else ctx.lineTo(x, y)
                }
                ctx.stroke()
            }
            for (var i = 0; i < n; i++) {
                var phase = 2 * Math.PI * (i + 0.5) / n
                fluteLine(phase)
                fluteLine(phase + gapPhase)
            }
            ctx.restore()

            // muchiile celor două teșituri, pe partea cu canale
            ctx.strokeStyle = root.edgeColor
            ctx.lineWidth = 1 / k
            ctx.beginPath()
            ctx.moveTo(c, -r); ctx.lineTo(c, r)
            ctx.moveTo(fEnd, -r); ctx.lineTo(fEnd, r)
            ctx.moveTo(bEnd, -rs); ctx.lineTo(bEnd, rs)
            ctx.stroke()

            outline()
            ctx.lineJoin = "round"
            ctx.lineWidth = 1.5 / k
            ctx.stroke()
            ctx.restore()
        }
    }
}
