// A thread seen from the side, as an operation's canvas draws it - external
// or internal alike: under the centre line the near half's profile, over it
// the far half's, half a turn round, and the helix joining them.
//
// The far half is half the lead on along the thread from Z Start toward Z
// End - inwards (to Z-) for a right-hand thread, cut toward the chuck,
// outwards for a left-hand one, cut away from it - so the helix leans one way
// or the other. Each crest's middle below is joined to the crest above it
// reaches, each root's to the root's.
//
// A profile: crests on Major Ø, roots on Minor Ø, a pitch from crest to
// crest, the flanks at the form's angle - each runs the thread's depth times
// tan(angle / 2) along Z - what is left of the pitch flat, a third at the
// crest and two at the root, as ISO truncates them. The same line bounds a
// bolt's thread and a nut's: an internal thread is drawn with it too, the
// material on its other side (StockActor).
//
// What is drawn is clipped at Z0 and split where the stock's middle is left
// out (brokenstock.js middleBreak) - each line run exactly to the edge of its
// piece. Lengths in mm; a point is {z, x}, x a diameter, negative over the
// centre line, z where it is drawn.
.pragma library
.import "brokenstock.js" as Broken

// More pitches than this along it, and it is not drawn.
var MAX_PITCHES = 1000

// The thread ``t`` - {zStart, zEnd, pitch, starts, major, minor, angle (the
// form's, degrees), brk (middleBreak's, or null)} - as {lower, upper: the
// halves' profiles, crests, roots: the helix's lines, face: the line across
// its ends at Z0 when its near end is past it}, each a list of lines of
// points; all empty when it cannot be drawn.
function drawing(t) {
    var none = { lower: [], upper: [], crests: [], roots: [], face: [] }
    var p = _profile(t)
    if (!p) return none
    var halfTurn = t.pitch * Math.max(1, t.starts) / 2
    var lower = _profileLines(t, p, 0, 1)
    var upper = _profileLines(t, p, halfTurn, -1)
    var helix = _helixLines(t, p, halfTurn)
    return { lower: lower, upper: upper, crests: helix.crests, roots: helix.roots,
             face: _face(t, lower, upper) }
}

// The profile's measures along Z - {crest, flank, root} - or null when the
// thread cannot be drawn.
function _profile(t) {
    if (!(t.pitch > 0) || !(t.major > 0) || !(t.minor > 0) || t.zStart === t.zEnd
            || Math.abs(t.zEnd - t.zStart) / t.pitch > MAX_PITCHES)
        return null
    var depth = Math.abs(t.major - t.minor) / 2
    var flank = Math.min(t.pitch / 2, depth * Math.tan(t.angle / 2 * Math.PI / 180))
    var flats = t.pitch - 2 * flank
    return { crest: flats / 3, flank: flank, root: flats - flats / 3 }
}

// The way from Z Start to Z End along Z, -1 or 1, and how long it is.
function _dir(t) { return t.zEnd < t.zStart ? -1 : 1 }
function _length(t) { return Math.abs(t.zEnd - t.zStart) }

// The profile's diameter ``s`` along the thread from Z Start, its pattern
// moved ``phase`` on.
function _diameterAt(t, p, s, phase) {
    var u = ((s - phase) % t.pitch + t.pitch) % t.pitch
    if (u < p.crest) return t.major
    u -= p.crest
    if (u < p.flank) return t.major + (t.minor - t.major) * u / p.flank
    u -= p.flank
    if (u < p.root) return t.minor
    u -= p.root
    return t.minor + (t.major - t.minor) * u / p.flank
}

// Its corners from Z Start to Z End, as [s along it], phase as above.
function _stations(t, p, phase) {
    var length = _length(t)
    var marks = [0, p.crest, p.crest + p.flank, p.crest + p.flank + p.root]
    var out = [0, length]
    for (var k = Math.floor(-phase / t.pitch) - 1; k * t.pitch + phase <= length; k++)
        for (var m = 0; m < marks.length; m++) {
            var s = k * t.pitch + phase + marks[m]
            if (s > 0 && s < length) out.push(s)
        }
    out.sort(function(a, b) { return a - b })
    return out
}

// A real Z's region of the drawing: past Z0, out of the stock and not drawn;
// the piece at the face, the far piece, or the stretch left out between them.
function _regionOf(brk, z) {
    if (z > 0) return "out"
    if (!brk || z >= brk.near) return "face"
    if (z + brk.shift <= brk.far) return "far"
    return "gap"
}

