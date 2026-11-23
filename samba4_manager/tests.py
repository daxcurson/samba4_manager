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

    # One group, with two members, for the group edit page.
    GROUP_ID = 'cc' * 16
    group_updates = []
    refuse_with = None

    def get_group_by_objectguid(self, objectguid):
        from samba_server import guid_base_dn
        from samba4_manager.model import Group
        guid_base_dn(objectguid)  # rejects invalid ids, like the real one
        if objectguid != self.GROUP_ID:
            return None
        group = Group('staff', 'CN=staff,CN=Users,DC=test,DC=lan')
        group.objectguid = objectguid
        group.description = 'Staff <b>members</b>'
        group.scope = 'Global'
        group.group_type = 'Security'
        group.members = ['CN=ana,CN=Users,DC=test,DC=lan', 'CN=pepe,CN=Users,DC=test,DC=lan']
        return group

    def update_group(self, objectguid, description, add_member_names=(), remove_member_dns=()):
        from samba_server import SambaError
        if FakeSambaServer.refuse_with:
            raise SambaError(FakeSambaServer.refuse_with)
        FakeSambaServer.group_updates.append({
            'acting_as': self.username, 'objectguid': objectguid,
            'description': description, 'add': list(add_member_names),
            'remove': list(remove_member_dns)})

    searches = []
    created = []
    CONTAINERS = ['CN=Users,DC=test,DC=lan', 'OU=Sales,DC=test,DC=lan']
    NEW_GROUP_ID = 'ee' * 16

    def listar_contenedores(self):
        return list(self.CONTAINERS)

    def listar_grupos(self):
        return []

    def listar_ous(self):
        return [('DC=test,DC=lan', 'DC=test,DC=lan', 0),
                ('OU=Empresa,DC=test,DC=lan', 'Empresa', 1),
                ('OU=Ventas\\, Norte,OU=Empresa,DC=test,DC=lan', 'Ventas, Norte', 2)]

    def crear_ou(self, name, parent, description=''):
        from samba_server import SambaError
        if FakeSambaServer.refuse_with:
            raise SambaError(FakeSambaServer.refuse_with)
        FakeSambaServer.created.append({'kind': 'ou', 'acting_as': self.username, 'name': name,
                                        'parent': parent, 'description': description})
        return 'OU=%s,%s' % (name, parent)

    def crear_usuario(self, username, password, container, given_name='', surname='',
                      description='', must_change_password=True, enabled=True):
        from samba_server import SambaError
        if FakeSambaServer.refuse_with:
            raise SambaError(FakeSambaServer.refuse_with)
        FakeSambaServer.created.append({
            'kind': 'user', 'acting_as': self.username, 'name': username, 'password': password,
            'container': container, 'given_name': given_name, 'surname': surname,
            'description': description, 'must_change_password': must_change_password,
            'enabled': enabled})

    def crear_grupo(self, name, container, scope='global', group_type='security', description=''):
        FakeSambaServer.created.append({
            'kind': 'group', 'acting_as': self.username, 'name': name, 'container': container,
            'scope': scope, 'group_type': group_type, 'description': description})
        return self.NEW_GROUP_ID

    def buscar_cuentas(self, texto, limite=20):
        FakeSambaServer.searches.append(texto)
        accounts = [
            {'name': 'pepe', 'display': 'Pepe Perez', 'type': 'user', 'dn': 'CN=pepe,CN=Users,DC=test,DC=lan'},
            {'name': 'perfiles', 'display': '', 'type': 'group', 'dn': 'CN=perfiles,CN=Users,DC=test,DC=lan'},
        ]
        return [a for a in accounts if a['name'].startswith(texto.strip())][:limite]

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


