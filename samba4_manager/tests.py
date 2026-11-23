import unittest
from unittest import mock

from samba4_manager.credentials import CredentialStore


class FakeClock(object):
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class CredentialStoreTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.store = CredentialStore(timeout=60, clock=self.clock)

    def test_each_login_gets_its_own_credentials(self):
        token_a = self.store.add('ana', 'pw-ana')
        token_b = self.store.add('pepe', 'pw-pepe')
        self.assertNotEqual(token_a, token_b)
        self.assertEqual(self.store.get(token_a).username, 'ana')
        self.assertEqual(self.store.get(token_a).password, 'pw-ana')
        self.assertEqual(self.store.get(token_b).username, 'pepe')
        self.assertEqual(self.store.get(token_b).password, 'pw-pepe')

    def test_unknown_or_empty_token(self):
        self.assertIsNone(self.store.get('nope'))
        self.assertIsNone(self.store.get(None))
        self.assertIsNone(self.store.get(''))

    def test_expires_after_inactivity(self):
        token = self.store.add('ana', 'pw')
        self.clock.now += 61
        self.assertIsNone(self.store.get(token))
        self.assertEqual(len(self.store), 0)

    def test_activity_extends_the_session(self):
        token = self.store.add('ana', 'pw')
        for _ in range(5):
            self.clock.now += 50
            self.assertIsNotNone(self.store.get(token))

    def test_remove(self):
        token = self.store.add('ana', 'pw')
        self.store.remove(token)
        self.assertIsNone(self.store.get(token))
        self.store.remove(token)  # removing twice is harmless
        self.store.remove(None)

    def test_expired_entries_are_purged_on_add(self):
        self.store.add('ana', 'pw')
        self.clock.now += 61
        self.store.add('pepe', 'pw')
        self.assertEqual(len(self.store), 1)

    def test_repr_hides_password(self):
        token = self.store.add('ana', 'secret-password')
        self.assertNotIn('secret-password', repr(self.store.get(token)))


ADMINS = {'admin': 'pw-admin', 'ana': 'pw-ana'}
USERS = dict(ADMINS, pepe='pw-pepe')


class FakeSambaServer(object):
    """Stands in for samba_server.SambaServer, without a real Samba."""

    def __init__(self, username, password):
        self.username = username
        self.password = password

    @classmethod
    def authenticate(cls, username, password):
        if USERS.get(username) == password:
            return cls(username, password)
        return None

    def es_miembro_de_alguno(self, group_sids):
        return self.username in ADMINS

    def get_domain(self):
        return 'DC=test,DC=lan'

    def search_root(self):
        return [{'dn': 'CN=Users,DC=test,DC=lan', 'objectguid': 'aa' * 16}]

    def search_children(self, objectguid):
        from samba_server import guid_base_dn
        guid_base_dn(objectguid)  # rejects invalid ids, like the real search
        return [{'dn': 'CN=Administrator,CN=Users,DC=test,DC=lan', 'objectguid': 'bb' * 16}]

    def listar_usuarios(self):
        # Report which credentials the request used.
        return [{'user': 'acting-as-%s' % self.username,
                 'description': 'password-ok=%s' % (USERS.get(self.username) == self.password),
                 'dn': 'CN=x', 'objectguid': b'', 'key': '00'}]


SETTINGS = {
    'samba4_manager.session_secret': 'test-session-secret',
    'samba4_manager.auth_secret': 'test-auth-secret',
}


class AppTestCase(unittest.TestCase):
    """Runs the real app with FakeSambaServer instead of Samba."""

    def setUp(self):
        patcher = mock.patch('samba4_manager.SambaServer', FakeSambaServer)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('samba4_manager.views.SambaServer', FakeSambaServer)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_app(self):
        from samba4_manager import main
        from webtest import TestApp
        return TestApp(main({}, **SETTINGS))

    def login(self, browser, username, password):
        return browser.post('/', {
            'inputUser': username,
            'inputPassword': password,
            'submitted': 'Login',
            'came_from': 'http://localhost/',
        })


