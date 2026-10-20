"""Fetch and parse the live GEE blocklist modules used by the Landsat export."""

import os
import re
import subprocess
import tempfile


ROOT_REQUIRE = 'users/mapbiomasworkspace1/mapbiomas-fire:00_Tools/require-landsat-collection'
SUPPORTED_SENSORS = ('landsat',)
_BLOCKLISTS = None


class BlocklistSourceError(RuntimeError):
    """Raised when current blocklists cannot be fetched or parsed safely."""


GEE_GIT_URL = 'https://earthengine.googlesource.com'


def _git_environment():
    """Build a non-interactive git environment for the public GEE sources.

    GEE git authentication uses a generated password (gitcookies or a
    credential helper), not an OAuth bearer header. A stale ``extraheader``
    inherited from the notebook turns anonymous reads into a credential
    prompt, so reset it. Helpers stay enabled for private repositories.
    """
    env = os.environ.copy()
    env['GIT_TERMINAL_PROMPT'] = '0'
    config_index = int(env.get('GIT_CONFIG_COUNT', '0'))
    env['GIT_CONFIG_COUNT'] = str(config_index + 1)
    env[f'GIT_CONFIG_KEY_{config_index}'] = f'http.{GEE_GIT_URL}/.extraheader'
    env[f'GIT_CONFIG_VALUE_{config_index}'] = ''
    return env


def _strip_js_comments(source):
    """Remove JavaScript comments without changing quoted strings."""
    result = []
    i = 0
    quote = None
    while i < len(source):
        char = source[i]
        if quote:
            result.append(char)
            if char == '\\' and i + 1 < len(source):
                i += 1
                result.append(source[i])
            elif char == quote:
                quote = None
            i += 1
            continue

        if char in ('\'', '"', '`'):
            quote = char
            result.append(char)
            i += 1
        elif source.startswith('//', i):
            while i < len(source) and source[i] not in '\r\n':
                result.append(' ')
                i += 1
        elif source.startswith('/*', i):
            result.extend((' ', ' '))
            i += 2
            while i < len(source) and not source.startswith('*/', i):
                result.append('\n' if source[i] == '\n' else ' ')
                i += 1
            if i < len(source):
                result.extend((' ', ' '))
                i += 2
        else:
            result.append(char)
            i += 1
    return ''.join(result)


def _require_calls(source):
    clean = _strip_js_comments(source)
    pattern = re.compile(
        r"\brequire\s*\(\s*(['\"])(.*?)\1\s*\)\s*\.\s*([A-Za-z_$][\w$]*)\s*\("
    )
    return [(match.group(2), match.group(3)) for match in pattern.finditer(clean)]


def _matching_bracket(source, start, opening='[', closing=']'):
    depth = 0
    quote = None
    i = start
    while i < len(source):
        char = source[i]
        if quote:
            if char == '\\':
                i += 2
                continue
            if char == quote:
                quote = None
        elif char in ('\'', '"', '`'):
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise BlocklistSourceError(f"Unclosed JavaScript {opening}{closing} list.")


def _string_values(source):
    values = []
    i = 0
    while i < len(source):
        if source[i] not in ('\'', '"'):
            i += 1
            continue
        quote = source[i]
        i += 1
        chars = []
        while i < len(source) and source[i] != quote:
            if source[i] == '\\' and i + 1 < len(source):
                i += 1
            chars.append(source[i])
            i += 1
        if i >= len(source):
            raise BlocklistSourceError("Unclosed JavaScript string in blocklist.")
        values.append(''.join(chars))
        i += 1
    return values


def _exported_list(source, sensor):
    clean = _strip_js_comments(source)
    export = re.search(
        rf"\bexports\s*\.\s*{re.escape(sensor)}\s*=\s*function\s*\([^)]*\)\s*\{{",
        clean,
    )
    if not export:
        return None

    returned = re.search(r"\breturn\b", clean[export.end():])
    if not returned:
        return None
    return_start = export.end() + returned.end()
    list_start = clean.find('[', return_start)
    if list_start < 0:
        return None
    list_end = _matching_bracket(clean, list_start)
    return _string_values(clean[list_start + 1:list_end])


