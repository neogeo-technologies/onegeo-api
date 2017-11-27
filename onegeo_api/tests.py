import json

from django.test import TestCase, RequestFactory
from onegeo_api.models import Context
from onegeo_api.models import Resource
from onegeo_api.models import Source

from django.contrib.auth.models import User, AnonymousUser

# from .views import ActionView
from onegeo_api.views import ContextIDView
from onegeo_api.views import ContextView
# from onegeo_api.views import ResourceIDView
# from onegeo_api.views import ResourceView
# from onegeo_api.views import SearchModelIDView
# from onegeo_api.views import SearchModelView
# from onegeo_api.views import SearchView
from onegeo_api.views import SourceIDView
from onegeo_api.views import SourceView

from onegeo_api.utils import check_uri


class SimpleTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username='user1', email='user_test@testing.com', password='passpass')

        self.user2 = User.objects.create_user(
            username='user2', email='user_test@testing.com', password='passpass')

        full_uri = check_uri('file:///RAAD')
        self.name_source_legit = "raad0"
        Source.objects.create(uri=full_uri, user=self.user, name=self.name_source_legit)

    # TESTS SOURCES
    def test_source_get__with_anonymous_user(self):
        rf = self.factory
        request = rf.get('/api/sources/')
        request.user = AnonymousUser()
        response = SourceView.as_view()(request)
        self.assertEqual(response.status_code, 401)

    def test_source_get(self):
        rf = self.factory
        request = rf.get('/api/sources/')

        # l'authetification passe par une classe qui vérifie le contenu de META[]
        request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='  # base64(user1:passpass)

        response = SourceView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_source_post_create(self):

        # Create source
        json_str = json.dumps({
            "uri": "file:///LYVIA",
            "mode": "pdf",
            "name": "lyvia0"})
        rf = self.factory
        request = rf.post(
            '/api/sources/',
            data=json_str,
            content_type="application/json")
        request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='

        response = SourceView.as_view()(request)
        self.assertEqual(response.status_code, 201)

        src = Source.objects.filter(user=self.user, name="lyvia0")
        self.assertEqual(src.count(), 1)

        src_sum = Source.objects.filter(user=self.user)
        self.assertEqual(src_sum.count(), 2)

    def test_source_uuid_get(self):

        short_uuid = Source.objects.get(user=self.user, name=self.name_source_legit).short_uuid

        rf = self.factory
        request2 = rf.get('/api/sources/{}'.format(short_uuid))
        request2.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='  # base64(user1:passpass)

        response2 = SourceView.as_view()(request2)
        self.assertEqual(response2.status_code, 200)

    def test_source_delete(self):
        rf = self.factory

        json_str = json.dumps({
            "uri": "file:///LYVIA",
            "mode": "pdf",
            "name": "lyvia1"})
        request = rf.post(
            '/api/sources/',
            data=json_str,
            content_type="application/json")
        request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='  # base64(user1:passpass)

        response = SourceView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        src = Source.objects.get(user=self.user, name="lyvia1")

        rf2 = self.factory
        request2 = rf2.delete('/api/sources/{}'.format(src.short_uuid))
        request2.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='
        response2 = SourceIDView.as_view()(request2, uuid=str(src.short_uuid))
        self.assertEqual(response2.status_code, 204)

    # TESTS CONTEXTS
    def test_contexts_post(self):
        # Utilisation d'une source dont la creation est garentie et de sa resource liée
        # Les tests étant réaliser sans garenti d'ordre, on s'assure d'avoir un couple source/resource disponible

        src = Source.objects.get(user=self.user, name=self.name_source_legit)
        rsrc = Resource.objects.get(source=src)

        ctx_post_data = {
            "name": "ctxnewname",
            "resource": "/sources/{}/resources/{}".format(src.short_uuid, rsrc.short_uuid),
            "reindex_frequency": "daily"}

        json_str = json.dumps(ctx_post_data)
        rf = self.factory
        request = rf.post(
            '/api/contexts/',
            data=json_str,
            content_type="application/json")
        request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='

        response = ContextView.as_view()(request)
        self.assertEqual(response.status_code, 201)

        ctx = Context.objects.filter(name="ctxnewname")
        self.assertEqual(ctx.count(), 1)

    def test_context_id_get(self):
        src = Source.objects.get(user=self.user, name=self.name_source_legit)
        rsrc = Resource.objects.get(source=src)

        Context.objects.create(
            resource=rsrc,
            name="ctx_name",
            clmn_properties={"ppt1": "val1", "ppt2": "val2"})

        rf = self.factory
        request = rf.get('/api/contexts/{}'.format(rsrc.short_uuid))
        request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='

        response = ContextIDView.as_view()(request, uuid=str(rsrc.short_uuid))

        self.assertEqual(response.status_code, 200)

    def test_context_id_delete(self):
        rf = self.factory
        src = Source.objects.get(user=self.user, name=self.name_source_legit)
        rsrc = Resource.objects.get(source=src)
        ctx = Context.objects.create(resource=rsrc, name="ctx_name2", clmn_properties={"ppt1": "val1", "ppt2": "val2"})

        request = rf.delete('/api/contexts/{}'.format(ctx.short_uuid))
        request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='

        response = ContextIDView.as_view()(request, uuid=(str(ctx.short_uuid)))
        self.assertEqual(response.status_code, 204)

    def test_context_id_delete_conflict_user(self):
        rf = self.factory
        user_alt = User.objects.create_user(
            username='user_alt', email='user_test@testing.com', password='passpass')

        full_uri = check_uri('file:///LYVIA')
        Source.objects.create(uri=full_uri, user=user_alt, name="lyvia2")
        src_alt = Source.objects.get(name="lyvia2")
        rsrc = Resource.objects.get(source=src_alt)
        ctx = Context.objects.create(resource=rsrc, name="ctx_name3", clmn_properties={"ppt1": "val1", "ppt2": "val2"})

        request = rf.delete('/api/contexts/{}'.format(ctx.short_uuid))
        request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='

        response = ContextIDView.as_view()(request, uuid=(str(ctx.short_uuid)))
        self.assertEqual(response.status_code, 403)

    # def test_action_view_post(self):
    #     rf = RequestFactory()
    #     src = Source.objects.get(user=self.user, name=self.name_source_legit)
    #     rsrc = Resource.objects.filter(source=src)
    #     ppt_list = [{"name": "file", "type": "pdf", "occurs": [1, 1]},
    #                 {"name": "/LOCALISATION", "type": None, "occurs": [0, 1]},
    #                 {"name": "/DOCUMENT_REF", "type": None, "occurs": [0, 1]},
    #                 {"name": "/DOSSIER_REF", "type": None, "occurs": [0, 1]},
    #                 {"name": "/Title", "type": None, "occurs": [0, 1]},
    #                 {"name": "/CreationDate", "type": None, "occurs": [0, 1]},
    #                 {"name": "/DateSeance", "type": None, "occurs": [0, 1]}]
    #     Context.objects.create(resource=rsrc[0], name="ctx_name3", clmn_properties=ppt_list)
    #     action_post_data = {"index": "ctx_name3",
    #                         "type": "rebuild"
    #                         }
    #     json_str = json.dumps(action_post_data)
    #     request = rf.post('/api/action/',
    #                                 data=json_str,
    #                                 content_type="application/json")
    #     request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='
    #
    #     response = ActionView.as_view()(request)
    #     self.assertEqual(response.status_code, 202)
    #
    # def test_search_model_post(self):
    #     rf = RequestFactory()
    #     model_post_data = {"config":{"daadada":"dedededed"},
    #                        "contexts":["namecontext"],
    #                        "name":"modelname"
    #                        }
    #     json_str = json.dumps(model_post_data)
    #     request = rf.post('/api/models/',
    #                                 data=json_str,
    #                                 content_type="application/json")
    #     request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='
    #     response = SearchModelView.as_view()(request)
    #     self.assertEqual(response.status_code, 201)
    #
    #
    #     # Creation context avec le meme nom que le model
    #     src = Source.objects.get(user=self.user, name=self.name_source_legit)
    #     rsrc = Resource.objects.filter(source=src)
    #     ctx_post_data = {"name": "modelname",
    #                      "resource": "/sources/{}/resources/{}".format(src.id, rsrc[0].id),
    #                      "reindex_frequency": "daily"
    #                      }
    #     json_str = json.dumps(ctx_post_data)
    #     request = rf.post('/api/contexts/',
    #                                 data=json_str,
    #                                 content_type="application/json")
    #     request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='
    #
    #     response = ContextView.as_view()(request)
    #     self.assertEqual(response.status_code, 409)
    #
    #
    # def test_search_view_post(self):
    #     re = RequestFactory()
    #
    #     # context
    #     src = Source.objects.get(user=self.user, name=self.name_source_legit)
    #     rsrc = Resource.objects.filter(source=src)
    #
    #     ctx_post_data = {"name": "ctxname",
    #                      "resource": "/sources/{}/resources/{}".format(src.id, rsrc[0].id),
    #                      "reindex_frequency": "daily"
    #                      }
    #     request = re.post('/api/contexts/',
    #                         data=json.dumps(ctx_post_data),
    #                         content_type="application/json")
    #     request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='
    #     response = ContextView.as_view()(request)
    #     self.assertEqual(response.status_code, 201)
    #
    #
    #     # search model
    #     model_post_data = {"config": {"daadada": "dedededed"},
    #                        "contexts": ["ctxname"],
    #                        "name": "modelname"
    #                        }
    #     request2 = re.post('/api/models/',
    #                       data=json.dumps(model_post_data),
    #                       content_type="application/json")
    #     request2.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='
    #     response2 = SearchModelView.as_view()(request2)
    #     self.assertEqual(response2.status_code, 201)
    #
    #
    #     # Search:
    #     sm = SearchModel.objects.get(name="modelname")
    #
    #     ## request sans mode == 501
    #     request3 = re.post('/api/models/{}/search/'.format(sm.name),
    #                       {"mode" : ""},
    #                       content_type="application/json")
    #     request3.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='
    #     response3 = SearchView.as_view()(request3, name=(str(sm.name)))
    #     self.assertEqual(response3.status_code, 501)

        # request avec mode -- a completer avec données elastic search pour data
        # request4 = re.post('/api/models/{}/search/'.format(sm.name),
        #                    {"mode": "throw"},
        #                    content_type="application/json")
        # request4.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjE6cGFzc3Bhc3M='
        # response4 = SearchView.as_view()(request4, name=(str(sm.name)))
        # self.assertEqual(response4.status_code, 200)