class GroupEditTests(AppTestCase):
    URL = '/editar_grupo/' + FakeSambaServer.GROUP_ID

    def setUp(self):
        super(GroupEditTests, self).setUp()
        FakeSambaServer.group_updates = []
        FakeSambaServer.refuse_with = None
        self.app = self.make_app()
        self.login(self.app, 'admin', 'pw-admin')

    def form(self):
        return self.app.get(self.URL).forms['group-form']

    def test_shows_the_group(self):
        res = self.app.get(self.URL)
        for text in ['CN=staff,CN=Users,DC=test,DC=lan', 'Global / Security',
                     'CN=ana,CN=Users,DC=test,DC=lan', 'CN=pepe,CN=Users,DC=test,DC=lan']:
            self.assertIn(text, res.text)
        self.assertEqual(res.forms['group-form']['description'].value, 'Staff <b>members</b>')

    def test_values_are_escaped(self):
        res = self.app.get(self.URL)
        self.assertNotIn('Staff <b>members</b>', res.text)
        self.assertIn('Staff &lt;b&gt;members&lt;/b&gt;', res.text)

    def test_save_changes(self):
        form = self.form()
        form['description'] = '  Office staff  '
        form['add_member'] = ' jdoe '
        form.get('remove_members', index=1).checked = True  # pepe
        res = form.submit()
        self.assertEqual(res.status_int, 302)
        self.assertEqual(FakeSambaServer.group_updates, [{
            'acting_as': 'admin', 'objectguid': FakeSambaServer.GROUP_ID,
            'description': 'Office staff', 'add': ['jdoe'],
            'remove': ['CN=pepe,CN=Users,DC=test,DC=lan']}])
        self.assertIn('The group was saved.', res.follow().text)

    def test_save_without_changes_adds_and_removes_nothing(self):
        self.form().submit()
        self.assertEqual(FakeSambaServer.group_updates[0]['add'], [])
        self.assertEqual(FakeSambaServer.group_updates[0]['remove'], [])

    def test_requires_csrf_token(self):
        self.app.post(self.URL, {'description': 'x'}, status=400)
        self.assertEqual(FakeSambaServer.group_updates, [])

    def test_cannot_remove_an_account_that_is_not_listed(self):
        form = self.form()
        res = self.app.post(self.URL, {
            'csrf_token': form['csrf_token'].value, 'description': 'x',
            'remove_members': 'CN=Administrator,CN=Users,DC=test,DC=lan'})
        self.assertEqual(res.status_int, 200)
        self.assertEqual(FakeSambaServer.group_updates, [])

    def test_missing_description_keeps_the_current_one(self):
        # Fields absent from the POST fall back to the group's current values.
        form = self.form()
        self.app.post(self.URL, {'csrf_token': form['csrf_token'].value})
        self.assertEqual(FakeSambaServer.group_updates[0]['description'], 'Staff <b>members</b>')

    def test_shows_what_samba_refused(self):
        FakeSambaServer.refuse_with = 'There is no user, group or computer named "nobody".'
        form = self.form()
        form['add_member'] = 'nobody'
        res = form.submit()
        self.assertEqual(res.status_int, 200)
        self.assertIn('There is no user, group or computer named &#34;nobody&#34;.', res.text)

    def test_unknown_group_and_invalid_id(self):
        self.app.get('/editar_grupo/' + 'dd' * 16, status=404)
        self.app.get('/editar_grupo/not-a-guid', status=400)


class AccountSearchTests(AppTestCase):
    """/buscar_cuentas feeds the suggestions of "Add member" in the group page."""

    def setUp(self):
        super(AccountSearchTests, self).setUp()
        FakeSambaServer.searches = []

    def test_returns_matching_accounts(self):
        app = self.make_app()
        self.login(app, 'admin', 'pw-admin')
        res = app.get('/buscar_cuentas', {'q': 'pep'})
        self.assertEqual(res.json, [{'name': 'pepe', 'display': 'Pepe Perez', 'type': 'user',
                                     'dn': 'CN=pepe,CN=Users,DC=test,DC=lan'}])
        self.assertEqual(app.get('/buscar_cuentas').json[1]['type'], 'group')
        self.assertEqual(FakeSambaServer.searches, ['pep', ''])

    def test_long_queries_are_cut(self):
        app = self.make_app()
        self.login(app, 'admin', 'pw-admin')
        app.get('/buscar_cuentas', {'q': 'x' * 1000})
        self.assertEqual(FakeSambaServer.searches, ['x' * 256])

    def test_requires_login(self):
        res = self.make_app().get('/buscar_cuentas', {'q': 'pep'})
        self.assertIn(b'inputPassword', res.body)  # the login page, not accounts
        self.assertEqual(FakeSambaServer.searches, [])

    def test_group_page_offers_suggestions(self):
        app = self.make_app()
        self.login(app, 'admin', 'pw-admin')
        res = app.get('/editar_grupo/' + FakeSambaServer.GROUP_ID)
        self.assertIn('list="account-suggestions"', res.text)
        self.assertIn('<datalist id="account-suggestions">', res.text)
        self.assertIn('"/buscar_cuentas"', res.text)


