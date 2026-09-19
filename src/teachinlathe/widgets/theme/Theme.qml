pragma Singleton
import QtQuick 2.15

/*
 * The design tokens the UI is drawn from.
 *
 * Every value here was taken from what the conversational tab already used,
 * by frequency - so adopting these changes nothing on screen. That is
 * deliberate: extracting the tokens and changing the values are two jobs, and
 * doing them at once makes a mistake indistinguishable from an intended
 * change. Adjust after the sweep, not during it.
 *
 * A note on naming: nothing here may start with "on" followed by a capital
 * letter. QML reads that as signal-handler syntax, so a token called
 * `onSurface` - the obvious name, coming from Material - silently evaluates
 * to undefined, with no error and no warning. Hence `foreground`.
 */
QtObject {

    // ── Typography ──────────────────────────────────────────────────────────
    //
    // Five steps.
    //
    // There were three small sizes doing one job - 13, 14 and 15 - and which
    // one a label got depended on the file it was in rather than on what it
    // was. The unit suffix "(mm)" appeared at all three. They are one token
    // now, at 14: the middle of what was there, and the size the strays were
    // already using.

    readonly property string fontFamily: "Noto Sans"

    readonly property int fontXSmall:  12   // the file browser's breadcrumbs and
                                            // counts, where 11 and 12 were used
                                            // interchangeably
    readonly property int fontSmall:   14   // option labels, units, helper text
    readonly property int fontBody:    16   // the default (151 uses)
    readonly property int fontLarge:   18   // sub-headings
    readonly property int fontTitle:   20   // screen titles

    // ── Metrics ─────────────────────────────────────────────────────────────
    //
    // The heights that actually recur. Interactive controls disagree today -
    // inputs are 48, buttons are 40, and one button is 36 - which is why they
    // are separate tokens rather than one: unifying them is a value change,
    // and this file is where it will happen when you decide to.

    // Buttons had ten heights doing four jobs: 34 and 36; 40, 42 and 44; 48
    // and 50; 70 and 80. Three of those groups are the same button drawn a
    // couple of pixels apart in different files, so they are one token each
    // now. The middle group settles on 44 rather than 40 - it is the largest
    // of the three, and this panel is worked with gloves on.
    readonly property int buttonHeightSmall: 36   // was 34, 36
    readonly property int buttonHeight:      44   // was 40, 42, 44
    readonly property int buttonHeightLarge: 48   // was 48, 50
    readonly property int buttonHeightTouch: 70   // was 70

    readonly property int inputHeight:   48   // NumpadField, parameter rows
    readonly property int rowHeight:     72   // OperationListItem
    readonly property int headerHeight:  56   // screen headers
    readonly property int barHeight:     64   // the app bar and the tab bar
    readonly property int barHeightSmall: 42  // the rapid-override strip
    readonly property int hairline:       1   // separators

    // Four steps, from what is actually drawn: 6 (41 uses), 8 (29), 4 (12),
    // 10 (7). The first scale here guessed 2/6/10 and had no token for 8,
    // which is the second commonest corner in the app.
    readonly property int radiusSmall:    4
    readonly property int radius:         6
    readonly property int radiusLarge:    8
    readonly property int radiusXLarge:  10

    // Spacing is deliberately only these four. The gaps in the app run 4, 6,
    // 8, 10, 12, 16, 20, 24, 30 - which is not a scale, it is ad hoc. Only
    // exact matches are tokenised; folding 10 into 12 or 6 into 8 would move
    // layouts, and that is a decision rather than a rename.
    readonly property int spacingSmall:   8
    readonly property int spacing:       12
    readonly property int spacingLarge:  16
    readonly property int margin:        24

    // ── Surfaces ────────────────────────────────────────────────────────────

    readonly property color surface:        "#ffffff"   // 15 uses
    readonly property color surfaceAlt:     "#f5f7fb"   // 14
    readonly property color surfaceSunken:  "#f5f5f5"
    readonly property color surfaceInverse: "#202225"   // 5 - the dark dialogs

    // ── Lines ───────────────────────────────────────────────────────────────

    readonly property color outline:        "#cccccc"   // 32 - the commonest
    readonly property color outlineStrong:  "#bdbdbd"   // 13
    readonly property color separator:      "#d6dce7"   // 10
    readonly property color outlineInverse: "#3a3d41"   // 11 - on dark dialogs
    readonly property color outlineDisabled:"#e0e0e0"

    //: The border of a raised dialog and of the buttons inside it. A touch
    //: bluer than outlineStrong, which is what the numpad has always used and
    //: what the other dialogs now match.
    readonly property color dialogBorder:   "#9aa3b0"

    // ── Text ────────────────────────────────────────────────────────────────

    readonly property color foreground:        "#1e2430"   // 7
    readonly property color foregroundStrong:  "#0f172a"   // 4
    readonly property color foregroundMuted:   "#4f4f4f"   // 6
    readonly property color foregroundFaint:   "#808080"   // placeholders
    readonly property color foregroundOnAccent:"#ffffff"
    readonly property color foregroundInverse: "#e8eaed"   // on dark dialogs

    // ── Accent and interaction states ───────────────────────────────────────

    readonly property color accent:        "#3b82f6"   // 9
    readonly property color accentStrong:  "#1565c0"   // 6
    readonly property color accentSoft:    "#e1f0ff"   // 7 - pressed fill
    readonly property color accentBorder:  "#8ec5ff"   // 9 - pressed border
    readonly property color selection:     "#dbeafe"   // 10
    readonly property color hover:         "#eef3fb"   // 5
    readonly property color focusBorder:   "#2a7bff"   // NumpadField focus

    // ── Semantic ────────────────────────────────────────────────────────────

    readonly property color success:    "#2e7d32"   // 5 - confirm
    readonly property color danger:     "#c62828"   // 10 - delete, abort
    readonly property color dangerSoft: "#ffebee"   // 4
    readonly property color dangerPressed: "#b71c1c"
    readonly property color warning:    "#ff9800"   // the manual tab already
                                                    // called this warningColor
                                                    // in three files

    // ── Manual tab ──────────────────────────────────────────────────────────

    //: A border that marks the selected one of several, in the tool library.
    //: Darker than outlineStrong on purpose - it has to read as chosen.
    readonly property color outlineEmphasis: "#999999"

    //: The on-screen QWERTY keyboard's keys, which sit on a dark overlay and
    //: so do not follow the light surface tokens.
    readonly property color keySurface:        "#5f6367"
    readonly property color keySurfacePressed: "#8b8f93"

    // ── Primary action ──────────────────────────────────────────────────────
    //
    // The green that marks the main action on a screen: the selected tab's
    // underline, Load Program, Cycle Start, the backplot's own buttons. It is
    // not `success`, which is the confirm green in dialog text - these two
    // were one colour apart and had drifted into doing different jobs.

    readonly property color primary:         "#2d7d46"
    readonly property color primaryPressed:  "#25673a"
    readonly property color primaryDisabled: "#8ea99a"
    readonly property color primaryBorder:   "#3fb950"

    //: Muted body text on the programs and dev screens - a slate, where
    //: foregroundMuted is a neutral grey.
    readonly property color foregroundSubtle: "#475569"
}