def _parse_asset_id(asset_id):
    match = re.fullmatch(r'users/([^/]+)/([^:]+):(.+)', asset_id)
    if not match:
        raise BlocklistSourceError(f"Unsupported GEE require path: {asset_id}")
    owner, repository, file_path = match.groups()
    remote = f"https://earthengine.googlesource.com/users/{owner}/{repository}"
    return remote, file_path


class _SparseGeeSources:
    """Read only the JavaScript files reachable from a GEE require path."""

    def __init__(self, temp_root):
        self.temp_root = temp_root
        self.repositories = {}
        self.git_env = _git_environment()

    def read(self, asset_id):
        remote, file_path = _parse_asset_id(asset_id)
        repository = self.repositories.get(remote)
        if repository is None:
            local_path = os.path.join(self.temp_root, f"source_{len(self.repositories)}")
            try:
                subprocess.run(
                    ['git', 'clone', '--depth', '1', '--filter=blob:none', '--sparse', remote, local_path],
                    check=True, capture_output=True, text=True, env=self.git_env,
                )
            except (OSError, subprocess.CalledProcessError) as error:
                detail = (getattr(error, 'stderr', None) or str(error)).strip()
                raise BlocklistSourceError(f"Could not fetch GEE source {remote}: {detail}") from error
            repository = {'path': local_path, 'files': set()}
            self.repositories[remote] = repository

        normalized_path = file_path.replace('\\', '/')
        if normalized_path not in repository['files']:
            repository['files'].add(normalized_path)
            sparse_paths = [f"/{path}" for path in sorted(repository['files'])]
            try:
                subprocess.run(
                    ['git', '-C', repository['path'], 'sparse-checkout', 'set', '--no-cone', *sparse_paths],
                    check=True, capture_output=True, text=True, env=self.git_env,
                )
            except subprocess.CalledProcessError as error:
                detail = (error.stderr or str(error)).strip()
                raise BlocklistSourceError(f"Could not select GEE source file {file_path}: {detail}") from error

        full_path = os.path.join(repository['path'], *normalized_path.split('/'))
        try:
            with open(full_path, 'r', encoding='utf-8') as source_file:
                return source_file.read()
        except OSError as error:
            raise BlocklistSourceError(f"GEE source file is unavailable: {asset_id}") from error


def extract_blocklists(read_source, root_require=ROOT_REQUIRE):
    """Resolve require() calls recursively and return distinct exported lists."""
    collected = {}
    visited = set()
    queue = [(root_require, None)]

    while queue:
        asset_id, sensor = queue.pop(0)
        key = (asset_id, sensor)
        if key in visited:
            continue
        visited.add(key)
        if len(visited) > 128:
            raise BlocklistSourceError("Too many nested require() modules while reading blocklists.")

        source = read_source(asset_id)
        if sensor:
            values = _exported_list(source, sensor)
            if values is not None:
                collected.setdefault(sensor.lower(), []).extend(values)
        queue.extend(_require_calls(source))

    result = {}
    for sensor, values in collected.items():
        # Preserve source order while matching Earth Engine's distinct() behavior.
        result[sensor] = list(dict.fromkeys(value for value in values if value))
    return result


def refresh_blocklists():
    """Fetch current GEE module sources and refresh the in-memory scene lists."""
    global _BLOCKLISTS
    with tempfile.TemporaryDirectory(prefix='mapbiomas_blocklists_') as temp_root:
        sources = _SparseGeeSources(temp_root)
        blocklists = extract_blocklists(sources.read)

    if not blocklists.get('landsat'):
        raise BlocklistSourceError("The current GEE require graph returned no Landsat blocklist entries.")
    _BLOCKLISTS = blocklists
    return {sensor: list(values) for sensor, values in blocklists.items()}


def get_blocklist(sensor):
    """Return the current blocklist for a sensor, fetching live sources if needed."""
    normalized_sensor = str(sensor).lower()
    if normalized_sensor not in SUPPORTED_SENSORS:
        return []
    if _BLOCKLISTS is None:
        refresh_blocklists()
    return list(_BLOCKLISTS.get(normalized_sensor, []))
