import pyrebase
from .tools import *

config = {
	'apiKey': "AIzaSyAqSxNtT_bZHO6aS0OmJOgthjFt4Xz_BxU",
	'authDomain': "testing-879cd.firebaseapp.com",
	'databaseURL': "https://testing-879cd-default-rtdb.firebaseio.com",
	'projectId': "testing-879cd",
	'storageBucket': "testing-879cd.appspot.com",
	'messagingSenderId': "187285994568",
	'appId': "1:187285994568:web:5125a87d7796c921b26c7d"
}

database = pyrebase.initialize_app(config).database()


class Database:
	def __init__(self):
		self.base = database
		self.data = self.base.get().val()
		
	def create(self, data):
		[self.base.update({key: value}) for key, value in data.items()]
		return self.data


class Default:
	def __init__(self, id):
		self.user = {f"users/{id}": {"invites": 0}}
		self.guild = {f"guilds/{id}": {"prefix": "."}}


class User:
	def __init__(self, user):
		self.discord = user
		self.create_if_doesnt_exist()
		self.data = Database().data['users'][str(self.discord.id)]

	def create_if_doesnt_exist(self):
		if "users" in list(dict(Database().data).keys()):
			if str(self.discord.id) in list(dict(Database().data['users']).keys()): return
			else: pass
		else: pass
		Database().create(Default(self.discord.id).user)

	def get(self, key : str):
		if '/' in key:
			key = key.split('/')
			return self.data[key[0]][key[1]]
		
		try: return self.data[key]
		except: return None

	def delete(self):
		self.data.remove()

	def add(self, key : str, value : int):
		Database().base.update({f"users/{self.discord.id}/{key}": self.get(key) + value})
		return self.data

	def update(self, key : str, value):
		Database().base.update({f"users/{self.discord.id}/{key}": value})
		return self.data

	def remove(self, key : str, value : int):
		if self.get(key) - value <= 0:
			Database().base.child(f"users/{self.discord.id}/{key}").remove()
			return self.data

		Database().base.update({f"users/{self.discord.id}/{key}": self.get(key) - value})
		return self.data


class Guild:
	def __init__(self, guild):
		self.discord = guild
		self.create_if_doesnt_exist()
		self.data = Database().data['guilds'][str(self.discord.id)]

	def create_if_doesnt_exist(self):
		if "guilds" in list(dict(Database().data).keys()):
			if str(self.discord.id) in list(dict(Database().data['guilds']).keys()): return
			else: pass
		else: pass
		Database().create(Default(self.discord.id).guild)

	def get(self, key : str):
		try: return self.data[key]
		except KeyError: return None

	def delete(self):
		self.data.remove()

	def add(self, key : str, value : int):
		Database().base.update({f"guilds/{self.discord.id}/{key}": self.get(key) + value})
		return self.data

	def update(self, key : str, value):
		Database().base.update({f"guilds/{self.discord.id}/{key}": value})
		return self.data

	def remove(self, key : str, value : int):
		if self.get(key) - value <= 0:
			Database().base.child(f"guilds/{self.discord.id}/{key}").remove()
			return self.data

		Database().base.update({f"guilds/{self.discord.id}/{key}": self.get(key) - value})
		return self.data