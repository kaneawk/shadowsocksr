﻿#!/usr/bin/python
# -*- coding: UTF-8 -*-

import traceback
from shadowsocks import common, shell
from configloader import load_config, get_config
import random
import getopt
import sys
import json

class MuJsonLoader(object):
	def __init__(self):
		self.json = None

	def load(self, path):
		with open(path, 'rb+') as f:
			self.json = json.loads(f.read().decode('utf8'))

	def save(self, path):
		if self.json:
			output = json.dumps(self.json, sort_keys=True, indent=4, separators=(',', ': '))
			with open(path, 'w') as f:
				f.write(output)

class MuMgr(object):
	def __init__(self):
		self.config_path = get_config().MUDB_FILE
		self.data = MuJsonLoader()

	def userinfo(self, user):
		ret = ""
		for key in user.keys():
			ret += '\n'
			if key in ['transfer_enable', 'u', 'd'] :
				val = user[key]
				if val / 1024 < 4:
					ret += "    %s : %s" % (key, val)
				elif val / 1024**2 < 4:
					val /= float(1024)
					ret += "    %s : %s  K bytes" % (key, val)
				elif val / 1024**3 < 4:
					val /= float(1024**2)
					ret += "    %s : %s  M bytes" % (key, val)
				else:
					val /= float(1024**3)
					ret += "    %s : %s  G bytes" % (key, val)
			else:
				ret += "    %s : %s" % (key, user[key])
		return ret

	def rand_pass(self):
		return b''.join([random.choice(b'''ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789~-_=+(){}[]^&%$@''') for i in range(8)])

	def add(self, user):
		up = {'enable': True, 'u': 0, 'd': 0, 'method': "aes-128-cfb",
		'protocol': "auth_sha1_v2_compatible",
		'obfs': "tls1.2_ticket_auth_compatible",
		'transfer_enable': 1125899906842624}
		up['passwd'] = self.rand_pass()
		up.update(user)

		self.data.load(self.config_path)
		for row in self.data.json:
			match = False
			if 'user' in user and row['user'] == user['user']:
				match = True
			if 'port' in user and row['port'] == user['port']:
				match = True
			if match:
				print("user [%s] port [%s] already exist" % (row['user'], row['port']))
				return
		self.data.json.append(up)
		print("### add user info %s" % self.userinfo(up))
		self.data.save(self.config_path)

	def edit(self, user):
		self.data.load(self.config_path)
		for row in self.data.json:
			match = True
			if 'user' in user and row['user'] != user['user']:
				match = False
			if 'port' in user and row['port'] != user['port']:
				match = False
			if match:
				print("edit user [%s]" % (row['user'],))
				row.update(user)
				print("### new user info %s" % self.userinfo(row))
				break
		self.data.save(self.config_path)

	def delete(self, user):
		self.data.load(self.config_path)
		index = 0
		for row in self.data.json:
			match = True
			if 'user' in user and row['user'] != user['user']:
				match = False
			if 'port' in user and row['port'] != user['port']:
				match = False
			if match:
				print("delete user [%s]" % row['user'])
				del self.data.json[index]
				break
			index += 1
		self.data.save(self.config_path)

	def clear_ud(self, user):
		up = {'u': 0, 'd': 0}
		self.data.load(self.config_path)
		for row in self.data.json:
			match = True
			if 'user' in user and row['user'] != user['user']:
				match = False
			if 'port' in user and row['port'] != user['port']:
				match = False
			if match:
				row.update(up)
				print("clear user [%s]" % row['user'])
		self.data.save(self.config_path)

	def list_user(self, user):
		self.data.load(self.config_path)
		if not user:
			for row in self.data.json:
				print("user [%s] port %s" % (row['user'], row['port']))
			return
		for row in self.data.json:
			match = True
			if 'user' in user and row['user'] != user['user']:
				match = False
			if 'port' in user and row['port'] != user['port']:
				match = False
			if match:
				print("### user [%s] info %s" % (row['user'], self.userinfo(row)))

def print_server_help():
    print('''usage: python mujson_manage.py -a|-d|-e|-c|-l [OPTION]...

Actions:
  -a ADD                 add/edit a user
  -d DELETE              delete a user
  -e EDIT                edit a user
  -c CLEAR               set u/d to zero
  -l LIST                display a user infomation or all users infomation

Options:
  -u USER                the user name
  -p PORT                server port
  -k PASSWORD            password
  -m METHOD              encryption method, default: aes-128-cfb
  -O PROTOCOL            protocol plugin, default: auth_sha1_v2_compatible
  -o OBFS                obfs plugin, default: tls1.2_ticket_auth_compatible
  -t TRANSFER            max transfer for G bytes, default: 1048576, can be float point number
  -f FORBID              set forbidden ports. Example (ban 1~79 and 81~100): -f "1-79,81-100"

General options:
  -h, --help             show this help message and exit
''')

def main():
	shortopts = 'adeclu:p:k:O:o:m:t:f:h'
	longopts = ['help']
	action = None
	user = {}
	try:
		optlist, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
		for key, value in optlist:
			if key == '-a':
				action = 1
			elif key == '-d':
				action = 2
			elif key == '-e':
				action = 3
			elif key == '-l':
				action = 4
			elif key == '-c':
				action = 0
			elif key == '-u':
				user['user'] = value
			elif key == '-p':
				user['port'] = int(value)
			elif key == '-k':
				user['passwd'] = value
			elif key == '-o':
				user['obfs'] = value
			elif key == '-O':
				user['protocol'] = value
			elif key == '-m':
				user['method'] = value
			elif key == '-f':
				user['forbidden_port'] = value
			elif key == '-t':
				val = float(value)
				try:
					val = int(value)
				except:
					pass
				user['transfer_enable'] = val * (1024 ** 3)
			elif key in ('-h', '--help'):
				print_server_help()
				sys.exit(0)
	except getopt.GetoptError as e:
		print(e)
		sys.exit(2)

	manage = MuMgr()
	if action == 0:
		manage.clear_ud(user)
	elif action == 1:
		if 'user' not in user and 'port' in user:
			user['user'] = str(user['port'])
		if 'user' in user and 'port' in user:
			manage.add(user)
		else:
			print("You have to set the port with -p")
	elif action == 2:
		if 'user' in user or 'port' in user:
			manage.delete(user)
		else:
			print("You have to set the user name or port with -u/-p")
	elif action == 3:
		if 'user' in user or 'port' in user:
			manage.edit(user)
		else:
			print("You have to set the user name or port with -u/-p")
	elif action == 4:
		manage.list_user(user)
	elif action is None:
		print_server_help()

if __name__ == '__main__':
	main()

