from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from .models import Competition, Participant, Applicant
from ..users.models import Account


class ApplicationViewSetTestCase(APITestCase):
    URL_PREFIX = "/api/applications"

    @classmethod
    def setUpTestData(cls):
        creator = Account.objects.create_user(
            email="user1@example", password="password", username="user1"
        )
        other_account = Account.objects.create_user(
            email="user2@example", password="password", username="user2"
        )
        cls.participant_account = Account.objects.create_user(
            email="user3@example", password="password", username="user3"
        )
        cls.applicant_account = Account.objects.create_user(
            email="user4@example", password="password", username="user4"
        )

        cls.competition = Competition.objects.create(
            creator=creator, title="Test Competition"
        )
        cls.token = AccessToken.for_user(other_account)
        Participant.objects.create(
            account=cls.participant_account,
            competition=cls.competition,
            order=1,
            displayed_name="participant1",
            hidden_name="participant1",
        )
        participant = Participant(
            competition=cls.competition,
            order=2,
            displayed_name="participant1",
            hidden_name="participant1",
            access_id="test-access-id1",
            access_password="<PASSWORD>",
        )
        participant.set_password("password")
        participant.save()
        Applicant.objects.create(
            account=cls.applicant_account,
            competition=cls.competition,
            displayed_name="applicant1",
            hidden_name="applicant1",
        )
        applicant = Applicant(
            competition=cls.competition,
            displayed_name="applicant2",
            hidden_name="applicant2",
            access_id="test-access-id2",
            access_password="password",
        )
        applicant.set_password("password")
        applicant.save()

    def test_unauthenticated_user_register(self):
        url = f"{self.URL_PREFIX}/register/"
        data = {
            "competition": self.competition.id,
            "access_id": "<EMAIL>",
            "access_password": "<PASSWORD>",
            "email": "user@example.com",
            "displayed_name": "d_name",
            "hidden_name": "h_name",
            "introduction": "hello world!",
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_unauthenticated_user_register_for_same_access_id_with_participant(self):
        url = f"{self.URL_PREFIX}/register/"
        data = {
            "competition": self.competition.id,
            "access_id": "test-access-id1",
            "access_password": "<PASSWORD>",
            "email": "user@example.com",
            "displayed_name": "d_name",
            "hidden_name": "h_name",
            "introduction": "hello world!",
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["access_id"][0], "이미 존재하는 접속 아이디입니다.")

    def test_unauthenticated_user_register_for_same_access_id_with_applicant(self):
        url = f"{self.URL_PREFIX}/register/"
        data = {
            "competition": self.competition.id,
            "access_id": "test-access-id2",
            "access_password": "<PASSWORD>",
            "email": "user@example.com",
            "displayed_name": "d_name",
            "hidden_name": "h_name",
            "introduction": "hello world!",
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["access_id"][0], "이미 존재하는 접속 아이디입니다.")

    def test_authenticated_user_register(self):
        url = f"{self.URL_PREFIX}/register/"
        data = {
            "competition": self.competition.id,
            "email": "user@example.com",
            "displayed_name": "d_name",
            "hidden_name": "h_name",
            "introduction": "hello world!",
        }
        res = self.client.post(
            url, data, headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_authenticated_user_register_with_creator(self):
        url = f"{self.URL_PREFIX}/register/"
        token = AccessToken.for_user(self.competition.creator)
        data = {
            "competition": self.competition.id,
            "email": "user@example.com",
            "displayed_name": "d_name",
            "hidden_name": "h_name",
            "introduction": "hello world!",
        }
        res = self.client.post(url, data, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        print(res.data)
        self.assertEqual(
            res.data["detail"], "대회 개최자는 참가 신청을 할 수 없습니다."
        )

    def test_authenticated_user_register_with_participant(self):
        url = f"{self.URL_PREFIX}/register/"
        token = AccessToken.for_user(self.participant_account)
        data = {
            "competition": self.competition.id,
            "email": "user@example.com",
            "displayed_name": "d_name",
            "hidden_name": "h_name",
            "introduction": "hello world!",
        }
        res = self.client.post(url, data, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_authenticated_user_register_with_applicant(self):
        url = f"{self.URL_PREFIX}/register/"
        token = AccessToken.for_user(self.applicant_account)
        data = {
            "competition": self.competition.id,
            "email": "user@example.com",
            "displayed_name": "d_name",
            "hidden_name": "h_name",
            "introduction": "hello world!",
        }
        res = self.client.post(url, data, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_unauthenticated_user_check(self):
        url = f"{self.URL_PREFIX}/check/"
        data = {
            "competition": self.competition.id,
            "access_id": "test-access-id2",
            "access_password": "password",
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_unauthenticated_user_check_with_invalid_password(self):
        url = f"{self.URL_PREFIX}/check/"
        data = {
            "competition": self.competition.id,
            "access_id": "test-access-id2",
            "access_password": "password23",
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["access_password"][0], "접속 비밀번호를 확인해주세요."
        )

    def test_authenticated_user_check(self):
        url = f"{self.URL_PREFIX}/check/"
        token = AccessToken.for_user(self.applicant_account)
        data = {
            "competition": self.competition.id,
        }
        res = self.client.post(url, data, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
