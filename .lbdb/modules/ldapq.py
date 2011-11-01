#!/usr/bin/env python

import ldap
import argparse
import logging
from logging.handlers import RotatingFileHandler
from os import path
import gnomekeyring as gkey


class Keyring(object):
    def __init__(self, name, server, protocol):
        self._name = name
        self._server = server
        self._protocol = protocol
        self._keyring = gkey.get_default_keyring_sync()

    def has_credentials(self):
        try:
            attrs = {"server": self._server, "protocol": self._protocol}
            items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
            return len(items) > 0
        except gkey.DeniedError:
            return False

    def get_credentials(self):
        attrs = {"server": self._server, "protocol": self._protocol}
        items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
        return (items[0].attributes["user"], items[0].secret)

    def set_credentials(self, (user, pw)):
        attrs = {
                "user": user,
                "server": self._server,
                "protocol": self._protocol,
            }
        gkey.item_create_sync(gkey.get_default_keyring_sync(),
                gkey.ITEM_NETWORK_PASSWORD, self._name, attrs, pw, True)


class Main(object):
    """Boilerplate.
    """

    def __init__(self, *args, **kwargs):
        self.logdir = kwargs['logdir'] if 'logdir' in kwargs else '.'
        self.logbackups = 1
        self.get_args()
        self.log = self.get_logger()
        self.log.debug("initialized")

    def __repr__(self):
        return "<Main object>"

    def get_args(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-n', '--dry-run', action='store_true')
        self.parser.add_argument('-d', '--debug', action='store_true')
        self.parser.add_argument('-s', '--server', required=True)
        self.parser.add_argument('-q', '--query', required=True)
        self.args = self.parser.parse_args()

    def get_logger(self):
        _log = logging.getLogger('%r' % self)
        handler = RotatingFileHandler(path.join(self.logdir,
                                                "info.log"),
                                        backupCount=self.logbackups)
        handler.doRollover()
        fmt = "%(name)s %(asctime)s %(levelname)-6s %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        _log.addHandler(handler)
        if self.args.debug:
            _log.level = logging.DEBUG
        return _log

    def main(self):
        try:
            self.connect()
            self.query()
        except:
            pass
        self.finalize()

    def connect(self):
        self.ldo = ldap.initialize('ldap://localhost:6138/')
        keyring = Keyring("offlineimap", self.args.server, "imap")
        (username, password) = keyring.get_credentials()
        self.ldo.bind(username, password)

    def query(self):
        base_dn = "ou=people"
        scope = ldap.SCOPE_SUBTREE
        search_f = '(cn=*%s*)' % self.args.query
        attr_l = ['cn', 'mail', 'sn', 'givenname', 'telephoneNumber', 'title' ]
        self.result = self.ldo.search_st(base_dn, scope, filterstr=search_f, attrlist=attr_l, timeout=10)

    def finalize(self):
        """name.surname@company.com  Name Surname
        """
        self.ldo.unbind()
        try:
            res = '%s\t%s %s' % (self.result[0][1]['mail'][0],
                                    self.result[0][1]['givenname'][0],
                                    self.result[0][1]['sn'][0])
            print res

        except (IndexError, AttributeError):
            return ''

if __name__ == '__main__':
    m = Main()
    m.main()
