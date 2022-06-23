from pyclassic import *

class SimpleAuth:
    def __init__(self, username, mppass):
        self.session = mppass
        self.username = username

    def connect(self, **kargs):
        assert "ip" in kargs and "port" in kargs
        ip, port = kargs['ip'], kargs['port']
        return ip, port, self.username, self.session
    
class ClassiCubeAuth(SimpleAuth):
    def __init__(self, username, password):
        self.session = self.get_session(username, password)
        self.username = username

    def check_auth(self):
        login = self.session.get(api_url('/login'))
        if login.status_code != 200: return None
        login_content = login.json()
        return login_content.get('authenticated')

    def get_session(self, username, password):
        session = requests.Session()
        token = session.get(api_url("/login"))
        assert token.status_code == 200, "Login did not return OK"
        token = token.json().get('token')
        if not token:
            raise PyClassicError("Token not found.")
        
        login = session.post(api_url("/login/"),
                              data = {"username": username,
                                      "password": password,
                                      "token": token})
        text = login.json()
        if not text.get('authenticated'):
            print(text)
            errors = text.get('errors')
            error = ""
            if 'password' in errors:
                error = "Invalid password."
            elif 'username' in errors:
                error = "Invalid username."
            elif 'token' in errors:
                error = "Invalid token. (what?)"
            elif 'verification' in errors:
                error = "Account must be verified."
            raise PyClassicError(error)
        return session

    def server_list(self):
        if not self.check_auth():
            raise PyClassicError("User is not authenticated.")

        servers = self.session.get(api_url("/servers"))
        return servers.json().get('servers')

    def connect(self, **kargs):
        serverlist = self.server_list()
        server = [x for x in serverlist
                  if contains_all(kargs, x)]
        if len(server) == 0:
            raise PyClassicError("Server not found")
        server = server[0]

        ip, port = server['ip'], server['port']
        username = self.username
        mppass = server.get('mppass')
        if not mppass:
            raise PyClassicError("mppass not found, is the user authenticated?")

        return ip, port, username, mppass
