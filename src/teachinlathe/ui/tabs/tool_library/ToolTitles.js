.pragma library

// A cutting tool's titles, coloured part by part. The words are the
// domain's (tooling/model/tool_titles.py), which the tool's view hands over
// in parts, each with its role (`view.titleParts`); this only colours them:
// an insert's family blue, its size in the insert's colour, its corner
// radius green; a threading insert's pitch green; a blade's width, a drill's
// or a reamer's diameter and a tap's thread in the tool's own colour.
//
// `card` is the cutting-tool models' card kind, `view` the tool's view and
// `theme` the Theme singleton. Rich text, for a Text with StyledText.

function font(color, text) {
    return "<font color='" + color + "'>" + text + "</font>"
}

// The colour of a title part's role, "" for the words between the parts.
function roleColor(role, view, theme) {
    switch (role) {
    case "family":
    case "hand":
        return theme.accentStrong
    case "insert":
        return view.insertBodyColor
    case "thickness":
        return theme.foregroundStrong
    case "radius":
    case "pitch":
        return theme.success
    case "body":
        return view.bodyColor
    }
    return ""
}

function painted(parts, view, theme) {
    var text = ""
    for (var i = 0; i < parts.length; ++i) {
        var color = roleColor(parts[i].role, view, theme)
        text += color ? font(color, parts[i].text) : parts[i].text
    }
    return text
}

// A cutting tool's name as its card heads it: "CCMT 060204", "16ER 1.5",
// "3 mm", "Ø6.8 mm", "M10x1.5".
function richTitle(card, view, theme) {
    return view ? painted(view.titleParts.card, view, theme) : ""
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
    return view ? painted(view.titleParts.list, view, theme) : ""
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
