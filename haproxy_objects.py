# coding=utf-8
import os


class ConfigIsInvalid(Exception):
    pass


class Config(object):
    def __init__(self):
        self.globals = GlobalConfig()
        self.defaults = DefaultConfig()
        self.frontends = {}
        self.backends = {}
        self.listens = {}
        super(Config, self).__init__()

    @classmethod
    def _read_to_next_part(cls, lines):
        _lines = []

        i = 0
        while i < len(lines):
            line = lines[i].partition('#')[0].strip()
            if line.startswith('global') or line.startswith('listen') or \
                    line.startswith('defaults') or line.startswith('frontend') or \
                    line.startswith('backend'):
                break

            if not line.startswith('#'):
                _lines.append(line)
            i += 1

        return _lines, i

    @classmethod
    def from_string(cls, filename):
        if not os.path.exists(filename):
            raise ConfigIsInvalid('%s is not exist' % filename)

        c = cls()

        with open(filename, 'rb') as handler:
            lines = handler.readlines()

            while lines:
                line = lines[0].partition('#')[0].strip()
                lines = lines[1:]

                if line and not line.startswith('#'):
                    parts = line.split()
                    part_name = parts[0]

                    if part_name in ['global', 'defaults', 'listen', 'frontend', 'backend']:
                        part_lines, _next_i = Config._read_to_next_part(lines)

                        if part_name == 'global':
                            c.globals = GlobalConfig()
                            c.globals.from_string(part_lines)

                        elif part_name == 'defaults':
                            c.defaults = DefaultConfig()
                            c.defaults.from_string(part_lines)

                        elif part_name == 'listen':
                            if len(parts) == 3:
                                part_lines.insert(0, 'bind %s' % parts[2])

                            l = ListenConfig()
                            l.name = parts[1]
                            l.from_string(part_lines)
                            c.listens[parts[1]] = l

                        elif part_name == 'frontend':
                            if len(parts) == 3:
                                part_lines.insert(0, 'bind %s' % parts[2])

                            l = FrontendConfig()
                            l.name = parts[1]
                            l.from_string(part_lines)
                            c.frontends[parts[1]] = l

                        elif part_name == 'backend':
                            l = BackendConfig()
                            l.name = parts[1]
                            l.from_string(part_lines)
                            c.backends[parts[1]] = l

                        lines = lines[_next_i:]
                        continue

        return c

    def to_string(self):
        lines = ['# created by haproxy-tool', '']
        lines.append('global')
        for line in self.globals.to_string().split('\n'):
            lines.append('\t' + line)

        lines.append('\n')

        lines.append('defaults')
        for line in self.defaults.to_string().split('\n'):
            lines.append('\t' + line)

        lines.append('\n')

        for frontend_name in self.frontends:
            lines.append('frontend %s' % frontend_name)

            for line in self.frontends[frontend_name].to_string().split('\n'):
                lines.append('\t' + line)

            lines.append('\n')

        for backend_name in self.backends:
            lines.append('backend %s' % backend_name)

            for line in self.backends[backend_name].to_string().split('\n'):
                lines.append('\t' + line)

            lines.append('\n')

        for listen_name in self.listens:
            lines.append('listen %s' % listen_name)

            for line in self.listens[listen_name].to_string().split('\n'):
                lines.append('\t' + line)

            lines.append('\n')

        return '\n'.join(lines)

    def __dict__(self):
        out = {
            'global': dict(self.globals),
            'defaults': dict(self.defaults),
            'frontend': {},
            'backend': {},
            'listen': {}
        }
        for key in self.frontends:
            out['frontend'][key] = dict(self.frontends[key])

        for key in self.backends:
            out['backend'][key] = dict(self.backends[key])

        for key in self.listens:
            out['listen'][key] = dict(self.listens[key])

        return out


