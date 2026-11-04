import QtQuick

/*
 * ThreadingInsert.qml  —  plăcuță de filetare ER / EL, parametrică
 * ---------------------------------------------------------------------------
 * Toate cotele sunt în MILIMETRI. Conversia în pixeli se face o singură dată,
 * prin `pxPerMm`, deci geometria internă rămâne în unități reale.
 *
 * CONSTRUCȚIA (verificată pe DXF ISCAR, eroare < 0.0001 mm):
 *   1. Corp = triunghi echilateral: laturile sunt tangente la cercul înscris
 *      de rază IC/2, colțurile teoretice se află la raza IC, latura L = IC·√3.
 *   2. Fiecare colț e retezat de o coardă PERPENDICULARĂ pe latura de referință.
 *   3. Dintele = V cu unghiul `a`, având BISECTOAREA PARALELĂ cu acea latură,
 *      sprijinit pe coardă. Vârful V-ului e rotunjit cu raza `r`.
 *   4. Vârful activ (punctul care urmărește toolpath-ul) = vârful V-ului.
 *
 *   Capătul coardei pe latura următoare rezultă analitic:  x = IC − √3·yb
 *
 * ORIENTARE: rotation = 0 este poziția corectă pentru un FILET EXTERIOR
 *            (vârful activ îndreptat în sus, latura de referință verticală).
 */
