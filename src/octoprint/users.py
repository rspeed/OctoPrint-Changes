# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask.ext.login import UserMixin
from flask.ext.principal import Identity
from werkzeug.local import LocalProxy
import hashlib
import os
import yaml
import uuid

import logging

from octoprint.settings import settings

class UserManager(object):
	valid_roles = ["user", "admin"]

	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._session_users_by_session = dict()
		self._session_users_by_username = dict()

	def login_user(self, user):
		self._cleanup_sessions()

		if user is None \
		        or (isinstance(user, LocalProxy) and not isinstance(user._get_current_object(), User)) \
		        or (not isinstance(user, LocalProxy) and not isinstance(user, User)):
			return None

		if not isinstance(user, SessionUser):
			user = SessionUser(user)
		self._session_users_by_session[user.get_session()] = user

		if not user.get_name() in self._session_users_by_username:
			self._session_users_by_username[user.get_name()] = []
		self._session_users_by_username[user.get_name()].append(user)

		self._logger.debug("Logged in user: %r" % user)

		return user

	def logout_user(self, user):
		if user is None:
			return

		if not isinstance(user, SessionUser):
			return

		if user.get_name() in self._session_users_by_username:
			users_by_username = self._session_users_by_username[user.get_name()]
			for u in users_by_username:
				if u.get_session() == user.get_session():
					users_by_username.remove(u)
					break

		if user.get_session() in self._session_users_by_session:
			del self._session_users_by_session[user.get_session()]

		self._logger.debug("Logged out user: %r" % user)

	def _cleanup_sessions(self):
		import time
		for session, user in self._session_users_by_session.items():
			if not isinstance(user, SessionUser):
				continue
			if user._created + (24 * 60 * 60) < time.time():
				self.logout_user(user)

	@staticmethod
	def createPasswordHash(password, salt=None):
		if not salt:
			salt = settings().get(["accessControl", "salt"])
			if salt is None:
				import string
				from random import choice
				chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
				salt = "".join(choice(chars) for _ in xrange(32))
				settings().set(["accessControl", "salt"], salt)
				settings().save()

		return hashlib.sha512(password + salt).hexdigest()

	def checkPassword(self, username, password):
		user = self.findUser(username)
		if not user:
			return False

		hash = UserManager.createPasswordHash(password)
		if user.check_password(hash):
			# new hash matches, correct password
			return True
		else:
			# new hash doesn't match, but maybe the old one does, so check that!
			oldHash = UserManager.createPasswordHash(password, salt="mvBUTvwzBzD3yPwvnJ4E4tXNf3CGJvvW")
			if user.check_password(oldHash):
				# old hash matches, we migrate the stored password hash to the new one and return True since it's the correct password
				self.changeUserPassword(username, password)
				return True
			else:
				# old hash doesn't match either, wrong password
				return False

	def addUser(self, username, password, active, roles):
		pass

	def changeUserActivation(self, username, active):
		pass

	def changeUserRoles(self, username, roles):
		pass

	def addRolesToUser(self, username, roles):
		pass

	def removeRolesFromUser(self, username, roles):
		pass

	def changeUserPassword(self, username, password):
		pass

	def removeUser(self, username):
		if username in self._session_users_by_username:
			users = self._session_users_by_username[username]
			sessions = [user.get_session() for user in users if isinstance(user, SessionUser)]
			for session in sessions:
				if session in self._session_users_by_session:
					del self._session_users_by_session[session]
			del self._session_users_by_username[username]

	def findUser(self, username=None, session=None):
		if session is not None:
			for session in self._session_users_by_session:
				user = self._session_users_by_session[session]
				if username is None or username == user.get_name():
					return user
				break

		return None

	def getAllUsers(self):
		return []

	def hasBeenCustomized(self):
		return False

##~~ FilebasedUserManager, takes available users from users.yaml file

