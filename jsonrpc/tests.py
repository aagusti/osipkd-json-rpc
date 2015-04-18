import unittest
import transaction

from pyramid import testing

from .models import DBSession

 
class ViewLoginTest(unittest.TestCase):
    def test_view_login(self):
        from .views import view_login    
        request = testing.DummyRequest()
        result = view_login(request)
        self.assertTrue('form' in result.keys())

