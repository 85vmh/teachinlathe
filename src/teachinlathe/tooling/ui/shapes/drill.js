// drill.js — burghiul din Drill.qml, desenat pe un context 2D dat: aceeași
// formă oriunde e desenat, în Tool Library sau pe canvasul unei operații.
// Vezi Drill.qml pentru cote, elice și canale.
//
// `d`: diameter, tipAngle, rightHand, helixAngle, helixLineWidth, helixGapPx,
// fluteLengthD, shankLengthD, length (mm, 0 = proporțional), bodyColor,
// edgeColor; pxPerMm; tipX, tipY - vârful, în px; corpul spre dreapta.
.pragma library

// Lungimile, în mm: vârful, canalele, coada, totalul.
function lengths(d) {
    var r = d.diameter / 2
    var point = d.tipAngle >= 179.999 ? 0 : r / Math.tan(d.tipAngle / 2 * Math.PI / 180)
    var body = d.length > 0 ? Math.max(0, d.length - point)
                            : (d.fluteLengthD + d.shankLengthD) * d.diameter
    var flute = body * d.fluteLengthD / (d.fluteLengthD + d.shankLengthD)
    return { point: point, flute: flute, shank: body - flute, total: point + body }
}

function paint(ctx, d) {
    var k = d.pxPerMm, r = d.diameter / 2
    if (r <= 0 || k <= 0) return
    var l = lengths(d)
    var h = l.point, fEnd = h + l.flute, end = l.total

    ctx.save()
    ctx.translate(d.tipX, d.tipY)
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
    ctx.fillStyle = d.bodyColor
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
    ctx.strokeStyle = d.edgeColor
    ctx.lineWidth = d.helixLineWidth / k
    var lead = Math.PI * d.diameter / Math.tan(d.helixAngle * Math.PI / 180)
    var half = lead / 2, steps = 24
    var sign = d.rightHand ? 1 : -1
    // Perechea, la helixGapPx măsurați perpendicular pe linie: pe mijloc,
    // unde linia face helixAngle cu axa, asta înseamnă gap / sin(unghi) de-a
    // lungul axei.
    var gap = d.helixGapPx / k / Math.sin(d.helixAngle * Math.PI / 180)  // mm, pe axă
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
    // de la o jumătate de pas înaintea vârfului, ca prima să intre în con,
    // până după capătul canalelor
    for (var x0 = fEnd - half * Math.ceil(fEnd / half + 1); x0 < fEnd; x0 += half) {
        helixLine(x0)
        helixLine(x0 + gap)
    }
    ctx.restore()

    // capătul canalelor, unde începe coada
    ctx.strokeStyle = d.edgeColor
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