class FilebasedUserManager(UserManager):
	def __init__(self):
		UserManager.__init__(self)

		userfile = settings().get(["accessControl", "userfile"])
		if userfile is None:
			userfile = os.path.join(settings().settings_dir, "users.yaml")
		self._userfile = userfile
		self._users = {}
		self._dirty = False

		self._customized = None
		self._load()

	def _load(self):
		if os.path.exists(self._userfile) and os.path.isfile(self._userfile):
			self._customized = True
			with open(self._userfile, "r") as f:
				data = yaml.safe_load(f)
				for name in data.keys():
					attributes = data[name]
					apikey = None
					if "apikey" in attributes:
						apikey = attributes["apikey"]
					self._users[name] = User(name, attributes["password"], attributes["active"], attributes["roles"], apikey)
		else:
			self._customized = False

	def _save(self, force=False):
		if not self._dirty and not force:
			return

		data = {}
		for name in self._users.keys():
			user = self._users[name]
			data[name] = {
				"password": user._passwordHash,
				"active": user._active,
				"roles": user._roles,
				"apikey": user._apikey
			}

		with open(self._userfile, "wb") as f:
			yaml.safe_dump(data, f, default_flow_style=False, indent="    ", allow_unicode=True)
			self._dirty = False
		self._load()

	def addUser(self, username, password, active=False, roles=None, apikey=None):
		if not roles:
			roles = ["user"]

		if username in self._users.keys():
			raise UserAlreadyExists(username)

		self._users[username] = User(username, UserManager.createPasswordHash(password), active, roles, apikey)
		self._dirty = True
		self._save()

	def changeUserActivation(self, username, active):
		if not username in self._users.keys():
			raise UnknownUser(username)

		if self._users[username]._active != active:
			self._users[username]._active = active
			self._dirty = True
			self._save()

	def changeUserRoles(self, username, roles):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]

		removedRoles = set(user._roles) - set(roles)
		self.removeRolesFromUser(username, removedRoles)

		addedRoles = set(roles) - set(user._roles)
		self.addRolesToUser(username, addedRoles)

	def addRolesToUser(self, username, roles):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		for role in roles:
			if not role in user._roles:
				user._roles.append(role)
				self._dirty = True
		self._save()

	def removeRolesFromUser(self, username, roles):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		for role in roles:
			if role in user._roles:
				user._roles.remove(role)
				self._dirty = True
		self._save()

	def changeUserPassword(self, username, password):
		if not username in self._users.keys():
			raise UnknownUser(username)

		passwordHash = UserManager.createPasswordHash(password)
		user = self._users[username]
		if user._passwordHash != passwordHash:
			user._passwordHash = passwordHash
			self._dirty = True
			self._save()

	def generateApiKey(self, username):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		user._apikey = ''.join('%02X' % ord(z) for z in uuid.uuid4().bytes)
		self._dirty = True
		self._save()
		return user._apikey

	def deleteApikey(self, username):
		if not username in self._users.keys():
			raise UnknownUser(username)

		user = self._users[username]
		user._apikey = None
		self._dirty = True
		self._save()

	def removeUser(self, username):
		UserManager.removeUser(self, username)

		if not username in self._users.keys():
			raise UnknownUser(username)

		del self._users[username]
		self._dirty = True
		self._save()

	def findUser(self, username=None, apikey=None, session=None):
		user = UserManager.findUser(self, username=username, session=session)

		if user is not None:
			return user

		if username is not None:
			if username not in self._users.keys():
				return None
			return self._users[username]

		elif apikey is not None:
			for user in self._users.values():
				if apikey == user._apikey:
					return user
			return None

		else:
			return None

	def getAllUsers(self):
		return map(lambda x: x.asDict(), self._users.values())

	def hasBeenCustomized(self):
		return self._customized

##~~ Exceptions

class UserAlreadyExists(Exception):
	def __init__(self, username):
		Exception.__init__(self, "User %s already exists" % username)

class UnknownUser(Exception):
	def __init__(self, username):
		Exception.__init__(self, "Unknown user: %s" % username)

class UnknownRole(Exception):
	def _init_(self, role):
		Exception.__init__(self, "Unknown role: %s" % role)

##~~ User object

class User(UserMixin):
	def __init__(self, username, passwordHash, active, roles, apikey=None):
		self._username = username
		self._passwordHash = passwordHash
		self._active = active
		self._roles = roles
		self._apikey = apikey

	def asDict(self):
		return {
			"name": self._username,
			"active": self.is_active(),
			"admin": self.is_admin(),
			"user": self.is_user(),
			"apikey": self._apikey
		}

	def check_password(self, passwordHash):
		return self._passwordHash == passwordHash

	def get_id(self):
		return self._username

	def get_name(self):
		return self._username

	def is_active(self):
		return self._active

	def is_user(self):
		return "user" in self._roles

	def is_admin(self):
		return "admin" in self._roles

	def __repr__(self):
		return "User(id=%s,name=%s,active=%r,user=%r,admin=%r)" % (self.get_id(), self.get_name(), self.is_active(), self.is_user(), self.is_admin())

class SessionUser(User):
	def __init__(self, user):
		User.__init__(self, user._username, user._passwordHash, user._active, user._roles, user._apikey)

		import string
		import random
		import time
		chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
		self._session = "".join(random.choice(chars) for _ in xrange(10))
		self._created = time.time()

	def get_session(self):
		return self._session

	def __repr__(self):
		return "SessionUser(id=%s,name=%s,active=%r,user=%r,admin=%r,session=%s,created=%s)" % (self.get_id(), self.get_name(), self.is_active(), self.is_user(), self.is_admin(), self._session, self._created)

##~~ DummyUser object to use when accessControl is disabled

class DummyUser(User):
	def __init__(self):
		User.__init__(self, "dummy", "", True, UserManager.valid_roles)

	def check_password(self, passwordHash):
		return True

class DummyIdentity(Identity):
	def __init__(self):
		Identity.__init__(self, "dummy")

def dummy_identity_loader():
	return DummyIdentity()


##~~ Apiuser object to use when global api key is used to access the API


class ApiUser(User):
	def __init__(self):
		User.__init__(self, "_api", "", True, UserManager.valid_roles)