class GlobalConfig(object):
    def __init__(self):
        # log <address> <facility> [<level> [<minlevel>]]
        self.log = {}
        self.max_connections = None
        self.user = 'haproxy'
        self.group = 'haproxy'
        self.daemon = True
        self.chroot = None
        self.stats = {
            'socket': '/tmp/haproxy'
        }
        self.number_processes = 5
        self.pid_file = '/var/run/haproxy.pid'
        self._raw = None
        super(GlobalConfig, self).__init__()

    def __dict__(self):
        return {
            'log': self.log,
            'max_connections': self.max_connections,
            'use': self.user,
            'group': self.group,
            'daemon': self.daemon,
            'chroot': self.chroot,
            'stats': self.stats,
            'number_processes': self.number_processes,
            'pid_file': self.pid_file
        }

    def set_value(self, key, line):
        parts = line.split()

        if key == 'log':
            address = parts[0]
            facility = parts[1]
            try:
                level = parts[2]
            except:
                level = None

            try:
                min_level = parts[3]
            except:
                min_level = None

            self.set_log(address, facility, level, min_level)

        elif key == 'maxconn':
            self.set_max_connections(parts[0])

        elif key == 'pidfile':
            self.set_pid_file(parts[0])

        elif key == 'daemon':
            self.set_daemon(True)

        elif key == 'user':
            self.set_user(parts[0])

        elif key == 'group':
            self.set_group(parts[0])

        elif key == 'chroot':
            try:
                chroot = parts[0]
            except:
                chroot = ''
            self.set_chroot(chroot)

        elif key == 'nbproc':
            self.set_number_processes(parts[0])

    def from_string(self, lines):
        self._raw = lines
        for line in lines:
            line = line.partition('#')[0].strip()

            if line and not line.startswith('#'):
                parts = line.split()
                key = parts[0]

                self.set_value(key, ' '.join(parts[1:]))

    def to_string(self):
        lines = []

        for address in self.log:
            for facility in self.log[address]:
                _log = 'log %s %s' % (address, facility)
                if self.log[address][facility]:
                    _log += ' %s' % self.log[address][facility].get('level', '')
                    _log += ' %s' % self.log[address][facility].get('min-level', '')

                lines.append(_log.strip())

        lines.append('user %s' % self.user)
        lines.append('group %s' % self.group)
        lines.append('pidfile %s' % self.pid_file)

        if self.max_connections:
            lines.append('maxconn %s' % self.max_connections)

        if self.daemon:
            lines.append('daemon')

        if self.chroot:
            lines.append('chroot')

        lines.append('nbproc %s' % self.number_processes)
        for t in self.stats:
            lines.append('stats %s %s' % (t, self.stats[t]))

        return '\n'.join(lines)

    def set_log(self, address, facility, level=None, min_level=None):
        """
        {
            '127.0.0.1': {
                'local0': {
                    'level': 'notice'
                }
            }
        }
        """
        if address not in self.log:
            self.log[address] = {}

        if facility not in self.log[address]:
            self.log[address][facility] = {}

        if level:
            self.log[address][facility]['level'] = level

        if min_level:
            self.log[address][facility]['min-level'] = min_level

    def set_stats_socket(self, socket_path):
        self.stats['socket'] = socket_path

    def set_stats_timeout(self, timeout='10s'):
        """
        timeout - milliseconds, The default timeout on the stats socket is set to 10 seconds
        the time unit is us, ms, s, m, h, d
        """
        self.stats['timeout'] = timeout

    def set_stats_max_connections(self, connections=10):
        """
        connections - By default, the stats socket is limited to 10 concurrent connections.
        """
        self.stats['maxconn'] = connections

    def set_pid_file(self, filename):
        dir_name = os.path.dirname(filename)
        if os.path.exists(dir_name):
            self.pid_file = filename

        else:
            raise ConfigIsInvalid('Global pid file config is not exists')

    def set_number_processes(self, value):
        try:
            self.number_processes = int(value)
        except:
            raise ConfigIsInvalid('Global nbproc config is invalid')

    def set_max_connections(self, value):
        try:
            self.max_connections = int(value)
        except:
            raise ConfigIsInvalid('Global maxconn config is invalid')

    def set_user(self, user):
        self.user = user

    def set_group(self, group):
        self.group = group

    def set_daemon(self, daemon=True):
        try:
            self.daemon = bool(daemon)
        except:
            raise ConfigIsInvalid('Global daemon config is invalid')

    def set_chroot(self, chroot='/var/lib/haproxy'):
        """
        Changes current directory to <jail dir> and performs a chroot() there before
        dropping privileges. This increases the security level in case an unknown
        vulnerability would be exploited, since it would make it very hard for the
        attacker to exploit the system. This only works when the process is started
        with superuser privileges. It is important to ensure that <jail_dir> is both
        empty and unwritable to anyone.
        """
        self.chroot = chroot


