import QtQuick

/*
 * TurningInsertBase.qml — motorul de geometrie pentru plăcuțele ISO de strunjire.
 * Nu se folosește direct: fiecare familie (CCMT, WNMG, ...) îl instanțiază.
 *
 * Toate cotele sunt în MILIMETRI. Conversia în pixeli se face o singură dată,
 * prin `pxPerMm`, deci 1 mm de piesă = pxPerMm pixeli pe ecran, indiferent de mărime.
 *
 * GEOMETRIE (ISO 1832): laturile sunt tangente la cercul înscris de diametru IC.
 *   rombic α (C=80°, D=55°, V=35°):  a = IC/sin α
 *                                     vârfuri (±a·cos(α/2), 0) și (0, ±a·sin(α/2))
 *                                     colțurile de așchiere = cele ascuțite, pe axa X
 *   triunghi T 60°:  circumrază = IC,           vârfuri la 90/210/330
 *   pătrat  S 90°:   circumrază = (IC/2)/cos45, vârfuri la 45/135/225/315
 *   trigon  W 80°:   Rc = IC/1.286, Ro = 0.6527·Rc
 *                    vârfuri ÎN ORDINE UNGHIULARĂ: 30(Ro) 90(Rc) 150(Ro) 210(Rc) 270(Ro) 330(Rc)
 *                    colțurile de așchiere = cele la Rc
 *   rotund  R:       cerc de rază IC/2
 *
 * Colțurile se rotunjesc cu `noseRadius` prin arcTo(). Vârfurile TREBUIE parcurse
 * în ordine pe contur — o săritură face ca arcTo să deseneze o stea.
 */
