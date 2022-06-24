"""
This module contains some classes useful in authentication.
"""
from pyclassic import *

class SimpleAuth:
    """
    Simple authentication by providing manually the username and the
    server salt. This is also the base class if other authentication
    classes has to be implemented.

    :param username: Username to log in with.
    :param mppass: The server salt to log in with.

    :type username: str
    :type mppass: str
    """
    def __init__(self, username, mppass):
        self.session = mppass
        self.username = username

    def connect(self, **kargs):
        """
        Provides information for :class:`PyClassic.client.Client` in
        order to connect to a server.

        :param ip: IP Address of the server
        :param port: Port of the server

        :type ip: str
        :type port: int

        :raise AssertionError: checks if an IP and a port has been
                               given.

        :return: IP, port, username and server salt.
        :rtype: (str, int, str, str)
        """
        assert "ip" in kargs and "port" in kargs
        ip, port = kargs['ip'], kargs['port']
        return ip, port, self.username, self.session
    
class ClassiCubeAuth(SimpleAuth):
    """
    Authentication class to use with a ClassiCube account. It makes
    use of the API to log in and retrieve the sever list.

    .. warning::
        Don't do like me, if you want to upload your bot somewhere,
        make sure to not expose your creds lol

    :param username: Username of the ClassiCube account
    :param password: Password of the ClassiCube account

    :type username: str
    :type password: str
    """
    def __init__(self, username, password):
        self.session = self.get_session(username, password)
        self.username = username

    def check_auth(self):
        """
        Function mostly used internally to check if the user is
        authenticated to ClassiCube.

        :return: True if the user is authenticated, otherwise False.
                 However if the status code is not 200, it returns None.
        :rtype: bool or None
        """
        login = self.session.get(api_url('/login'))
        if login.status_code != 200: return None
        login_content = login.json()
        return login_content.get('authenticated')

    def get_session(self, username, password):
        """
        Also mostly used internally, creates the session cookie and
        log in to ClassiCube servers using the API.

        :param username: Username
        :param password: Password
        :type username: str
        :type password: str

        :raise AssertionError: The requests to /api/login did not
                               returned 200 OK as status code.
        :raise pyclassic.PyClassicError: Authentication has failed.
        
        :return: Session
        :rtype: :class:`requests.Session`
        """
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
        """
        Retrieves the server list.

        :raise pyclassic.PyClassicError: User is not authenticated.

        :return: JSON response from the ClassiCube API
        :rtype: dict
        """
        if not self.check_auth():
            raise PyClassicError("User is not authenticated.")

        servers = self.session.get(api_url("/servers"))
        return servers.json().get('servers')

    def connect(self, **kargs):
        """
        Provides information for :class:`PyClassic.client.Client` in
        order to connect to a server.

        :param kargs: Server list query, can be the server name, the IP
                      or even the port. Can be multiple at once. Log in
                      to your ClassiCube account and visit
                      http://www.classicube.net/api/servers to know
                      available parameters you can use.

        :raise pyclassic.PyClassicError: Server has not been found or
                                         it failed to retrieve the
                                         mppass (server salt).

        :return: ip, port, username and mppass
                 (see :func:`pyclassic.auth.SimpleAuth.connect`)
        :rtype:  (str, int, str, str)
        """
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