class DefaultConfig(object):
    def __init__(self):
        self.log = {}
        self.option = {}
        self.mode = 'http'
        self.option = {}
        self.retries = None
        self.max_connections = None
        self.client_timeout = None
        self.server_timeout = None
        self.connect_timeout = None
        self._raw = None
        super(DefaultConfig, self).__init__()

    def __dict__(self):
        return {
            'log': self.log,
            'option': self.option,
            'mode': self.mode,
            'retries': self.retries,
            'max_connections': self.max_connections,
        }

    def set_log(self, address, facility, level=None, min_level=None):
        """
        {
            '127.0.0.1': {
                'local0': {
                    'level': 'notice'
                }
            }
        }
        """
        if address not in self.log:
            self.log[address] = {}

        if facility not in self.log[address]:
            self.log[address][facility] = {}

        if level:
            self.log[address][facility]['level'] = level

        if min_level:
            self.log[address][facility]['min-level'] = min_level

    def set_option(self, key, parts):
        if isinstance(parts, list):
            value = ' '.join(parts)
        else:
            value = parts

        self.option[key] = value

    def set_max_connections(self, value):
        try:
            self.max_connections = int(value)

        except:
            raise ConfigIsInvalid('Default maxconn config is invalid')

    def set_retries(self, value):
        try:
            self.retries = int(value)

        except:
            raise ConfigIsInvalid('Default retries config is invalid')

    def set_connect_timeout(self, value):
        try:
            self.connect_timeout = int(value)

        except:
            raise ConfigIsInvalid('Default contimeout config is invalid')

    def set_client_timeout(self, value):
        try:
            self.client_timeout = int(value)

        except:
            raise ConfigIsInvalid('Default clitimeout config is invalid')

    def set_server_timeout(self, value):
        try:
            self.server_timeout = int(value)

        except:
            raise ConfigIsInvalid('Default srvtimeout config is invalid')

    def set_mode(self, value):
        self.mode = value

    def set_value(self, key, line):
        parts = line.split()

        if key == 'log':
            if len(parts) == 1:
                self.set_log(parts[0], parts[0])

            else:
                address = parts[0]
                facility = parts[1]
                try:
                    level = parts[2]
                except:
                    level = None

                try:
                    min_level = parts[3]
                except:
                    min_level = None

                self.set_log(address, facility, level, min_level)

        elif key == 'mode':
            self.set_mode(parts[0])

        elif key == 'maxconn':
            self.set_max_connections(parts[0])

        elif key == 'retries':
            self.set_retries(parts[0])

        elif key == 'option':
            self.set_option(parts[0], parts[1:])

        elif key == 'contimeout':
            self.set_connect_timeout(parts[0])

        elif key == 'clitimeout':
            self.set_client_timeout(parts[0])

        elif key == 'srvtimeout':
            self.set_server_timeout(parts[0])

    def from_string(self, lines):
        self._raw = lines
        for line in lines:
            line = line.partition('#')[0].strip()

            if line and not line.startswith('#'):
                parts = line.split()
                key = parts[0]

                self.set_value(key, ' '.join(parts[1:]))

    def to_string(self):
        lines = []
        for address in self.log:
            if address == 'global':
                lines.append('log global')

            else:
                for facility in self.log[address]:
                    line = 'log %s %s' % (address, facility)

                    if self.log[address][facility].get('level'):
                        line += ' %s' % self.log[address][facility]['level']

                    if self.log[address][facility].get('min-level'):
                        line += ' %s' % self.log[address][facility]['min-level']

                    lines.append(line)

        if self.mode:
            lines.append('mode %s' % self.mode)

        if self.connect_timeout:
            lines.append('timeout connect %s' % self.connect_timeout)

        if self.client_timeout:
            lines.append('timeout client %s' % self.client_timeout)

        if self.server_timeout:
            lines.append('timeout server %s' % self.server_timeout)

        for key in self.option:
            if self.option[key]:
                lines.append('option %s %s' % (key, self.option[key]))

            else:
                lines.append('option %s' % key)

        if self.retries:
            lines.append('retries %s' % self.retries)

        if self.max_connections:
            lines.append('maxconn %s' % self.max_connections)

        return '\n'.join(lines)


