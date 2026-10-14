import QtQuick

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

    // ---- derivate (mm) ----------------------------------------------------
    readonly property real radius: diameter / 2
    readonly property real threadDepth: pitch * Math.sqrt(3) / 2
    // Un pas prea mare pentru diametru ar trece dinții de axă: fundul rămâne
    // cel puțin la o treime din rază.
    readonly property real rootRadius: Math.max(radius - threadDepth, radius / 3)
    readonly property real leadLength: leadThreads * pitch
    readonly property real threadLength: Math.max(threadLengthD * diameter, minThreads * pitch)
    readonly property real totalLength: length > 0 ? Math.max(length, threadLength)
                                                   : threadLength + shankLengthD * diameter
    readonly property real shankRadius: Math.min(radius, Math.max(rootRadius, shankRatio * radius))

    readonly property point tipPoint: Qt.point(0, height / 2)

    implicitWidth:  totalLength * pxPerMm
    implicitHeight: diameter * pxPerMm

    // Raza vârfurilor dinților la x: de la fundul filetului la vârf până la
    // D/2 la capătul conicității.
    function crestRadius(x) {
        if (x >= leadLength) return radius
        return rootRadius + (radius - rootRadius) * Math.max(0, x) / leadLength
    }

    // Raza profilului la x, pe o latură; `phase` decalează dinții (P/2 jos).
    function profileRadius(x, phase) {
        var u = ((x - phase) / pitch) % 1
        if (u < 0) u += 1
        var tri = 1 - Math.abs(2 * u - 1)             // 0 la fund, 1 la vârf
        return Math.min(rootRadius + tri * (radius - rootRadius), crestRadius(x))
    }

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
            var k = root.pxPerMm, P = root.pitch
            var tEnd = root.threadLength, end = root.totalLength
            if (root.radius <= 0 || P <= 0) return

            ctx.save()
            ctx.translate(root.tipPoint.x, root.tipPoint.y)
            ctx.scale(k, k)                          // y în jos, ca pe ecran

            // Profilul: vârfurile și funduri dinților, plus capetele
            // conicității, ca muchiile să cadă exact pe ele.
            function stations(phase) {
                var xs = [0, root.leadLength, tEnd]
                for (var n = Math.floor(-phase / P); phase + n * P <= tEnd; n++) {
                    var x0 = phase + n * P
                    xs.push(x0, x0 + P / 2)
                }
                xs = xs.filter(function(x) { return x >= 0 && x <= tEnd })
                xs.sort(function(a, b) { return a - b })
                return xs
            }
            var top = stations(0), bottom = stations(P / 2)

            ctx.beginPath()
            ctx.moveTo(0, root.profileRadius(0, P / 2))
            ctx.lineTo(0, -root.profileRadius(0, 0))
            for (var i = 0; i < top.length; i++)
                ctx.lineTo(top[i], -root.profileRadius(top[i], 0))
            ctx.lineTo(tEnd, -root.shankRadius)
            ctx.lineTo(end, -root.shankRadius)
            ctx.lineTo(end, root.shankRadius)
            ctx.lineTo(tEnd, root.shankRadius)
            for (var j = bottom.length - 1; j >= 0; j--)
                ctx.lineTo(bottom[j], root.profileRadius(bottom[j], P / 2))
            ctx.closePath()
            ctx.fillStyle = root.bodyColor
            ctx.fill()
            ctx.lineJoin = "miter"
            ctx.lineWidth = 1.2 / k
            ctx.strokeStyle = root.edgeColor
            ctx.stroke()

            // Elicea pe fața văzută: fiecare vârf de sus spre vârful de jos
            // de după el, jumătate de pas mai încolo.
            ctx.lineWidth = root.helixLineWidth / k
            var dir = root.rightHand ? 1 : -1
            for (var n = 0; n * P <= tEnd; n++) {
                var xt = n * P + P / 2                       // vârf de sus
                var xb = xt + dir * P / 2                    // vârful de jos
                if (xt > tEnd || xb < 0 || xb > tEnd) continue
                ctx.beginPath()
                ctx.moveTo(xt, -root.crestRadius(xt))
                ctx.lineTo(xb, root.crestRadius(xb))
                ctx.stroke()
            }

            ctx.restore()
        }
    }
}
