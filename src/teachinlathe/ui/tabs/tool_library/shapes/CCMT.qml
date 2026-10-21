import QtQuick

/*
 * CCMT.qml — romb 80°, pozitivă, o singură față — finisare/semifinisare
 *
 * Utilizare:
 *     import "Inserts"          // sau: import Inserts
 *
 *     CCMT {
 *         size: CCMT.Size.S09
 *         noseRadius: 0.8
 *         orientation: 0
 *         showInscribedCircle: true
 *         showToolTip: true
 *         pxPerMm: 20
 *     }
 */
Item {
    id: root

    // mărimile disponibile (cifra din codul ISO)
    enum Size { S06, S09, S12, S16 }

    // ---- parametri --------------------------------------------------------
    property int  size: CCMT.Size.S09
    property real noseRadius: 0.8            // mm — vezi `noseRadii`
    property real orientation: 0             // grade
    property real pxPerMm: 20
    property int  activeCorner: 0
    property bool showInscribedCircle: false
    property bool showToolTip: false
    property bool showHole: true

    property alias bodyColor: insert.bodyColor
    property alias edgeColor: insert.edgeColor
    property alias holeColor: insert.holeColor

    // ---- date familie -----------------------------------------------------
    readonly property string family: "CCMT"
    readonly property string shape: "C"
    readonly property string insertType: "T"
    readonly property var icValues: [6.35, 9.525, 12.7, 15.875]          // mm, în ordinea enum-ului
    readonly property var sizeCodes: ["06", "09", "12", "16"]
    readonly property var noseRadii: [0.2, 0.4, 0.8, 1.2, 1.6]

    readonly property real ic: icValues[Math.max(0, Math.min(size, icValues.length - 1))]
    readonly property string sizeCode: sizeCodes[Math.max(0, Math.min(size, sizeCodes.length - 1))]
    readonly property real sideLength: insert.edgeLength()
    readonly property string isoCode: family + " " + sizeCode + " .. " +
                                      (noseRadius * 10 < 10 ? "0" : "") + Math.round(noseRadius * 10)

    // vârful programat (mm, sistemul plăcuței) — pune-l pe traiectorie
    function activeTip()  { return insert.activeTip() }
    // centrul razei la vârf — folosit când e activă compensarea G41/G42
    function noseCenter() { return insert.noseCenter() }

    implicitWidth:  insert.implicitWidth
    implicitHeight: insert.implicitHeight

    TurningInsertBase {
        id: insert
        anchors.fill: parent
        shape: root.shape
        insertType: root.insertType
        ic: root.ic
        noseRadius: root.noseRadius
        orientation: root.orientation
        pxPerMm: root.pxPerMm
        activeCorner: root.activeCorner
        showInscribedCircle: root.showInscribedCircle
        showToolTip: root.showToolTip
        showHole: root.showHole
    }
}
