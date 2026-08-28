import json
import math
import os
import re
import shutil
import tempfile
from ctypes import CDLL

import linuxcnc
from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from qtpyvcp.utilities import logger


LOG = logger.getLogger('qtpyvcp.' + __name__)


INCH_TO_MM = 25.4

TOOLPATH_STYLES = {
    'feed': {
        'strokeColor': '#333333',
        'lineWidth': 1.2,
        'dashPattern': [],
    },
    'traverse': {
        'strokeColor': '#777777',
        'lineWidth': 0.9,
        'dashPattern': [6, 3],
    },
}


class ToolpathModel(QObject):
    toolpathChanged = pyqtSignal()
    statusChanged = pyqtSignal()

    def __init__(self, runtime_store=None, parent=None):
        super().__init__(parent)
        self._runtime_store = runtime_store
        self._batches = []
        self._extents = {}
        self._workpiece = {}
        self._stock_profile = []
        self._error = ''
        self._loading = False
        self._current_file = ''

    @pyqtProperty('QVariantList', notify=toolpathChanged)
    def batches(self):
        return self._batches

    @pyqtProperty('QVariantMap', notify=toolpathChanged)
    def extents(self):
        return self._extents

    @pyqtProperty('QVariantMap', notify=toolpathChanged)
    def workpiece(self):
        return self._workpiece

    @pyqtProperty('QVariantList', notify=toolpathChanged)
    def stockProfile(self):
        return self._stock_profile

    @pyqtProperty(str, notify=statusChanged)
    def error(self):
        return self._error

    @pyqtProperty(bool, notify=statusChanged)
    def loading(self):
        return self._loading

    @pyqtProperty(str, notify=toolpathChanged)
    def currentFile(self):
        return self._current_file

    @pyqtSlot(str)
    def loadFile(self, filename):
        filename = os.path.abspath(str(filename or ''))
        if not filename or not os.path.isfile(filename):
            self._set_result([], {}, {}, [], '', filename)
            return

        self._set_loading(True)
        try:
            program_data = self._load_program_json(filename)
            canon = self._parse_native(filename)
            batches, extents, stock_profile = self._build_batches(canon)
            workpiece = self._workpiece_from_program_data(program_data)
            self._set_result(batches, extents, workpiece, stock_profile, '', filename)
        except Exception as exc:
            LOG.exception('Toolpath preview failed for %s', filename)
            self._set_result([], {}, {}, [], str(exc), filename)
        finally:
            self._set_loading(False)

    @pyqtSlot()
    def clear(self):
        self._set_result([], {}, {}, [], '', '')

    def _set_loading(self, loading):
        loading = bool(loading)
        if self._loading == loading:
            return
        self._loading = loading
        self.statusChanged.emit()

    def _set_result(self, batches, extents, workpiece, stock_profile, error, filename):
        self._batches = batches
        self._extents = extents
        self._workpiece = workpiece or {}
        self._stock_profile = stock_profile or []
        self._error = error
        self._current_file = filename
        self.toolpathChanged.emit()
        self.statusChanged.emit()

    def _parse_native(self, filename):
        self._init_tooldata()
        import gcode

        parse_native = getattr(gcode, 'parse_native', None)
        if parse_native is None:
            raise RuntimeError('gcode.parse_native is not available; update LinuxCNC native preview first')

        stat = self._stat()
        stat.poll()
        ini = self._ini()
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._build_config(stat, ini, temp_dir)
            initcodes = self._build_initcodes(stat, ini)
            parsed = parse_native(filename, config, initcodes)

        canon, result, seq = self._unpack_parse_result(parsed)
        min_error = getattr(gcode, 'MIN_ERROR', 0)
        if result > min_error:
            raise RuntimeError('G-code preview error %s at seq %s' % (result, seq))
        if not self._has_drawable_data(canon):
            raise RuntimeError(
                'native preview canon does not expose drawable elements; got %s with fields: %s'
                % (type(canon).__name__, ', '.join(self._public_fields(canon)[:24]))
            )
        return canon

    def _unpack_parse_result(self, parsed):
        if not isinstance(parsed, tuple):
            raise RuntimeError('gcode.parse_native returned %s, expected tuple' % type(parsed).__name__)

        canon = None
        result = 0
        seq = 0
        numbers = []
        for value in parsed:
            if self._has_drawable_data(value):
                canon = value
            elif isinstance(value, int):
                numbers.append(value)

        if canon is None and parsed:
            canon = parsed[0]
        if numbers:
            result = numbers[0]
        if len(numbers) > 1:
            seq = numbers[1]
        return canon, result, seq

    def _has_drawable_data(self, obj):
        return any(hasattr(obj, name) for name in ('elements', 'lines', 'traverse', 'feed', 'arcfeed'))

    def _public_fields(self, obj):
        try:
            return sorted(name for name in dir(obj) if not name.startswith('_'))
        except Exception:
            return []

    def _init_tooldata(self):
        try:
            tooldata = CDLL('libtooldata.so.0')
            tooldata.tool_mmap_user()
        except Exception as exc:
            LOG.exception('Toolpath preview could not initialize tool data mmap')
            raise RuntimeError('tool data mmap could not be initialized') from exc

    def _stat(self):
        if self._runtime_store is not None:
            return self._runtime_store.stat
        return linuxcnc.stat()

    def _ini(self):
        ini_file = os.getenv('INI_FILE_NAME')
        if not ini_file:
            return None
        try:
            return linuxcnc.ini(ini_file)
        except Exception:
            LOG.exception('Toolpath preview could not read INI file %s', ini_file)
            return None

    def _build_config(self, stat, ini, temp_dir):
        parameter_file = ''
        if ini is not None:
            source_parameter = ini.find('RS274NGC', 'PARAMETER_FILE') or ''
            if source_parameter:
                parameter_file = os.path.join(temp_dir, os.path.basename(source_parameter))
                shutil.copy(source_parameter, parameter_file)

        return {
            'tools': list(getattr(stat, 'tool_table', ()) or ()),
            'axis_mask': int(getattr(stat, 'axis_mask', 0) or 0),
            'angular_units': float(getattr(stat, 'angular_units', 1.0) or 1.0),
            'linear_units': float(getattr(stat, 'linear_units', 1.0) or 1.0),
            'block_delete': bool(getattr(stat, 'block_delete', False)),
            'random_toolchanger': self._ini_int(ini, 'EMCIO', 'RANDOM_TOOLCHANGER', 0),
            'parameter_file': parameter_file,
            'arcdivision': self._ini_int(ini, 'DISPLAY', 'ARCDIVISION', 64),
            'is_foam': False,
        }

    def _build_initcodes(self, stat, ini):
        initcodes = []
        startup = ini.find('RS274NGC', 'RS274NGC_STARTUP_CODE') if ini is not None else ''
        if startup:
            initcodes.append(startup)

        linear_units = int(getattr(stat, 'linear_units', 0) or 0)
        initcodes.append('G%d' % (20 + (linear_units == 1)))

        tool_offset = 'G43.1'
        has_offset = False
        offsets = getattr(stat, 'tool_offset', ()) or ()
        axis_mask = int(getattr(stat, 'axis_mask', 0) or 0)
        for index, axis in enumerate('XYZABCUVW'):
            if axis_mask & (1 << index):
                value = float(offsets[index] if index < len(offsets) else 0.0)
                tool_offset += ' %s%.8f' % (axis, value)
                has_offset = has_offset or abs(value) > 1e-12
        if has_offset:
            initcodes.append(tool_offset)
        return initcodes

    def _ini_int(self, ini, section, key, default):
        if ini is None:
            return default
        try:
            return int(ini.find(section, key) or default)
        except Exception:
            return default

    def _load_program_json(self, filename):
        json_path = self._source_json_path(filename)
        if not json_path:
            return None
        try:
            with open(json_path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
        except Exception:
            LOG.exception('Toolpath preview could not read program data from %s', json_path)
        return None

    def _workpiece_from_program_data(self, data):
        workpiece = (((data or {}).get('header') or {}).get('workpiece') or {})
        if isinstance(workpiece, dict):
            out = dict(workpiece)
            if not out.get('stock_length') and out.get('stickout_length'):
                out['stock_length'] = out.get('stickout_length')
            return out
        return {}

    def _source_json_path(self, filename):
        comment_name = self._program_json_comment(filename)
        candidates = []
        if comment_name:
            candidates.append(os.path.join(os.path.dirname(filename), comment_name))
            parent = os.path.dirname(os.path.dirname(filename))
            candidates.append(os.path.join(parent, 'Conversational Json', comment_name))
        base = os.path.splitext(os.path.basename(filename))[0] + '.json'
        parent = os.path.dirname(os.path.dirname(filename))
        candidates.append(os.path.join(parent, 'Conversational Json', base))
        candidates.append(os.path.splitext(filename)[0] + '.json')

        for candidate in candidates:
            candidate = os.path.abspath(candidate)
            if os.path.isfile(candidate):
                return candidate
        return ''

    def _program_json_comment(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8', errors='replace') as handle:
                for _index in range(20):
                    line = handle.readline()
                    if not line:
                        break
                    match = re.search(r'\(\s*Program:\s*([^)]+?)\s*\)', line)
                    if match:
                        return os.path.basename(match.group(1).strip())
        except Exception:
            LOG.exception('Toolpath preview could not inspect program header %s', filename)
        return ''

    def _build_batches(self, canon):
        batches_by_style = {}
        feed_edges = []
        feed_chains = []
        current_feed_chain = None
        z_min = x_min = math.inf
        z_max = x_max = -math.inf

        def batch_for(style):
            if style not in batches_by_style:
                style_config = TOOLPATH_STYLES.get(style, TOOLPATH_STYLES['feed'])
                batches_by_style[style] = {
                    'style': style,
                    'strokeColor': style_config['strokeColor'],
                    'lineWidth': style_config['lineWidth'],
                    'dashPattern': list(style_config['dashPattern']),
                    'lines': [],
                    'arcs': [],
                }
            return batches_by_style[style]

        def include(z, x):
            nonlocal z_min, x_min, z_max, x_max
            z_min = min(z_min, z)
            z_max = max(z_max, z)
            x_min = min(x_min, x)
            x_max = max(x_max, x)

        def add_feed_edge(edge):
            nonlocal current_feed_chain
            feed_edges.append(edge)
            if current_feed_chain and self._edges_connect(current_feed_chain[-1], edge):
                current_feed_chain.append(edge)
                return
            current_feed_chain = [edge]
            feed_chains.append(current_feed_chain)

        arcs = list(getattr(canon, 'arcs', ()) or ())
        elements = list(self._elements(canon))

        if not elements:
            for style, _lineno, start, end, _tooloffset in self._historical_segments(canon):
                z0 = self._axis(start, 2) * INCH_TO_MM
                x0 = self._axis(start, 0) * INCH_TO_MM * 2
                z1 = self._axis(end, 2) * INCH_TO_MM
                x1 = self._axis(end, 0) * INCH_TO_MM * 2
                include(z0, x0)
                include(z1, x1)
                batch_for(style)['lines'].append([z0, x0, z1, x1])
                if style == 'feed':
                    feed_edges.append({'type': 'line', 'z0': z0, 'x0': x0, 'z1': z1, 'x1': x1})
            extents = {}
            if z_min != math.inf:
                extents = {'zMin': z_min, 'zMax': z_max, 'xMin': x_min, 'xMax': x_max}
            return self._ordered_batches(batches_by_style), extents, self._build_stock_profile(feed_edges)

        for element in elements:
            kind = self._field(element, 'kind', '')
            if str(kind).upper() == 'DWELL':
                continue

            start = self._field(element, 'start', None)
            end = self._field(element, 'end', None)
            if start is None or end is None:
                continue

            z0 = self._axis(start, 2) * INCH_TO_MM
            x0 = self._axis(start, 0) * INCH_TO_MM * 2
            z1 = self._axis(end, 2) * INCH_TO_MM
            x1 = self._axis(end, 0) * INCH_TO_MM * 2
            include(z0, x0)
            include(z1, x1)

            arc_index = int(self._field(element, 'arc_index', -1) or -1)
            style = self._style_for_element(element)
            if style != 'feed':
                current_feed_chain = None
            if arc_index >= 0 and arc_index < len(arcs):
                arc = arcs[arc_index]
                center = self._field(arc, 'center', None)
                radius = float(self._field(arc, 'radius', 0.0) or 0.0) * INCH_TO_MM
                if center is not None and radius > 0:
                    cz = self._axis(center, 2) * INCH_TO_MM
                    cx = self._axis(center, 0) * INCH_TO_MM * 2
                    a0 = float(self._field(arc, 'start_angle', 0.0) or 0.0)
                    a1 = float(self._field(arc, 'end_angle', 0.0) or 0.0)
                    include(cz - radius, cx - radius * 2)
                    include(cz + radius, cx + radius * 2)
                    arc_data = {
                        'cz': cz,
                        'cx': cx,
                        'r': radius,
                        'a0': a0,
                        'a1': a1,
                        'z0': z0,
                        'x0': x0,
                        'z1': z1,
                        'x1': x1,
                    }
                    batch_for(style)['arcs'].append(arc_data)
                    if style == 'feed':
                        add_feed_edge({'type': 'arc', **arc_data})
                    continue

            batch_for(style)['lines'].append([z0, x0, z1, x1])
            if style == 'feed':
                add_feed_edge({'type': 'line', 'z0': z0, 'x0': x0, 'z1': z1, 'x1': x1})

        extents = {}
        if z_min != math.inf:
            extents = {'zMin': z_min, 'zMax': z_max, 'xMin': x_min, 'xMax': x_max}
        profile_edges = self._select_profile_edges(feed_chains, feed_edges)
        return self._ordered_batches(batches_by_style), extents, self._build_stock_profile(profile_edges)

    def _ordered_batches(self, batches_by_style):
        return [
            batches_by_style[style]
            for style in ('traverse', 'feed')
            if style in batches_by_style
        ]

    def _style_for_element(self, element):
        kind_text = str(self._field(element, 'kind', '')).upper()
        if 'TRAVERSE' in kind_text or 'RAPID' in kind_text:
            return 'traverse'
        return 'feed'

    def _sample_arc_for_profile(self, cz, cx, radius, a0, a1):
        sweep = a1 - a0
        steps = max(8, min(96, int(abs(sweep) / (math.pi / 24)) + 1))
        points = []
        for index in range(steps + 1):
            angle = a0 + sweep * index / steps
            points.append([cz + math.cos(angle) * radius, cx + math.sin(angle) * radius * 2])
        return points

    def _build_stock_profile(self, edges):
        edges = list(edges or [])
        if not edges:
            return []

        z_values = []
        for edge in edges:
            if edge.get('type') == 'arc':
                z_values.extend(point[0] for point in self._sample_arc_for_profile(
                    edge['cz'], edge['cx'], edge['r'], edge['a0'], edge['a1']))
            else:
                z_values.extend((edge.get('z0', 0.0), edge.get('z1', 0.0)))
        z_min = min(z_values)
        z_max = max(z_values)
        z_samples = {round(float(z), 3) for z in z_values}

        span = z_max - z_min
        if span > 1e-9:
            sample_count = max(80, min(1600, int(span / 0.25) + 1))
            for index in range(sample_count + 1):
                z_samples.add(round(z_min + span * index / sample_count, 3))

        out = []
        for z in sorted(z_samples):
            candidates = []
            for edge in edges:
                candidates.extend(self._edge_x_at_z(edge, z))
            if not candidates:
                continue
            x = min(candidates)
            if x > 0:
                out.append([z, x])
        return out

    def _select_profile_edges(self, chains, fallback_edges):
        profile_edges = []
        for chain in chains:
            if self._is_profile_chain(chain):
                profile_edges.extend(chain)
        return profile_edges or fallback_edges

    def _is_profile_chain(self, chain):
        chain = list(chain or [])
        if len(chain) < 2 and not any(edge.get('type') == 'arc' for edge in chain):
            return False

        z_values = []
        x_values = []
        for edge in chain:
            z_values.extend((edge.get('z0', 0.0), edge.get('z1', 0.0)))
            x_values.extend((edge.get('x0', 0.0), edge.get('x1', 0.0)))
            if edge.get('type') == 'arc':
                arc_points = self._sample_arc_for_profile(edge['cz'], edge['cx'], edge['r'], edge['a0'], edge['a1'])
                z_values.extend(point[0] for point in arc_points)
                x_values.extend(point[1] for point in arc_points)

        if not z_values or not x_values:
            return False
        return max(z_values) - min(z_values) > 1e-6 and max(x_values) - min(x_values) > 1e-6

    def _edges_connect(self, previous, current):
        return (
            abs(previous.get('z1', 0.0) - current.get('z0', 0.0)) <= 1e-6
            and abs(previous.get('x1', 0.0) - current.get('x0', 0.0)) <= 1e-6
        )

    def _edge_x_at_z(self, edge, target_z):
        if edge.get('type') == 'arc':
            return self._arc_x_at_z(edge, target_z)

        hits = []
        z0 = edge.get('z0', 0.0)
        x0 = edge.get('x0', 0.0)
        z1 = edge.get('z1', 0.0)
        x1 = edge.get('x1', 0.0)
        z_lo = min(z0, z1)
        z_hi = max(z0, z1)
        if target_z < z_lo - 1e-6 or target_z > z_hi + 1e-6:
            return hits
        if abs(z1 - z0) <= 1e-9:
            if abs(target_z - z0) <= 1e-6:
                hits.extend((x0, x1))
            return hits
        t = (target_z - z0) / (z1 - z0)
        hits.append(x0 + t * (x1 - x0))
        return hits

    def _arc_x_at_z(self, edge, target_z):
        radius = edge.get('r', 0.0)
        dz = target_z - edge.get('cz', 0.0)
        if radius <= 0 or abs(dz) > radius + 1e-9:
            return []

        candidates = []
        for angle in (math.acos(max(-1.0, min(1.0, dz / radius))),
                      -math.acos(max(-1.0, min(1.0, dz / radius)))):
            if self._angle_on_render_arc(angle, edge.get('a0', 0.0), edge.get('a1', 0.0)):
                candidates.append(edge.get('cx', 0.0) + math.sin(angle) * radius * 2.0)
        return candidates

    def _angle_on_render_arc(self, angle, start_angle, end_angle):
        sweep = end_angle - start_angle
        if abs(sweep) <= 1e-12:
            return abs(self._normalize_angle(angle) - self._normalize_angle(start_angle)) <= 1e-9
        if sweep > 0:
            while angle < start_angle:
                angle += 2.0 * math.pi
            while end_angle < start_angle:
                end_angle += 2.0 * math.pi
            return start_angle - 1e-9 <= angle <= end_angle + 1e-9
        while angle > start_angle:
            angle -= 2.0 * math.pi
        while end_angle > start_angle:
            end_angle -= 2.0 * math.pi
        return end_angle - 1e-9 <= angle <= start_angle + 1e-9

    def _normalize_angle(self, angle):
        two_pi = 2.0 * math.pi
        while angle < 0.0:
            angle += two_pi
        while angle >= two_pi:
            angle -= two_pi
        return angle

    def _elements(self, canon):
        elements = getattr(canon, 'elements', None)
        if callable(elements):
            return elements()
        return getattr(canon, 'lines', ()) or ()

    def _historical_segments(self, canon):
        for name in ('traverse', 'feed', 'arcfeed'):
            style = 'traverse' if name == 'traverse' else 'feed'
            for segment in getattr(canon, name, ()) or ():
                if len(segment) >= 4:
                    lineno, start, end, tooloffset = segment[:4]
                    yield style, lineno, start, end, tooloffset

    def _field(self, obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    def _axis(self, values, index):
        try:
            return float(values[index])
        except Exception:
            return 0.0
