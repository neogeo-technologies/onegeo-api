from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.test import tag

from django.test import TestCase

from onegeo_api.models import Source
from onegeo_api.models import Resource
from onegeo_api.models import Context
from onegeo_api.models import Alias
from onegeo_api.utils import check_uri

import base64
import json
from re import search


class ApiItemsMixin(object):

    def create_user(self, name, email, password):
        return User.objects.create_user(name, email, password)

    def create_users(self):
        self.user1 = self.create_user("user1", "bob@loblow.com", "passpass")
        self.user2 = self.create_user("user2", "jack@.com", "passpass")

    def create_source(self, name, user, uri):
        uri = check_uri(uri)
        alias = Alias.objects.create(model_name="Source")
        src = Source.objects.create(name=name, user=user, uri=uri, alias=alias)
        return src

    def basic_auth(self, client, str_cred):
        credentials = base64.b64encode(bytes(str_cred, 'utf8')).decode('utf8')
        client.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials


@tag('unauthentified')
class BasicAuthTest(ApiItemsMixin, TestCase):
    def setUp(self):
        self.create_users()
        self.source1 = self.create_source('lyvia1', self.user2, 'file:///LYVIA')
        self.resource1 = Resource.objects.filter(source=self.source1).last()
        self.basic_auth(self.client, 'user1:poussepousse')

    def test_login_source_detail(self):
        response = self.client.get("/sources/{}/".format(self.source1.alias.handle))
        self.assertEqual(response.status_code, 401)

    def test_login_source_list(self):
        response = self.client.get("/sources")
        self.assertEqual(response.status_code, 401)

    # def test_login_action(self):
    #     response = self.client.get(reverse("action"))
    #     self.assertEqual(response.status_code, 401)
    #
    def test_login_context_detail_task_view_list(self):
        response = self.client.get("/indexes/abc123abc/tasks/")
        self.assertEqual(response.status_code, 401)

    def test_login_context_detail_task_view_detail(self):
        response = self.client.get("/indexes/abc123abc/tasks/1/")
        self.assertEqual(response.status_code, 401)

    def test_login_context_detail(self):
        response = self.client.get("/indexes/abc123")
        self.assertEqual(response.status_code, 401)

    def test_login_context_list(self):
        response = self.client.get("/indexes/")
        self.assertEqual(response.status_code, 401)

    def test_login_context_create(self):
        body = {
            "name": "ctx_radie1",
            "resources": ["/sources/123a465b/resources/123a465b"]
            }
        response = self.client.post("/indexes/", data=json.dumps(body), content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_login_seamod_detail_search(self):
        response = self.client.get("/services/abc123abc/search/")
        self.assertEqual(response.status_code, 401)

    def test_login_seamod_detail(self):
        response = self.client.get("/services/abc123abc")
        self.assertEqual(response.status_code, 401)

    def test_login_seamod_list(self):
        response = self.client.get("/services/")
        self.assertEqual(response.status_code, 401)

    def test_login_source_detail_resource_detail(self):
        response = self.client.get("/sources/abc123abc/resources/cde123cde/")
        self.assertEqual(response.status_code, 401)

    def test_login_source_detail_resources(self):
        response = self.client.get("/sources/abc123abc/resources/")
        self.assertEqual(response.status_code, 401)

    def test_login_directories(self):
        response = self.client.get("/sources_directories/")
        self.assertEqual(response.status_code, 401)

    def test_login_task_detail(self):
        response = self.client.get("/tasks/1/")
        self.assertEqual(response.status_code, 401)

    def test_login_task_list(self):
        response = self.client.get("/tasks/")
        self.assertEqual(response.status_code, 401)


@tag('authentified')
class SourceTestAuthent(ApiItemsMixin, TestCase):

        def setUp(self):
            self.create_users()
            self.source2 = self.create_source('src_raad', self.user1, 'file:///RAAD')
            self.resource2 = Resource.objects.filter(source=self.source2).last()
            self.basic_auth(self.client, 'user1:passpass')

        def test_sources(self):
            response = self.client.get(reverse("api:source_list"))
            self.assertEqual(response.status_code, 200)

        def test_login_source_detail(self):
            response = self.client.get("/sources/{}/".format(self.source2.alias.handle))
            self.assertEqual(response.status_code, 200)

        def test_login_source_detail_resources(self):
            response = self.client.get("/sources/{}/resources/{}".format(self.source2.alias.handle, self.resource2.alias.handle))
            self.assertEqual(response.status_code, 200)

        def test_create_source_w_alias(self):

            body = {
                "uri": "file:///LYVIA",
                "mode": "pdf",
                "name": "lyvia",
                "alias": "lyvia_is_source"
                }
            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            location = search('^http://testserver/sources/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.get("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 200)

        def test_create_source_wo_alias(self):

            body = {
                "uri": "file:///LYVIA",
                "mode": "pdf",
                "name": "lyvia"
                }
            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            location = search('^http://testserver/sources/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.get("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 200)

        def test_create_source_repeated_alias(self):

            body = {
                "uri": "file:///LYVIA",
                "mode": "pdf",
                "name": "lyvia",
                "alias": "lyvia_is_source"
                }

            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)

            location = search('^http://testserver/sources/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.get("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 200)

            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 409)

        def test_create_source_uri_repetitas(self):
            body = {
                "uri": "file:///RAAD",
                "mode": "pdfo",
                "name": "raado"
                }
            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 400)

            response = self.client.get("/sources")
            self.assertEqual(len(response.json()), 1)

        def test_delete_source_w_alias(self):
            alias = "lyvia_is_source"
            body = {
                "uri": "file:///LYVIA",
                "mode": "pdf",
                "name": "lyvia",
                "alias": alias
                }
            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            response = self.client.get("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 200)
            response = self.client.delete("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 204)
            alias_still_exists = Alias.objects.filter(handle=alias, model_name="Source").exists()
            self.assertEqual(alias_still_exists, False)

        def test_delete_source_wo_alias(self):

            body = {
                "uri": "file:///LYVIA",
                "mode": "pdf",
                "name": "lyvia"
                }
            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            location = search('^http://testserver/sources/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.get("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 200)
            response = self.client.delete("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 204)
            alias_still_exists = Alias.objects.filter(handle=alias, model_name="Source").exists()
            self.assertEqual(alias_still_exists, False)


@tag('authentified')
class ContextTestAuthent(ApiItemsMixin, TestCase):

        def setUp(self):
            self.create_users()
            self.source2 = self.create_source('src_raad', self.user1, 'file:///RAAD')
            self.resource2 = Resource.objects.filter(source=self.source2).last()
            self.basic_auth(self.client, 'user1:passpass')

        def test_context_create_and_update(self):
            # Create
            data = {
                "name": "context_test2",
                "resource": ["/sources/{}/resources/{}".format(self.source2.alias.handle, self.resource2.alias.handle)]
                }
            response = self.client.post("/indexes", data=json.dumps(data), content_type="application/json")
            self.assertEqual(response.status_code, 201)

            # get detailed context
            location = search('^http://testserver/indexes/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)

            # Update
            response = self.client.get("/indexes")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()[0]['name'], "context_test2")
            self.context = Context.objects.get(alias=alias)
            updated_alias = "updated_alias"

            data = {
                "location": "/indexes/{}".format(self.context.alias),
                "alias": "{}".format(updated_alias),
                "resource": ["/sources/{}/resources/{}".format(self.source2.alias.handle, self.resource2.alias.handle)],
                "reindex_frequency": "monthly",
                "columns": [
                    {
                        "type": "pdf",
                        "occurs": [
                            1,
                            1
                            ],
                        "analyzer": None,
                        "pattern": None,
                        "search_analyzer": None,
                        "rejected": False,
                        "alias": None,
                        "searchable": False,
                        "count": None,
                        "weight": None,
                        "name": "data"
                        }
                    ],
                "name": "context_test2"
                }

            response = self.client.put("/indexes/{}".format(alias), data=json.dumps(data), content_type="application/json")
            self.assertEqual(response.status_code, 204)
            response = self.client.get("/indexes/{}".format("updated_alias"))
            self.assertEqual(response.status_code, 200)
            # response = self.client.get("/indexes/{}".format("updated_alia"))
            # self.assertEqual(response.status_code, 200)
            # response = self.client.get("/indexes/{}".format("updated_alias2"))
            # self.assertEqual(response.status_code, 404)
            response = self.client.get("/indexes/{}".format(updated_alias))
            self.assertEqual(response.status_code, 200)

@tag('authentified')
class TokenFilterTestAuthent(ApiItemsMixin, TestCase):

        def setUp(self):
            self.create_users()
            self.basic_auth(self.client, 'user1:passpass')

        def test_create_filter_w_alias(self):
            alias_filter = "alias_filter"
            body = {
                "name": "filter_name",
                "config": {"one": 1, "two": True, "three": "abc", "four": [1, "2", False]},
                "alias": alias_filter
                }
            response = self.client.post("/tokenfilters", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            location = search('^http://testserver/tokenfilters/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.get("/tokenfilters/{}".format(alias))
            self.assertEqual(response.status_code, 200)
            response = self.client.get("/tokenfilters/{}".format(alias_filter))
            self.assertEqual(response.status_code, 200)

        def test_create_filter_wo_alias(self):

            body = {
                "name": "filter_name1",
                "config": {"one": 1, "two": True, "three": "abc", "four": [1, "2", False]},
                "alias": None
                }
            response = self.client.post("/tokenfilters", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            location = search('^http://testserver/tokenfilters/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.get("/tokenfilters/{}".format(alias))
            self.assertEqual(response.status_code, 200)

        def test_create_filter_w_alias_repeated(self):
            alias_filter = "alias_filter"
            body = {
                "name": "filter_name_1",
                "config": {"one": 1, "two": True, "three": "abc", "four": [1, "2", False]},
                "alias": alias_filter
                }
            response = self.client.post("/tokenfilters", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)

            response = self.client.get("/tokenfilters/{}".format(alias_filter))
            self.assertEqual(response.status_code, 200)

            body = {
                "name": "filter_name2",
                "config": {"one": 1, "two": True, "three": "abc", "four": [1, "2", False]},
                "alias": alias_filter
                }
            response = self.client.post("/tokenfilters", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 409)