Item {
    id: base

    // ---- intrări (setate de fișierul de familie) --------------------------
    property string shape: "C"          // C D V T S W R
    property string insertType: "T"     // T = pozitivă 1 față | G = negativă 2 fețe
    property real   ic: 9.525           // cerc înscris [mm]
    property real   noseRadius: 0.8     // rază la vârf [mm]
    property real   orientation: 0      // grade
    property real   pxPerMm: 20
    property int    activeCorner: 0     // care colț de așchiere e activ
    property bool   showInscribedCircle: false
    property bool   showToolTip: false
    property bool   showHole: true

    property color bodyColor: "#39424c"
    property color edgeColor: "#aeb9c4"
    property color holeColor: "#12161b"
    property color markColor: "#e6a24b"
    property color guideColor: "#3fb7c2"

    readonly property real d2r: Math.PI / 180

    // gaură + teșitură [mm], pe cerc înscris și tip. m:true = măsurat din DXF.
    readonly property var holeTable: ({
        "6.35":  { "T": { "d": 2.85, "cs": 4.46, "m": true  }, "G": { "d": 2.80, "cs": 4.10 } },
        "9.525": { "T": { "d": 4.40, "cs": 6.33, "m": true  }, "G": { "d": 3.81, "cs": 5.50 } },
        "12.7":  { "T": { "d": 5.50, "cs": 7.85, "m": true  }, "G": { "d": 5.16, "cs": 7.40 } },
        "15.875":{ "T": { "d": 6.60, "cs": 9.20 },             "G": { "d": 6.35, "cs": 9.00 } },
        "19.05": { "T": { "d": 7.93, "cs": 11.0 },             "G": { "d": 7.93, "cs": 11.0 } },
        "8":     { "T": { "d": 3.40, "cs": 5.00 },             "G": { "d": 3.40, "cs": 5.00 } },
        "10":    { "T": { "d": 4.40, "cs": 6.33 },             "G": { "d": 4.40, "cs": 6.33 } },
        "12":    { "T": { "d": 5.50, "cs": 7.85 },             "G": { "d": 5.50, "cs": 7.85 } },
        "16":    { "T": { "d": 6.60, "cs": 9.20 },             "G": { "d": 6.60, "cs": 9.20 } }
    })

    function hole() {
        var row = holeTable[String(ic)];
        if (row === undefined) return null;
        return row[insertType === "G" ? "G" : "T"] || row["T"] || row["G"];
    }

    // ---- geometrie --------------------------------------------------------
    function polar(deg, r) { return { x: r * Math.cos(deg * d2r), y: r * Math.sin(deg * d2r) }; }

    // {verts:[{x,y}], cutting:[indici], round:bool}
    function outline() {
        var R = ic / 2, v = [], k, a;
        switch (shape) {
        case "R":
            return { verts: [], cutting: [], round: true };
        case "S":
            var Rs = R / Math.cos(45 * d2r);
            for (k = 0; k < 4; k++) v.push(polar(45 + 90 * k, Rs));
            return { verts: v, cutting: [0, 1, 2, 3], round: false };
        case "T":
            var Rt = R / Math.cos(60 * d2r);            // = IC
            for (k = 0; k < 3; k++) v.push(polar(90 + 120 * k, Rt));
            return { verts: v, cutting: [0, 1, 2], round: false };
        case "W":
            var Rc = ic / 1.286, Ro = 0.6527 * Rc;
            var spec = [[30, Ro], [90, Rc], [150, Ro], [210, Rc], [270, Ro], [330, Rc]];
            for (k = 0; k < spec.length; k++) v.push(polar(spec[k][0], spec[k][1]));
            return { verts: v, cutting: [1, 3, 5], round: false };
        default:                                        // C / D / V
            var alpha = shape === "C" ? 80 : (shape === "D" ? 55 : 35);
            var side = (R * 2) / Math.sin(alpha * d2r);
            var dx = side * Math.cos(alpha / 2 * d2r);
            var dy = side * Math.sin(alpha / 2 * d2r);
            return { verts: [{ x: dx, y: 0 }, { x: 0, y: dy },
                             { x: -dx, y: 0 }, { x: 0, y: -dy }],
                     cutting: [0, 2], round: false };
        }
    }

    // lungimea muchiei de așchiere [mm]
    function edgeLength() {
        if (shape === "S") return ic;
        if (shape === "T") return ic * Math.sqrt(3);
        if (shape === "C") return ic / Math.sin(80 * d2r);
        if (shape === "D") return ic / Math.sin(55 * d2r);
        if (shape === "V") return ic / Math.sin(35 * d2r);
        if (shape === "W") return 0.879 * (ic / 1.286);
        return Math.PI * ic;                            // rotundă: circumferința
    }

    // vârful teoretic ascuțit al colțului activ — punctul programat pe toolpath
    function activeTip() {
        var o = outline();
        if (o.round) return Qt.point(0, ic / 2);
        var i = o.cutting[Math.min(activeCorner, o.cutting.length - 1)];
        return Qt.point(o.verts[i].x, o.verts[i].y);
    }

    // centrul razei la vârf (punctul real când e activă compensarea G41/G42)
    function noseCenter() {
        var o = outline();
        if (o.round) return Qt.point(0, 0);
        var n = o.verts.length;
        var i = o.cutting[Math.min(activeCorner, o.cutting.length - 1)];
        var V = o.verts[i], A = o.verts[(i - 1 + n) % n], B = o.verts[(i + 1) % n];
        var u1 = norm(A.x - V.x, A.y - V.y), u2 = norm(B.x - V.x, B.y - V.y);
        var bx = u1.x + u2.x, by = u1.y + u2.y;
        var bl = Math.hypot(bx, by); if (bl < 1e-9) return Qt.point(V.x, V.y);
        var halfAng = Math.acos(Math.max(-1, Math.min(1, u1.x * u2.x + u1.y * u2.y))) / 2;
        var dist = noseRadius / Math.sin(halfAng);
        return Qt.point(V.x + bx / bl * dist, V.y + by / bl * dist);
    }
    function norm(x, y) { var m = Math.hypot(x, y) || 1; return { x: x / m, y: y / m }; }

    function maxRadius() {
        var o = outline();
        if (o.round) return ic / 2;
        var m = ic / 2;
        for (var i = 0; i < o.verts.length; i++)
            m = Math.max(m, Math.hypot(o.verts[i].x, o.verts[i].y));
        return m;
    }

    implicitWidth:  2 * (maxRadius() + noseRadius) * pxPerMm + 24
    implicitHeight: implicitWidth

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        Connections {
            target: base
            function onShapeChanged()       { canvas.requestPaint() }
            function onIcChanged()          { canvas.requestPaint() }
            function onNoseRadiusChanged()  { canvas.requestPaint() }
            function onOrientationChanged() { canvas.requestPaint() }
            function onPxPerMmChanged()     { canvas.requestPaint() }
            function onActiveCornerChanged(){ canvas.requestPaint() }
            function onShowInscribedCircleChanged() { canvas.requestPaint() }
            function onShowToolTipChanged() { canvas.requestPaint() }
            function onShowHoleChanged()    { canvas.requestPaint() }
        }

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            var k = base.pxPerMm, o = base.outline();

            ctx.save();
            ctx.translate(width / 2, height / 2);
            ctx.rotate(-base.orientation * base.d2r);
            ctx.scale(k, -k);                          // -y : matematic -> ecran

            // contur
            ctx.beginPath();
            if (o.round) {
                ctx.arc(0, 0, base.ic / 2, 0, 2 * Math.PI);
            } else {
                var n = o.verts.length;
                var m0 = mid(o.verts[n - 1], o.verts[0]);
                ctx.moveTo(m0.x, m0.y);
                for (var i = 0; i < n; i++) {
                    var c = o.verts[i], nx = o.verts[(i + 1) % n], m = mid(c, nx);
                    ctx.arcTo(c.x, c.y, m.x, m.y, base.noseRadius);
                    ctx.lineTo(m.x, m.y);
                }
                ctx.closePath();
            }
            ctx.fillStyle = base.bodyColor;
            ctx.fill();
            ctx.lineJoin = "round";
            ctx.lineWidth = 1.5 / k;
            ctx.strokeStyle = base.edgeColor;
            ctx.stroke();

            // gaură + teșitură
            var hl = base.hole();
            if (base.showHole && hl) {
                ctx.beginPath();
                ctx.arc(0, 0, hl.cs / 2, 0, 2 * Math.PI);
                ctx.lineWidth = 1.2 / k;
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(0, 0, hl.d / 2, 0, 2 * Math.PI);
                ctx.fillStyle = base.holeColor;
                ctx.fill();
                ctx.lineWidth = 1.4 / k;
                ctx.stroke();
            }

            // cerc înscris
            if (base.showInscribedCircle) {
                ctx.beginPath();
                ctx.arc(0, 0, base.ic / 2, 0, 2 * Math.PI);
                ctx.lineWidth = 1 / k;
                ctx.strokeStyle = base.guideColor;
                ctx.stroke();
            }
            ctx.restore();

            // vârful sculei (în pixeli, după rotație)
            if (base.showToolTip) {
                var t = base.activeTip();
                var a = base.orientation * base.d2r;
                var px = width  / 2 + k * (t.x * Math.cos(a) - t.y * Math.sin(a));
                var py = height / 2 - k * (t.x * Math.sin(a) + t.y * Math.cos(a));
                ctx.strokeStyle = base.markColor;
                ctx.fillStyle = base.markColor;
                ctx.lineWidth = 1;
                ctx.beginPath(); ctx.arc(px, py, 3.5, 0, 2 * Math.PI); ctx.fill();
                ctx.beginPath();
                ctx.moveTo(px - 12, py); ctx.lineTo(px + 12, py);
                ctx.moveTo(px, py - 12); ctx.lineTo(px, py + 12);
                ctx.stroke();
            }
        }
        function mid(a, b) { return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }; }
    }
}