Item {
    id: root

    // ---- intrări ----------------------------------------------------------
    property string insertSize: "16"     // "11" | "16" | "22"
    property real   pitch:      1.5      // pas filet [mm] — vezi pitchTable
    property string hand:       "R"      // "R" = ER (dreapta) | "L" = EL (stânga)
    property real   pxPerMm:    20       // scara de randare
    property real   orientation: 0       // grade; 0 = filet exterior

    property color  bodyColor:  "#e8c84b"
    property color  edgeColor:  "#20242b"
    property color  holeColor:  "#12161b"
    property bool   showInscribedCircle: false

    // ---- constante --------------------------------------------------------
    readonly property real s3: Math.sqrt(3)
    readonly property real d2r: Math.PI / 180

    // cerc înscris [mm]
    readonly property var icTable: ({ "11": 6.35, "16": 9.525, "22": 12.7 })

    // gaură de prindere + teșitură [mm] — măsurate din DXF.
    // Raportul gaură/IC NU e constant (0.512 la 11 → 0.399 la 22).
    readonly property var holeTable: ({
        "11": { "d": 3.25, "cs": 4.80 },
        "16": { "d": 4.00, "cs": 6.00 },
        "22": { "d": 5.07, "cs": 7.70 }
    })

    // Parametrii dintelui, per (mărime, pas):
    //   r = raza la vârf                a = unghiul V [grade]
    //   X = distanța ⊥ de la latura lungă la bisectoare
    //   Y = distanța de la colțul teoretic, DE-A LUNGUL laturii, la vârful rotunjit
    //   h = înălțimea dintelui (de la coardă la vârful ascuțit)
    //   exact = true -> valori măsurate din DXF; false -> interpolate
    // ATENȚIE: r NU are formulă. r/P variază 0.126…0.157, iar la același pas
    // mărimile 11 și 16 au raze diferite. Se folosește tabelul, nu o formulă.
    readonly property var pitchTable: ({
      "11": {
        "0.5": { "r": 0.11, "a": 60.767, "X": 0.7278, "Y": 0.5998, "h": 0.414, "exact": false },
        "0.6": { "r": 0.11, "a": 60.767, "X": 0.6639, "Y": 0.5998, "h": 0.467, "exact": false },
        "0.7": { "r": 0.11, "a": 60.767, "X": 0.6, "Y": 0.5998, "h": 0.52, "exact": true },
        "0.75": { "r": 0.11, "a": 60.767, "X": 0.6, "Y": 0.5998, "h": 0.601, "exact": true },
        "0.8": { "r": 0.12, "a": 60.767, "X": 0.6, "Y": 0.5998, "h": 0.66, "exact": true },
        "1": { "r": 0.15, "a": 60.8, "X": 0.6932, "Y": 0.65, "h": 0.742, "exact": true },
        "1.25": { "r": 0.16, "a": 60.84, "X": 0.9, "Y": 0.7992, "h": 0.8836, "exact": true },
        "1.5": { "r": 0.1931, "a": 60.84, "X": 1.0, "Y": 0.8066, "h": 1.1193, "exact": true },
        "1.75": { "r": 0.2262, "a": 60.84, "X": 1.2145, "Y": 0.814, "h": 1.55, "exact": false },
        "2": { "r": 0.2593, "a": 60.84, "X": 1.2483, "Y": 0.8214, "h": 1.673, "exact": false }
      },
      "16": {
        "0.35": { "r": 0.0448, "a": 60.652, "X": 0.6003, "Y": 0.5795, "h": 0.3345, "exact": false },
        "0.4": { "r": 0.0534, "a": 60.691, "X": 0.6001, "Y": 0.5825, "h": 0.361, "exact": false },
        "0.45": { "r": 0.062, "a": 60.729, "X": 0.6001, "Y": 0.5854, "h": 0.3875, "exact": false },
        "0.5": { "r": 0.0706, "a": 60.767, "X": 0.6, "Y": 0.5883, "h": 0.414, "exact": true },
        "0.6": { "r": 0.0878, "a": 60.844, "X": 0.6, "Y": 0.5941, "h": 0.467, "exact": false },
        "0.7": { "r": 0.105, "a": 60.92, "X": 0.6, "Y": 0.6, "h": 0.52, "exact": true },
        "0.75": { "r": 0.1003, "a": 60.767, "X": 0.6, "Y": 0.5929, "h": 0.601, "exact": true },
        "0.8": { "r": 0.1022, "a": 60.774, "X": 0.6382, "Y": 0.614, "h": 0.66, "exact": false },
        "1": { "r": 0.11, "a": 60.8, "X": 0.7008, "Y": 0.6982, "h": 0.742, "exact": true },
        "1.25": { "r": 0.157, "a": 60.84, "X": 0.9, "Y": 0.8, "h": 0.8836, "exact": true },
        "1.5": { "r": 0.189, "a": 60.84, "X": 1.15, "Y": 0.9, "h": 1.1193, "exact": true },
        "1.75": { "r": 0.221, "a": 60.84, "X": 1.2, "Y": 0.9, "h": 1.55, "exact": true },
        "2": { "r": 0.25, "a": 60.8, "X": 1.3, "Y": 1.0, "h": 1.673, "exact": true },
        "2.5": { "r": 0.3428, "a": 60.767, "X": 1.5, "Y": 1.1501, "h": 1.9199, "exact": true },
        "3": { "r": 0.378, "a": 60.84, "X": 1.6, "Y": 1.2, "h": 2.238, "exact": true },
        "3.5": { "r": 0.5169, "a": 60.91, "X": 1.5999, "Y": 1.2666, "h": 2.629, "exact": true }
      },
      "22": {
        "1.5": { "r": 0.1856, "a": 61.132, "X": 1.2111, "Y": 1.4381, "h": 1.1193, "exact": false },
        "1.75": { "r": 0.2199, "a": 61.096, "X": 1.4648, "Y": 1.4584, "h": 1.55, "exact": false },
        "2": { "r": 0.2542, "a": 61.059, "X": 1.5366, "Y": 1.4786, "h": 1.673, "exact": false },
        "2.5": { "r": 0.3228, "a": 60.986, "X": 1.6806, "Y": 1.5191, "h": 1.9199, "exact": false },
        "3": { "r": 0.3914, "a": 60.913, "X": 1.866, "Y": 1.5596, "h": 2.238, "exact": false },
        "3.5": { "r": 0.46, "a": 60.84, "X": 2.3, "Y": 1.6001, "h": 2.629, "exact": true },
        "4": { "r": 0.5286, "a": 60.767, "X": 2.3, "Y": 1.6406, "h": 3.013, "exact": true },
        "4.5": { "r": 0.5893, "a": 60.767, "X": 2.4, "Y": 1.7077, "h": 3.3872, "exact": false },
        "5": { "r": 0.6499, "a": 60.767, "X": 2.5, "Y": 1.7748, "h": 3.7615, "exact": true },
        "5.5": { "r": 0.7106, "a": 60.767, "X": 2.6448, "Y": 1.8419, "h": 4.1357, "exact": false },
        "6": { "r": 0.7712, "a": 60.767, "X": 2.8643, "Y": 1.909, "h": 4.51, "exact": false }
      }
    })

    // ---- derivate ---------------------------------------------------------
    readonly property real ic:   icTable[insertSize]
    readonly property var  spec: pitchTable[insertSize][String(pitch)]
    readonly property real sideLength: ic * s3            // L = IC·√3
    readonly property bool specValid: spec !== undefined

    // lista de pași disponibili pentru mărimea curentă (pentru ComboBox)
    function availablePitches(sz) {
        var out = [];
        for (var k in pitchTable[sz]) out.push(parseFloat(k));
        out.sort(function (a, b) { return a - b; });
        return out;
    }

    // vârful activ, în mm, în sistemul plăcuței (centru = 0,0, y în sus)
    function activeTip() {
        if (!specValid) return Qt.point(0, 0);
        var half     = spec.a / 2 * d2r;
        var setback  = spec.r / Math.sin(half) - spec.r;
        var cornerY  = ic * s3 / 2;
        var ax = -ic / 2 + spec.X;
        var ay = cornerY - spec.Y + setback;
        return Qt.point(hand === "L" ? -ax : ax, ay);
    }

    // conturul complet, în mm: listă de puncte {x, y, tip}
    // `tip: true` marchează vârful care trebuie rotunjit cu raza r.
    function outlinePoints() {
        var half    = spec.a / 2 * d2r;
        var setback = spec.r / Math.sin(half) - spec.r;
        var cornerY = ic * s3 / 2;
        var fx      = -ic / 2;                       // latura de referință
        var apexX   = fx + spec.X;
        var apexY   = cornerY - spec.Y + setback;    // vârf ASCUȚIT
        var yb      = apexY - spec.h;                // nivelul coardei
        var t       = spec.h * Math.tan(half);       // jumătate bază

        var sector = [
            { x: fx,          y: yb, tip: false },   // capătul laturii lungi
            { x: apexX - t,   y: yb, tip: false },   // piciorul flancului 1
            { x: apexX,    y: apexY, tip: true  },   // VÂRF ACTIV
            { x: apexX + t,   y: yb, tip: false },   // piciorul flancului 2
            { x: ic - s3 * yb, y: yb, tip: false }   // începutul laturii următoare
        ];

        var pts = [];
        for (var k = 0; k < 3; k++) {                // simetrie 3-fold
            var ang = -120 * k * d2r;
            var c = Math.cos(ang), s = Math.sin(ang);
            for (var i = 0; i < sector.length; i++) {
                var p = sector[i];
                pts.push({ x: p.x * c - p.y * s,
                           y: p.x * s + p.y * c,
                           tip: p.tip });
            }
        }
        if (hand === "L")                            // EL = oglindit
            for (var j = 0; j < pts.length; j++) pts[j].x = -pts[j].x;
        return pts;
    }

    implicitWidth:  2.2 * ic * pxPerMm
    implicitHeight: 2.2 * ic * pxPerMm

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true
        rotation: -root.orientation

        // orice schimbare de parametru redesenează
        Connections {
            target: root
            function onInsertSizeChanged() { canvas.requestPaint() }
            function onPitchChanged()      { canvas.requestPaint() }
            function onHandChanged()       { canvas.requestPaint() }
            function onPxPerMmChanged()    { canvas.requestPaint() }
        }

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            if (!root.specValid) return;

            var k = root.pxPerMm;
            ctx.save();
            ctx.translate(width / 2, height / 2);
            ctx.scale(k, -k);                        // -y : matematic -> ecran

            var pts = root.outlinePoints();
            var n = pts.length;

            // contur cu vârfurile rotunjite prin arcTo()
            ctx.beginPath();
            var m0 = midPoint(pts[n - 1], pts[0]);
            ctx.moveTo(m0.x, m0.y);
            for (var i = 0; i < n; i++) {
                var cur = pts[i], nxt = pts[(i + 1) % n];
                var m = midPoint(cur, nxt);
                if (cur.tip) ctx.arcTo(cur.x, cur.y, m.x, m.y, root.spec.r);
                else         ctx.lineTo(cur.x, cur.y);
                ctx.lineTo(m.x, m.y);
            }
            ctx.closePath();

            ctx.fillStyle = root.bodyColor;
            ctx.fill();
            ctx.lineJoin = "round";
            ctx.lineWidth = 1.5 / k;
            ctx.strokeStyle = root.edgeColor;
            ctx.stroke();

            // teșitură + gaură
            var hl = root.holeTable[root.insertSize];
            ctx.beginPath();
            ctx.arc(0, 0, hl.cs / 2, 0, 2 * Math.PI);
            ctx.lineWidth = 1.2 / k;
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(0, 0, hl.d / 2, 0, 2 * Math.PI);
            ctx.fillStyle = root.holeColor;
            ctx.fill();
            ctx.lineWidth = 1.5 / k;
            ctx.stroke();

            if (root.showInscribedCircle) {
                ctx.beginPath();
                ctx.arc(0, 0, root.ic / 2, 0, 2 * Math.PI);
                ctx.lineWidth = 1 / k;
                ctx.strokeStyle = "#3fb7c2";
                ctx.stroke();
            }
            ctx.restore();
        }

        function midPoint(a, b) {
            return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
        }
    }
}
