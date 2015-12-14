from django.test import TestCase


class TestSaveShardHandler(TestCase):

    def test_shard_is_set(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create(username='test', password='test')
        self.assertIsNotNone(user.shard)
