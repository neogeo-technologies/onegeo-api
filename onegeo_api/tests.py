from django.contrib.auth.models import User
from django.test import tag

from django.test import TestCase

from onegeo_api.models import Alias
from onegeo_api.models import IndexProfile
from onegeo_api.models import Resource
from onegeo_api.models import Source
from onegeo_api.models import Task
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

    def test_login_action(self):
        body = {
            "name": "ctx_radie1",
            "resource": "/sources/123a465b/resources/123a465b"
            }
        response = self.client.post("/action", data=json.dumps(body), content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_login_index_profile_detail_task_view_list(self):
        response = self.client.get("/indexes/abc123abc/tasks/")
        self.assertEqual(response.status_code, 401)

    def test_login_index_profile_detail_task_view_detail(self):
        response = self.client.get("/indexes/abc123abc/tasks/1/")
        self.assertEqual(response.status_code, 401)

    def test_login_index_profile_detail(self):
        response = self.client.get("/indexes/abc123")
        self.assertEqual(response.status_code, 401)

    def test_login_index_profile_list(self):
        response = self.client.get("/indexes/")
        self.assertEqual(response.status_code, 401)

    def test_login_index_profile_create(self):
        body = {
            "name": "ctx_radie1",
            "resource": "/sources/123a465b/resources/123a465b"
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

    def test_login_alias(self):
        response = self.client.get("/alias/132abc")
        self.assertEqual(response.status_code, 401)


@tag('authentified')
class SourceTestAuthent(ApiItemsMixin, TestCase):

        def setUp(self):
            self.create_users()
            self.source2 = self.create_source('src_raad', self.user1, 'file:///RAAD')
            self.resource2 = Resource.objects.filter(source=self.source2).last()
            self.basic_auth(self.client, 'user1:passpass')

        def test_sources(self):
            response = self.client.get("/sources/")
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
                "protocol": "pdf",
                "name": "lyvia",
                "alias": "lyvia_is_source"
                }
            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            location = search('^http://testserver/sources/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.get("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 200)
            response = self.client.get("/alias/{}".format(alias))
            self.assertEqual(response.status_code, 302)

            self.basic_auth(self.client, 'user2:passpass')
            response = self.client.get("/alias/{}".format(alias))
            self.assertEqual(response.status_code, 403)

        def test_create_source_resource_index_profile(self):

            body = {
                "uri": "file:///LYVIA",
                "protocol": "pdf",
                "name": "lyvia",
                "alias": "lyvia_is_source"
                }
            # Create sources an related resources
            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            location = search('^http://testserver/sources/(\S+)$', response._headers.get("location")[1])
            src_alias = location.group(1)

            # Create IndexProfiles from related resources
            response = self.client.get("/sources/{}/resources".format(src_alias))
            resources_list = response.json()
            for idx, res in enumerate(resources_list):
                ctx_alias = "index_profile_alias_{}".format(idx)
                data = {
                    "name": "index_profile_test_{}".format(idx),
                    "alias": ctx_alias,
                    "resource": res.get("location")
                    }
                response = self.client.post("/indexes", data=json.dumps(data), content_type="application/json")
                self.assertEqual(response.status_code, 201)
                get_ind = self.client.get("/indexes/{}".format(ctx_alias))
                self.assertEqual(get_ind.status_code, 200)
                get_al = self.client.get("/alias/{}".format(ctx_alias))
                self.assertEqual(get_al.status_code, 302)

                self.basic_auth(self.client, 'user2:passpass')
                response = self.client.get("/indexes/{}".format(ctx_alias))
                self.assertEqual(response.status_code, 403)
                response = self.client.get("/alias/{}".format(ctx_alias))
                self.assertEqual(response.status_code, 403)

        def test_create_source_wo_alias(self):

            body = {
                "uri": "file:///LYVIA",
                "protocol": "pdf",
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
                "protocol": "pdf",
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
                "protocol": "pdfo",
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
                "protocol": "pdf",
                "name": "lyvia",
                "alias": alias
                }
            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            response = self.client.get("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 200)
            response = self.client.delete("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 204)

            source_still_exists = Source.objects.filter(alias__handle=alias).exists()
            alias_still_exists = Alias.objects.filter(handle=alias, model_name="Source").exists()
            task_still_exists = Task.objects.filter(alias__handle=alias).exists()
            self.assertEqual(source_still_exists, False)
            self.assertEqual(alias_still_exists, False)
            self.assertEqual(task_still_exists, False)

        def test_delete_source_wrong_user(self):

            body = {
                "uri": "file:///LYVIA",
                "protocol": "pdf",
                "name": "lyvia"}

            response = self.client.post("/sources", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            location = search('^http://testserver/sources/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.get("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 200)

            self.basic_auth(self.client, 'user2:passpass')
            response = self.client.delete("/sources/{}".format(alias))
            self.assertEqual(response.status_code, 403)

            source_still_exists = Source.objects.filter(alias__handle=alias).exists()
            alias_still_exists = Alias.objects.filter(handle=alias, model_name="Source").exists()
            task_still_exists = Task.objects.filter(alias__handle=alias).exists()

            self.assertEqual(source_still_exists, True)
            self.assertEqual(alias_still_exists, True)
            self.assertEqual(task_still_exists, True)


@tag('authentified')
class IndexProfileTestAuthent(ApiItemsMixin, TestCase):

        def setUp(self):
            self.create_users()
            self.source2 = self.create_source('src_raad', self.user1, 'file:///RAAD')
            self.resource2 = Resource.objects.filter(source=self.source2).last()
            self.basic_auth(self.client, 'user1:passpass')

        def test_index_profile_create_and_update(self):
            # Create
            data = {
                "name": "index_profile_test2",
                "resource": "/sources/{}/resources/{}".format(self.source2.alias.handle, self.resource2.alias.handle)
                }
            response = self.client.post("/indexes", data=json.dumps(data), content_type="application/json")
            self.assertEqual(response.status_code, 201)

            # get detailed IndexProfile
            location = search('^http://testserver/indexes/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)

            # Update
            response = self.client.get("/indexes")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()[0]['name'], "index_profile_test2")

            self.index_profile = IndexProfile.objects.get(alias__handle=alias)
            updated_alias = "updated_alias"

            data = {
                "location": "/indexes/{}".format(self.index_profile.alias),
                "alias": updated_alias,
                "resource": "/sources/{}/resources/{}".format(self.source2.alias.handle, self.resource2.alias.handle),
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
                "name": "index_profile_test2"
                }

            response = self.client.put("/indexes/{}".format(alias), data=json.dumps(data), content_type="application/json")
            self.assertEqual(response.status_code, 204)
            response = self.client.get("/indexes/{}".format("updated_alias"))
            self.assertEqual(response.status_code, 200)
            response = self.client.get("/indexes/{}".format(updated_alias))
            self.assertEqual(response.status_code, 200)
            response = self.client.get("/alias/{}".format(updated_alias))
            self.assertEqual(response.status_code, 302)

        def test_index_profile_create_and_delete(self):
            data = {
                "name": "index_profile_test2",
                "resource": "/sources/{}/resources/{}".format(self.source2.alias.handle, self.resource2.alias.handle)
                }
            response = self.client.post("/indexes", data=json.dumps(data), content_type="application/json")
            self.assertEqual(response.status_code, 201)

            location = search('^http://testserver/indexes/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.get("/indexes/{}".format(alias))
            self.assertEqual(response.status_code, 200)

            response = self.client.delete("/indexes/{}".format(alias))
            self.assertEqual(response.status_code, 204)


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

        def test_create_filter_w_alias_delete(self):
            alias_filter = "alias_filter"
            body = {
                "name": "filter_name",
                "config": {"one": 1, "two": True, "three": "abc", "four": [1, "2", False]},
                "alias": alias_filter
                }
            response = self.client.post("/tokenfilters", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            response = self.client.delete("/tokenfilters/{}".format(alias_filter))
            self.assertEqual(response.status_code, 204)

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

        def test_create_filter_wo_alias_delete(self):

            body = {
                "name": "filter_name1",
                "config": {"one": 1, "two": True, "three": "abc", "four": [1, "2", False]},
                "alias": None
                }
            response = self.client.post("/tokenfilters", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            location = search('^http://testserver/tokenfilters/(\S+)$', response._headers.get("location")[1])
            alias = location.group(1)
            response = self.client.delete("/tokenfilters/{}".format(alias))
            self.assertEqual(response.status_code, 204)

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