class ServerConfig(object):
    def __init__(self):
        self.name = None
        self.ip = None
        self.port = 80
        self.weight = 1
        self.cookie = None
        self.check_inter = 2000
        self.check_fall = 3
        self.max_connections = None
        self.min_connections = None
        self.backup = False
        self.keywords = ['cookie', 'check', 'maxconn', 'minconn', 'backup']
        self._raw = None
        super(ServerConfig, self).__init__()

    def __dict__(self):
        return {
            'name': self.name,
            'ip': self.ip,
            'port': self.port,
            'weight': self.weight,
            'cookie': self.cookie,
            'check_inter': self.check_inter,
            'check_fall': self.check_fall,
            'max_connections': self.max_connections,
            'min_connections': self.min_connections,
            'backup': self.backup,
        }

    def set_cookie(self, value):
        self.cookie = value

    def set_min_connections(self, value):
        try:
            self.min_connections = int(value)

        except:
            raise ConfigIsInvalid('Server minconn config is invalid')

    def set_max_connections(self, value):
        try:
            self.max_connections = int(value)

        except:
            raise ConfigIsInvalid('Server maxconn config is invalid')

    def set_check_inter(self, inter=None):
        try:
            self.check_inter = int(inter)

        except:
            raise ConfigIsInvalid('Server check inter config is invalid')

    def set_check_fall(self, fall=None):
        try:
            self.check_fall = int(fall)

        except:
            raise ConfigIsInvalid('Server check fall config is invalid')

    def set_backup(self, backup=True):
        self.backup = backup

    def set_value(self, key, parts):
        if key == 'cookie':
            if parts and parts[0] not in self.keywords:
                self.set_cookie(parts[0])
                parts = parts[1:]

        elif key == 'backup':
            self.set_backup(True)

        elif key == 'minconn':
            self.set_min_connections(parts[0])
            parts = parts[1:]

        elif key == 'maxconn':
            self.set_max_connections(parts[0])
            parts = parts[1:]

        elif key == 'check':
            while parts:
                if parts[0] == 'inter':
                    self.set_check_inter(parts[1])
                    parts = parts[2:]

                elif parts[0] == 'fall':
                    self.set_check_fall(parts[1])
                    parts = parts[2:]

                else:
                    break

    def from_string(self, value):
        self._raw = value
        _config = value.split()

        self.name = _config[0]
        ip_and_port = _config[1]
        if ':' not in ip_and_port:
            ip_and_port = '%s:80' % ip_and_port

        self.ip, _t, self.port = ip_and_port.partition(':')
        self.port = int(self.port)

        _config = _config[2:]

        while _config:
            key = _config[0]
            _config = _config[1:]
            self.set_value(key, _config)

    def to_string(self):
        output = 'server %s %s:%s weight %s' % (self.name, self.ip, self.port, self.weight)

        if self.cookie:
            output += ' cookie %s' % self.cookie

        if self.check_inter or self.check_fall:
            output += ' check'

            if self.check_inter:
                output += ' inter %s' % self.check_inter

            if self.check_fall:
                output += ' fall %s' % self.check_fall

        if self.max_connections:
            output += ' maxconn %s' % self.max_connections

        if self.min_connections:
            output += ' minconn %s' % self.min_connections

        if self.backup:
            output += ' backup'

        return output