class LoginTests(AppTestCase):

    def test_requires_login(self):
        res = self.make_app().get('/')
        self.assertIn(b'inputPassword', res.body)

    def test_each_user_acts_with_their_own_credentials(self):
        app = self.make_app()
        # Two browsers on the same application, logged in as different admins.
        browser_a = app
        from webtest import TestApp
        browser_b = TestApp(app.app)

        self.assertEqual(self.login(browser_a, 'admin', 'pw-admin').status_int, 302)
        self.assertEqual(self.login(browser_b, 'ana', 'pw-ana').status_int, 302)

        res_a = browser_a.get('/')
        res_b = browser_b.get('/')
        self.assertIn(b'acting-as-admin', res_a.body)
        self.assertNotIn(b'acting-as-ana', res_a.body)
        self.assertIn(b'acting-as-ana', res_b.body)
        self.assertNotIn(b'acting-as-admin', res_b.body)
        self.assertIn(b'password-ok=True', res_a.body)
        self.assertIn(b'password-ok=True', res_b.body)

    def test_password_is_not_stored_in_cookies(self):
        app = self.make_app()
        self.login(app, 'admin', 'pw-admin')
        cookies = ' '.join(app.cookies.values())
        self.assertNotIn('pw-admin', cookies)
        import base64
        for value in app.cookies.values():
            try:
                decoded = base64.urlsafe_b64decode(value.strip('"') + '==')
            except Exception:
                continue
            self.assertNotIn(b'pw-admin', decoded)

    def test_login_labels_point_at_their_fields(self):
        # The floating labels are drawn on top of the fields, so a click on a
        # field only reaches it if the label's "for" matches the field's id.
        import re
        body = self.make_app().get('/login').text
        targets = re.findall(r'<label for="([^"]+)"', body)
        self.assertIn('inputUser', targets)
        self.assertIn('inputPassword', targets)
        for target in targets:
            self.assertRegex(body, r'<input[^>]*\bid="%s"' % re.escape(target))

    def test_wrong_password(self):
        res = self.login(self.make_app(), 'admin', 'wrong')
        self.assertEqual(res.status_int, 200)
        self.assertIn(b'Failed login', res.body)

    def test_non_admin_cannot_log_in(self):
        app = self.make_app()
        res = self.login(app, 'pepe', 'pw-pepe')
        self.assertIn(b'Only domain administrators', res.body)
        self.assertIn(b'inputPassword', app.get('/').body)

    def test_restart_requires_new_login(self):
        app = self.make_app()
        self.login(app, 'admin', 'pw-admin')
        self.assertIn(b'acting-as-admin', app.get('/').body)

        # Same secrets, so the old cookies are still validly signed, but the
        # new process has no credentials for them.
        restarted = self.make_app()
        for name, value in app.cookies.items():
            restarted.set_cookie(name, value)
        res = restarted.get('/')
        self.assertIn(b'inputPassword', res.body)
        self.assertNotIn(b'acting-as-admin', res.body)

    def test_logout_forgets_credentials(self):
        app = self.make_app()
        self.login(app, 'admin', 'pw-admin')
        old_cookies = dict(app.cookies)
        app.get('/logout')
        self.assertIn(b'inputPassword', app.get('/').body)

        # Replaying the cookies from before the logout does not work either.
        from webtest import TestApp
        replay = TestApp(app.app)
        for name, value in old_cookies.items():
            replay.set_cookie(name, value)
        self.assertIn(b'inputPassword', replay.get('/').body)

    def test_auth_cookie_alone_is_not_enough(self):
        app = self.make_app()
        self.login(app, 'admin', 'pw-admin')
        from webtest import TestApp
        other = TestApp(app.app)
        other.set_cookie('auth_tkt', app.cookies['auth_tkt'])
        self.assertIn(b'inputPassword', other.get('/').body)


class AdvancedTreeTests(AppTestCase):
    """The Advanced Editing tree (jstree) loads branches from /listar_subrama."""

    def logged_in_app(self):
        app = self.make_app()
        self.login(app, 'admin', 'pw-admin')
        return app

    def test_root_returns_the_domain_node_with_its_children(self):
        res = self.logged_in_app().get('/listar_subrama', {'id': '#'})
        self.assertEqual(res.json['text'], 'DC=test,DC=lan')
        self.assertEqual([c['id'] for c in res.json['children']], ['aa' * 16])
        self.assertTrue(res.json['children'][0]['children'])  # can be expanded

    def test_branch_returns_only_its_children(self):
        # jstree expects the list of children, not the expanded node itself.
        res = self.logged_in_app().get('/listar_subrama', {'id': 'aa' * 16})
        self.assertIsInstance(res.json, list)
        self.assertEqual([c['id'] for c in res.json], ['bb' * 16])
        self.assertEqual(res.json[0]['text'], 'CN=Administrator,CN=Users,DC=test,DC=lan')

    def test_invalid_id_is_a_bad_request(self):
        app = self.logged_in_app()
        app.get('/listar_subrama', {'id': 'not-a-guid'}, status=400)
        app.get('/listar_subrama', status=400)


class GuidTests(unittest.TestCase):
    def test_guid_base_dn(self):
        from samba_server import guid_base_dn
        # Checked against a real Samba DC: the tree id of CN=LostAndFound
        # (hex of the raw objectGUID) and the GUID Samba accepts for it.
        self.assertEqual(guid_base_dn('1b8b034ad409f2469c1023a4745e87f1'),
                         '<GUID=4a038b1b-09d4-46f2-9c10-23a4745e87f1>')

    def test_guid_base_dn_rejects_invalid_ids(self):
        from samba_server import guid_base_dn
        with self.assertRaises(ValueError):
            guid_base_dn('not-a-guid')


class SambaServerReprTests(unittest.TestCase):
    def test_repr_hides_password(self):
        from samba_server import SambaServer
        self.assertNotIn('secret-password', repr(SambaServer('ana', 'secret-password')))
