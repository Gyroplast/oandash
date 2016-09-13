#!/usr/bin/env python
# -*- coding: utf-8 -*-

# LICENSING INFORMATION
#
#    This file is part of oandash.
#
#    oandash is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    oandash is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with oandash.  If not, see <http://www.gnu.org/licenses/>.

import cmd
import getpass
import io
import json
import os
import sys
from base64 import b64encode as serialize, b64decode as deserialize

try:
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.Cipher import AES
    from Crypto import Random
except ImportError:
    print("Could not import required package: pycrypto", file=sys.stderr)
    sys.exit(2)

try:
    import pyreadline as readline
except ImportError:
    try:
        import readline
    except ImportError:
        pass
try:    
    import requests
except ImportError:
    print("Could not import required package: requests", file=sys.stderr)
    sys.exit(2)

try:
    import appdirs
except ImportError:
    print("Could not import required package: appdirs", file=sys.stderr)
    sys.exit(2)

try:
    from colorama import init as colorama_init, deinit as colorama_deinit
    from colorama import Fore, Back, Style
except ImportError:
    print("Could not import required package: colorama", file=sys.stderr)
    sys.exit(2)

import oandash.fmt as fmt

with io.open("meta.json", "r", encoding='utf-8') as fp:
        meta = json.load(fp)

dirs = appdirs.AppDirs(meta['name'], "Veloxis")

fxtrade_base_uri = 'https://api-fxtrade.oanda.com'
base_uri = fxtrade_base_uri

class Cipher(object):
    def __init__(self, cipher=AES):
        self.cipher = cipher
        self._salt_len = 32
        self._key_len = 32
        self._pbkdf2_rounds = 8000

    def _pad(self, s):
        BS = self.cipher.block_size
        return s + (BS - len(s) % BS) * chr(BS - len(s) % BS)

    def _unpad(self, s):
        return s[:-ord(s[len(s)-1:])]

    def encrypt(self, plaintext, key):
        iv = Random.new().read(self.cipher.block_size)
        salt = Random.new().read(self._salt_len)
        key = PBKDF2(key, salt, dkLen=self._key_len, count=self._pbkdf2_rounds)

        encrypter = self.cipher.new(key, self.cipher.MODE_CFB, iv)
        ciphertext = encrypter.encrypt(self._pad(plaintext))

        return (b'$'.join(map(serialize, (salt, iv, ciphertext)))).decode('ascii')


    def decrypt(self, ciphertext, key):
        salt, iv, msg = map(deserialize, ciphertext.split('$'))
        key = PBKDF2(key, salt, dkLen=self._key_len, count=self._pbkdf2_rounds)

        decrypter = self.cipher.new(key, self.cipher.MODE_CFB, iv)
        return self._unpad(decrypter.decrypt(msg))

def login(username=None):
    if username:
        suggested_user = username
    else:
        suggested_user = getpass.getuser()

    user = input("Username [%s]: " % suggested_user)
    if not user:
        user = suggested_user

    password = getpass.getpass("Password: ")
    return user, password

def get_encrypted_apikey(user, conf):
    try:
        with io.open(conf, "r", encoding='utf-8') as fp:
                users = json.load(fp)
        apikey = users[user]['apikey']
    except:
        apikey = ""

    return apikey

def fmt_account_short(account):
    s  = "%(accountName)s (#%(accountId)s): %(accountCurrency)s %(balance).2f" % account
    s += " (%s)" % fmt.balance(account['unrealizedPl'])
    return s