class ListenConfig(object):
    def __init__(self):
        self.name = None
        self.ip = '*'
        self.port = None
        self.balance = 'roundrobin'
        self.mode = 'http'
        self.option = {
            'httpchk': '/ GET HTTP/1.0'
        }
        self.max_connections = None
        self.retries = None
        self.server = {}
        self.cookie_name = None
        self.cookie_insert = False
        self.cookie_rewrite = False
        self.cookie_nocache = False
        self.cookie_indirect = False
        self.cookie_maxidle = None
        self.cookie_maxlife = None
        self.client_timeout = None
        self.server_timeout = None
        self.connect_timeout = None
        self._raw = None
        super(ListenConfig, self).__init__()

    def __dict__(self):
        out = {
            'name': self.name,
            'ip': self.ip,
            'port': self.port,
            'balance': self.balance,
            'mode': self.mode,
            'option': self.option,
            'max_connections': self.max_connections,
            'retries': self.retries,
            'server': {},
            'cookie_name': self.cookie_name,
            'cookie_insert': self.cookie_insert,
            'cookie_rewrite': self.cookie_rewrite,
            'cookie_nocache': self.cookie_nocache,
            'cookie_indirect': self.cookie_indirect,
            'cookie_maxidle': self.cookie_maxidle,
            'cookie_maxlife': self.cookie_maxlife,
            'client_timeout': self.client_timeout,
            'server_timeout': self.server_timeout,
            'connect_timeout': self.connect_timeout
        }
        for key in self.server:
            out['server'][key] = dict(self.server[key])

        return out

    def set_cookie(self, parts):
        self.cookie_name = parts[0]
        if 'insert' in parts:
            self.cookie_insert = True

        if 'rewrite' in parts:
            self.cookie_rewrite = True

        if 'nocache' in parts:
            self.cookie_nocache = True

        if 'indirect' in parts:
            self.cookie_indirect = True

        if 'maxidle' in parts:
            index = parts.index('maxidle')
            self.cookie_maxidle = parts[index+1]

        if 'maxlife' in parts:
            index = parts.index('maxlife')
            self.cookie_maxlife = parts[index+1]

    def set_balance(self, value):
        self.balance = value

    def set_bind(self, value):
        if ':' not in value:
            self.ip = value
            self.port = 80

        else:
            self.ip, _t, self.port = value.partition(':')

    def set_option(self, key, parts):
        if isinstance(parts, list):
            value = ' '.join(parts)
        else:
            value = parts

        self.option[key] = value

    def set_max_connections(self, value):
        try:
            self.max_connections = int(value)

        except:
            raise ConfigIsInvalid('Default maxconn config is invalid')

    def set_retries(self, value):
        try:
            self.retries = int(value)

        except:
            raise ConfigIsInvalid('Default retries config is invalid')

    def set_connect_timeout(self, value):
        try:
            self.connect_timeout = int(value)

        except:
            raise ConfigIsInvalid('Default contimeout config is invalid')

    def set_client_timeout(self, value):
        try:
            self.client_timeout = int(value)

        except:
            raise ConfigIsInvalid('Default clitimeout config is invalid')

    def set_server_timeout(self, value):
        try:
            self.server_timeout = int(value)

        except:
            raise ConfigIsInvalid('Default srvtimeout config is invalid')

    def set_server(self, value):
        server = ServerConfig()
        server.from_string(value)

        if server.name:
            self.server[server.name] = server

    def set_value(self, key, line):
        parts = line.split()

        if key == 'bind':
            self.set_bind(parts[0])

        elif key == 'cookie':
            self.set_cookie(parts)

        elif key == 'balance':
            self.set_balance(parts[0])

        elif key == 'maxconn':
            self.set_max_connections(parts[0])

        elif key == 'retries':
            self.set_retries(parts[0])

        elif key == 'option':
            self.set_option(parts[0], parts[1:])

        elif key == 'retries':
            self.set_retries(parts[0])

        elif key == 'contimeout':
            self.set_connect_timeout(parts[0])

        elif key == 'clitimeout':
            self.set_client_timeout(parts[0])

        elif key == 'srvtimeout':
            self.set_server_timeout(parts[0])

        elif key == 'server':
            self.set_server(line)

    def from_string(self, lines):
        self._raw = lines
        for line in lines:
            line = line.partition('#')[0].strip()

            if line and not line.startswith('#'):
                parts = line.split()
                key = parts[0]

                self.set_value(key, ' '.join(parts[1:]))

    def to_string(self):
        lines = []
        lines.append('bind %s:%s' % (self.ip, self.port))
        lines.append('balance %s' % self.balance)
        lines.append('mode %s' % self.mode)

        if self.connect_timeout:
            lines.append('timeout connect %s' % self.connect_timeout)

        if self.client_timeout:
            lines.append('timeout client %s' % self.client_timeout)

        if self.server_timeout:
            lines.append('timeout server %s' % self.server_timeout)

        if self.cookie_name:
            cookie_define = 'cookie %s' % self.cookie_name

            if self.cookie_insert:
                cookie_define += ' insert'

            if self.cookie_rewrite:
                cookie_define += ' rewrite'

            if self.cookie_nocache:
                cookie_define += ' nocache'

            if self.cookie_indirect:
                cookie_define += ' indirect'

            if self.cookie_maxidle:
                cookie_define += ' maxidle %s' % self.cookie_maxidle

            if self.cookie_maxlife:
                cookie_define += ' maxlife %s' % self.cookie_maxlife

            lines.append(cookie_define)

        if self.max_connections:
            lines.append('maxconn %s' % self.max_connections)

        for key in self.option:
            line = 'option %s' % key
            if self.option[key]:
                line += ' %s' % self.option[key]
            lines.append(line)

        for server_name in self.server:
            lines.append(self.server[server_name].to_string())

        return '\n'.join(lines)