class AddAccountTestCase(AppTestCase):
    def setUp(self):
        super(AddAccountTestCase, self).setUp()
        FakeSambaServer.created = []
        FakeSambaServer.refuse_with = None
        self.app = self.make_app()
        self.login(self.app, 'admin', 'pw-admin')


class AddUserTests(AddAccountTestCase):
    def user_form(self):
        form = self.app.get('/agregar_usuario').forms['user-form']
        form['samaccountname'] = ' jdoe '
        form['given_name'] = 'Juan'
        form['surname'] = 'Doe'
        form['password'] = 'Secret!123'
        form['confirm_password'] = 'Secret!123'
        return form

    def test_users_list_links_to_the_form(self):
        res = self.app.get('/')
        form = [f for f in res.forms.values() if f.action == '/agregar_usuario'][0]
        self.assertEqual(form.method, 'GET')
        self.assertEqual(form.submit().status_int, 200)

    def test_form_defaults(self):
        form = self.app.get('/agregar_usuario').forms['user-form']
        self.assertEqual(form.action, '/agregar_usuario_grabar')
        self.assertEqual(form['container'].options[0][0], 'CN=Users,DC=test,DC=lan')
        self.assertTrue(form['must_change_password'].checked)
        self.assertTrue(form['enabled'].checked)

    def test_creates_the_user(self):
        form = self.user_form()
        form['container'] = 'OU=Sales,DC=test,DC=lan'
        res = form.submit()
        self.assertEqual(res.status_int, 302)
        self.assertEqual(FakeSambaServer.created, [{
            'kind': 'user', 'acting_as': 'admin', 'name': 'jdoe', 'password': 'Secret!123',
            'container': 'OU=Sales,DC=test,DC=lan', 'given_name': 'Juan', 'surname': 'Doe',
            'description': '', 'must_change_password': True, 'enabled': True}])
        self.assertIn('The user &#34;jdoe&#34; was created.', res.follow().text)

    def test_unchecked_options(self):
        form = self.user_form()
        form['must_change_password'] = False
        form['enabled'] = False
        form.submit()
        self.assertFalse(FakeSambaServer.created[0]['must_change_password'])
        self.assertFalse(FakeSambaServer.created[0]['enabled'])

    def test_passwords_must_match(self):
        form = self.user_form()
        form['confirm_password'] = 'other'
        res = form.submit()
        self.assertIn('The passwords do not match.', res.text)
        self.assertEqual(FakeSambaServer.created, [])

    def test_invalid_account_name(self):
        form = self.user_form()
        form['samaccountname'] = 'j/doe'
        res = form.submit()
        self.assertIn('It cannot contain any of these characters', res.text)
        self.assertEqual(FakeSambaServer.created, [])

    def test_container_must_be_one_of_the_list(self):
        form = self.user_form()
        fields = dict(form.submit_fields())
        fields['container'] = 'OU=Domain Controllers,DC=test,DC=lan'
        res = self.app.post('/agregar_usuario_grabar', fields)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(FakeSambaServer.created, [])

    def test_requires_csrf_token(self):
        self.app.post('/agregar_usuario_grabar', {'samaccountname': 'jdoe', 'password': 'x',
                                                  'confirm_password': 'x'}, status=400)
        self.assertEqual(FakeSambaServer.created, [])

    def test_shows_what_samba_refused_without_echoing_the_password(self):
        FakeSambaServer.refuse_with = "The password does not meet the domain's password policy."
        res = self.user_form().submit()
        self.assertEqual(res.status_int, 200)
        self.assertIn('password policy', res.text)
        self.assertNotIn('Secret!123', res.text)