def fmt_account_long(account):
    if account['openOrders'] == 0:
        orders = "no open orders"
    elif account['openOrders'] == 1:
        orders = "%s1%s open order" % (Fore.GREEN, Fore.RESET)
    else:
        orders = "%s%d%s open orders" % (Fore.GREEN, account['openOrders'], Fore.RESET)

    if account['openTrades'] == 0:
        trades = "no open trades"
    elif account['openTrades'] == 1:
        trades = "%s1%s open trade" % (Fore.GREEN, Fore.RESET)
    else:
        trades = "%s%d%s open trades" % (Fore.GREEN, account['openTrades'], Fore.RESET)

    leverage = 1 / account['marginRate']

    s  = fmt_account_short(account) + "\n"
    s += "\tBalance             "  + fmt.balance(account['balance']).rjust(25, '.') + "\n"
    s += "\tUnrealized P&L      "  + fmt.balance(account['unrealizedPl']).rjust(25, '.') + "\n"
    s += "\tUnrealized P&L [%]  "  + fmt.balance(account['unrealizedPl'] * 100 / account['balance']).rjust(25, '.') + "\n"
    s += "\tNet Asset Value     "  + fmt.balance(account['unrealizedPl'] + account['balance']).rjust(25, '.') + "\n"
    s += "\tRealized P&L        "  + fmt.balance(account['realizedPl']).rjust(25, '.') + "\n"
    s += "\tMargin Used         "  + fmt.balance(account['marginUsed']).rjust(25, '.') + "\n"
    s += "\tMargin Available    "  + fmt.balance(account['marginAvail']).rjust(25, '.') + "\n"
    s += "\t------\n"
    s += "\tLeverage is %d:1. %s, and %s.\n" % (leverage, orders.capitalize(), trades)
    return s

class OandaShell(cmd.Cmd):
    _headers = {}
    intro = fmt.reindent(
                """{name} {version} Copyright (C) 2016 Dennis Herbrich

                This program comes with ABSOLUTELY NO WARRANTY, to the extent
                permitted by law. This is free software, and you are welcome
                to change and redistribute it under certain conditions.

                {_G}Welcome to the OandA Shell.    Type help or ? to list commands.{_RST}""".format(_G=Fore.GREEN, _RST=Style.RESET_ALL, **meta)
                )

    prompt = Style.BRIGHT + 'oandash> ' + Style.RESET_ALL

    def help_quit(self):
        help_data = {
            "cmd": "quit",
            "args": "",
            "desc": """Exits the shell immediately without asking for confirmation."""
        }
        print(fmt.help(help_data))

    def do_quit(self, arg):
        return True

    def do_version(self, arg):
        print(fmt.reindent(
                """{name} {version} Copyright (C) 2016 Dennis Herbrich
                {desc}

                License {license}

                This program comes with ABSOLUTELY NO WARRANTY, to the extent
                permitted by law. This is free software, and you are welcome
                to change and redistribute it under certain conditions.

                Homepage: {homepage}
                Maintainer: {maintainer} <{email}>
                """.format(**meta)
                ))

    def do_accounts(self, arg):
        if not "Authorization" in self._headers:
            print("Please 'login' first.")
            return False

        r = requests.get(base_uri + '/v1/accounts', headers=self._headers)
        try:
            accountIds = [account['accountId'] for account in r.json()['accounts']]
        except KeyError:
            print("Could not understand OandA response:", file=sys.stderr)
            print(json.dumps(r.json(), sort_keys=True,
                  indent=4, separators=(',', ': ')), file=sys.stderr)
            return False

        for accountId in accountIds:
            r = requests.get(base_uri + '/v1/accounts/%d' % (accountId), headers=self._headers)
            try:
                print(fmt_account_long(r.json()))
            except KeyError:
                print("Could not understand OandA response:", file=sys.stderr)
                print(json.dumps(r.json(), sort_keys=True,
                      indent=4, separators=(',', ': ')), file=sys.stderr)
                return False

    def do_login(self, arg):
        try:
            user, password = login()
        except:
            print("Login failed.")
            return False

        encrypted_apikey = get_encrypted_apikey(user, os.path.join(dirs.user_config_dir, "users.json"))
        if not encrypted_apikey:
            print("Login failed: invalid username or password.", file=sys.stderr)
            return False

        cipher = Cipher(cipher=AES)
        apikey = cipher.decrypt(encrypted_apikey, password).decode('ascii')
        if not apikey:
            print("Login failed: invalid username or password.", file=sys.stderr)
            return False

        self._headers["Authorization"] = "Bearer %s" % apikey

if __name__ == "__main__":
    colorama_init(autoreset=True)
    print(Style.RESET_ALL)

    try:
        OandaShell().cmdloop()
    finally:
        colorama_deinit()