// Where two neighbouring regions meet: {real, drawn} Z - the drawn one
// given, not worked out from the real one, which rounding can put a hair
// into the stretch left out.
function _boundary(brk, a, b) {
    if (a === "out" || b === "out") return { real: 0, drawn: 0 }
    return a === "far" || b === "far" ? { real: brk.far - brk.shift, drawn: brk.far }
                                      : { real: brk.near, drawn: brk.near }
}

function _drawn(region) { return region === "face" || region === "far" }

// One half's profile, its pattern ``phase`` on, x times ``sign``.
function _profileLines(t, p, phase, sign) {
    var lines = [], dir = _dir(t), brk = t.brk
    var stations = _stations(t, p, phase)
    var current = [], region = null, last = null
    function edge(from, to, z, x) {
        var e = _boundary(brk, from, to)
        return { z: e.drawn, x: last.x + (x - last.x) * (e.real - last.z) / (z - last.z) }
    }
    for (var i = 0; i < stations.length; i++) {
        var z = t.zStart + dir * stations[i], x = sign * _diameterAt(t, p, stations[i], phase)
        var r = _regionOf(brk, z)
        if (r !== region) {
            if (last && _drawn(region)) current.push(edge(region, r, z, x))
            if (current.length > 1) lines.push(current)
            current = []
            if (last && _drawn(r)) current.push(edge(region, r, z, x))
            region = r
        }
        if (_drawn(r)) current.push({ z: Broken.drawnZ(brk, z), x: x })
        last = { z: z, x: x }
    }
    if (current.length > 1) lines.push(current)
    return lines
}

// The helix: {crests, roots}. A line that runs past Z Start or Z End - the
// crest or root at its other end is not on the thread: many starts make the
// lead, and so the half turn, long - is cut there, as the thread ends.
function _helixLines(t, p, shift) {
    var out = { crests: [], roots: [] }
    var length = _length(t), dir = _dir(t), brk = t.brk
    var marks = [[p.crest / 2, t.major], [p.crest + p.flank + p.root / 2, t.minor]]
    // from the first line whose far end reaches Z Start to the last whose
    // near end does not pass Z End
    var kFirst = Math.floor(Math.min(0, -shift) / t.pitch) - 1
    var kLast = Math.ceil(Math.max(length, length - shift) / t.pitch)
    for (var k = kFirst; k <= kLast; k++)
        for (var m = 0; m < marks.length; m++) {
            var s0 = k * t.pitch + marks[m][0], s1 = s0 + shift
            var x0 = marks[m][1], x1 = -marks[m][1]
            // cut to the thread: s from 0 (Z Start) to its length (Z End)
            var ta = -s0 / (s1 - s0), tb = (length - s0) / (s1 - s0)
            var t0 = Math.max(0, Math.min(ta, tb)), t1 = Math.min(1, Math.max(ta, tb))
            if (t1 - t0 <= 1e-9) continue
            var z0 = t.zStart + dir * (s0 + (s1 - s0) * t0), z1 = t.zStart + dir * (s0 + (s1 - s0) * t1)
            var xa = x0 + (x1 - x0) * t0, xb = x0 + (x1 - x0) * t1
            // and at Z0
            if (z0 > 0 && z1 > 0) continue
            if (z0 > 0) { xa = xa + (xb - xa) * z0 / (z0 - z1); z0 = 0 }
            else if (z1 > 0) { xb = xb + (xa - xb) * z1 / (z1 - z0); z1 = 0 }
            var r0 = _regionOf(brk, z0), r1 = _regionOf(brk, z1)
            if (r0 === "gap" || r0 !== r1) continue
            out[m === 0 ? "crests" : "roots"].push([{ z: Broken.drawnZ(brk, z0), x: xa },
                                                     { z: Broken.drawnZ(brk, z1), x: xb }])
        }
    return out
}

// The face at Z0 across the thread's ends, when its near end is past it: the
// profiles' ends there - their first point when they run from Z Start toward
// the chuck, their last when they run toward the face.
function _face(t, lower, upper) {
    if (!(Math.max(t.zStart, t.zEnd) > 0) || lower.length === 0 || upper.length === 0) return []
    if (t.zEnd < t.zStart) return [[upper[0][0], lower[0][0]]]
    var lo = lower[lower.length - 1], up = upper[upper.length - 1]
    return [[up[up.length - 1], lo[lo.length - 1]]]
}