class FrontendConfig(object):
    def __init__(self):
        self.name = None
        self.ip = '*'
        self.port = None
        self.acl = {}
        self.option = {}
        self.use_backend = {}
        self.default_backend = None
        self._raw = None
        self.client_timeout = 60000
        self.max_connections = None
        super(FrontendConfig, self).__init__()

    def __dict__(self):
        return {
            'name': self.name,
            'ip': self.ip,
            'port': self.port,
            'acl': self.acl,
            'option': self.option,
            'use_backend': self.use_backend,
            'default_backend': self.default_backend,
            'client_timeout': self.client_timeout,
            'max_connections': self.max_connections
        }

    def to_string(self):
        lines = []

        lines.append('bind %s:%s' % (self.ip, self.port))
        if self.client_timeout:
            lines.append('timeout client %s' % self.client_timeout)

        if self.max_connections:
            lines.append('maxconn %s' % self.max_connections)

        for acl_name in self.acl:
            lines.append('acl %s %s %s' % (acl_name, self.acl[acl_name]['method'], self.acl[acl_name]['value']))

        for key in self.option:
            line = 'option %s' % key
            if self.option[key]:
                line += ' %s' % self.option[key]
            lines.append(line)

        for backend_name in self.use_backend:
            for conditions in self.use_backend[backend_name]:
                lines.append('use_backend %s if %s' % (backend_name, ' '.join(conditions)))

        lines.append('default_backend %s' % self.default_backend)

        return '\n'.join(lines)

    def from_string(self, lines):
        self._raw = lines
        for line in lines:
            line = line.partition('#')[0].strip()

            if line and not line.startswith('#'):
                parts = line.split()
                key = parts[0]

                self.set_value(key, ' '.join(parts[1:]))

    def set_value(self, key, line):
        parts = line.split()

        if key == 'bind':
            self.set_bind(parts[0])

        elif key == 'option':
            self.set_option(parts[0], parts[1:])

        elif key == 'clitimeout':
            self.set_client_timeout(parts[0])

        elif key == 'use_backend':
            self.set_use_backend(parts)

        elif key == 'acl':
            self.set_acl(parts)

        elif key == 'default_backend':
            self.set_default_backend(parts[0])

    def set_default_backend(self, name):
        self.default_backend = name

    def set_use_backend(self, parts):
        backend_name = parts[0]
        if backend_name not in self.use_backend:
            self.use_backend[backend_name] = []

        self.use_backend[backend_name].append(parts[2:])

    def set_acl(self, parts):
        acl_name = parts[0]
        acl_method = parts[1]
        acl_value = ' '.join(parts[2:])

        if acl_name not in self.acl:
            self.acl[acl_name] = {}

        self.acl[acl_name]['method'] = acl_method
        self.acl[acl_name]['value'] = acl_value

    def set_client_timeout(self, value):
        try:
            self.client_timeout = int(value)

        except:
            raise ConfigIsInvalid('Default clitimeout config is invalid')

    def set_bind(self, value):
        if ':' not in value:
            self.ip = value
            self.port = 80

        else:
            self.ip, _t, self.port = value.partition(':')

    def set_option(self, key, parts):
        if isinstance(parts, list):
            value = ' '.join(parts)
        else:
            value = parts

        self.option[key] = value


