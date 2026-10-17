// drill.js — burghiul din Drill.qml, desenat pe un context 2D dat: aceeași
// formă oriunde e desenat, în Tool Library sau pe canvasul unei operații.
// Vezi Drill.qml pentru cote, elice și canale.
//
// `d`: diameter, tipAngle, rightHand, helixAngle, helixLineWidth, helixGapPx,
// fluteLengthD, shankLengthD, length, bodyColor, edgeColor; pxPerMm; tipX,
// tipY - vârful, în px; corpul spre dreapta.
//
// Burghiul e mereu același, dat doar de diametru și unghiul vârfului: vârf,
// `fluteLengthD` diametre de canale, `shankLengthD` de coadă - ca în backplot
// (programs/ui/backplot/actors/tool_outlines.py, `drill`). `length` [mm], dacă
// e dat, doar îl taie: se desenează de la vârf atât cât, cât încape, iar
// elicea, canalele și coada rămân unde sunt - așa arată la fel oriunde.
.pragma library

// Lungimile, în mm: vârful, canalele, coada, totalul burghiului, și cât din
// el se desenează (`drawn`).
function lengths(d) {
    var r = d.diameter / 2
    var point = d.tipAngle >= 179.999 ? 0 : r / Math.tan(d.tipAngle / 2 * Math.PI / 180)
    var flute = d.fluteLengthD * d.diameter
    var shank = d.shankLengthD * d.diameter
    var total = point + flute + shank
    return { point: point, flute: flute, shank: shank, total: total,
             drawn: d.length > 0 ? Math.min(d.length, total) : total }
}

function paint(ctx, d) {
    var k = d.pxPerMm, r = d.diameter / 2
    if (r <= 0 || k <= 0) return
    var l = lengths(d)
    var h = l.point, fEnd = h + l.flute, end = l.drawn

    ctx.save()
    ctx.translate(d.tipX, d.tipY)
    ctx.scale(k, k)                          // y în jos, ca pe ecran

    // cut off inside the point, the cone is cut there too
    var cut = Math.min(h, end), cutR = h > 0 ? r * cut / h : r
    function outline() {
        ctx.beginPath()
        ctx.moveTo(0, 0)
        ctx.lineTo(cut, -cutR)
        if (end > cut) { ctx.lineTo(end, -r); ctx.lineTo(end, r) }
        ctx.lineTo(cut, cutR)
        ctx.closePath()
    }

    outline()
    ctx.fillStyle = d.bodyColor
    ctx.fill()

    // muchiile canalelor, tăiate la vârf + canale, și unde se oprește desenul
    ctx.save()
    outline()
    ctx.clip()
    ctx.beginPath()
    ctx.rect(0, -r, fEnd, 2 * r)
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

    // capătul canalelor, unde începe coada - dacă se ajunge acolo
    if (fEnd < end) {
        ctx.strokeStyle = d.edgeColor
        ctx.lineWidth = 1 / k
        ctx.beginPath()
        ctx.moveTo(fEnd, -r); ctx.lineTo(fEnd, r)
        ctx.stroke()
    }

    outline()
    ctx.lineJoin = "round"
    ctx.lineWidth = 1.5 / k
    ctx.stroke()
    ctx.restore()
}
