// A groove's four points: P1 where its right flank starts, P2 that flank's
// bottom, P3 the left flank's bottom, P4 where the left flank starts - each
// one's colour, its boxes' and its marks', and its name as the labels set it.
.pragma library

var colors = ["#1565c0", "#00838f", "#6d4c41", "#ad1457"]

// px, the names' size: over the body text, so the small caps and the
// lowered digit read at a glance
var fontSize = 18

function color(point) {
    return colors[Math.max(0, Math.min(3, point - 1))]
}

// "P1 X" as rich text, at fontSize: the P bold, the 1 set down, half as
// tall, ``axes`` ("X", "XZ") in small caps - capitals as tall as the font's
// small letters, set by hand: Qt draws its own small caps too small to read
function name(point, axes) {
    return "<b>P</b><sub>" + point + "</sub> <span style=\"font-size: "
         + Math.round(fontSize * 0.78) + "px\">" + String(axes).toUpperCase() + "</span>"
}