class AddGroupTests(AddAccountTestCase):
    def test_groups_list_links_to_the_form(self):
        res = self.app.get('/grupos')
        form = [f for f in res.forms.values() if f.action == '/agregar_grupo'][0]
        self.assertIn('type="submit"', res.text.split('/agregar_grupo')[1][:200])
        self.assertEqual(form.submit().status_int, 200)

    def test_creates_the_group_and_opens_it(self):
        form = self.app.get('/agregar_grupo').forms['group-form']
        self.assertEqual(form['scope'].value, 'global')
        self.assertEqual(form['group_type'].value, 'security')
        form['samaccountname'] = 'Sales team'
        form['description'] = 'Everyone in sales'
        form['scope'] = 'universal'
        form['group_type'] = 'distribution'
        res = form.submit()
        self.assertEqual(res.status_int, 302)
        self.assertTrue(res.location.endswith('/editar_grupo/' + FakeSambaServer.NEW_GROUP_ID))
        self.assertEqual(FakeSambaServer.created, [{
            'kind': 'group', 'acting_as': 'admin', 'name': 'Sales team',
            'container': 'CN=Users,DC=test,DC=lan', 'scope': 'universal',
            'group_type': 'distribution', 'description': 'Everyone in sales'}])

    def test_requires_csrf_token(self):
        self.app.post('/agregar_grupo_grabar', {'samaccountname': 'x'}, status=400)
        self.assertEqual(FakeSambaServer.created, [])


class AddOUTests(AddAccountTestCase):
    def test_sidebar_links_to_the_page(self):
        self.assertIn('href="/agregar_ou"', self.app.get('/').text)

    def test_offers_the_domain_and_its_ous_as_a_tree(self):
        res = self.app.get('/agregar_ou')
        form = res.forms['ou-form']
        self.assertEqual(form.action, '/agregar_ou_grabar')
        options = form['parent'].options
        self.assertEqual([value for value, selected, text in options], [
            'DC=test,DC=lan', 'OU=Empresa,DC=test,DC=lan',
            'OU=Ventas\\, Norte,OU=Empresa,DC=test,DC=lan'])
        self.assertEqual(options[0][2], 'DC=test,DC=lan (top level)')
        self.assertEqual(options[2][2], '\u00a0' * 8 + 'Ventas, Norte')
        self.assertIn('id="ou-tree"', res.text)

    def test_creates_the_ou(self):
        form = self.app.get('/agregar_ou').forms['ou-form']
        form['name'] = ' Grupos '
        form['parent'] = 'OU=Empresa,DC=test,DC=lan'
        form['description'] = 'All the groups'
        res = form.submit()
        self.assertEqual(res.status_int, 302)
        self.assertTrue(res.location.endswith('/agregar_ou'))
        self.assertEqual(FakeSambaServer.created, [{
            'kind': 'ou', 'acting_as': 'admin', 'name': 'Grupos',
            'parent': 'OU=Empresa,DC=test,DC=lan', 'description': 'All the groups'}])
        self.assertIn('The organizational unit &#34;Grupos&#34; was created.', res.follow().text)

    def test_name_is_required(self):
        res = self.app.get('/agregar_ou').forms['ou-form'].submit()
        self.assertEqual(res.status_int, 200)
        self.assertEqual(FakeSambaServer.created, [])

    def test_parent_must_be_one_of_the_list(self):
        fields = dict(self.app.get('/agregar_ou').forms['ou-form'].submit_fields())
        fields.update(name='X', parent='CN=Users,DC=test,DC=lan')
        res = self.app.post('/agregar_ou_grabar', fields)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(FakeSambaServer.created, [])

    def test_requires_csrf_token(self):
        self.app.post('/agregar_ou_grabar', {'name': 'X', 'parent': 'DC=test,DC=lan'}, status=400)
        self.assertEqual(FakeSambaServer.created, [])

    def test_shows_what_samba_refused(self):
        FakeSambaServer.refuse_with = 'There is already an OU called "Grupos" there.'
        form = self.app.get('/agregar_ou').forms['ou-form']
        form['name'] = 'Grupos'
        res = form.submit()
        self.assertEqual(res.status_int, 200)
        self.assertIn('There is already an OU called &#34;Grupos&#34; there.', res.text)


class GroupTypeTests(unittest.TestCase):
    def test_describe_group_type(self):
        from samba_server import describe_group_type
        # groupType values as Samba stores them (signed 32-bit integers).
        self.assertEqual(describe_group_type(-2147483646), ('Global', 'Security'))
        self.assertEqual(describe_group_type(-2147483644), ('Domain local', 'Security'))
        self.assertEqual(describe_group_type(-2147483643), ('Builtin local', 'Security'))  # Administrators
        self.assertEqual(describe_group_type(8), ('Universal', 'Distribution'))


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
