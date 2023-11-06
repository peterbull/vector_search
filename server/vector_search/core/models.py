import os
import glob
import csv

import logging

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.tokens import default_token_generator
from django.db import models
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

from pgvector.django import VectorExtension
from pgvector.django import VectorField

from vector_search.common.models import AbstractBaseModel
from vector_search.utils.sites import get_site_url

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    """Custom User model manager, eliminating the 'username' field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.

        All emails are lowercased automatically.
        """
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        logger.info(f"New user: {email}")
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create a superuser with the given email and password."""
        logger.warning(f"Creating superuser: {email}")
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["has_reset_password"] = True
        return self._create_user(email, password, **extra_fields)

    class Meta:
        ordering = ("id",)


class User(AbstractUser, AbstractBaseModel):
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(blank=True, max_length=255)
    last_name = models.CharField(blank=True, max_length=255)
    has_reset_password = models.BooleanField(default=False)
    objects = UserManager()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    def reset_password_context(self):
        return {
            "user": self,
            "site_url": get_site_url(),
            "support_email": settings.STAFF_EMAIL,
            "token": default_token_generator.make_token(self),
        }

    class Meta:
        ordering = ["email"]


# Create Job Description model
class JobDescription(AbstractBaseModel):
    """A Job Description"""

    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    language = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title
    
    @classmethod
    def import_job_description(cls):
        def get_jobs_csv():
            """Find all the CSV files in the jobs directory and return them as a generator"""
            data_directory = os.path.join(settings.BASE_DIR, "..", "data", "jobs")
            csv_paths = glob.glob(f"{data_directory}/*.csv")
            for csv_path in csv_paths:
                with open(csv_path, "r") as f:
                    yield f

        for csvfile in get_jobs_csv():
            print(f"Loading {csvfile.name}...")
            start_time = time.time()

            csvreader = csv.DictReader(csvfile, delimiter=",")

            job_descriptions = []
            for row in csvreader:
                # try:
                #     language = detect(row["description"])
                # except LangDetectException:
                #     language = ""
                job_descriptions.append(
                    cls(
                        title=row["title"],
                        company=row["company"],
                        location=row["location"],
                        description=row["description"],
                        skills=row["skills"],
                        # language=language,
                    )
                )

            cls.objects.bulk_create(job_descriptions)

            print(f"    Loaded in {time.time() - start_time} seconds.")

    @classmethod
    def detect_languages(cls):
        def get_job_descriptions():
            page_size = 1000
            num_pages = cls.objects.count() // page_size + 1
            for page in range(num_pages):
                qs = cls.objects.filter(language="")[page * page_size: (page + 1) * page_size]
                for job_description in qs:
                    yield job_description

        count = 0
        total_jds = cls.objects.filter(language="").count()
        for job_description in get_job_descriptions():
            count += 1
            print(f"Detecting language for JD #{count} of {total_jds}...")
            try:
                language = detect(job_description.description)
            except LangDetectException:
                language = ""
            job_description.language = language
            job_description.save()

class JobDescriptionChunk(AbstractBaseModel):
    job_description = models.ForeignKey(
        JobDescription, on_delete=models.CASCADE, related_name="chunks"
    )
    chunk = models.TextField()
    embedding = VectorField(dimensions=384)

    def __str__(self):
        return f"{self.job_description.title} - {self.chunk_type} - {self.chunk[:50]}"
