import dbhandler

class User():
    def __init__(self, email="", name=""):
        self.email = email
        self.name = name
        self.nickname = self.name
        self.fetch_db()

    def fetch_db(self):
        UserDB = dbhandler.UserDB()
        if self.email and self.name:
            return True
        elif not len(self.name) > 0:
            self.name, self.nickname = UserDB.get_name_nickname_by_email(self.email)
        elif not len(self.email) > 0:
            self.email = UserDB.get_email_by_nickname(self.nickname)
        else:
            pass