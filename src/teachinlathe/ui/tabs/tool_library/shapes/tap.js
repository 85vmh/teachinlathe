// tap.js — tarodul din Tap.qml, desenat pe un context 2D dat: aceeași formă
// oriunde e desenat, în Tool Library sau pe canvasul unei operații
// (Tapping). Vezi Tap.qml pentru dinți, conicitate și elice.
//
// `d`: diameter, pitch, rightHand, leadThreads, threadLengthD, minThreads,
// shankRatio, shankLengthD, helixLineWidth, length (mm, 0 = filet + coadă),
// bodyColor, edgeColor; pxPerMm; tipX, tipY - vârful, în px; corpul spre
// dreapta.
//
// Tarodul e dat doar de diametru și pas: filetul începe mereu de la vârf, așa
// că oriunde e desenat dinții și elicea cad la fel; `length` doar lungește
// sau scurtează coada.
.pragma library

// Cotele, în mm: raza, adâncimea dinților, raza fundului, conicitatea de
// atac, partea filetată, lungimea desenată, raza cozii.
function geometry(d) {
    var radius = d.diameter / 2
    var depth = d.pitch * Math.sqrt(3) / 2
    // Un pas prea mare pentru diametru ar trece dinții de axă: fundul rămâne
    // cel puțin la o treime din rază.
    var root = Math.max(radius - depth, radius / 3)
    var lead = d.leadThreads * d.pitch
    var thread = Math.max(d.threadLengthD * d.diameter, d.minThreads * d.pitch)
    var total = d.length > 0 ? Math.max(d.length, thread) : thread + d.shankLengthD * d.diameter
    var shank = Math.min(radius, Math.max(root, d.shankRatio * radius))
    return { radius: radius, depth: depth, root: root, lead: lead, thread: thread,
             total: total, shank: shank }
}

// Raza vârfurilor dinților la x: de la fundul filetului la vârf până la D/2
// la capătul conicității.
function crestRadius(g, x) {
    if (x >= g.lead) return g.radius
    return g.root + (g.radius - g.root) * Math.max(0, x) / g.lead
}

// Raza profilului la x, pe o latură; `phase` decalează dinții (P/2 jos).
function profileRadius(g, P, x, phase) {
    var u = ((x - phase) / P) % 1
    if (u < 0) u += 1
    var tri = 1 - Math.abs(2 * u - 1)             // 0 la fund, 1 la vârf
    return Math.min(g.root + tri * (g.radius - g.root), crestRadius(g, x))
}

function paint(ctx, d) {
    var k = d.pxPerMm, P = d.pitch
    if (d.diameter <= 0 || P <= 0 || k <= 0) return
    var g = geometry(d)
    var tEnd = g.thread, end = g.total

    ctx.save()
    ctx.translate(d.tipX, d.tipY)
    ctx.scale(k, k)                          // y în jos, ca pe ecran

    // Profilul: vârfurile și funduri dinților, plus capetele conicității,
    // ca muchiile să cadă exact pe ele.
    function stations(phase) {
        var xs = [0, g.lead, tEnd]
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
    ctx.moveTo(0, profileRadius(g, P, 0, P / 2))
    ctx.lineTo(0, -profileRadius(g, P, 0, 0))
    for (var i = 0; i < top.length; i++)
        ctx.lineTo(top[i], -profileRadius(g, P, top[i], 0))
    ctx.lineTo(tEnd, -g.shank)
    ctx.lineTo(end, -g.shank)
    ctx.lineTo(end, g.shank)
    ctx.lineTo(tEnd, g.shank)
    for (var j = bottom.length - 1; j >= 0; j--)
        ctx.lineTo(bottom[j], profileRadius(g, P, bottom[j], P / 2))
    ctx.closePath()
    ctx.fillStyle = d.bodyColor
    ctx.fill()
    ctx.lineJoin = "miter"
    ctx.lineWidth = 1.2 / k
    ctx.strokeStyle = d.edgeColor
    ctx.stroke()

    // Elicea pe fața văzută: fiecare vârf de sus spre vârful de jos de după
    // el, jumătate de pas mai încolo.
    ctx.lineWidth = d.helixLineWidth / k
    var dir = d.rightHand ? 1 : -1
    for (var n = 0; n * P <= tEnd; n++) {
        var xt = n * P + P / 2                       // vârf de sus
        var xb = xt + dir * P / 2                    // vârful de jos
        if (xt > tEnd || xb < 0 || xb > tEnd) continue
        ctx.beginPath()
        ctx.moveTo(xt, -crestRadius(g, xt))
        ctx.lineTo(xb, crestRadius(g, xb))
        ctx.stroke()
    }

    ctx.restore()
}
