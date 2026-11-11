// speeds.js — an operation's speeds_and_feeds, as its views read and edit it
// (SpeedsAndFeeds.qml, SpindleParameters.qml): what it says, with the
// defaults it is shown with, and the whole of it with a change made.
.pragma library

// What ``speeds`` (an operation's speeds_and_feeds) says: mode "rpm" | "css"
// - RPM only when ``rpmOnly`` - the speeds, direction "M3" | "M4" - the
// tool's when it allows only one (``onlyClockwise`` true M3, false M4) -
// and the feeds.
function read(speeds, rpmOnly, onlyClockwise) {
    var sp = speeds || {}
    var hasRpm = sp.rpm_value !== undefined && sp.rpm_value !== null
    var hasCss = sp.css_value !== undefined && sp.css_max_speed !== undefined
    return {
        mode: rpmOnly ? "rpm" : (sp.mode === "css" || sp.mode === "rpm") ? sp.mode : (hasRpm ? "rpm" : "css"),
        rpm_value: hasRpm ? +sp.rpm_value : 0,
        css_value: hasCss ? +sp.css_value : 0,
        css_max_speed: hasCss ? +sp.css_max_speed : 0,
        direction: onlyClockwise === true ? "M3" : onlyClockwise === false ? "M4"
                 : (sp.direction === "M3" ? "M3" : "M4"),
        feed_rate: (sp.feed_rate !== undefined && sp.feed_rate !== null) ? +sp.feed_rate : 0,
        feed_rate_2: (sp.feed_rate_2 !== undefined && sp.feed_rate_2 !== null) ? +sp.feed_rate_2 : 0
    }
}

// The whole speeds_and_feeds: ``current`` (as read gives it) with ``changes``
// made - the speeds for its mode, then the feed rate when ``withFeed``, and
// Parting's second one when ``withFeed2``.
function edited(current, changes, withFeed, withFeed2) {
    var v = Object.assign({}, current, changes)
    var out = { direction: v.direction, mode: v.mode }
    if (v.mode === "rpm") {
        out.rpm_value = v.rpm_value
    } else {
        out.css_value = v.css_value
        out.css_max_speed = v.css_max_speed
    }
    if (withFeed)
        out.feed_rate = v.feed_rate
    if (withFeed2)
        out.feed_rate_2 = v.feed_rate_2
    return out
}
