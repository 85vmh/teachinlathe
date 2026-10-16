// The Z axis where the drawing leaves out a stretch of the stock, as the
// Program Header does a long bar's middle (brokenstock.js).
//
// A break is {near, far, shift}, in drawn Z: ``near`` where the piece at the
// face is broken off, ``far`` where the far piece starts again (far < near),
// and ``shift`` what was left out: a real Z on the far piece is drawn at
// real + shift. Right of ``near`` the drawing is true to Z; between the two
// nothing is marked; left of ``far`` the marks carry the real Z.
.pragma library

// The marks every ``step`` in the drawn range [zMin, zMax], as
// [{drawn, real}], none in the gap. Without a break, every multiple of the
// step; with one, the far piece's marks at the multiples of its real Z.
function marks(zMin, zMax, step, brk) {
    var out = []
    if (step <= 0) return out
    var z
    if (!brk) {
        for (z = Math.floor(zMin / step) * step; z <= zMax; z += step)
            out.push({ drawn: z, real: z })
        return out
    }
    // the piece at the face, true to Z
    for (z = Math.ceil(Math.max(zMin, brk.near) / step) * step; z <= zMax; z += step)
        out.push({ drawn: z, real: z })
    // the far piece, at its real Z
    var realMin = zMin - brk.shift, realMax = Math.min(zMax, brk.far) - brk.shift
    for (z = Math.floor(realMin / step) * step; z <= realMax; z += step)
        if (z + brk.shift >= zMin) out.push({ drawn: z + brk.shift, real: z })
    return out
}
