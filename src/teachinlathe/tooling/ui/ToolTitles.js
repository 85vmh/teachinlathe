.pragma library

// A cutting tool's name as its card heads it, coloured part by part: an
// insert's family blue, its size in the insert's colour, its corner radius
// green; a threading insert's pitch green; a blade's width, a drill's or a
// reamer's diameter and a tap's thread in the tool's own colour.
//
// `card` is the cutting-tool models' card kind, `view` the tool's view and
// `theme` the Theme singleton. Rich text, for a Text with StyledText.

function font(color, text) {
    return "<font color='" + color + "'>" + text + "</font>"
}

function mm(value) {
    return Number(value.toFixed(3)) + " mm"
}

function richTitle(card, view, theme) {
    if (!view)
        return ""
    switch (card) {
    case "turning":
        return font(theme.accentStrong, view.familyCode) + " "
             + font(view.insertBodyColor, view.sizeCode)
             + font(theme.foregroundStrong, view.thicknessCode)
             + font(theme.success, view.radiusCode)
    case "threading":
        return font(view.insertBodyColor, view.sizeCode)
             + font(theme.accentStrong, view.hand) + " "
             + font(theme.success, view.pitchText)
    case "blade":
        return font(view.bodyColor, mm(view.bladeWidth))
    case "drilling":
    case "reaming":
        return font(view.bodyColor, "Ø" + mm(view.diameter))
    case "tapping":
        return font(view.bodyColor, view.designation)
    }
    return view.text !== undefined ? view.text : ""
}

// What a tool is, as the Tool Holders pane heads its box: "Turning Tool",
// "Boring Tool", "Parting Blade" (orientation 6), "Grooving Blade" (8),
// "Trepanning Blade" (5 and 7), "OD Threading", "ID Threading",
// "Drill Tool", "Reamer Tool", "Tap". Plain text.
function kindTitle(card, view) {
    if (!view)
        return ""
    switch (card) {
    case "turning":
        return view.toolType === "boring" ? "Boring Tool" : "Turning Tool"
    case "threading":
        return view.hand === "IR" ? "ID Threading" : "OD Threading"
    case "blade":
        return { 6: "Parting Blade", 8: "Grooving Blade", 5: "Trepanning Blade",
                 7: "Trepanning Blade" }[view.orientation] || "Blade"
    case "drilling":
        return "Drill Tool"
    case "reaming":
        return "Reamer Tool"
    case "tapping":
        return "Tap"
    }
    return ""
}

// A tool's name as the Manual Turning list heads it: what the tool is as
// well as its size - "Turning CCMT 060204", "3mm Grooving/Parting Blade",
// "ER16 OD Threading", "RH Tap M10x1.5mm", "118° RH Drill Ø6.8mm",
// "6.8mm Reamer". Coloured as richTitle colours the card's.
function listTitle(card, view, theme) {
    if (!view)
        return ""
    function size(v) { return Number(Number(v).toFixed(3)) + "mm" }
    switch (card) {
    case "turning":
        return (view.toolType === "boring" ? "Boring " : "Turning ")
             + richTitle(card, view, theme)
    case "threading":
        return font(theme.accentStrong, view.hand)
             + font(view.insertBodyColor, view.sizeCode)
             + (view.hand === "IR" ? " ID" : " OD") + " Threading"
    case "blade": {
        var kind = { 6: "Grooving/Parting Blade", 5: "Trepanning Blade",
                     7: "Trepanning Blade", 8: "Grooving Blade" }[view.orientation] || "Blade"
        return font(view.bodyColor, size(view.bladeWidth)) + " " + kind
    }
    case "drilling":
        return Number(Number(view.tipAngle).toFixed(1)) + "° "
             + (view.rightHand ? "RH" : "LH") + " Drill "
             + font(view.bodyColor, "Ø" + size(view.diameter))
    case "reaming":
        return font(view.bodyColor, size(view.diameter)) + " Reamer"
    case "tapping":
        return (view.rightHand ? "RH" : "LH") + " Tap "
             + font(view.bodyColor, view.designation + "mm")
    }
    return richTitle(card, view, theme)
}

// The first two figures a tool's card shows, coloured as there:
// [{ label, value, color }]. An insert's tip and radius, a threading
// insert's type and pitch, a blade's corner radii, a drill's tip and twist,
// a tap's pitch and hand; none for a reamer.
function figures(card, view, theme) {
    if (!view)
        return []
    function deg(v) { return Number(Number(v).toFixed(2)) + "°" }
    function len(v) { return Number(Number(v).toFixed(3)) + " mm" }
    function radius(v) { return "R" + Number(Number(v).toFixed(3)) }
    switch (card) {
    case "turning":
        if (view.isRound)
            return [{ label: "Round insert", value: "", color: theme.accentStrong },
                    { label: "Ø", value: len(view.ic), color: theme.success }]
        return [{ label: "Tip:", value: deg(view.cornerAngle), color: theme.accentStrong },
                { label: "Radius:", value: len(view.noseRadiusMm), color: theme.success }]
    case "threading":
        return [{ label: "Type:", value: view.kind, color: theme.accentStrong },
                { label: "Pitch:", value: len(view.pitch), color: theme.success }]
    case "blade":
        return [{ label: "Left:", value: radius(view.leftRadius), color: theme.success },
                { label: "Right:", value: radius(view.rightRadius), color: theme.success }]
    case "drilling":
        return [{ label: "Tip:", value: Number(view.tipAngle.toFixed(1)) + "°", color: theme.accentStrong },
                { label: "Twist:", value: view.rightHand ? "RH" : "LH", color: theme.foreground }]
    case "tapping":
        return [{ label: "Pitch:", value: String(Number(view.pitch.toFixed(3))), color: theme.success },
                { label: "Thread:", value: view.rightHand ? "RH" : "LH", color: theme.foreground }]
    }
    return []
}
