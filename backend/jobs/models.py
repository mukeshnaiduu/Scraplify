from django.db import models

class Job(models.Model):
    role = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    job_type = models.CharField(max_length=100)
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="USD")
    experience_required = models.CharField(max_length=100, null=True, blank=True)
    apply_link = models.URLField(null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    full_description = models.TextField(null=True, blank=True)
    skills_required = models.JSONField(default=list, blank=True)
    compensation = models.CharField(max_length=200, default="", blank=True)
    external_id = models.CharField(max_length=100, null=True, blank=True)
    view_details_link = models.URLField(null=True, blank=True)
    details_scraped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.role} at {self.company_name}"