class BackendConfig(object):
    def __init__(self):
        self.name = None
        self.mode = 'http'
        self.balance = 'roundrobin'
        self.option = {
            'httpchk': '/ GET HTTP/1.0'
        }
        self.max_connections = None
        self.retries = None
        self.cookie_name = None
        self.cookie_insert = False
        self.cookie_nocache = False
        self.cookie_indirect = False
        self.cookie_rewrite = False
        self.cookie_maxidle = None
        self.cookie_maxlife = None
        self.server = {}
        self.server_timeout = 3000
        self.connect_timeout = 3000
        self._raw = None
        super(BackendConfig, self).__init__()

    def __dict__(self):
        out = {
            'name': self.name,
            'mode': self.mode,
            'balance': self.balance,
            'option': self.option,
            'max_connections': self.max_connections,
            'retries': self.retries,
            'cookie_name': self.cookie_name,
            'cookie_insert': self.cookie_insert,
            'cookie_nocache': self.cookie_nocache,
            'cookie_indirect': self.cookie_indirect,
            'cookie_rewrite': self.cookie_rewrite,
            'cookie_maxidle': self.cookie_maxidle,
            'cookie_maxlife': self.cookie_maxlife,
            'server_timeout': self.server_timeout,
            'connect_timeout': self.connect_timeout,
            'server': {}
        }
        for key in self.server:
            out['server'][key] = dict(self.server[key])

        return out

    def set_cookie(self, parts):
        self.cookie_name = parts[0]
        if 'insert' in parts:
            self.cookie_insert = True

        if 'nocache' in parts:
            self.cookie_nocache = True

        if 'indirect' in parts:
            self.cookie_indirect = True

        if 'rewrite' in parts:
            self.cookie_rewrite = True

        if 'maxidle' in parts:
            index = parts.index('maxidle')
            self.cookie_maxidle = parts[index+1]

        if 'maxlife' in parts:
            index = parts.index('maxlife')
            self.cookie_maxlife = parts[index+1]

    def set_balance(self, value):
        self.balance = value

    def set_option(self, key, parts):
        if isinstance(parts, list):
            value = ' '.join(parts)
        else:
            value = parts

        self.option[key] = value

    def set_max_connections(self, value):
        try:
            self.max_connections = int(value)

        except:
            raise ConfigIsInvalid('Default maxconn config is invalid')

    def set_retries(self, value):
        try:
            self.retries = int(value)

        except:
            raise ConfigIsInvalid('Default retries config is invalid')

    def set_connect_timeout(self, value):
        try:
            self.connect_timeout = int(value)

        except:
            raise ConfigIsInvalid('Default contimeout config is invalid')

    def set_server_timeout(self, value):
        try:
            self.server_timeout = int(value)

        except:
            raise ConfigIsInvalid('Default srvtimeout config is invalid')

    def set_server(self, value):
        server = ServerConfig()
        server.from_string(value)

        if server.name:
            self.server[server.name] = server

    def set_value(self, key, line):
        parts = line.split()

        if key == 'balance':
            self.set_balance(parts[0])

        elif key == 'maxconn':
            self.set_max_connections(parts[0])

        elif key == 'retries':
            self.set_retries(parts[0])

        elif key == 'option':
            self.set_option(parts[0], parts[1:])

        elif key == 'retries':
            self.set_retries(parts[0])

        elif key == 'contimeout':
            self.set_connect_timeout(parts[0])

        elif key == 'srvtimeout':
            self.set_server_timeout(parts[0])

        elif key == 'server':
            self.set_server(line)

        elif key == 'cookie':
            self.set_cookie(parts)

    def from_string(self, lines):
        self._raw = lines

        for line in lines:
            line = line.partition('#')[0].strip()

            if line and not line.startswith('#'):
                parts = line.split()
                key = parts[0]

                self.set_value(key, ' '.join(parts[1:]))

    def to_string(self):
        lines = []
        lines.append('balance %s' % self.balance)
        lines.append('mode %s' % self.mode)
        if self.connect_timeout:
            lines.append('timeout connect %s' % self.connect_timeout)

        if self.server_timeout:
            lines.append('timeout server %s' % self.server_timeout)

        for key in self.option:
            line = 'option %s' % key
            if self.option[key]:
                line += ' %s' % self.option[key]
            lines.append(line)

        if self.max_connections:
            lines.append('maxconn %s' % self.max_connections)

        if self.retries:
            lines.append('retries %s' % self.retries)

        if self.cookie_name:
            cookie_define = 'cookie %s' % self.cookie_name

            if self.cookie_insert:
                cookie_define += ' insert'

            if self.cookie_rewrite:
                cookie_define += ' rewrite'

            if self.cookie_nocache:
                cookie_define += ' nocache'

            if self.cookie_indirect:
                cookie_define += ' indirect'

            if self.cookie_maxidle:
                cookie_define += ' maxidle %s' % self.cookie_maxidle

            if self.cookie_maxlife:
                cookie_define += ' maxlife %s' % self.cookie_maxlife

            lines.append(cookie_define)

        for server_name in self.server:
            lines.append(self.server[server_name].to_string())

        return '\n'.join(lines)

